"""M-13 acceptance: механическая проверка приёмки FR-17 (TSK-1301).

Сверяет sha256 файлов цеха с приёмочными таблицами CHANGELOG — правка без
новой записи обнаруживается чекером, а не дисциплиной.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from workshop.result import Err, Ok, Result

CHANGELOG_NOT_FOUND = "CHANGELOG_NOT_FOUND"
NO_ACCEPTED_FILES = "NO_ACCEPTED_FILES"

# строка приёмочной таблицы: | `путь` | роль | `sha256[:16]` |
# значение `removed` вместо hash снимает путь с проверки (переезд/удаление файла)
_ROW_RE = re.compile(
    r"^\|\s*`([^`]+)`\s*\|[^|]*\|\s*`([0-9a-f]{16}|removed)`\s*\|", re.MULTILINE
)
_REMOVED = "removed"


@dataclass(frozen=True)
class AcceptanceReport:
    matched: tuple[str, ...]
    mismatched: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def is_clean(self) -> bool:
        return len(self.mismatched) == 0 and len(self.missing) == 0


def verify_acceptance(changelog_path: Path) -> Result[AcceptanceReport]:
    if not changelog_path.is_file():
        return Err(CHANGELOG_NOT_FOUND, str(changelog_path))

    text = changelog_path.read_text(encoding="utf-8")
    accepted: dict[str, str] = {}
    for rel_path, digest in _ROW_RE.findall(text):
        # WHY: поздняя запись перекрывает раннюю — действует свежая приёмка файла
        accepted[rel_path] = digest
    if not accepted:
        return Err(NO_ACCEPTED_FILES, str(changelog_path))

    base_dir = changelog_path.parent
    matched: list[str] = []
    mismatched: list[str] = []
    missing: list[str] = []
    for rel_path in sorted(accepted):
        if accepted[rel_path] == _REMOVED:
            continue
        target = base_dir / rel_path
        if not target.is_file():
            missing.append(rel_path)
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
        if actual == accepted[rel_path]:
            matched.append(rel_path)
        else:
            mismatched.append(rel_path)

    return Ok(AcceptanceReport(
        matched=tuple(matched), mismatched=tuple(mismatched), missing=tuple(missing)
    ))
