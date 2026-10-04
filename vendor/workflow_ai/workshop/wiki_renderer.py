"""M-17 wiki_renderer: детерминированная HTML-витрина wiki для человека (TSK-1701).

Источник истины — Markdown (FR-18); рендер без LLM и внешних зависимостей.
Mermaid-блоки отдаются client-side (<pre class="mermaid"> + скрипт в шапке).
"""
from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from workshop.result import Err, Ok, Result
from workshop.wiki_loader import check_links

RENDER_TARGET_EXISTS = "RENDER_TARGET_EXISTS"
RENDER_IO_ERROR = "RENDER_IO_ERROR"

_ASSETS_DIR = "assets"
_MERMAID_SCRIPT = (
    '<script type="module">import mermaid from '
    '"https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";'
    "mermaid.initialize({startOnLoad: true});</script>"
)
_PAGE_CSS = (
    "body{max-width:56rem;margin:2rem auto;padding:0 1rem;"
    "font:16px/1.6 system-ui,sans-serif;color:#1a1a1a}"
    "pre{background:#f6f6f6;padding:.8rem;overflow-x:auto}"
    "code{background:#f2f2f2;padding:0 .2em}"
    "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.3em .6em}"
    "nav{color:#777;font-size:.9em;margin-bottom:1rem}"
)

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class RenderReport:
    out_dir: Path
    pages: tuple[str, ...]
    broken_links: tuple[str, ...]


def render_wiki(root: Path, out_dir: Path) -> Result[RenderReport]:
    """TSK-1701: wiki → статический HTML-сайт; битые ссылки — в отчёт, не отказ."""
    if out_dir.exists() and any(out_dir.iterdir()):
        return Err(RENDER_TARGET_EXISTS, str(out_dir))

    pages = sorted(
        page for page in root.rglob("*.md")
        if _ASSETS_DIR not in page.relative_to(root).parts
    )
    broken: list[str] = []
    rendered: list[str] = []
    try:
        for page in pages:
            rel = page.relative_to(root)
            target = (out_dir / rel).with_suffix(".html")
            target.parent.mkdir(parents=True, exist_ok=True)
            text = page.read_text(encoding="utf-8")
            target.write_text(_page_html(str(rel), text), encoding="utf-8")
            rendered.append(str(rel))

            report = check_links(root, str(rel))
            if isinstance(report, Ok):
                broken.extend(f"{rel}: {link}" for link in report.value.broken_links)

        assets_src = root / _ASSETS_DIR
        if assets_src.is_dir():
            shutil.copytree(assets_src, out_dir / _ASSETS_DIR, dirs_exist_ok=True)
    except OSError as exc:
        return Err(RENDER_IO_ERROR, str(exc))

    return Ok(RenderReport(
        out_dir=out_dir, pages=tuple(rendered), broken_links=tuple(broken)
    ))


def _page_html(rel_path: str, markdown_text: str) -> str:
    body = _markdown_to_html(markdown_text)
    depth = rel_path.count("/")
    home = "../" * depth + "index.html"
    mermaid = _MERMAID_SCRIPT if 'class="mermaid"' in body else ""
    title = html.escape(rel_path)
    return (
        "<!DOCTYPE html>\n<html lang=\"ru\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{title}</title>\n<style>{_PAGE_CSS}</style>\n{mermaid}\n</head>\n<body>\n"
        f'<nav><a href="{home}">wiki</a> / {title}</nav>\n{body}\n</body>\n</html>\n'
    )


def _markdown_to_html(text: str) -> str:
    """Конвертер подмножества Markdown, используемого в wiki (детерминированный)."""
    out: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]

        if line.startswith("```"):
            language = line[3:].strip()
            block: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1  # закрывающий ```
            code = html.escape("\n".join(block))
            if language == "mermaid":
                out.append(f'<pre class="mermaid">{code}</pre>')
            else:
                out.append(f"<pre><code>{code}</code></pre>")
            continue

        heading = _HEADING_RE.match(line)
        if heading is not None:
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        if line.startswith("|"):
            rows: list[str] = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    index += 1  # разделительная строка |---|
                    continue
                tag = "th" if not rows else "td"
                rows.append(
                    "<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>"
                )
                index += 1
            out.append("<table>" + "".join(rows) + "</table>")
            continue

        if line.lstrip().startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith("- "):
                item_lines = [lines[index].lstrip()[2:]]
                index += 1
                # продолжение пункта — отступ без маркера
                while (
                    index < len(lines)
                    and lines[index].startswith("  ")
                    and not lines[index].lstrip().startswith("- ")
                ):
                    item_lines.append(lines[index].strip())
                    index += 1
                items.append(f"<li>{_inline(' '.join(item_lines))}</li>")
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        if not line.strip():
            index += 1
            continue

        # обычный абзац: собрать до пустой строки/структурного маркера
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not _is_structural(lines[index]):
            paragraph.append(lines[index])
            index += 1
        out.append(f"<p>{_inline(' '.join(paragraph))}</p>")

    return "\n".join(out)


def _is_structural(line: str) -> bool:
    if line.startswith(("```", "|", "#")):
        return True
    return line.lstrip().startswith("- ")


def _inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = _CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    return _LINK_RE.sub(_render_link, escaped)


def _render_link(match: re.Match[str]) -> str:
    label, target = match.group(1), match.group(2)
    if "://" not in target and not target.startswith("mailto:"):
        if target.endswith(".md"):
            target = target[:-3] + ".html"
        elif not Path(target).suffix:
            target = target.rstrip("/") + "/index.html"
    return f'<a href="{target}">{label}</a>'
