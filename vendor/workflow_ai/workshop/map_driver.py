"""M-23 map_driver: массовый прогон цеха по списку элементов (TSK-2301..2303).

Оркестратор M-09 гоняет линейный DAG один раз; итерация по элементам
(файлы промптов, таблицы schema.yaml) живёт здесь: детерминированная нарезка
источника → прогон пайплайна на элемент со своим под-стором → сводка.
Ошибка одного элемента не останавливает остальные.
"""
from __future__ import annotations

import glob as glob_module
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import yaml

from workshop.artifact_store import ArtifactStore
from workshop.codegen_loop import SandboxRunner
from workshop.hitl_cli import HITL
from workshop.llm_client import LLMClient
from workshop.models import GraphConfig
from workshop.orchestrator import run_pipeline
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog
from workshop.sandbox import run_in_docker

MAP_NO_ITEMS = "MAP_NO_ITEMS"
MAP_SOURCE_INVALID = "MAP_SOURCE_INVALID"
MAP_PARALLEL_HITL = "MAP_PARALLEL_HITL"

_MAX_WORKERS = 16


@dataclass(frozen=True)
class MapItem:
    slug: str      # стабильное имя элемента: имя файла / schema.table
    title: str
    content: str   # входной материал прогона


def defuse_placeholders(text: str) -> tuple[str, int]:
    """Разводит двойные фигурные скобки пробелом: «{{» → «{ {».

    WHY (TSK-2619): узел цитирует такое место в отчёте, отчёт уходит в промпт
    приёмщика через INPUTS и роняет его сборку (UNRESOLVED_PLACEHOLDER,
    TSK-0302) — элемент теряется целиком. inline_limit_chars=0 закрывает
    только половину шва: сам материал в промпт не попадает, а цитата из него
    попадает. Правило «не цитируй двойные скобки» в промпте вероятностно и на
    практике нарушается, поэтому замена делается ДЕТЕРМИНИРОВАННО и до модели
    (образец — санитизация TOC, TSK-2207).

    Возвращает текст и число замен: ненулевое требует пометки в элементе —
    у prompt_roaster двойные скобки сами являются предметом ревью, и молчаливая
    подмена превратилась бы в ложную находку «сломанный плейсхолдер».
    """
    count = text.count("{" "{") + text.count("}" "}")
    if count == 0:
        return text, 0
    return text.replace("{" "{", "{ {").replace("}" "}", "} }"), count


def _placeholder_note(count: int) -> str:
    if count == 0:
        return ""
    return (
        f"\nВнимание: в тексте {count} мест с двойными фигурными скобками — "
        f"при сборке элемента они разведены пробелом («{{ {{»). В исходнике "
        f"они записаны слитно; считай их корректными плейсхолдерами."
    )


@dataclass(frozen=True)
class MapRow:
    slug: str
    status: str    # done | failed | skipped
    details: str


@dataclass(frozen=True)
class MapReport:
    rows: tuple[MapRow, ...]
    summary_path: str


def split_files(pattern: str | Sequence[str]) -> Result[list[MapItem]]:
    """TSK-2301а: элемент = файл по glob; slug = имя файла без расширения.

    Принимает один паттерн или несколько (повторяемый --files): {a,b}-скобки
    Python-glob не понимает, объединение паттернов — здесь, с дедупликацией.
    """
    patterns = [pattern] if isinstance(pattern, str) else list(pattern)
    matched = {
        Path(p) for pat in patterns for p in glob_module.glob(pat) if Path(p).is_file()
    }
    paths = sorted(matched)
    if not paths:
        return Err(MAP_NO_ITEMS, f"glob не нашёл файлов: {', '.join(patterns)}")
    slugs = _unique_slugs(paths)
    items: list[MapItem] = []
    for path, slug in zip(paths, slugs):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return Err(MAP_SOURCE_INVALID, f"{path}: {exc}")
        defused, defused_count = defuse_placeholders(text)
        items.append(
            MapItem(
                slug=slug,
                title=path.name,
                content=(
                    f"Ревьюируемый файл: {path.name}"
                    f"{_placeholder_note(defused_count)}\n\n{defused}"
                ),
            )
        )
    return Ok(items)


