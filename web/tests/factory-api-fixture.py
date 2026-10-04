"""Real factory API/queue/worker; replace only paid native-model execution."""
import json
import os
from pathlib import Path
import sys
import threading

import uvicorn

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "case-finder-main/server"))
sys.path.insert(0, str(root / "vendor/workflow_ai"))

from agent_factory_baseline import web_worker
from agent_factory_baseline.web_api import app


def fixture_run(documents, output, log_path):
    text = documents[0].read_text(encoding="utf-8-sig")
    partial = "PARTIAL" in text
    count = 3 if "THREE" in text else 1
    (output / "sources").mkdir(parents=True)
    (output / "sources/S1.md").write_text(text, encoding="utf-8")
    local = [{"id": f"users.f{i}", "check_ids": ["users.roles"], "severity": "major",
              "statement": f"Unclear role {i}", "question": f"Which role {i}?", "evidence_ids": ["users.e1"]}
             for i in range(count)]
    synthesis = {"summary": "Fixture summary", "field_ids": ["users"], "findings": [
        {**finding, "kind": "local", "field_ids": ["users"], "upstream_finding_ids": [finding["id"]],
         "affected_fields": ["integrations"], "impact": "Integration access is unclear"} for finding in local],
        "maturity": [{"component": "role resolution", "level": "experiment", "reason": "Needs validation",
                      "field_ids": ["users"], "evidence_ids": ["users.e1"]}], "excluded_findings": []}
    result = {"status": "failed" if partial else "completed", "error": "fixture failure" if partial else None,
              "extractions": {"users": {"field_id": "users", "items": [
                  {"check_id": "users.roles", "status": "found", "evidence": [
                      {"id": "users.e1", "source_id": "S1", "start_line": 2, "end_line": 2,
                       "quote": "Model paraphrase, deliberately different from original"}]}]}},
              "verdicts": {"users": {"field_id": "users", "checks": [], "findings": local}},
              "synthesis": None if partial else synthesis}
    (output / "result.json").write_text(json.dumps(result), encoding="utf-8")
    log_path.write_text("Offline deterministic execution fixture\n", encoding="utf-8")
    return 1 if partial else 0


if __name__ == "__main__":
    storage = Path(os.environ["FACTORY_STORAGE_PATH"]).resolve()
    if not storage.is_relative_to(root / ".agent"):
        raise ValueError("Fixture storage must be inside this project's .agent directory")
    web_worker.run_factory = fixture_run
    threading.Thread(target=web_worker.main, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FIXTURE_PORT", "0")))
