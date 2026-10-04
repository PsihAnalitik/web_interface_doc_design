"""M-27 skill_exporter: компиляция цеха в Skill для Claude Code (TSK-2701).

Скилл — производный артефакт цеха, как wiki_html относительно wiki: конфиги
`configs/<shop>/` остаются источником истины, дерево скилла собирается заново.
Дизайн: user_docs/skills_export_design.md.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from workshop.config_loader import load_graph_config, load_model_registry, load_node_config
from workshop.models import GraphConfig, ModelRegistry, NodeConfig, NodeSpec
from workshop.prompt_builder import assemble, parse_stage_map
from workshop.result import Err, Ok, Result

SKILL_META_MISSING = "SKILL_META_MISSING"
SKILL_META_INVALID = "SKILL_META_INVALID"
SKILL_PHASE_MISSING = "SKILL_PHASE_MISSING"
SKILL_TEMPLATE_MISSING = "SKILL_TEMPLATE_MISSING"
SKILL_WIKI_REF_MISSING = "SKILL_WIKI_REF_MISSING"
SKILL_TARGET_DIRTY = "SKILL_TARGET_DIRTY"
SKILL_IO_ERROR = "SKILL_IO_ERROR"

_SKILL_DIR = "skill"                 # ручные файлы цеха: meta.json, 0-init.md, finish.md
_META_NAME = "meta.json"
_INIT_NAME = "0-init.md"
_FINISH_NAME = "finish.md"
_REFERENCES_WIKI = "references/wiki"
# WHY: assets — картинки HTML-витрины wiki, узлам они не адресуемы; в скилле
# это мёртвый вес
_SKIP_AREAS = ("assets",)

# инструменты цеха → инструменты Claude Code (тот же смысл, другой исполнитель)
_TOOL_MAP = {
    "web_search": "WebSearch",
    "wiki_search": "Grep",
    "wiki_get": "Read",
    "material_search": "Grep",
    "material_get": "Read",
    "db_query": "Bash",
}

_WIKI_VERSION_RE = re.compile(r"^#\s.*\(v(\d+)\)", re.MULTILINE)

_INPUTS_NODE = """=== INPUTS ===
Вход этой фазы собери сам, по её шапке:
1. `inputs:` — для каждого имени возьми ПОСЛЕДНЮЮ версию артефакта
   `.workshop/<run>/artifacts/<имя>/v<N>.xml`; имя `input_material` означает
   входной материал прогона (`input_material` в state.json).
2. `reads:` — прочитай перечисленные файлы Read'ом.
3. `reads_from:` (если есть) — пути справок названы в артефакте этого узла;
   прочитай их дополнительно.
4. `tree:` (если есть) — дерево путей вики; получи листингом каталога.
5. Если `iteration` > 1 — добавь `<prior_findings>` из последнего отчёта
   `.workshop/<run>/reviews/<этот узел>/v<N>.md`."""

_INPUTS_REVIEW = """=== INPUTS ===
Вход ревью: проверяемый артефакт `.workshop/<run>/artifacts/<узел>/v<N>.xml`
(версия из `state.json`), справки из `reads:` шапки, и `<prior_findings>` —
находки прошлого прохода, если `iteration` > 1."""

_TARGET_WIKI = """
## Целевая вики

`reads:` и `tree:` выше — снимок вики фабрики: это ОБРАЗЕЦ методологии и
структуры, а не место записи. Куда пишем — `wiki_profile` в `state.json`
(его заполняет фаза 0):

- `root` — корень целевой вики; дерево путей получай листингом ЭТОГО корня,
  снимок деревом цели НЕ является;
- `indexes` — индексные файлы цели; прочитай их и сверяй с ними пути страниц
  и строки индексов;
- `conventions` — файл конвенций цели, если он есть.

Правила оформления страниц ниже — конвенции вики фабрики. Они действуют,
ПОКА `wiki_profile.conventions` пуст. Файл конвенций назван — он СТАРШЕ:
заголовки, фронтматтер, вид индексов и имена файлов подчиняются ему, правила
фабрики применяются только там, где он молчит.
"""

_TARGET_WIKI_REVIEW = """
## Целевая вики