def _unique_slugs(paths: list[Path]) -> list[str]:
    """Слаг = имя файла без расширения; при коллизии (11 __init__.py разных
    пакетов сливались в один элемент) добавляются родительские каталоги
    (core____init__) до уникальности. Пути уникальны → цикл завершается."""
    depth = {path: 1 for path in paths}
    while True:
        slugs = [
            "__".join(path.with_suffix("").parts[-depth[path]:]) for path in paths
        ]
        counts: dict[str, int] = {}
        for slug in slugs:
            counts[slug] = counts.get(slug, 0) + 1
        duplicated = {slug for slug, count in counts.items() if count > 1}
        if not duplicated:
            return slugs
        for path, slug in zip(paths, slugs):
            if slug in duplicated and depth[path] < len(path.with_suffix("").parts):
                depth[path] += 1


def split_schema_tables(
    schema_path: str,
    cards_dir: str | None = None,
    tools_path: str | None = None,
    templates_dir: str | None = None,
) -> Result[list[MapItem]]:
    """TSK-2301б/2305: элемент = таблица schema.yaml + карточка + MCP-инструменты.

    tools.yaml индексируется по полю table; templates_dir даёт шаблонные
    дет-проверки TSK-2304 (table.yaml / table_card.yaml / tool.yaml).
    """
    path = Path(schema_path)
    if not path.is_file():
        return Err(MAP_SOURCE_INVALID, f"{schema_path}: файл не найден")
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return Err(MAP_SOURCE_INVALID, f"{schema_path}: {exc}")
    if not isinstance(parsed, dict) or "databases" not in parsed:
        return Err(MAP_SOURCE_INVALID, f"{schema_path}: нет ключа databases")

    tools_by_table: dict[str, list[dict]] = {}
    if tools_path is not None:
        tools_result = _load_tools_index(tools_path)
        if isinstance(tools_result, Err):
            return tools_result
        tools_by_table = tools_result.value

    templates: dict[str, dict] = {}
    if templates_dir is not None:
        templates_result = _load_templates(templates_dir)
        if isinstance(templates_result, Err):
            return templates_result
        templates = templates_result.value

    items: list[MapItem] = []
    for db_name, db_def in sorted(parsed["databases"].items()):
        schemas = db_def.get("schemas") if isinstance(db_def, dict) else None
        if not isinstance(schemas, dict):
            continue
        for schema_name, schema_def in sorted(schemas.items()):
            tables = schema_def.get("tables") if isinstance(schema_def, dict) else None
            if not isinstance(tables, dict):
                continue
            for table_name, table_def in sorted(tables.items()):
                slug = f"{schema_name}.{table_name}"
                content = _table_item_content(
                    db_name, schema_name, table_name, table_def, cards_dir,
                    tools_by_table.get(slug, []), templates,
                )
                items.append(MapItem(slug=slug, title=slug, content=content))
    if not items:
        return Err(MAP_NO_ITEMS, f"{schema_path}: таблиц не найдено")
    return Ok(items)


def check_template(data: dict, template: dict, label: str) -> list[str]:
    """TSK-2304: пропуски required, неизвестные ключи, nested-правила «для каждого»."""
    findings: list[str] = []
    if not isinstance(data, dict):
        return [f"[шаблон {label}] артефакт — не словарь"]
    required = list(template.get("required", []))
    optional = list(template.get("optional", []))
    nested = template.get("nested", {}) if isinstance(template.get("nested"), dict) else {}

    for key in required:
        value = data.get(key)
        if value is None or (isinstance(value, (str, list, dict)) and not value):
            findings.append(f"[шаблон {label}] отсутствует/пуст обязательный ключ «{key}»")
    known = set(required) | set(optional) | set(nested)
    for key in data:
        if key not in known:
            findings.append(f"[шаблон {label}] неизвестный ключ «{key}» (дрейф формата?)")
    for nested_key, nested_template in nested.items():
        container = data.get(nested_key)
        if not isinstance(container, dict):
            continue
        for entry_name, entry in container.items():
            if not isinstance(entry, dict):
                findings.append(
                    f"[шаблон {label}] {nested_key}.{entry_name}: не словарь"
                )
                continue
            findings.extend(
                finding.replace(f"[шаблон {label}]", f"[шаблон {label}] {nested_key}.{entry_name}:")
                for finding in check_template(
                    entry,
                    {k: v for k, v in nested_template.items() if k != "nested"},
                    label,
                )
            )
    return findings


