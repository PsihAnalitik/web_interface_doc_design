"""M-03 prompt_builder: сборка промпта base + stage-карта + INPUTS (TSK-0301, TSK-0302)."""
from __future__ import annotations

import re
from collections import Counter

from workshop.result import Err, Ok, Result

FRAGMENT_MALFORMED = "FRAGMENT_MALFORMED"
DUPLICATE_FRAGMENT = "DUPLICATE_FRAGMENT"
UNRESOLVED_PLACEHOLDER = "UNRESOLVED_PLACEHOLDER"
INPUTS_EMPTY = "INPUTS_EMPTY"

_INPUTS_NAME = "INPUTS"

_FRAGMENT_RE = re.compile(
    r"<!--\s*@fragment:\s*([A-Za-z_][A-Za-z0-9_]*)\s*-->\n?(.*?)\n?\s*<!--\s*@end\s*-->",
    re.DOTALL,
)
_FRAGMENT_MARKER_RE = re.compile(r"@fragment:\s*([A-Za-z_][A-Za-z0-9_]*)")
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


def _strip_leading_comments(base: str) -> str:
    remaining = base
    while True:
        candidate = remaining.lstrip()
        if not candidate.startswith("<!--"):
            return remaining
        end = candidate.find("-->")
        if end == -1:
            return remaining
        remaining = candidate[end + len("-->"):]


def parse_stage_map(stage_map_text: str) -> Result[dict[str, str]]:
    matched = _FRAGMENT_RE.findall(stage_map_text)
    marker_names = _FRAGMENT_MARKER_RE.findall(stage_map_text)

    unmatched = Counter(marker_names) - Counter(name for name, _ in matched)
    if unmatched:
        return Err(FRAGMENT_MALFORMED, f"@fragment без @end: {next(iter(unmatched))}")

    fragments: dict[str, str] = {}
    for name, body in matched:
        if name in fragments:
            return Err(DUPLICATE_FRAGMENT, name)
        fragments[name] = body.strip()
    return Ok(fragments)


def assemble(base: str, fragments: dict[str, str], inputs: str) -> Result[str]:
    # WHY: только ВЕДУЩИЙ заголовочный комментарий — meta-документация для человека
    # (в т.ч. с примерами {{NAME}}), в контекст LLM не идёт (NFR-03). Комментарии
    # в теле base — содержательная часть промпта и сохраняются.
    stripped_base = _strip_leading_comments(base)

    placeholder_names = _PLACEHOLDER_RE.findall(stripped_base)
    if _INPUTS_NAME in placeholder_names and not inputs.strip():
        return Err(INPUTS_EMPTY, "в base есть {{INPUTS}}, а содержимое пустое")

    missing = [
        name
        for name in placeholder_names
        if name != _INPUTS_NAME and name not in fragments
    ]
    if missing:
        return Err(UNRESOLVED_PLACEHOLDER, missing[0])

    def substitute(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == _INPUTS_NAME:
            return inputs
        return fragments[name]

    # single-pass: re.sub не пересканирует подставленный текст
    final_prompt = _PLACEHOLDER_RE.sub(substitute, stripped_base)

    leftover = _PLACEHOLDER_RE.search(final_prompt)
    if leftover is not None:
        # WHY: плейсхолдер пришёл изнутри фрагмента или INPUTS — рекурсивную
        # подстановку не разворачиваем (mental test TSK-0302), детерминированный отказ
        return Err(UNRESOLVED_PLACEHOLDER, f"вложенный: {leftover.group(1)}")
    return Ok(final_prompt)
