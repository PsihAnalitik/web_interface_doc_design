"""M-05 run_log: append-only журнал прогонов узлов (TSK-0501, NFR-03/04)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from workshop.result import Err, Ok, Result

LOG_IO_ERROR = "LOG_IO_ERROR"


@dataclass(frozen=True)
class RunRecord:
    node_id: str
    iteration: int
    prompt: str
    input_ref: str
    params: dict[str, object] = field(default_factory=dict)
    response: str = ""
    # TSK-0402: вызовы инструментов узла «имя(аргументы) → результат»;
    # дефолт пуст — старые записи jsonl совместимы
    tool_trace: list[str] = field(default_factory=list)
    # usage провайдера (prompt_tokens/completion_tokens) — метрики стоимости
    # прогонов; дефолт пуст — старые записи jsonl совместимы
    usage: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RunRef:
    path: str
    line_number: int


class RunLog:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> str:
        return str(self._path)

    def append(self, record: RunRecord) -> Result[RunRef]:
        entry = asdict(record)
        entry["logged_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            with self._path.open("r", encoding="utf-8") as stream:
                line_number = sum(1 for _ in stream)
        except OSError as exc:
            return Err(LOG_IO_ERROR, str(exc))
        return Ok(RunRef(path=str(self._path), line_number=line_number))