def _load_tools_index(tools_path: str) -> Result[dict[str, list[dict]]]:
    path = Path(tools_path)
    if not path.is_file():
        return Err(MAP_SOURCE_INVALID, f"{tools_path}: файл не найден")
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return Err(MAP_SOURCE_INVALID, f"{tools_path}: {exc}")
    tools = parsed.get("tools") if isinstance(parsed, dict) else None
    if not isinstance(tools, list):
        return Err(MAP_SOURCE_INVALID, f"{tools_path}: нет списка tools")
    index: dict[str, list[dict]] = {}
    for tool in tools:
        if isinstance(tool, dict) and isinstance(tool.get("table"), str):
            index.setdefault(tool["table"], []).append(tool)
    return Ok(index)


def _load_templates(templates_dir: str) -> Result[dict[str, dict]]:
    """Шаблоны по видам артефактов: table.yaml / table_card.yaml / tool.yaml."""
    root = Path(templates_dir)
    if not root.is_dir():
        return Err(MAP_SOURCE_INVALID, f"{templates_dir}: не директория")
    templates: dict[str, dict] = {}
    for kind in ("table", "table_card", "tool"):
        template_path = root / f"{kind}.yaml"
        if not template_path.is_file():
            continue
        try:
            parsed = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return Err(MAP_SOURCE_INVALID, f"{template_path}: {exc}")
        if not isinstance(parsed, dict):
            return Err(MAP_SOURCE_INVALID, f"{template_path}: ожидается словарь")
        templates[kind] = parsed
    if not templates:
        return Err(MAP_SOURCE_INVALID, f"{templates_dir}: нет ни одного шаблона")
    return Ok(templates)


def check_table(table_def: dict) -> list[str]:
    """TSK-2303: детерминированные проверки таблицы ДО LLM; пусто = пройдены."""
    findings: list[str] = []
    if not isinstance(table_def, dict):
        return ["определение таблицы — не словарь"]
    columns = table_def.get("columns")
    if not isinstance(columns, dict) or not columns:
        findings.append("нет ни одной колонки (columns пуст)")
        columns = {}
    if not str(table_def.get("description", "")).strip():
        findings.append("пустое description")
    if not str(table_def.get("granularity", "")).strip():
        findings.append("пустое granularity")
    for metric in table_def.get("fact_metrics", []) or []:
        if not isinstance(metric, dict):
            findings.append(f"fact_metrics: не-словарь {metric!r}")
        elif metric.get("column") not in columns:
            findings.append(
                f"fact_metrics.column «{metric.get('column')}» отсутствует в columns"
            )
    return findings


def map_run(
    graph: GraphConfig,
    items: list[MapItem],
    llm: LLMClient,
    hitl: HITL,
    base_dir: Path,
    resume: bool = False,
    limit: int | None = None,
    sandbox: SandboxRunner = run_in_docker,
    workers: int = 1,
) -> Result[MapReport]:
    """TSK-2302/2306: прогон цеха на каждый элемент; ошибка элемента → строка сводки.

    workers>1 — пул потоков (LLM-вызовы I/O-bound): элементы независимы
    (свой под-стор/журнал), сводка — в порядке элементов, не завершения.
    """
    if not items:
        return Err(MAP_NO_ITEMS, "пустой список элементов")
    if limit is not None:
        items = items[:limit]
    workers = min(max(workers, 1), _MAX_WORKERS)
    if workers > 1 and any(node.gates.hitl for node in graph.nodes):
        return Err(
            MAP_PARALLEL_HITL,
            "hitl-гейты несовместимы с параллельным map — запусти с --workers 1",
        )
    last_node_id = graph.nodes[-1].id

    def run_item(item: MapItem) -> MapRow:
        item_dir = base_dir / "map" / _fs_slug(item.slug)
        store = ArtifactStore(item_dir / "artifacts")
        if resume and isinstance(store.latest_version(last_node_id), Ok):
            return MapRow(item.slug, "skipped", "принят в прошлом прогоне")
        result = run_pipeline(
            graph,
            item.content,
            store,
            llm,
            RunLog(item_dir / "log.jsonl"),
            hitl,
            sandbox=sandbox,
        )
        if isinstance(result, Err):
            return MapRow(item.slug, "failed", f"{result.code}: {result.details}")
        accepted = ", ".join(
            f"{ref.name} v{ref.version}" for ref in result.value.accepted_artifacts
        )
        return MapRow(item.slug, "done", accepted)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        # результат map — в порядке подачи элементов: сводка детерминированна
        rows = list(pool.map(run_item, items))

    summary_path = base_dir / "map" / "summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_render_summary(rows), encoding="utf-8")
    return Ok(MapReport(rows=tuple(rows), summary_path=str(summary_path)))


