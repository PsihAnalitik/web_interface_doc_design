"""M-18 wiki_applier: применение принятого file map страниц к wiki (TSK-1801).

Детерминированный шаг без LLM (FR-21): файлы wiki — следствие принятых артефактов.
Проверки выполняются на временной копии; отказ не оставляет частичной записи.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from workshop.codegen_loop import NO_FILE_BLOCKS, parse_file_map
from workshop.result import Err, Ok, Result
from workshop.wiki_loader import SOURCE_SUFFIX, collect_problems

APPLY_INVALID_PATH = "APPLY_INVALID_PATH"
WIKI_CHECK_FAILED = "WIKI_CHECK_FAILED"
APPLY_IO_ERROR = "APPLY_IO_ERROR"
SOURCE_SPEC_INVALID = "SOURCE_SPEC_INVALID"

_SOURCE_PAGE_RE = re.compile(r'<source_page\s+path="([^"]+)"\s+for="([^"]+)"\s*/?>')
_SOURCE_REQUEST_RE = re.compile(r"<source_request>(.*?)</source_request>", re.DOTALL)


@dataclass(frozen=True)
class ApplyReport:
    written: tuple[str, ...]
    changelog_rows: tuple[str, ...]


def extract_source_page(spec_content: str) -> Result[tuple[str, str] | None]:
    """TSK-1801 шаг 1a: страница-исходник из спеки — (path, тело) или None.

    Тело — <source_request> ВЕРБАТИМ под заголовком-провенансом:
    вербатим силами LLM ненадёжен, поэтому материализация детерминированная.
    """
    match = _SOURCE_PAGE_RE.search(spec_content)
    if match is None:
        return Ok(None)
    path, for_page = match.group(1), match.group(2)
    if not path.endswith(SOURCE_SUFFIX):
        return Err(SOURCE_SPEC_INVALID, f"path без суффикса {SOURCE_SUFFIX}: {path}")
    request = _SOURCE_REQUEST_RE.search(spec_content)
    if request is None or not request.group(1).strip():
        return Err(SOURCE_SPEC_INVALID, "<source_request> пуст или отсутствует")
    body = (
        f"# wiki: исходник — {for_page}\n\n"
        "> вербатим-приложение: полный входной текст изменения; "
        "материализовано wiki-apply из артефакта спеки (source_request), "
        "механические проверки wiki не применяются.\n\n"
        f"{request.group(1).strip()}\n"
    )
    return Ok((path, body))


def apply_file_map(
    content: str, wiki_root: Path, spec_content: str | None = None
) -> Result[ApplyReport]:
    """TSK-1801: наложить file map на wiki с полной проверкой до записи."""
    files = parse_file_map(content)
    if not files:
        return Err(NO_FILE_BLOCKS, "в артефакте нет блоков ```file:<путь>")
    if spec_content is not None:
        source = extract_source_page(spec_content)
        if isinstance(source, Err):
            return source
        if source.value is not None:
            # детерминированная версия сильнее LLM-версии из file map
            source_path, source_body = source.value
            files[source_path] = source_body

    root = wiki_root.resolve()
    for rel_path in files:
        # пути пришли из ответа LLM — недоверенный ввод (как в TSK-1102)
        if not (root / rel_path).resolve().is_relative_to(root):
            return Err(APPLY_INVALID_PATH, rel_path)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp) / "wiki"
            shutil.copytree(wiki_root, tmp_root)
            for rel_path, body in files.items():
                target = tmp_root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")

            problems = collect_problems(tmp_root)
            if isinstance(problems, Err):
                return problems
            if problems.value:
                return Err(WIKI_CHECK_FAILED, "; ".join(problems.value))

        written: list[str] = []
        for rel_path in sorted(files):
            target = wiki_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(files[rel_path], encoding="utf-8")
            written.append(rel_path)
    except OSError as exc:
        return Err(APPLY_IO_ERROR, str(exc))

    changelog_rows = tuple(
        f"| `{rel_path}` | — | "
        f"`{hashlib.sha256((wiki_root / rel_path).read_bytes()).hexdigest()[:16]}` |"
        for rel_path in written
    )
    return Ok(ApplyReport(written=tuple(written), changelog_rows=changelog_rows))
