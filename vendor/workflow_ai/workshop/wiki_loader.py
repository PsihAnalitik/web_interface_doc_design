"""M-16 wiki_loader: страницы wiki-базы знаний, бандлы и кросс-ссылки (TSK-1601..1604)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from workshop.result import Err, Ok, Result

WIKI_PAGE_NOT_FOUND = "WIKI_PAGE_NOT_FOUND"
WIKI_PAGE_INVALID = "WIKI_PAGE_INVALID"
WIKI_BUNDLE_TOO_LARGE = "WIKI_BUNDLE_TOO_LARGE"
WIKI_IO_ERROR = "WIKI_IO_ERROR"
WIKI_REFS_SOURCE_UNPARSEABLE = "WIKI_REFS_SOURCE_UNPARSEABLE"

# WHY: явный лимит бандла вместо тихого переполнения контекста узла (NFR-03);
# переопределяется параметром build_bundle
DEFAULT_BUNDLE_LIMIT_CHARS = 200_000

_INDEX_NAME = "index.md"
_ASSETS_PART = "assets"
# вербатим-приложения TSK-1801: проверки содержимого и сироты не применяются
SOURCE_SUFFIX = ".source.md"
# литеральные {{ в странице уронят сборку M-03 (UNRESOLVED_PLACEHOLDER) — ловим раньше
_FORBIDDEN_MARKER = "{{"
# относительная MD-ссылка: [текст](путь); внешние и якорные не проверяются
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")

_FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)

_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    """Убрать fenced-блоки и inline-код: ссылки-примеры в них — не ссылки."""
    return _INLINE_CODE_RE.sub("", _FENCED_CODE_RE.sub("", text))
_TECH_REF_RE = re.compile(r"<tech\s+ref=\"([^\"]+)\"")
_PAGE_RE = re.compile(r"<page\s+path=\"([^\"]+)\"\s+action=\"(\w+)\"")


@dataclass(frozen=True)
class WikiLinkReport:
    """Факты о ссылках страницы, не вердикт (образец — CrosslinkReport TSK-0203)."""

    broken_links: tuple[str, ...]


def load_page(root: Path, ref: str) -> Result[str]:
    """TSK-1601: разрешить wiki-ссылку в текст страницы (директория → index.md)."""
    resolved = _resolve_ref(root, ref)
    if resolved is None:
        return Err(WIKI_PAGE_NOT_FOUND, ref)
    try:
        return Ok(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        return Err(WIKI_IO_ERROR, f"{ref}: {exc}")


def build_bundle(
    root: Path, refs: list[str], limit_chars: int = DEFAULT_BUNDLE_LIMIT_CHARS
) -> Result[str]:
    """TSK-1602: бандл страниц для INPUTS узла; дубликат пути включается один раз."""
    pages: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for ref in refs:
        expanded = _expand_ref(root, ref)
        if expanded is None:
            return Err(WIKI_PAGE_NOT_FOUND, ref)
        for label, page_path in expanded:
            if page_path in seen:
                continue
            seen.add(page_path)
            pages.append((label, page_path))

    parts: list[str] = []
    for rel_path, page_path in pages:
        try:
            text = page_path.read_text(encoding="utf-8")
        except OSError as exc:
            return Err(WIKI_IO_ERROR, f"{rel_path}: {exc}")
        if _FORBIDDEN_MARKER in text:
            return Err(
                WIKI_PAGE_INVALID,
                f"{rel_path}: литеральные {{{{ уронят сборку промпта (M-03)",
            )
        parts.append(f"=== wiki: {rel_path} ===\n{text}")

    bundle = "\n\n".join(parts)
    if len(bundle) > limit_chars:
        return Err(WIKI_BUNDLE_TOO_LARGE, f"{len(bundle)} > {limit_chars}")
    return Ok(bundle)


def tree_listing(root: Path) -> Result[str]:
    """TSK-1606: листинг дерева wiki — пути всех страниц БЕЗ содержимого.

    Даёт узлу (например, ревью wiki_pages) видимость реального дерева:
    существование страницы проверяется по листингу, а не только по индексам.
    """
    # WHY: явный отказ вместо пустого листинга — опечатка в wiki_tree_root
    # иначе молча превратила бы все ссылки в «битые» для ревью
    if not root.is_dir():
        return Err(WIKI_PAGE_NOT_FOUND, str(root))
    try:
        pages = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md"))
    except OSError as exc:
        return Err(WIKI_IO_ERROR, str(exc))
    return Ok("\n".join(["=== wiki tree ==="] + pages))


def check_links(root: Path, page_ref: str) -> Result[WikiLinkReport]:
    """TSK-1603: проверить относительные MD-ссылки страницы; битые — в отчёт."""
    resolved = _resolve_ref(root, page_ref)
    if resolved is None:
        return Err(WIKI_PAGE_NOT_FOUND, page_ref)
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return Err(WIKI_IO_ERROR, f"{page_ref}: {exc}")

    broken: list[str] = []
    for target in _MD_LINK_RE.findall(_strip_code(text)):
        if "://" in target or target.startswith("mailto:"):
            continue
        candidate = (resolved.parent / target).resolve()
        if candidate.is_file():
            continue
        if candidate.is_dir() and (candidate / _INDEX_NAME).is_file():
            continue
        broken.append(target)
    return Ok(WikiLinkReport(broken_links=tuple(broken)))


def find_orphans(root: Path) -> Result[list[str]]:
    """TSK-1605: страницы, не упомянутые ни в одном index.md (кроме index.md и assets/)."""
    linked: set[Path] = set()
    try:
        for index_page in sorted(root.rglob(_INDEX_NAME)):
            if _ASSETS_PART in index_page.relative_to(root).parts:
                continue
            for target in _MD_LINK_RE.findall(index_page.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("mailto:"):
                    continue
                candidate = (index_page.parent / target).resolve()
                if candidate.is_dir():
                    candidate = candidate / _INDEX_NAME
                linked.add(candidate)

        orphans: list[str] = []
        # исключения: корневой index.md (вершина), корневой CHANGELOG.md
        # (приёмочный журнал FR-21 — не страница знаний) и assets/
        excluded = {(root / _INDEX_NAME).resolve(), (root / "CHANGELOG.md").resolve()}
        for page in sorted(root.rglob("*.md")):
            parts = page.relative_to(root).parts
            # index.md области — тоже страница: должен быть упомянут индексом выше
            if page.resolve() in excluded or _ASSETS_PART in parts:
                continue
            if page.name.endswith(SOURCE_SUFFIX):
                continue
            if page.resolve() not in linked:
                orphans.append(str(page.relative_to(root)))
        return Ok(orphans)
    except OSError as exc:
        return Err(WIKI_IO_ERROR, str(exc))


def collect_problems(root: Path) -> Result[list[str]]:
    """Полная механическая проверка wiki: индексы, ссылки, "{{", сироты.

    Общая для CLI wiki-check и M-18 wiki_applier; формулировки проблем стабильны.
    """
    problems: list[str] = []
    try:
        directories = [root] + sorted(
            d for d in root.rglob("*")
            if d.is_dir() and _ASSETS_PART not in d.relative_to(root).parts
        )
        for directory in directories:
            if not (directory / _INDEX_NAME).is_file():
                problems.append(f"нет index.md: {directory.relative_to(root) or '.'}")

        for page in sorted(root.rglob("*.md")):
            page_ref = str(page.relative_to(root))
            if page.name.endswith(SOURCE_SUFFIX):
                continue
            if _FORBIDDEN_MARKER in page.read_text(encoding="utf-8"):
                problems.append(f"литеральные {{{{ в {page_ref} — уронят сборку промпта")
            report = check_links(root, page_ref)
            if isinstance(report, Err):
                return report
            problems.extend(
                f"битая ссылка в {page_ref}: {target}"
                for target in report.value.broken_links
            )
    except OSError as exc:
        return Err(WIKI_IO_ERROR, str(exc))

    orphans = find_orphans(root)
    if isinstance(orphans, Err):
        return orphans
    problems.extend(f"страница-сирота (нет в index.md): {page}" for page in orphans.value)
    return Ok(problems)


def parse_wiki_refs_source(content: str) -> Result[list[str]]:
    """TSK-1604: динамические wiki-ссылки из артефакта-источника (чистая функция).

    Понимает tech_stack (<tech ref>) и wiki_change (<page path action>):
    для wiki_change возвращаются ТОЛЬКО update-страницы — их текущий текст
    нужен генератору; add-страниц ещё не существует. Все страницы add → Ok([]).
    """
    tech_refs = _TECH_REF_RE.findall(content)
    pages = _PAGE_RE.findall(content)
    if not tech_refs and not pages:
        return Err(
            WIKI_REFS_SOURCE_UNPARSEABLE,
            "нет ни одного <tech ref=> или <page path= action=>",
        )
    update_refs = [path for path, action in pages if action == "update"]
    return Ok(tech_refs + update_refs)


def _resolve_ref(root: Path, ref: str) -> Path | None:
    candidate = root / ref
    if candidate.is_file():
        return candidate
    if candidate.is_dir() and (candidate / _INDEX_NAME).is_file():
        return candidate / _INDEX_NAME
    return None


def _expand_ref(root: Path, ref: str) -> list[tuple[str, Path]] | None:
    """Директория → все её .md (index.md первым), файл → он сам.

    Метка страницы строится из ref (не из root): ref может быть и абсолютным путём.
    """
    candidate = root / ref
    if candidate.is_file():
        return [(ref, candidate)]
    if candidate.is_dir():
        pages = sorted(candidate.glob("*.md"), key=lambda p: (p.name != _INDEX_NAME, p.name))
        if pages:
            return [(f"{ref.rstrip('/')}/{page.name}", page) for page in pages]
    return None
