"""Web queue contracts without network calls or paid model execution."""
import json
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "case-finder-main/server"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor/workflow_ai"))

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.job_store import JobStore
from workshop.llm_client import MODEL_UNAVAILABLE, PROVIDER_ERROR, PROVIDER_QUOTA, classify_provider_failure

from agent_factory_baseline import web_api, web_worker


@pytest.fixture
def setup(tmp_path):
    store = JobStore(tmp_path / "storage")
    settings = replace(Settings.from_env(), api_users={"user": "pass"}, max_files=2,
                       max_file_size_bytes=64, max_total_upload_bytes=80)
    web_api.app.dependency_overrides[web_api.get_store] = lambda: store
    web_api.app.dependency_overrides[web_api.get_settings] = lambda: settings
    with TestClient(web_api.app) as client:
        client.auth = ("user", "pass")
        yield client, store
    web_api.app.dependency_overrides.clear()


def upload(client):
    response = client.post("/start_process", files=[("files", ("input.md", "# Original\nsource text"))])
    assert response.status_code == 202
    return response.json()["process_id"]


def test_auth_start_progress_result(setup):
    client, store = setup
    assert client.post("/start_process", auth=("bad", "bad")).status_code == 401
    pid = upload(client)
    assert client.get(f"/get_progress/{pid}", auth=("bad", "bad")).status_code == 401
    assert client.get(f"/get_result/{pid}", auth=("bad", "bad")).status_code == 401
    assert client.get(f"/get_progress/{pid}").json()["status"] == "queued"
    assert client.get(f"/get_result/{pid}").status_code == 409
    assert client.get("/get_progress/not-a-uuid").status_code == 404
    assert client.get("/get_result/not-a-uuid").status_code == 404
    assert (store.job_dir(pid) / "input/original/001.md").read_text() == "# Original\nsource text"


@pytest.mark.parametrize("files,data,code", [
    ([], {}, 422),
    ([("files", ("a.md", "ok"))], {"text": "pasted"}, 422),
    ([("files", ("a.pdf", b"pdf"))], {}, 422),
    ([("files", ("a.md", b"\xff"))], {}, 422),
    ([("files", ("a.md", "   "))], {}, 422),
    ([("files", ("a.md", b"\x00binary"))], {}, 422),
    ([("files", ("a.md", "x" * 65))], {}, 413),
    ([("files", ("a.md", "x" * 41)), ("files", ("b.md", "x" * 41))], {}, 413),
    ([("files", ("a.md", "ok"))] * 3, {}, 422),
])
def test_reject_uploads(setup, files, data, code):
    client, store = setup
    response = client.post("/start_process", files=files, data=data)
    assert response.status_code == code
    if code == 422:
        assert response.json()["detail"]["code"] == "document_rejected"
        assert response.json()["detail"]["message"]
    assert not list(store.pending_dir.iterdir())


def fake_result(output, status="completed", synthesis=True):
    (output / "sources").mkdir(parents=True)
    (output / "sources/S1.md").write_text("# Original\nactual source")
    finding = {"id": "f1", "question": "Question?", "statement": "Missing detail", "severity": "major",
               "evidence_ids": ["e1"], "field_ids": ["users"], "affected_fields": ["integrations"], "impact": "Impact"}
    result = {"status": status, "extractions": {"users": {"items": [{"evidence": [
        {"id": "e1", "source_id": "S1", "start_line": 2, "end_line": 2, "quote": "model paraphrase"}]}]}},
        "verdicts": {"users": {"findings": [finding]}}, "synthesis": None}
    if synthesis:
        result["synthesis"] = {"summary": "Summary", "findings": [finding], "maturity": []}
    (output / "result.json").write_text(json.dumps(result))