`reads:` и `tree:` выше — снимок вики фабрики, ОБРАЗЕЦ структуры. Проверяемое
изменение адресовано вики пользователя: её корень, индексные файлы и файл
конвенций названы в `wiki_profile` (`state.json`).

Пункты чек-листа про существование путей, сиротство страниц, разрешение ссылок
и сохранность индексов считай по ЦЕЛЕВОЙ вики: дерево — листингом
`wiki_profile.root`, текущие индексы — из `wiki_profile.indexes`. Пункты про
формат страниц — по `wiki_profile.conventions`, если он назван; иначе по
конвенциям фабрики из чек-листа.
"""

_GATE_P3 = """**Гейт (шкала p3_high, 🔴p3 — высший вес):** блокируют находки
веса **p2 и выше**. Есть хотя бы одна — гейт FAIL. Только p1/p0 — PASS,
находки остаются в отчёте как замечания."""

_GATE_P0 = """**Гейт (шкала p0_high, p0 — высший вес; обратная шкала цехов
анализа безопасности):** блокируют находки веса **p1 и ниже** (p0, p1).
Есть хотя бы одна — гейт FAIL. Только p2/p3 — PASS."""


@dataclass(frozen=True)
class ExportReport:
    skill_dir: Path
    phases: tuple[str, ...]
    reviews: tuple[str, ...]
    areas: tuple[str, ...]
    wiki_version: str


def export_skill(
    graph_path: str,
    out_root: Path,
    wiki_root: Path = Path("wiki"),
    template_path: Path = Path("prompts/skill/SKILL.template.md"),
    snapshot_date: str = "",
) -> Result[ExportReport]:
    """TSK-2701: `configs/<shop>/` → дерево скилла в out_root/<имя скилла>/."""
    graph_result = load_graph_config(graph_path)
    if isinstance(graph_result, Err):
        return graph_result
    graph = graph_result.value
    shop_dir = Path(graph_path).parent

    meta = _load_meta(shop_dir)
    if isinstance(meta, Err):
        return meta
    init_phase = _read_manual_phase(shop_dir / _SKILL_DIR / _INIT_NAME, required=True)
    if isinstance(init_phase, Err):
        return init_phase
    finish_phase = _read_manual_phase(shop_dir / _SKILL_DIR / _FINISH_NAME, required=False)
    if isinstance(finish_phase, Err):
        return finish_phase

    template = _read_text(template_path, SKILL_TEMPLATE_MISSING)
    if isinstance(template, Err):
        return template

    registry: ModelRegistry | None = None
    if graph.llm_profiles_path is not None:
        registry_result = load_model_registry(graph.llm_profiles_path)
        if isinstance(registry_result, Err):
            return registry_result
        registry = registry_result.value

    ordered = _topological_order(graph)
    built = _build_phases(graph, ordered, registry)
    if isinstance(built, Err):
        return built
    phases, areas = built.value

    wiki_version = _wiki_version(wiki_root)
    skill_md = _render_skill_md(
        template.value, meta.value, graph, phases, wiki_version, snapshot_date,
        finish_index=len(ordered) + 1 if finish_phase.value is not None else None,
    )
    if isinstance(skill_md, Err):
        return skill_md

    skill_dir = out_root / meta.value["name"]
    prepared = _prepare_target(skill_dir)
    if isinstance(prepared, Err):
        return prepared

    try:
        (skill_dir / "phases").mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_md.value.lstrip("\n"), encoding="utf-8")
        (skill_dir / "phases" / _INIT_NAME).write_text(init_phase.value, encoding="utf-8")
        written = [_INIT_NAME]
        reviews: list[str] = []
        for phase in phases:
            (skill_dir / "phases" / phase.file_name).write_text(phase.body, encoding="utf-8")
            written.append(phase.file_name)
            if phase.review_file is not None:
                (skill_dir / "phases" / phase.review_file).write_text(
                    phase.review_body, encoding="utf-8"
                )
                reviews.append(phase.review_file)
        if finish_phase.value is not None:
            finish_name = f"{len(ordered) + 1}-finish.md"
            (skill_dir / "phases" / finish_name).write_text(
                finish_phase.value, encoding="utf-8"
            )
            written.append(finish_name)
        copied = _copy_areas(wiki_root, skill_dir / _REFERENCES_WIKI, areas)
        if isinstance(copied, Err):
            return copied
    except OSError as exc:
        return Err(SKILL_IO_ERROR, str(exc))

    return Ok(ExportReport(
        skill_dir=skill_dir,
        phases=tuple(written),
        reviews=tuple(reviews),
        areas=copied.value,
        wiki_version=wiki_version,
    ))


@dataclass(frozen=True)
class _Phase:
    file_name: str
    body: str
    review_file: str | None
    review_body: str


def _build_phases(
    graph: GraphConfig, ordered: list[NodeSpec], registry: ModelRegistry | None
) -> Result[tuple[list[_Phase], set[str]]]:
    phases: list[_Phase] = []
    areas: set[str] = set()
    for index, node in enumerate(ordered, start=1):
        config = load_node_config(node.config_path, registry)
        if isinstance(config, Err):
            return config
        body = _phase_body(config.value, _INPUTS_NODE)
        if isinstance(body, Err):
            return body

        review_file: str | None = None
        review_body = ""
        if node.gates.review_config_path is not None:
            review_config = load_node_config(node.gates.review_config_path, registry)
            if isinstance(review_config, Err):
                return review_config
            areas.update(_areas_of(review_config.value))
            rendered_review = _phase_body(review_config.value, _INPUTS_REVIEW)
            if isinstance(rendered_review, Err):
                return rendered_review
            review_file = f"{index}-{node.id}.review.md"
            review_body = _front_matter({
                "node": node.id,
                "role": "review",
                "reviews": f"{index}-{node.id}.md",
                "severity_scale": graph.severity_scale,
                "reads": _reads(review_config.value),
                "tree": _tree(review_config.value),
                "target": _target(review_config.value),
            }) + _target_block(review_config.value, _TARGET_WIKI_REVIEW) \
                + rendered_review.value

        header = _front_matter({
            "node": node.id,
            "inputs": _inputs(graph, node),
            "reads": _reads(config.value),
            "reads_from": config.value.wiki_refs_from,
            "tree": _tree(config.value),
            "tools": _tools(config.value),
            "review": review_file,
            "hitl": _hitl(node),
            "backend": "mcp" if node.kind == "codegen" else "inline",
            "max_iterations": node.max_iterations,
            "target": _target(config.value),
        })
        phases.append(_Phase(
            file_name=f"{index}-{node.id}.md",
            body=header + _target_block(config.value, _TARGET_WIKI) + body.value,
            review_file=review_file,
            review_body=review_body,
        ))
        areas.update(_areas_of(config.value))
    return Ok((phases, areas))


def _phase_body(config: NodeConfig, inputs_stub: str) -> Result[str]:
    base = _read_text(Path(config.base_prompt_path), SKILL_PHASE_MISSING)
    if isinstance(base, Err):
        return base
    stage_text = _read_text(Path(config.stage_map_path), SKILL_PHASE_MISSING)
    if isinstance(stage_text, Err):
        return stage_text
    fragments = parse_stage_map(stage_text.value)
    if isinstance(fragments, Err):
        return fragments
    # stage-фрагменты инлайнятся здесь: в скилле подстановки нет
    return assemble(base.value, fragments.value, inputs_stub)


def _inputs(graph: GraphConfig, node: NodeSpec) -> list[str]:
    upstream = [edge.from_node for edge in graph.edges if edge.to_node == node.id]
    if upstream:
        return upstream
    return ["input_material"]


def _reads(config: NodeConfig) -> list[str]:
    return [f"{_REFERENCES_WIKI}/{_strip_wiki_prefix(ref.path)}" for ref in config.wiki_refs]


def _tree(config: NodeConfig) -> str | None:
    if config.wiki_tree_root is None:
        return None
    stripped = _strip_wiki_prefix(config.wiki_tree_root)
    if not stripped:
        return _REFERENCES_WIKI
    return f"{_REFERENCES_WIKI}/{stripped}"


def _is_wiki_node(config: NodeConfig) -> bool:
    """Wiki-осведомлённый узел: ходит по вики, значит ему нужна ЦЕЛЬ (§7.1)."""
    return bool(config.wiki_refs) or config.wiki_tree_root is not None


def _target(config: NodeConfig) -> str | None:
    if not _is_wiki_node(config):
        return None
    return "wiki_profile (state.json)"


def _target_block(config: NodeConfig, block: str) -> str:
    if not _is_wiki_node(config):
        return ""
    return block


def _tools(config: NodeConfig) -> list[str]:
    mapped: list[str] = []
    for tool in config.tools:
        claude_tool = _TOOL_MAP.get(tool, tool)
        if claude_tool not in mapped:
            mapped.append(claude_tool)
    return mapped


def _hitl(node: NodeSpec) -> str | bool:
    if node.gates.hitl_required:
        return "required"
    return node.gates.hitl


def _areas_of(config: NodeConfig) -> set[str]:
    """Области, затронутые узлом: по wiki_refs, а корень tree — это ВСЕ области."""
    areas: set[str] = set()
    for ref in config.wiki_refs:
        head = _strip_wiki_prefix(ref.path).split("/")[0]
        if head:
            areas.add(head)
    if config.wiki_tree_root is not None:
        stripped = _strip_wiki_prefix(config.wiki_tree_root)
        areas.add(stripped.split("/")[0] if stripped else "*")
    return areas


def _copy_areas(
    wiki_root: Path, target: Path, areas: set[str]
) -> Result[tuple[str, ...]]:
    """Vendoring областей ЦЕЛИКОМ: обрезанная область даёт битые related-ссылки.

    Возвращает имена скопированных областей — в отчёт идёт то, что легло на
    диск, а не запрошенное множество (в нём есть пути файлов и маркер «*»).
    """
    if not wiki_root.is_dir():
        return Err(SKILL_WIKI_REF_MISSING, str(wiki_root))
    if not areas:
        return Ok(())

    if "*" in areas:
        names = {entry.name for entry in wiki_root.iterdir() if entry.is_dir()}
    else:
        names = {area for area in areas if (wiki_root / area).is_dir()}
        missing = sorted(area for area in areas if not (wiki_root / area).exists())
        if missing:
            return Err(SKILL_WIKI_REF_MISSING, ", ".join(missing))
    names -= set(_SKIP_AREAS)

    try:
        target.mkdir(parents=True, exist_ok=True)
        for name in sorted(names):
            shutil.copytree(wiki_root / name, target / name, dirs_exist_ok=True)
        # корневой index.md — карта областей, на неё ссылается каждая область
        root_index = wiki_root / "index.md"
        if root_index.is_file():
            shutil.copy2(root_index, target / "index.md")
    except OSError as exc:
        return Err(SKILL_IO_ERROR, str(exc))
    return Ok(tuple(sorted(names)))


def _render_skill_md(
    template: str,
    meta: dict[str, str],
    graph: GraphConfig,
    phases: list[_Phase],
    wiki_version: str,
    snapshot_date: str,
    finish_index: int | None,
) -> Result[str]:
    rows = ["| фаза | файл | ревью | подтверждение человеком |", "|---|---|---|---|"]
    rows.append(f"| 0. инициализация | `phases/{_INIT_NAME}` | — | — |")
    for index, phase in enumerate(phases, start=1):
        review = f"`phases/{phase.review_file}`" if phase.review_file else "—"
        hitl = _hitl_label(phase.body)
        title = phase.file_name[len(f"{index}-"):-len(".md")]
        rows.append(f"| {index}. {title} | `phases/{phase.file_name}` "
                    f"| {review} | {hitl} |")
    if finish_index is not None:
        rows.append(f"| {finish_index}. применение и приёмка "
                    f"| `phases/{finish_index}-finish.md` | — | отчёт пользователю |")
    hitl_note = (
        "Фазы с `hitl: required` подтверждает человек ВСЕГДА — режим `autopilot` "
        "их не пропускает. Фазы с `hitl: true` в режиме `autopilot` проходят "
        "автоматически (агентское ревью остаётся)."
        if any("hitl: required" in phase.body for phase in phases)
        else "Фазы с `hitl: true` подтверждает человек; в режиме `autopilot` "
             "они проходят автоматически (агентское ревью остаётся)."
    )
    snapshot = (
        f"снимок вики {wiki_version}"
        + (f" от {snapshot_date}" if snapshot_date else "")
    )
    fragments = {
        "SKILL_NAME": meta["name"],
        "DESCRIPTION": meta["description"],
        "SHOP": meta.get("title", meta["name"]),
        "PHASE_TABLE": "\n".join(rows),
        "GATE_RULE": _GATE_P0 if graph.severity_scale == "p0_high" else _GATE_P3,
        "HITL_NOTE": hitl_note,
        "SNAPSHOT": snapshot,
    }
    return assemble(template, fragments, "")


def _hitl_label(phase_body: str) -> str:
    if "hitl: required" in phase_body:
        return "обязательно"
    if "hitl: true" in phase_body:
        return "да"
    return "—"


def _load_meta(shop_dir: Path) -> Result[dict[str, str]]:
    path = shop_dir / _SKILL_DIR / _META_NAME
    if not path.is_file():
        return Err(SKILL_META_MISSING, f"создайте {path} с полями name и description")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Err(SKILL_META_INVALID, f"{path}: {exc}")
    if not isinstance(raw, dict) or not raw.get("name") or not raw.get("description"):
        return Err(SKILL_META_INVALID, f"{path}: обязательны name и description")
    return Ok(raw)


def _read_manual_phase(path: Path, required: bool) -> Result[str | None]:
    if not path.is_file():
        if required:
            return Err(SKILL_PHASE_MISSING, str(path))
        return Ok(None)
    return _read_text(path, SKILL_PHASE_MISSING)


def _read_text(path: Path, missing_code: str) -> Result[str]:
    if not path.is_file():
        return Err(missing_code, str(path))
    try:
        return Ok(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return Err(SKILL_IO_ERROR, f"{path}: {exc}")


def _prepare_target(skill_dir: Path) -> Result[None]:
    """Перевыпуск перезаписывает СВОЙ каталог; чужой каталог — отказ."""
    if not skill_dir.exists():
        return Ok(None)
    if not (skill_dir / "SKILL.md").is_file() and any(skill_dir.iterdir()):
        return Err(SKILL_TARGET_DIRTY, str(skill_dir))
    try:
        shutil.rmtree(skill_dir)
    except OSError as exc:
        return Err(SKILL_IO_ERROR, str(exc))
    return Ok(None)


def _front_matter(fields: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == [] or value is False and key != "hitl":
            continue
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(str(item) for item in value)}]")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---\n")
    return "\n".join(lines)


def _topological_order(graph: GraphConfig) -> list[NodeSpec]:
    """Порядок Кана; при равных кандидатах — порядок объявления (детерминизм)."""
    by_id = {node.id: node for node in graph.nodes}
    order_index = {node.id: index for index, node in enumerate(graph.nodes)}
    incoming: dict[str, int] = {node.id: 0 for node in graph.nodes}
    successors: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        incoming[edge.to_node] += 1
        successors[edge.from_node].append(edge.to_node)

    ready = sorted(
        (node_id for node_id, count in incoming.items() if count == 0),
        key=lambda node_id: order_index[node_id],
    )
    ordered: list[NodeSpec] = []
    while ready:
        current = ready.pop(0)
        ordered.append(by_id[current])
        for successor in successors[current]:
            incoming[successor] -= 1
            if incoming[successor] == 0:
                ready.append(successor)
                ready.sort(key=lambda node_id: order_index[node_id])
    # цикл невозможен: load_graph_config уже отверг бы граф
    return ordered


def _strip_wiki_prefix(path: str) -> str:
    normalized = path.strip("/")
    if normalized == "wiki":
        return ""
    if normalized.startswith("wiki/"):
        return normalized[len("wiki/"):]
    return normalized


def _wiki_version(wiki_root: Path) -> str:
    index = wiki_root / "index.md"
    if not index.is_file():
        return "v0"
    match = _WIKI_VERSION_RE.search(index.read_text(encoding="utf-8"))
    return f"v{match.group(1)}" if match else "v0"
