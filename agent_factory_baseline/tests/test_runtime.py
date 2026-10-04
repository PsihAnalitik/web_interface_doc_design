"""Native factory integration; no model provider or network is used."""

import json
import subprocess

from workshop.llm_client import LLMResponse
from workshop.models import LLMParams
from workshop.result import Err, Ok

from agent_factory_baseline.catalog import Check, PassportField, FIELDS
from agent_factory_baseline.inputs import load_sources
from agent_factory_baseline.runtime import PACKAGE, ReplayLLM, execute


def fixture(tmp_path, special=False):
    path = tmp_path / "document.md"
    quote = 'Требуется только чтение. {{TOKEN}} ```json <xml> @@SOURCE_CONTEXT@@' if special else 'Требуется только чтение.'
    path.write_text(quote + "\n", encoding="utf-8")
    sources = load_sources([("customer", path)])
    field = PassportField("actions", "Действия", (Check("actions.scope", "Найти действия", "Достаточность"),), ())
    extraction = {"field_id": "actions", "items": [{"check_id": "actions.scope", "status": "found",
        "evidence": [{"id": "actions.e1", "source_id": "S1", "start_line": 1, "end_line": 1, "quote": quote}]}]}
    verdict = {"field_id": "actions", "checks": [{"check_id": "actions.scope", "status": "satisfied",
        "reason": "Режим чтения определён.", "evidence_ids": ["actions.e1"]}], "findings": []}
    synthesis = {"summary": "Чтение без выполнения действий.", "field_ids": ["actions"],
                 "findings": [], "maturity": [], "excluded_findings": []}
    replies = {"extract_actions": extraction, "verdict_actions": verdict, "synthesis": synthesis}
    return sources, field, replies


PARAMS = LLMParams(provider="openai", model="test-fixture")


def test_native_factory_roundtrip_and_provenance(tmp_path):
    sources, field, replies = fixture(tmp_path, special=True)
    client = ReplayLLM(replies)
    output = tmp_path / "run"
    result = execute(sources, output, PARAMS, client, mode="replay", fields=(field,))
    assert result["status"] == "completed"
    assert client.calls == 3
    assert result["extractions"]["actions"] == replies["extract_actions"]
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["parents"]["synthesis"] == ["extract_actions", "verdict_actions"]
    assert manifest["configuration_sha256"]
    assert manifest["sources"][0]["sha256"] == sources["S1"].sha256
    assert (output / "artifacts/verdict_actions/v1.xml").exists()
    assert 'LLM не вызывалась' in (output / "report.md").read_text()
    assert len((output / "calls.jsonl").read_text().splitlines()) == 3
    assert (output / "sources/S1.md").read_text() == sources["S1"].text


def test_reference_failure_is_reworked_before_downstream(tmp_path):
    sources, field, replies = fixture(tmp_path)

    class FirstQuoteWrong(ReplayLLM):
        def complete(self, prompt, params, tools=()):
            if self.calls == 0:
                self.calls += 1
                wrong = json.loads(json.dumps(replies["extract_actions"]))
                wrong["items"][0]["evidence"][0]["end_line"] = 999
                return Ok(LLMResponse(json.dumps(wrong)))
            if self.calls == 1:
                assert "invalid source line range" in prompt
            return super().complete(prompt, params, tools)

    client = FirstQuoteWrong(replies)
    result = execute(sources, tmp_path / "repair", PARAMS, client, mode="replay", fields=(field,))
    assert result["status"] == "completed"
    assert client.calls == 4
    assert len(json.loads((tmp_path / "repair/validation.json").read_text())) == 1


def test_persistent_invalid_output_stops_with_partial_status(tmp_path):
    sources, field, _ = fixture(tmp_path)
    client = ReplayLLM({"extract_actions": {"invented": "{{SECRET}} ```"}})
    output = tmp_path / "failed"
    result = execute(sources, output, PARAMS, client, mode="replay", fields=(field,), max_iterations=2)
    assert result["status"] == "failed"
    assert "MAX_ITERATIONS_EXCEEDED" in result["error"]
    assert client.calls == 2
    assert result["synthesis"] is None
    assert result["verdicts"] == {}
    assert "Анализ не завершён" in (output / "report.md").read_text()


def test_provider_failure_is_preserved(tmp_path):
    sources, field, _ = fixture(tmp_path)

    class Unavailable:
        def complete(self, prompt, params, tools=()):
            return Err("TIMEOUT", "fixture timeout")

    result = execute(sources, tmp_path / "unavailable", PARAMS, Unavailable(), fields=(field,))
    assert result["status"] == "failed"
    assert "TIMEOUT" in result["error"]
    assert "fixture timeout" in result["error"]