def test_worker_success_and_source_evidence(setup, monkeypatch):
    client, store = setup
    pid = upload(client)
    assert store.claim_next() == pid
    def run(documents, output, log_path):
        assert documents[0].suffix == ".md"
        fake_result(output)
        return 0
    monkeypatch.setattr(web_worker, "run_factory", run)
    web_worker.process_job(store, pid)
    assert store.read_status(pid)["status"] == "completed"
    result = client.get(f"/get_result/{pid}").json()
    assert result["kind"] == "factory" and result["status"] == "complete"
    assert result["questions"][0]["evidence"][0]["text"] == "actual source"
    assert not list(store.running_dir.iterdir())


@pytest.mark.parametrize("has_result", [False, True])
def test_worker_failure_partial_or_no_result(setup, monkeypatch, has_result):
    client, store = setup
    pid = upload(client)
    store.claim_next()
    def run(documents, output, log_path):
        if has_result:
            fake_result(output, status="failed", synthesis=False)
        return 1
    monkeypatch.setattr(web_worker, "run_factory", run)
    web_worker.process_job(store, pid)
    assert store.read_status(pid)["status"] == "failed"
    response = client.get(f"/get_result/{pid}")
    assert response.status_code == (200 if has_result else 409)
    if has_result:
        assert response.json()["status"] == "partial"


def test_worker_exception_redacted_and_restart_no_requeue(setup, monkeypatch):
    client, store = setup
    pid = upload(client)
    store.claim_next()
    def run(*args):
        raise RuntimeError("secret-token /private/path")
    monkeypatch.setattr(web_worker, "run_factory", run)
    web_worker.process_job(store, pid)
    status = store.read_status(pid)
    assert "secret" not in json.dumps(status)
    assert status["error"]["code"] == "pipeline_failed"
    interrupted = upload(client)
    store.claim_next()
    store.update_status(interrupted, "running", 5)
    web_worker.recover_interrupted(store)
    assert store.read_status(interrupted)["status"] == "failed"
    assert store.read_status(interrupted)["error"]["code"] == "interrupted"
    assert store.claim_next() is None
    assert not list(store.running_dir.iterdir())


def test_restart_preserves_completed_job(setup):
    client, store = setup
    pid = upload(client)
    store.claim_next()
    store.update_status(pid, "completed", 100)
    web_worker.recover_interrupted(store)
    assert store.read_status(pid)["status"] == "completed"


def test_cli_contract_fixed_parameters(tmp_path, monkeypatch):
    monkeypatch.delenv("FACTORY_MODEL", raising=False)
    monkeypatch.delenv("FACTORY_VERDICT_MODEL", raising=False)
    def run(command, **kwargs):
        assert command[:4] == [sys.executable, "-m", "agent_factory_baseline", "run"]
        assert command[command.index("--model") + 1] == "qwen3.7-plus"
        assert command[command.index("--verdict-model") + 1] == "qwen3.7-plus"
        assert command[command.index("--reasoning-effort") + 1] == "none"
        assert command[command.index("--max-tokens") + 1] == "32768"
        assert command.count("--document") == 2
        assert kwargs["check"] is False
        from types import SimpleNamespace
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(web_worker.subprocess, "run", run)
    assert web_worker.run_factory([tmp_path / "a.md", tmp_path / "b.md"], tmp_path / "run", tmp_path / "log") == 1


def test_nonzero_exit_cannot_mark_completed(setup, monkeypatch):
    client, store = setup
    pid = upload(client)
    store.claim_next()
    def run(documents, output, log_path):
        fake_result(output)
        return 1
    monkeypatch.setattr(web_worker, "run_factory", run)
    web_worker.process_job(store, pid)
    assert store.read_status(pid)["status"] == "failed"
    assert client.get(f"/get_result/{pid}").json()["status"] == "partial"


@pytest.mark.parametrize("status,code,expected", [
    (404, "model_not_found", MODEL_UNAVAILABLE),
    (404, None, MODEL_UNAVAILABLE),
    (400, "model_not_found", MODEL_UNAVAILABLE),
    (402, None, PROVIDER_QUOTA),
    (429, "insufficient_quota", PROVIDER_QUOTA),
    (429, "billing_hard_limit_reached", PROVIDER_QUOTA),
    (429, "rate_limit_exceeded", PROVIDER_ERROR),
    (500, None, PROVIDER_ERROR),
    (401, "invalid_api_key", PROVIDER_ERROR),
])
def test_classify_provider_failure(status, code, expected):
    assert classify_provider_failure(status, code) == expected


