"""Deterministic provenance checks, not an assessment of semantic correctness."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Protocol

from .models import Evidence, Extraction, FieldVerdict, Synthesis

if TYPE_CHECKING:
    from .catalog import PassportField


class SourceText(Protocol):
    text: str
    role: str


def _unique(values: Sequence[str], label: str) -> set[str]:
    result = set(values)
    if len(result) != len(values):
        raise ValueError(f"{label}: duplicate IDs")
    return result


def _references(
    values: Sequence[str], allowed: set[str], label: str, *, required: bool = False
) -> set[str]:
    actual = _unique(values, label)
    if required and not actual:
        raise ValueError(f"{label}: at least one reference is required")
    unknown = actual - allowed
    if unknown:
        raise ValueError(f"{label}: unknown references {sorted(unknown)}")
    return actual


def _coverage(values: Sequence[str], expected: set[str], label: str) -> None:
    actual = _unique(values, label)
    if actual != expected:
        raise ValueError(
            f"{label}: missing {sorted(expected - actual)}, "
            f"unexpected {sorted(actual - expected)}"
        )


def _field_id(actual: str, expected: str) -> None:
    if actual != expected:
        raise ValueError(f"field_id: expected {expected!r}, got {actual!r}")


def _prefixed(identifier: str, field_id: str) -> None:
    prefix = field_id + "."
    if not identifier.startswith(prefix) or not identifier[len(prefix):].strip():
        raise ValueError(f"ID {identifier!r} must start with {prefix!r} and have a suffix")


def validate_extraction(
    value: Extraction, field: PassportField, sources: Mapping[str, SourceText]
) -> None:
    """Check coverage and source ranges; model wording is not a verified quotation."""
    _field_id(value.field_id, field.id)
    _coverage(
        [item.check_id for item in value.items],
        {check.id for check in field.checks},
        f"{field.id}.items",
    )
    evidence_ids: list[str] = []
    for item in value.items:
        if item.status == "found" and not item.evidence:
            raise ValueError(f"{item.check_id}: found requires evidence")
        if item.status == "not_found" and item.evidence:
            raise ValueError(f"{item.check_id}: not_found cannot contain evidence")
        for evidence in item.evidence:
            _prefixed(evidence.id, field.id)
            evidence_ids.append(evidence.id)
            if evidence.source_id not in sources:
                raise ValueError(f"{evidence.id}: unknown source {evidence.source_id!r}")
            lines = sources[evidence.source_id].text.splitlines()
            if evidence.end_line < evidence.start_line or evidence.end_line > len(lines):
                raise ValueError(f"{evidence.id}: invalid source line range")
    _unique(evidence_ids, f"{field.id}.evidence")


def validate_verdict(
    value: FieldVerdict, field: PassportField, extraction: Extraction
) -> None:
    """Require valid local references; do not infer the truth of an LLM verdict."""
    _field_id(value.field_id, field.id)
    _field_id(extraction.field_id, field.id)
    check_ids = {check.id for check in field.checks}
    _coverage([check.check_id for check in value.checks], check_ids, f"{field.id}.checks")
    _coverage([item.check_id for item in extraction.items], check_ids, f"{field.id}.items")
    extracted = {item.check_id: item for item in extraction.items}
    evidence_ids = {evidence.id for item in extraction.items for evidence in item.evidence}
    for check in value.checks:
        item = extracted[check.check_id]
        cited = _references(
            check.evidence_ids,
            {evidence.id for evidence in item.evidence},
            f"{check.check_id}.evidence_ids",
        )
        if check.status != "insufficient_data" and (item.status != "found" or not cited):
            raise ValueError(f"{check.check_id}: {check.status} requires found, cited evidence")
    _unique([finding.id for finding in value.findings], f"{field.id}.findings")
    for finding in value.findings:
        _prefixed(finding.id, field.id)
        _references(finding.check_ids, check_ids, f"{finding.id}.check_ids", required=True)
        _references(finding.evidence_ids, evidence_ids, f"{finding.id}.evidence_ids")


def validate_synthesis(
    value: Synthesis,
    fields: tuple[PassportField, ...],
    extractions: Mapping[str, Extraction],
    verdicts: Mapping[str, FieldVerdict],
    sources: Mapping[str, SourceText],
) -> None:
    """Check global provenance and explicit disposition of every local finding."""
    field_ids = {field.id for field in fields}
    _coverage(value.field_ids, field_ids, "synthesis.field_ids")
    _coverage(list(extractions), field_ids, "extractions")
    _coverage(list(verdicts), field_ids, "verdicts")
    evidence: dict[str, Evidence] = {}
    evidence_fields: dict[str, str] = {}
    local_fields: dict[str, str] = {}
    for field in fields:
        extraction = extractions[field.id]
        verdict = verdicts[field.id]
        _field_id(extraction.field_id, field.id)
        _field_id(verdict.field_id, field.id)
        for item in extraction.items:
            for quote in item.evidence:
                if quote.id in evidence:
                    raise ValueError(f"duplicate extraction evidence ID {quote.id!r}")
                if quote.source_id not in sources:
                    raise ValueError(f"{quote.id}: unknown source {quote.source_id!r}")
                evidence[quote.id] = quote
                evidence_fields[quote.id] = field.id
        for finding in verdict.findings:
            if finding.id in local_fields:
                raise ValueError(f"duplicate local finding ID {finding.id!r}")
            local_fields[finding.id] = field.id

    _unique([finding.id for finding in value.findings], "synthesis.findings")
    carried: list[str] = []
    for finding in value.findings:
        involved = _references(
            finding.field_ids, field_ids, f"{finding.id}.field_ids", required=True
        )
        if finding.kind == "cross_section" and len(involved) < 2:
            raise ValueError(f"{finding.id}: cross_section requires at least two fields")
        if finding.kind == "local" and len(involved) != 1:
            raise ValueError(f"{finding.id}: local requires exactly one field")
        upstream = _references(
            finding.upstream_finding_ids,
            set(local_fields),
            f"{finding.id}.upstream_finding_ids",
            required=finding.kind == "local",
        )
        if any(local_fields[identifier] not in involved for identifier in upstream):
            raise ValueError(f"{finding.id}: upstream finding belongs to an undeclared field")
        cited = _references(finding.evidence_ids, set(evidence), f"{finding.id}.evidence_ids")
        if any(evidence_fields[identifier] not in involved for identifier in cited):
            raise ValueError(f"{finding.id}: evidence belongs to an undeclared field")
        _references(finding.affected_fields, field_ids, f"{finding.id}.affected_fields")
        carried.extend(finding.upstream_finding_ids)
    _unique(carried, "synthesis.upstream_finding_ids")
    excluded = [finding.finding_id for finding in value.excluded_findings]
    _references(excluded, set(local_fields), "synthesis.excluded_findings")
    overlap = set(carried) & set(excluded)
    if overlap:
        raise ValueError(f"local findings both carried and excluded: {sorted(overlap)}")
    omitted = set(local_fields) - set(carried) - set(excluded)
    if omitted:
        raise ValueError(f"local findings neither carried nor excluded: {sorted(omitted)}")
    for maturity in value.maturity:
        involved = _references(
            maturity.field_ids, field_ids, f"maturity {maturity.component}.field_ids", required=True
        )
        cited = _references(
            maturity.evidence_ids, set(evidence), f"maturity {maturity.component}.evidence_ids"
        )
        if any(evidence_fields[identifier] not in involved for identifier in cited):
            raise ValueError(
                f"maturity {maturity.component}: evidence belongs to an undeclared field"
            )
        if maturity.level != "undetermined" and not cited:
            raise ValueError(
                f"maturity {maturity.component}: {maturity.level} requires evidence"
            )
        if maturity.level == "repeat_deployment" and not any(
            sources[evidence[identifier].source_id].role == "team" for identifier in cited
        ):
            raise ValueError(
                f"maturity {maturity.component}: repeat_deployment requires team evidence"
            )
