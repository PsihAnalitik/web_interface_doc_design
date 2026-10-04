"""Offline acceptance checks for source boundaries and cross-stage provenance."""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_factory_baseline.catalog import Check, PassportField
from agent_factory_baseline.inputs import Source, load_sources, wire_json
from agent_factory_baseline.models import Evidence, Extraction, FieldVerdict, Synthesis
from agent_factory_baseline.validation import (
    validate_extraction,
    validate_synthesis,
    validate_verdict,
)


@pytest.fixture
def fields():
    return (
        PassportField("data", "Data", (
            Check("data.access", "Find access restrictions", "Check available operations"),
            Check("data.quality", "Find quality evidence", "Check known data quality"),
        )),
        PassportField("team", "Team", (
            Check("team.experience", "Find past delivery", "Check relevant experience"),
            Check("team.availability", "Find allocation", "Check available capacity"),
        ), ("data",)),
    )


@pytest.fixture
def sources():
    return {
        "customer": Source(
            "customer", "customer", "customer.md",
            "# Request\n\nCRM supports read-only queries.\n", "customer-digest",
        ),
        "team": Source(
            "team", "team", "team.md",
            "# Team\nImplemented an analogous agent.\n", "team-digest",
        ),
    }


@pytest.fixture
def extractions():
    return {
        "data": Extraction.model_validate({
            "field_id": "data",
            "items": [
                {"check_id": "data.access", "status": "found", "evidence": [{
                    "id": "data.e1", "source_id": "customer",
                    "start_line": 3, "end_line": 3,
                    "quote": "CRM supports read-only queries.",
                }]},
                {"check_id": "data.quality", "status": "not_found", "evidence": []},
            ],
        }),
        "team": Extraction.model_validate({
            "field_id": "team",
            "items": [
                {"check_id": "team.experience", "status": "found", "evidence": [{
                    "id": "team.e1", "source_id": "team",
                    "start_line": 2, "end_line": 2,
                    "quote": "Implemented an analogous agent.",
                }]},
                {"check_id": "team.availability", "status": "not_found", "evidence": []},
            ],
        }),
    }


@pytest.fixture
def verdicts(fields):
    return {
        field.id: FieldVerdict.model_validate({
            "field_id": field.id,
            "checks": [
                {"check_id": field.checks[0].id, "status": "satisfied",
                 "reason": "Explicit source information is available.",
                 "evidence_ids": [field.id + ".e1"]},
                {"check_id": field.checks[1].id, "status": "insufficient_data",
                 "reason": "The document supplies no information for this criterion.",
                 "evidence_ids": []},
            ],
            "findings": [{
                "id": field.id + ".f1", "check_ids": [field.checks[1].id],
                "severity": "major", "statement": "A required condition is unknown.",
                "question": "Can this condition be clarified?", "evidence_ids": [],
            }],
        })
        for field in fields
    }


@pytest.fixture
def synthesis():
    return Synthesis.model_validate({
        "summary": "Clarify the conditions for applying the team's experience.",
        "field_ids": ["data", "team"],
        "findings": [{
            "id": "overall.f1", "kind": "cross_section", "severity": "major",
            "statement": "Data suitability and team availability remain unconfirmed.",
            "question": "Who can verify data suitability and when are they available?",
            "field_ids": ["data", "team"],
            "upstream_finding_ids": ["data.f1", "team.f1"],
            "evidence_ids": ["data.e1", "team.e1"], "affected_fields": ["team"],
            "impact": "The answers determine whether the proposed work can proceed.",
        }],
        "maturity": [{
            "component": "assistant", "level": "repeat_deployment",
            "reason": "The team reports prior implementation of an analogous agent.",
            "field_ids": ["team"], "evidence_ids": ["team.e1"],
        }],
        "excluded_findings": [],
    })


def test_markdown_sources_keep_lines_roles_and_distinct_ids(tmp_path: Path):
    request = tmp_path / "request.md"
    request.write_text("# Request\n\n  Keep this spacing.\n", encoding="utf-8")
    team = tmp_path / "team.MD"
    team.write_text("# Team\nAvailable part time.\n", encoding="utf-8")

    loaded = load_sources([("customer", request), ("team", team)])

    assert len(loaded) == 2
    assert [source.role for source in loaded.values()] == ["customer", "team"]
    source = next(iter(loaded.values()))
    assert source.text == "# Request\n\n  Keep this spacing.\n"
    assert source.payload()["lines"][2] == {"number": 3, "text": "  Keep this spacing."}
    assert source.path == str(request.resolve())
    assert len(source.sha256) == 64


