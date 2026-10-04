"""Serial factory worker. Interrupted jobs are never automatically billed again."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time

from app.job_store import JobStore

from .catalog import FIELDS

logger = logging.getLogger(__name__)
FAILURE = "Анализ не завершён. Подробности доступны администратору."
INTERRUPTED = "Анализ прерван перезапуском сервиса; автоматический повтор отключён."


def project_result(result: dict, run_dir: Path) -> dict | None:
    """Expose accepted findings and original excerpts, never server paths or traces."""
    synthesis = result.get("synthesis")
    complete = result.get("status") == "completed" and bool(synthesis)
    evidence = {}
    for extraction in result.get("extractions", {}).values():
        for item in extraction["items"]:
            for entry in item["evidence"]:
                # Source IDs originate in the validated factory contract.
                source_id = entry["source_id"]
                if Path(source_id).name != source_id:
                    raise ValueError("Invalid source identifier")
                lines = (run_dir / "sources" / f"{source_id}.md").read_text(encoding="utf-8").splitlines()
                evidence[entry["id"]] = {
                    "source_id": source_id, "start_line": entry["start_line"], "end_line": entry["end_line"],
                    "text": "\n".join(lines[entry["start_line"] - 1:entry["end_line"]]),
                }
    findings = synthesis["findings"] if synthesis else [
        {**finding, "field_ids": [field_id], "affected_fields": []}
        for field_id, verdict in result.get("verdicts", {}).items() for finding in verdict["findings"]]
    if not synthesis and not findings:
        return None
    titles = {field.id: field.title for field in FIELDS}
    questions = [{
        "id": finding["id"], "text": finding["question"],
        "subsystem": ", ".join(titles.get(field, field) for field in finding["field_ids"]),
        "understanding": finding["statement"], "importance": finding.get("impact", ""),
        "severity": finding["severity"],
        "evidence": [evidence[key] for key in finding["evidence_ids"]],
        "affected_fields": [titles.get(field, field) for field in finding.get("affected_fields", [])],
    } for finding in findings]
    return {"kind": "factory", "status": "complete" if complete else "partial",
            "title": "Агентская фабрика", "summary": [synthesis["summary"]] if synthesis else [],
            "questions": questions, "maturity": [
                {key: item[key] for key in ("component", "level", "reason")}
                for item in synthesis.get("maturity", [])] if synthesis else [],
            "message": "" if complete else "Частичный результат: итоговая проверка связей не завершена."}


def run_factory(documents: list[Path], output: Path, log_path: Path) -> int:
    model = os.getenv("FACTORY_MODEL", "qwen3.7-plus")
    command = [sys.executable, "-m", "agent_factory_baseline", "run", "--output", str(output),
               "--model", model, "--verdict-model", os.getenv("FACTORY_VERDICT_MODEL", model),
               "--reasoning-effort", "none", "--max-tokens", "32768"]
    for document in documents:
        command.extend(["--document", str(document)])
    with log_path.open("w", encoding="utf-8") as log:
        return subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False).returncode


def process_job(store: JobStore, process_id: str) -> None:
    directory = store.job_dir(process_id)
    try:
        store.update_status(process_id, "running", 5)
        request = store.read_json(process_id, "request.json")
        documents = [directory / "input" / "original" / item["stored_name"] for item in request["files"]]
        output = directory / "run"
        exit_code = run_factory(documents, output, directory / "worker.log")
        result = json.loads((output / "result.json").read_text(encoding="utf-8")) if (output / "result.json").exists() else {}
        public = project_result(result, output)
        completed = exit_code == 0 and result.get("status") == "completed" and bool(result.get("synthesis"))
        if public:
            if not completed:
                public.update(status="partial", message=FAILURE)
            store.write_json(process_id, "web_result.json", public)
        store.update_status(process_id, "completed" if completed else "failed", 100, None if completed else FAILURE)
    except Exception:
        logger.exception("Factory job failed: %s", process_id)
        store.update_status(process_id, "failed", 100, FAILURE)
    finally:
        store.finish(process_id)


def recover_interrupted(store: JobStore) -> None:
    for marker in store.running_dir.glob("*.json"):
        process_id = marker.stem
        # A crash after the terminal status write must not discard a completed result.
        state = store.read_status(process_id)
        if state["status"] not in {"completed", "failed"}:
            store.update_status(process_id, "failed", 100, INTERRUPTED)
        store.finish(process_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    store = JobStore(Path(os.getenv("FACTORY_STORAGE_PATH", "/app/factory-storage")))
    recover_interrupted(store)
    while True:
        process_id = store.claim_next()
        if process_id:
            process_job(store, process_id)
        else:
            time.sleep(1)


if __name__ == "__main__":
    main()