def test_plan_never_calls_client_and_cannot_overwrite(tmp_path):
    import pytest
    sources, field, replies = fixture(tmp_path)
    client = ReplayLLM(replies)
    result = execute(sources, tmp_path / "plan", PARAMS, client, mode="plan", fields=(field,))
    assert result["status"] == "planned"
    assert client.calls == 0
    with pytest.raises(FileExistsError):
        execute(sources, tmp_path / "plan", PARAMS, client, mode="plan", fields=(field,))


def test_full_demo_through_launcher(tmp_path):
    command = subprocess.run(["bash", str(PACKAGE / "run.sh"), "demo", "--output", str(tmp_path / "demo")],
                             text=True, capture_output=True)
    assert command.returncode == 0, command.stderr + command.stdout
    result = json.loads((tmp_path / "demo/result.json").read_text())
    assert result["status"] == "completed"
    assert len(result["extractions"]) == len(result["verdicts"]) == len(FIELDS) == 18
    assert result["synthesis"]["findings"]


def test_live_cli_requires_explicit_model_without_sending(tmp_path, monkeypatch, capsys):
    import pytest
    from agent_factory_baseline.__main__ import main
    monkeypatch.setattr('agent_factory_baseline.__main__.ENV_FILE', tmp_path / 'missing.env')
    monkeypatch.delenv("BASELINE_MODEL", raising=False)
    sources, _, _ = fixture(tmp_path)
    with pytest.raises(SystemExit) as failure:
        main(["run", "--document", sources["S1"].path, "--output", str(tmp_path / "not-created")])
    assert failure.value.code == 2
    assert not (tmp_path / "not-created").exists()
    assert "--model" in capsys.readouterr().err


def test_stage_models_and_disabled_reasoning_reach_native_calls(tmp_path):
    sources, field, replies = fixture(tmp_path)

    class Capture(ReplayLLM):
        def __init__(self):
            super().__init__(replies)
            self.params = []

        def complete(self, prompt, params, tools=()):
            self.params.append(params.model_dump())
            return super().complete(prompt, params, tools)

    extractor = PARAMS.model_copy(update={"model": "extractor", "reasoning_effort": "none"})
    judge = extractor.model_copy(update={"model": "judge"})
    client = Capture()
    output = tmp_path / "mixed"
    result = execute(sources, output, extractor, client, fields=(field,), verdict_params=judge)
    assert result["status"] == "completed"
    assert [p["model"] for p in client.params] == ["extractor", "judge", "judge"]
    assert all(p["reasoning_effort"] == "none" for p in client.params)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["stage_models"]["synthesis"] == judge.model_dump()
    assert manifest["elapsed_seconds"] >= 0


def test_plan_cli_exposes_judge_and_reasoning(tmp_path):
    from agent_factory_baseline.__main__ import main
    sources, _, _ = fixture(tmp_path)
    output = tmp_path / "plan-models"
    assert main(["plan", "--document", sources["S1"].path, "--model", "extractor",
                 "--verdict-model", "judge", "--reasoning-effort", "none",
                 "--output", str(output)]) == 0
    for name, model in (("extract_acceptance", "extractor"), ("verdict_acceptance", "judge"),
                        ("synthesis", "judge")):
        config = json.loads((output / "config" / (name + ".json")).read_text())
        assert config["llm"]["model"] == model
        assert config["llm"]["reasoning_effort"] == "none"


def test_paraphrase_keeps_original_context_for_judges_and_report(tmp_path):
    import re
    sources, field, replies = fixture(tmp_path, special=True)
    original = sources['S1'].text.splitlines()[0]
    replies['extract_actions']['items'][0]['evidence'][0]['quote'] = 'Модель описывает режим своими словами.'

    class InspectContext(ReplayLLM):
        def complete(self, prompt, params, tools=()):
            if '<baseline_node>extract_' not in prompt:
                context = json.loads(re.search(r'<source_context>\s*(.*?)\s*</source_context>', prompt, re.S)[1])
                assert context['originals'] == [{
                    'evidence_id': 'actions.e1', 'source_id': 'S1',
                    'start_line': 1, 'end_line': 1, 'source_text': original,
                }]
                assert context['sources'] == [sources['S1'].payload()]
                assert '<source_context>\n@@SOURCE_CONTEXT@@\n</source_context>' not in prompt
            return super().complete(prompt, params, tools)

    output = tmp_path / 'paraphrase'
    client = InspectContext(replies)
    result = execute(sources, output, PARAMS, client, mode='replay', fields=(field,))
    assert result['status'] == 'completed'
    assert client.calls == 3
    report = (output / 'report.md').read_text()
    assert 'Текст модели (пересказ или цитата)' in report
    assert 'Оригинал по ссылке (подтянут кодом)' in report
    assert 'Модель описывает режим своими словами.' in report
    assert original in report
    assert '(sources/S1.md#L1)' in report