@pytest.mark.parametrize("suffix", [".pdf", ".docx", ".txt", ".png"])
def test_only_markdown_inputs_are_accepted(tmp_path: Path, suffix: str):
    source = tmp_path / ("request" + suffix)
    source.write_text("Plain text despite the extension", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Only \.md"):
        load_sources([("customer", source)])


@pytest.mark.parametrize("content", [
    "![diagram](diagram.png)",
    "![diagram][picture]\n\n[picture]: diagram.png",
    '<img src="diagram.png">',
    "<SVG><circle /></SVG>",
    '<picture><source srcset="diagram.png"></picture>',
    '<iframe src="https://example.invalid"></iframe>',
    '<video src="demo.mp4"></video>',
    "data:image/png;base64,AAAA",
])
def test_visual_content_requires_prior_conversion(tmp_path: Path, content: str):
    source = tmp_path / "request.md"
    source.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Visual/embedded content"):
        load_sources([("customer", source)])


def test_document_set_requires_a_customer_and_rejects_duplicates(tmp_path: Path):
    source = tmp_path / "request.md"
    source.write_text("# Request", encoding="utf-8")
    with pytest.raises(ValueError, match="customer"):
        load_sources([("team", source)])
    with pytest.raises(ValueError, match="more than once"):
        load_sources([("customer", source), ("team", source)])


def test_wire_json_preserves_template_markers_fences_and_literal_escapes():
    payload = {
        "{{NAME}}": "Keep {{NAME}}, ```json\n{}\n```, <tag>, Russian: текст",
        "nested": [{"quoted": 'The string "x" and literal \\u0060 must survive.'}],
    }
    encoded = wire_json(payload)
    assert json.loads(encoded) == payload
    assert "{{NAME}}" not in encoded
    assert "```" not in encoded
    assert "<tag>" not in encoded


def test_valid_pipeline_contracts(fields, sources, extractions, verdicts, synthesis):
    for field in fields:
        validate_extraction(extractions[field.id], field, sources)
        validate_verdict(verdicts[field.id], field, extractions[field.id])
    validate_synthesis(synthesis, fields, extractions, verdicts, sources)


@pytest.mark.parametrize("replacement", [
    {"source_id": "invented-source"},
    {"end_line": 500},
    {"start_line": 3, "end_line": 2},
    {"id": "team.fabricated"},
])
def test_extraction_rejects_fabricated_provenance(fields, sources, extractions, replacement):
    raw = extractions["data"].model_dump()
    raw["items"][0]["evidence"][0].update(replacement)
    with pytest.raises(ValueError):
        validate_extraction(Extraction.model_validate(raw), fields[0], sources)


@pytest.mark.parametrize("wording", ["Only reading is supported.", "read-only queries"])
def test_extraction_accepts_paraphrase_or_partial_quote(fields, sources, extractions, wording):
    raw = extractions["data"].model_dump()
    raw["items"][0]["evidence"][0]["quote"] = wording
    validate_extraction(Extraction.model_validate(raw), fields[0], sources)


def test_valid_range_does_not_establish_semantic_relevance(fields, sources, extractions):
    raw = extractions["data"].model_dump()
    raw["items"][0]["evidence"][0].update(start_line=1, end_line=1)
    validate_extraction(Extraction.model_validate(raw), fields[0], sources)


@pytest.mark.parametrize("replacement", [
    {"start_line": True}, {"start_line": "3"}, {"start_line": 3.0},
    {"start_line": 0}, {"quote": " \t"}, {"fabricated_score": 0.99},
])
def test_evidence_schema_rejects_coercion_and_fabricated_parameters(extractions, replacement):
    raw = extractions["data"].items[0].evidence[0].model_dump()
    raw.update(replacement)
    with pytest.raises(ValidationError):
        Evidence.model_validate(raw)


@pytest.mark.parametrize("duplicate", [False, True])
def test_extraction_requires_every_check_exactly_once(fields, sources, extractions, duplicate):
    raw = extractions["data"].model_dump()
    if duplicate:
        raw["items"].append(deepcopy(raw["items"][0]))
    else:
        raw["items"].pop()
    with pytest.raises(ValueError):
        validate_extraction(Extraction.model_validate(raw), fields[0], sources)


def test_found_and_not_found_have_distinct_evidence_contracts(fields, sources, extractions):
    raw = extractions["data"].model_dump()
    raw["items"][0]["status"] = "not_found"
    with pytest.raises(ValueError, match="not_found"):
        validate_extraction(Extraction.model_validate(raw), fields[0], sources)
    raw["items"][0]["status"] = "found"
    raw["items"][0]["evidence"] = []
    with pytest.raises(ValueError, match="found requires evidence"):
        validate_extraction(Extraction.model_validate(raw), fields[0], sources)


def test_positive_verdict_requires_facts_for_that_check(fields, extractions, verdicts):
    raw = verdicts["data"].model_dump()
    raw["checks"][1]["status"] = "satisfied"
    with pytest.raises(ValueError, match="satisfied requires"):
        validate_verdict(FieldVerdict.model_validate(raw), fields[0], extractions["data"])
    raw["checks"][1]["evidence_ids"] = ["data.e1"]
    with pytest.raises(ValueError, match="unknown references"):
        validate_verdict(FieldVerdict.model_validate(raw), fields[0], extractions["data"])


def test_verdict_cannot_borrow_another_fields_evidence(fields, extractions, verdicts):
    raw = verdicts["data"].model_dump()
    raw["checks"][0]["evidence_ids"] = ["team.e1"]
    with pytest.raises(ValueError, match="unknown references"):
        validate_verdict(FieldVerdict.model_validate(raw), fields[0], extractions["data"])


@pytest.mark.parametrize("status", ["not_satisfied", "not_applicable"])
def test_missing_information_cannot_become_a_definite_verdict(fields, extractions, verdicts, status):
    raw = verdicts["data"].model_dump()
    raw["checks"][1]["status"] = status
    with pytest.raises(ValueError, match="requires found, cited evidence"):
        validate_verdict(FieldVerdict.model_validate(raw), fields[0], extractions["data"])
    raw["checks"][1]["status"] = "insufficient_data"
    raw["checks"][0]["status"] = status
    validate_verdict(FieldVerdict.model_validate(raw), fields[0], extractions["data"])


@pytest.mark.parametrize("level", ["known_approach", "experiment", "research", "repeat_deployment"])
def test_maturity_without_evidence_stays_undetermined(
    fields, sources, extractions, verdicts, synthesis, level
):
    raw = synthesis.model_dump()
    raw["maturity"][0].update(level=level, evidence_ids=[])
    with pytest.raises(ValueError, match="requires evidence"):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)
    raw["maturity"][0]["level"] = "undetermined"
    validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)


