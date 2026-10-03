from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobNotFoundError(FileNotFoundError):
    pass


class JobStore:
    def __init__(self, root: Path):
        self.root = root
        self.jobs_dir = root / "jobs"
        self.pending_dir = root / "queue" / "pending"
        self.running_dir = root / "queue" / "running"
        for directory in (self.jobs_dir, self.pending_dir, self.running_dir):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_id(process_id: str) -> str:
        try:
            return str(uuid.UUID(process_id))
        except ValueError as exc:
            raise JobNotFoundError(process_id) from exc

    def job_dir(self, process_id: str) -> Path:
        return self.jobs_dir / self.validate_id(process_id)

    def create_job(
        self,
        *,
        text: str,
        files: list[tuple[str, bytes, str]],
        combined_text: str,
        question_count: int,
        language: str,
    ) -> str:
        process_id = str(uuid.uuid4())
        job_dir = self.job_dir(process_id)
        original_dir = job_dir / "input" / "original"
        parsed_dir = job_dir / "input" / "parsed"
        original_dir.mkdir(parents=True)
        parsed_dir.mkdir(parents=True)
        metadata = []
        for position, (original_name, content, parsed_text) in enumerate(
            files, start=1
        ):
            extension = Path(original_name).suffix.lower()
            stored_name = f"{position:03d}{extension}"
            (original_dir / stored_name).write_bytes(content)
            (parsed_dir / f"{position:03d}.txt").write_text(
                parsed_text, encoding="utf-8"
            )
            metadata.append(
                {
                    "original_name": original_name,
                    "stored_name": stored_name,
                    "size_bytes": len(content),
                }
            )
        (job_dir / "input" / "combined.txt").write_text(combined_text, encoding="utf-8")
        self._atomic_json(
            job_dir / "request.json",
            {
                "process_id": process_id,
                "text_supplied": bool(text.strip()),
                "files": metadata,
                "question_count": question_count,
                "language": language,
            },
        )
        now = _utc_now()
        self._atomic_json(
            job_dir / "status.json",
            {
                "process_id": process_id,
                "status": "queued",
                "progress": 0,
                "created_at": now,
                "updated_at": now,
                "error": None,
            },
        )
        self._atomic_json(
            self.pending_dir / f"{process_id}.json", {"process_id": process_id}
        )
        return process_id

    def read_status(self, process_id: str) -> dict[str, Any]:
        path = self.job_dir(process_id) / "status.json"
        if not path.exists():
            raise JobNotFoundError(process_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def read_json(self, process_id: str, name: str) -> Any:
        path = self.job_dir(process_id) / name
        if not path.exists():
            raise JobNotFoundError(process_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def update_status(
        self, process_id: str, status: str, progress: int, error=None
    ) -> None:
        current = self.read_status(process_id)
        current.update(
            status=status,
            progress=progress,
            updated_at=_utc_now(),
            error=error,
        )
        self._atomic_json(self.job_dir(process_id) / "status.json", current)

    def write_json(self, process_id: str, name: str, value: Any) -> None:
        job_dir = self.job_dir(process_id)
        if not job_dir.exists():
            raise JobNotFoundError(process_id)
        path = job_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_json(path, value)

    def claim_next(self) -> str | None:
        for source in sorted(self.pending_dir.glob("*.json")):
            target = self.running_dir / source.name
            try:
                os.replace(source, target)
            except FileNotFoundError:
                continue
            return source.stem
        return None

    def finish(self, process_id: str) -> None:
        (self.running_dir / f"{self.validate_id(process_id)}.json").unlink(
            missing_ok=True
        )

    def recover_running(self) -> None:
        for source in self.running_dir.glob("*.json"):
            process_id = source.stem
            if (self.jobs_dir / process_id).exists():
                os.replace(source, self.pending_dir / source.name)
                try:
                    self.update_status(process_id, "queued", 0)
                except JobNotFoundError:
                    pass
            else:
                source.unlink(missing_ok=True)

    def delete(self, process_id: str) -> str:
        process_id = self.validate_id(process_id)
        job_dir = self.jobs_dir / process_id
        if not job_dir.exists():
            raise JobNotFoundError(process_id)
        pending = self.pending_dir / f"{process_id}.json"
        running = self.running_dir / f"{process_id}.json"
        pending.unlink(missing_ok=True)
        if running.exists():
            self.update_status(process_id, "deletion_requested", 0)
            (job_dir / ".delete_requested").touch()
            return "deletion_requested"
        shutil.rmtree(job_dir)
        return "deleted"

    def deletion_requested(self, process_id: str) -> bool:
        return (self.job_dir(process_id) / ".delete_requested").exists()

    def delete_claimed(self, process_id: str) -> None:
        shutil.rmtree(self.job_dir(process_id), ignore_errors=True)
        self.finish(process_id)

    @staticmethod
    def _atomic_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
