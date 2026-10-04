"""Strict payloads exchanged by the passport workshops."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _meaningful(value: str) -> str:
    if not value.strip():
        raise ValueError("must contain non-whitespace text")
    return value


Text = Annotated[str, AfterValidator(_meaningful)]
Severity = Literal["critical", "major", "minor"]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Payload):
    id: Text
    source_id: Text
    start_line: Annotated[int, Field(ge=1)]
    end_line: Annotated[int, Field(ge=1)]
    quote: Text = Field(description="Текст модели: пересказ или цитата. Оригинал берётся кодом по source_id и диапазону строк; совпадение формулировок не требуется.")


class ExtractedItem(Payload):
    check_id: Text
    status: Literal["found", "not_found"]
    evidence: list[Evidence]


class Extraction(Payload):
    field_id: Text
    items: list[ExtractedItem]


class CheckResult(Payload):
    check_id: Text
    status: Literal[
        "satisfied", "not_satisfied", "insufficient_data", "not_applicable"
    ]
    reason: Text
    evidence_ids: list[Text]


class LocalFinding(Payload):
    id: Text
    check_ids: list[Text]
    severity: Severity
    statement: Text
    question: Text
    evidence_ids: list[Text]


class FieldVerdict(Payload):
    field_id: Text
    checks: list[CheckResult]
    findings: list[LocalFinding]


class RankedFinding(Payload):
    id: Text
    kind: Literal["local", "cross_section"]
    severity: Severity
    statement: Text
    question: Text
    field_ids: list[Text]
    upstream_finding_ids: list[Text]
    evidence_ids: list[Text]
    affected_fields: list[Text]
    impact: Text


class Maturity(Payload):
    component: Text
    level: Literal[
        "repeat_deployment", "known_approach", "experiment", "research", "undetermined"
    ]
    reason: Text
    field_ids: list[Text]
    evidence_ids: list[Text]


class ExcludedFinding(Payload):
    finding_id: Text
    reason: Text


class Synthesis(Payload):
    summary: Text
    field_ids: list[Text]
    findings: list[RankedFinding]
    maturity: list[Maturity]
    excluded_findings: list[ExcludedFinding]
