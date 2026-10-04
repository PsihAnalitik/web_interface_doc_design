"""M-06 workshop_node: один запуск мастерской = один артефакт или вопрос (TSK-0601)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from workshop.artifact_store import validate_crosslinks
from workshop.db_query import build_db_tools
from workshop.llm_client import LLMClient, ToolSpec
from workshop.material import (
    MaterialStore,
    build_material_tools,
    build_wiki_tools,
    load_wiki_store,
)
from workshop.models import Artifact, ArtifactRef, CrosslinkReport, NodeConfig
from workshop.prompt_builder import assemble, parse_stage_map
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog, RunRecord
from workshop.web_search import build_tools
from workshop.wiki_loader import build_bundle, tree_listing

PROMPT_BUILD_FAILED = "PROMPT_BUILD_FAILED"
LLM_FAILED = "LLM_FAILED"
OUTPUT_UNPARSEABLE = "OUTPUT_UNPARSEABLE"
MATERIAL_NOT_CONFIGURED = "MATERIAL_NOT_CONFIGURED"
WIKI_TOOLS_NEED_TREE_ROOT = "WIKI_TOOLS_NEED_TREE_ROOT"

_MATERIAL_TOOL_NAMES = ("material_search", "material_get")
_WIKI_TOOL_NAMES = ("wiki_search", "wiki_get")
_DB_TOOL_NAMES = ("db_query",)

_CLARIFICATION_MARKER = "NEEDS_CLARIFICATION"
_CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_.-]*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class ArtifactOutcome:
    content: str
    crosslink_report: CrosslinkReport | None


@dataclass(frozen=True)
class ClarificationOutcome:
    question: str


type WorkshopOutcome = ArtifactOutcome | ClarificationOutcome


def run_workshop(
    node_id: str,
    config: NodeConfig,
    upstream: Artifact,
    llm: LLMClient,
    run_log: RunLog,
    iteration: int = 1,
    iteration_context: str | None = None,
    material: MaterialStore | None = None,
) -> Result[WorkshopOutcome]:
    prompt = build_node_prompt(config, upstream, iteration_context)
    if isinstance(prompt, Err):
        return prompt

    tools_result = _build_node_tools(config, material)
    if isinstance(tools_result, Err):
        return tools_result
    tools = tools_result.value

    llm_result = llm.complete(prompt.value, config.llm, tools=tools)
    if isinstance(llm_result, Ok):
        response_text = llm_result.value.text
        tool_trace = list(llm_result.value.tool_trace)
        usage = dict(llm_result.value.usage)
    else:
        response_text = f"<LLM ERROR {llm_result.code}: {llm_result.details}>"
        tool_trace = []
        usage = {}

    # лог пишется ДО парсинга: прогон воспроизводим даже при отказе (NFR-04)
    log_result = run_log.append(
        RunRecord(
            node_id=node_id,
            iteration=iteration,
            prompt=prompt.value,
            input_ref=f"{upstream.ref.name}@v{upstream.ref.version}",
            params=config.llm.model_dump(),
            response=response_text,
            tool_trace=tool_trace,
            usage=usage,
        )
    )
    if isinstance(log_result, Err):
        return log_result
    if isinstance(llm_result, Err):
        return Err(LLM_FAILED, f"{llm_result.code}: {llm_result.details}")
    return _parse_outcome(llm_result.value.text, upstream)


def _build_node_tools(
    config: NodeConfig, material: MaterialStore | None
) -> Result[list[ToolSpec]]:
    """TSK-2203/2205: web_search — реестр M-21, material_*/wiki_* — поверх сторов M-22.

    Опечатка в config.tools, material_* без блока material в графе, wiki_*
    без wiki_tree_root узла — явный отказ ДО вызова LLM (контракт TSK-2102).
    """
    local_names = _MATERIAL_TOOL_NAMES + _WIKI_TOOL_NAMES + _DB_TOOL_NAMES
    web_names = [name for name in config.tools if name not in local_names]
    material_names = [name for name in config.tools if name in _MATERIAL_TOOL_NAMES]
    wiki_names = [name for name in config.tools if name in _WIKI_TOOL_NAMES]
    db_names = [name for name in config.tools if name in _DB_TOOL_NAMES]

    tools: list[ToolSpec] = []
    if web_names:
        web_result = build_tools(web_names)
        if isinstance(web_result, Err):
            return web_result
        tools.extend(web_result.value)
    if material_names:
        if material is None:
            return Err(
                MATERIAL_NOT_CONFIGURED,
                f"{', '.join(material_names)}: у графа нет блока material",
            )
        tools.extend(
            spec
            for spec in build_material_tools(material)
            if spec.name in material_names
        )
    if wiki_names:
        if config.wiki_tree_root is None:
            return Err(
                WIKI_TOOLS_NEED_TREE_ROOT,
                f"{', '.join(wiki_names)}: у узла не задан wiki_tree_root",
            )
        wiki_store = load_wiki_store(Path(config.wiki_tree_root))
        if isinstance(wiki_store, Err):
            return wiki_store
        store, pages = wiki_store.value
        tools.extend(
            spec
            for spec in build_wiki_tools(store, pages)
            if spec.name in wiki_names
        )
    if db_names:
        # DSN проверяется исполнителем при вызове (без DSN — текст модели):
        # инструмент объявляют цеха, работающие и без живой БД
        tools.extend(build_db_tools())
    return Ok(tools)


def build_node_prompt(
    config: NodeConfig, upstream: Artifact, iteration_context: str | None
) -> Result[str]:
    try:
        base = Path(config.base_prompt_path).read_text(encoding="utf-8")
        stage_text = Path(config.stage_map_path).read_text(encoding="utf-8")
    except OSError as exc:
        return Err(PROMPT_BUILD_FAILED, str(exc))

    # wiki — бандлом M-16 (TSK-1602): дедупликация, лимит, lint на "{{";
    # пути wiki_refs — относительно корня репозитория
    bundle = build_bundle(Path("."), [ref.path for ref in config.wiki_refs])
    if isinstance(bundle, Err):
        return bundle

    # TSK-1606: листинг реального дерева wiki (пути без содержимого) —
    # узел проверяет существование страниц не только по индексам и file map
    tree = ""
    if config.wiki_tree_root is not None:
        tree_result = tree_listing(Path(config.wiki_tree_root))
        if isinstance(tree_result, Err):
            return tree_result
        tree = tree_result.value

    fragments = parse_stage_map(stage_text)
    if isinstance(fragments, Err):
        return Err(PROMPT_BUILD_FAILED, f"{fragments.code}: {fragments.details}")

    inputs_parts = [part for part in (bundle.value, tree) if part] + [upstream.content]
    if iteration_context is not None and iteration_context.strip():
        inputs_parts.append(
            f"<iteration_context>\n{iteration_context}\n</iteration_context>"
        )

    assembled = assemble(base, fragments.value, "\n\n".join(inputs_parts))
    if isinstance(assembled, Err):
        return Err(PROMPT_BUILD_FAILED, f"{assembled.code}: {assembled.details}")
    return Ok(assembled.value)


def _parse_outcome(response: str, upstream: Artifact) -> Result[WorkshopOutcome]:
    # локальный импорт: codegen_loop импортирует workshop_node (разрыв цикла)
    from workshop.codegen_loop import parse_file_map, serialize_files

    # WHY: блок артефакта проверяется РАНЬШЕ маркера clarification — иначе слово
    # NEEDS_CLARIFICATION в ДАННЫХ артефакта (например, source_request, где маркер
    # упомянут текстом) инжектится в протокол и уводит узел в ложный вопрос
    files = parse_file_map(response)
    block = _CODE_BLOCK_RE.search(response)
    if files:
        # мастерская выдала file map (FR-21) — артефакт = ВСЕ блоки канонично
        content = serialize_files(files)
    elif block is not None:
        content = block.group(1).strip()
    elif _CLARIFICATION_MARKER in response:
        question = response.split(_CLARIFICATION_MARKER, 1)[1].lstrip(" :\n").strip()
        if not question:
            return Err(OUTPUT_UNPARSEABLE, f"{_CLARIFICATION_MARKER} без вопроса")
        return Ok(ClarificationOutcome(question=question))
    else:
        return Err(
            OUTPUT_UNPARSEABLE,
            f"в ответе нет ни блока артефакта, ни {_CLARIFICATION_MARKER}",
        )

    draft = Artifact(
        ref=ArtifactRef(name="draft", version=0),
        content=content,
        derived_from=upstream.ref,
    )
    report_result = validate_crosslinks(draft, upstream)
    if isinstance(report_result, Ok):
        report = report_result.value
    else:
        # WHY: у старшего нет id (например, сырой запрос пользователя) — проверять нечего
        report = None
    return Ok(ArtifactOutcome(content=content, crosslink_report=report))