def test_worker_reports_distinct_public_failures(setup, monkeypatch):
    client, store = setup

    def fail(error="", log="", findings=False):
        pid = upload(client)
        store.claim_next()

        def run(documents, output, log_path):
            log_path.write_text(log, encoding="utf-8")
            if findings or error:
                if findings:
                    fake_result(output, status="failed", synthesis=False)
                    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
                else:
                    output.mkdir(parents=True)
                    result = {"status": "failed", "extractions": {}, "verdicts": {}, "synthesis": None}
                result["error"] = error or None
                (output / "result.json").write_text(json.dumps(result), encoding="utf-8")
            return 1

        monkeypatch.setattr(web_worker, "run_factory", run)
        web_worker.process_job(store, pid)
        return pid

    document = fail(log="Ошибка: Visual/embedded content in 001.md; prepare text-only Markdown first")
    document_status = store.read_status(document)
    document_body = client.get(f"/get_result/{document}")
    assert document_status["error"]["code"] == "document_rejected"
    assert document_body.status_code == 409
    assert document_body.json()["detail"] == document_status["error"]
    assert "001.md" not in document_status["error"]["message"]

    model = fail(error="NODE_FAILED: extract_acceptance: LLM_FAILED: MODEL_UNAVAILABLE: model `secret-model` model_not_found")
    model_error = store.read_status(model)["error"]
    assert model_error["code"] == "model_unavailable"
    assert client.get(f"/get_result/{model}").json()["detail"] == model_error
    assert "secret-model" not in json.dumps(model_error)

    quota = fail(
        error="NODE_FAILED: extract_acceptance: LLM_FAILED: PROVIDER_QUOTA: Error code: 402 insufficient_quota",
        findings=True,
    )
    quota_status = store.read_status(quota)["error"]
    quota_result = client.get(f"/get_result/{quota}")
    assert quota_status["code"] == "provider_quota"
    assert quota_result.status_code == 200
    assert quota_result.json()["status"] == "partial"
    assert quota_result.json()["error"] == quota_status
    assert quota_result.json()["message"] == quota_status["message"]
    assert "insufficient_quota" not in quota_status["message"]

    pipeline = fail(error="SYNTHESIS_MISSING")
    assert store.read_status(pipeline)["error"]["code"] == "pipeline_failed"
    assert client.get(f"/get_result/{pipeline}").json()["detail"]["code"] == "pipeline_failed"

    limited = fail(error="NODE_FAILED: LLM_FAILED: PROVIDER_ERROR: Error code: 429 rate_limit_exceeded")
    assert store.read_status(limited)["error"]["code"] == "pipeline_failed"


@pytest.mark.parametrize("with_passport", [True, False])
def test_web_projection_uses_saved_titles_or_legacy_ids(tmp_path, with_passport):
    result = {"status": "completed", "extractions": {}, "synthesis": {
        "summary": "Summary", "maturity": [], "findings": [{
            "id": "f1", "field_ids": ["users"], "affected_fields": ["integrations"],
            "question": "Question?", "statement": "Unknown", "severity": "major", "evidence_ids": [],
        }],
    }}
    if with_passport:
        (tmp_path / "passport.json").write_text(json.dumps({"sections": [
            {"id": "users", "title": "Историческое название"},
            {"id": "integrations", "title": "Исторические интеграции"},
        ]}))
    projected = web_worker.project_result(result, tmp_path)["questions"][0]
    assert projected["subsystem"] == ("Историческое название" if with_passport else "users")
    assert projected["affected_fields"] == (["Исторические интеграции"] if with_passport else ["integrations"])
