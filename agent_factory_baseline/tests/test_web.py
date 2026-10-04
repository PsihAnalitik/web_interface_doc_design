"""Web queue contracts without network calls or paid model execution."""
import json
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "case-finder-main/server"))

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.job_store import JobStore
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
    assert client.post("/start_process", files=files, data=data).status_code == code
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
    assert "secret" not in json.dumps(store.read_status(pid))
    interrupted = upload(client)
    store.claim_next()
    store.update_status(interrupted, "running", 5)
    web_worker.recover_interrupted(store)
    assert store.read_status(interrupted)["status"] == "failed"
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