@pytest.mark.parametrize("operation", ["drop", "unknown", "duplicate"])
def test_synthesis_must_account_for_each_local_finding_once(
    fields, sources, extractions, verdicts, synthesis, operation
):
    raw = synthesis.model_dump()
    if operation == "drop":
        raw["findings"][0]["upstream_finding_ids"].remove("team.f1")
    elif operation == "unknown":
        raw["findings"][0]["upstream_finding_ids"].append("unknown.f1")
    else:
        raw["findings"].append(dict(deepcopy(raw["findings"][0]), id="overall.f2"))
    with pytest.raises(ValueError):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)


def test_synthesis_keeps_explicit_exclusion_and_rejects_double_disposition(
    fields, sources, extractions, verdicts, synthesis
):
    raw = synthesis.model_dump()
    raw["excluded_findings"] = [{
        "finding_id": "team.f1", "reason": "Out of this agreed review scope.",
    }]
    with pytest.raises(ValueError, match="both carried and excluded"):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)
    raw["findings"][0]["upstream_finding_ids"].remove("team.f1")
    value = Synthesis.model_validate(raw)
    validate_synthesis(value, fields, extractions, verdicts, sources)
    assert value.excluded_findings[0].reason == "Out of this agreed review scope."


def test_cross_section_finding_requires_two_fields(fields, sources, extractions, verdicts, synthesis):
    raw = synthesis.model_dump()
    raw["findings"][0]["field_ids"] = ["data"]
    with pytest.raises(ValueError, match="at least two fields"):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)


def test_repeated_deployment_requires_team_evidence(fields, sources, extractions, verdicts, synthesis):
    raw = synthesis.model_dump()
    raw["maturity"][0].update(field_ids=["data"], evidence_ids=["data.e1"])
    with pytest.raises(ValueError, match="requires team evidence"):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)


def test_synthesis_cannot_reference_unknown_evidence(fields, sources, extractions, verdicts, synthesis):
    raw = synthesis.model_dump()
    raw["findings"][0]["evidence_ids"].append("invented.e1")
    with pytest.raises(ValueError, match="unknown references"):
        validate_synthesis(Synthesis.model_validate(raw), fields, extractions, verdicts, sources)