def _table_item_content(
    db_name: str,
    schema_name: str,
    table_name: str,
    table_def: dict,
    cards_dir: str | None,
    tools: list[dict],
    templates: dict[str, dict],
) -> str:
    parts = [
        f"Проверяемая таблица: {db_name} / {schema_name}.{table_name}",
        "",
        "```yaml",
        yaml.safe_dump(
            {table_name: table_def}, allow_unicode=True, sort_keys=False
        ).strip(),
        "```",
    ]
    findings = check_table(table_def)
    if "table" in templates:
        findings.extend(check_template(table_def, templates["table"], "table"))

    card_data: dict | None = None
    if cards_dir is not None:
        card_path = Path(cards_dir) / f"{schema_name}_{table_name}.yaml"
        if card_path.is_file():
            card_text = card_path.read_text(encoding="utf-8").strip()
            parts += [
                "",
                f"Карточка таблицы ({card_path.name}):",
                "```yaml",
                card_text,
                "```",
            ]
            try:
                card_data = yaml.safe_load(card_text)
            except yaml.YAMLError:
                findings.append(f"[карточка] {card_path.name}: невалидный YAML")
        else:
            parts += ["", "Карточки таблицы в table_cards НЕТ (это находка сама по себе)."]
    if card_data is not None and "table_card" in templates:
        findings.extend(check_template(card_data, templates["table_card"], "table_card"))

    if tools:
        parts += ["", f"MCP-инструменты таблицы из tools.yaml ({len(tools)} шт.):"]
        for tool in tools:
            parts += [
                "```yaml",
                yaml.safe_dump(tool, allow_unicode=True, sort_keys=False).strip(),
                "```",
            ]
            if "tool" in templates:
                findings.extend(
                    check_template(tool, templates["tool"], f"tool {tool.get('name', '?')}")
                )
    else:
        parts += ["", "MCP-инструментов для таблицы в tools.yaml НЕТ (сверять нечего — отметь в T6)."]

    if findings:
        finding_lines = "\n".join(f"- {finding}" for finding in findings)
        parts += ["", "<deterministic_findings>", finding_lines, "</deterministic_findings>"]
    # карточки таблиц и domain_rules — фрагменты промпта: двойные скобки
    # в них встречаются и роняют сборку так же, как в файлах-элементах
    defused, defused_count = defuse_placeholders("\n".join(parts))
    if defused_count == 0:
        return defused
    return defused.replace(
        f"Проверяемая таблица: {db_name} / {schema_name}.{table_name}",
        f"Проверяемая таблица: {db_name} / {schema_name}.{table_name}"
        f"{_placeholder_note(defused_count)}",
        1,
    )


def _fs_slug(slug: str) -> str:
    return slug.replace("/", "_").replace(".", "_")


def _render_summary(rows: list[MapRow]) -> str:
    lines = [
        "# map: сводка прогона",
        "",
        "| Элемент | Статус | Детали |",
        "|---|---|---|",
    ]
    for row in rows:
        details = row.details.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{row.slug}` | {row.status} | {details} |")
    counts = {status: sum(1 for r in rows if r.status == status)
              for status in ("done", "failed", "skipped")}
    lines += [
        "",
        f"Итого: done {counts['done']}, failed {counts['failed']}, "
        f"skipped {counts['skipped']} из {len(rows)}.",
    ]
    return "\n".join(lines) + "\n"
