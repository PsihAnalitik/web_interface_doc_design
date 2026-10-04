"""TSK-0903 CLI-вход.

Подкоманды:
    python -m workshop run <graph.json> <input: файл|текст> [--store DIR] [--log FILE] [--resume]
    python -m workshop extract <артефакт.xml> <каталог>
    python -m workshop package <graph.json> [--out DIR] [--store DIR] [--log FILE]
    python -m workshop verify-acceptance <каталог-цеха | CHANGELOG.md>
    python -m workshop assemble <product.json> [--out DIR]
    python -m workshop decompose <graph.json> [--store DIR] [--out DIR]
    python -m workshop wiki-check [--wiki DIR]
    python -m workshop skill-export <цех> --out DIR [--wiki DIR] [--date ГГГГ-ММ-ДД]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from workshop.acceptance import verify_acceptance
from workshop.artifact_store import ArtifactStore
from workshop.assembler import assemble_product
from workshop.codegen_loop import extract_files
from workshop.config_loader import load_graph_config, load_product_spec
from workshop.decomposer import decompose
from workshop.hitl_cli import HITL, CliHITL
from workshop.llm_client import LLMClient
from workshop.openai_llm import OpenAILLM
from workshop.codegen_loop import SandboxRunner
from workshop.orchestrator import run_pipeline
from workshop.packager import build_package
from workshop.result import Err
from workshop.skill_exporter import export_skill
from workshop.run_log import RunLog
from workshop.sandbox import run_in_docker
from workshop.factory_cli import discover_shops, project_status, run_menu
from workshop.wiki_applier import apply_file_map
from workshop.wiki_loader import collect_problems
from workshop.wiki_renderer import render_wiki


def load_dotenv(path: Path) -> None:
    """Подгружает KEY=VALUE из .env; уже заданное окружение НЕ перекрывается."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if key.strip() and value.strip():
            os.environ.setdefault(key.strip(), value.strip())


def main(
    argv: list[str] | None = None,
    llm: LLMClient | None = None,
    hitl: HITL | None = None,
    sandbox: SandboxRunner | None = None,
) -> int:
    load_dotenv(Path(".env"))
    parser = argparse.ArgumentParser(prog="workshop", description="Агентская мастерская")
    # без подкоманды → интерактивное меню фабрики (FR-22, TSK-1903)
    subparsers = parser.add_subparsers(dest="command", required=False)

    run_parser = subparsers.add_parser(
        "run", help="запустить цех: по имени (см. shops) или по пути к graph.json"
    )
    run_parser.add_argument("graph", help="имя цеха или путь к graph.json")
    run_parser.add_argument(
        "--autopilot", action="store_true",
        help="при запуске по имени взять graph.autopilot.json цеха",
    )
    run_parser.add_argument("input", help="входной материал: путь к файлу или сам текст")
    run_parser.add_argument(
        "--store", default=None,
        help="каталог стора артефактов (дефолт: projects/<project>/artifacts)",
    )
    run_parser.add_argument(
        "--log", default=None,
        help="файл журнала прогонов (дефолт: projects/<project>/runs/log.jsonl)",
    )
    run_parser.add_argument(
        "--resume", action="store_true",
        help="пропустить узлы, чьи артефакты уже приняты в сторе (TSK-0905)",
    )
    run_parser.add_argument(
        "--project", default=None,
        help="переопределить project графа (дочерние прогоны декомпозиции, FR-15)",
    )

    extract_parser = subparsers.add_parser(
        "extract", help="распаковать file map артефакта в каталог"
    )
    extract_parser.add_argument("artifact", help="путь к файлу артефакта (например, artifacts/executor/v1.xml)")
    extract_parser.add_argument("out_dir", help="каталог назначения (файлы не перезаписываются)")

    package_parser = subparsers.add_parser(
        "package", help="собрать выходной пакет проекта (FR-13) из принятых артефактов"
    )
    package_parser.add_argument("graph", help="путь к graph.json с блоком package")
    package_parser.add_argument("--out", default=None, help="каталог пакета (дефолт: projects/<project>/package)")
    package_parser.add_argument("--store", default=None, help="каталог стора артефактов")
    package_parser.add_argument("--log", default=None, help="файл журнала прогонов")

    acceptance_parser = subparsers.add_parser(
        "verify-acceptance",
        help="сверить файлы цеха с последней HITL-приёмкой в CHANGELOG (FR-17)",
    )
    acceptance_parser.add_argument(
        "target", help="каталог цеха (с CHANGELOG.md) или путь к CHANGELOG.md"
    )

    assemble_parser = subparsers.add_parser(
        "assemble", help="собрать продукт из сервисов-пакетов (FR-14)"
    )
    assemble_parser.add_argument("spec", help="путь к product.json")
    assemble_parser.add_argument(
        "--out", default=None, help="каталог продукта (дефолт: projects/<product>/product)"
    )

    decompose_parser = subparsers.add_parser(
        "decompose", help="породить подмодули-проекты из доменов domains.xml (FR-15)"
    )
    decompose_parser.add_argument("graph", help="путь к graph.json цеха")
    decompose_parser.add_argument("--store", default=None, help="каталог стора артефактов")
    decompose_parser.add_argument(
        "--out", default=None, help="каталог подмодулей (дефолт: projects/<project>/submodules)"
    )

    wiki_check_parser = subparsers.add_parser(
        "wiki-check",
        help="проверить wiki: index.md в каждой директории, кросс-ссылки, линт «{{» (FR-18)",
    )
    wiki_check_parser.add_argument(
        "--wiki", default="wiki", help="корень wiki-базы знаний (дефолт: wiki)"
    )

    wiki_render_parser = subparsers.add_parser(
        "wiki-render", help="отрендерить wiki в статический HTML-сайт (FR-20)"
    )
    wiki_render_parser.add_argument(
        "--wiki", default="wiki", help="корень wiki-базы знаний (дефолт: wiki)"
    )
    wiki_render_parser.add_argument(
        "--out", default="wiki_html", help="каталог сайта (дефолт: wiki_html)"
    )

    wiki_apply_parser = subparsers.add_parser(
        "wiki-apply",
        help="применить принятый file map страниц к wiki с полной проверкой (FR-21)",
    )
    wiki_apply_parser.add_argument(
        "artifact", help="путь к артефакту wiki_pages (например, .../wiki_pages/v1.xml)"
    )
    wiki_apply_parser.add_argument(
        "--wiki", default="wiki", help="корень wiki-базы знаний (дефолт: wiki)"
    )
    wiki_apply_parser.add_argument(
        "--spec",
        default=None,
        help="артефакт wiki_spec: материализовать страницу-исходник <source_page> "
        "(без него ссылка на исходник в страницах будет битой)",
    )

    map_parser = subparsers.add_parser(
        "map", help="массовый прогон цеха по элементам: файлы или таблицы schema.yaml (M-23)"
    )
    map_parser.add_argument("graph", help="имя цеха или путь к graph.json")
    map_source = map_parser.add_mutually_exclusive_group(required=True)
    map_source.add_argument(
        "--files", default=None, action="append",
        help="glob файлов-элементов (например, 'prompts/*.md'); можно повторять "
             "для нескольких паттернов ({a,b}-скобки glob не поддерживает)",
    )
    map_source.add_argument(
        "--schema-tables", default=None, help="путь к schema.yaml — элемент = таблица"
    )
    map_parser.add_argument(
        "--table-cards", default=None,
        help="каталог table_cards/*.yaml — карточки добавляются к таблицам",
    )
    map_parser.add_argument(
        "--tools", default=None,
        help="tools.yaml — MCP-инструменты подшиваются к таблицам по полю table (TSK-2305)",
    )
    map_parser.add_argument(
        "--templates", default=None,
        help="каталог шаблонов (table.yaml/table_card.yaml/tool.yaml) — дет-проверки структуры (TSK-2304)",
    )
    map_parser.add_argument(
        "--autopilot", action="store_true",
        help="при запуске по имени взять graph.autopilot.json цеха",
    )
    map_parser.add_argument(
        "--resume", action="store_true",
        help="пропустить элементы, чей последний узел уже принят",
    )
    map_parser.add_argument(
        "--limit", type=int, default=None, help="обрезать список элементов (smoke)"
    )
    map_parser.add_argument(
        "--workers", type=int, default=1,
        help="параллельные прогоны элементов (потолок 16; hitl-цеха — только 1)",
    )

    skill_parser = subparsers.add_parser(
        "skill-export",
        help="скомпилировать цех в Skill для Claude Code (TSK-2701)",
    )
    skill_parser.add_argument("graph", help="имя цеха или путь к graph.json")
    skill_parser.add_argument(
        "--out", required=True,
        help="каталог репозитория скиллов: пишется <out>/<имя скилла>/",
    )
    skill_parser.add_argument("--wiki", default="wiki", help="корень wiki для снимка справок")
    skill_parser.add_argument(
        "--date", default="",
        help="дата снимка в строке SKILL.md (дефолт: без даты)",
    )

    subparsers.add_parser("shops", help="реестр цехов фабрики (FR-22)")

    subparsers.add_parser(
        "mcp-serve", help="MCP-сервер фабрики поверх stdio (FR-23)"
    )

    status_parser = subparsers.add_parser(
        "status", help="статус проектов: артефакты и журналы (FR-22)"
    )
    status_parser.add_argument(
        "--project", default=None, help="имя проекта (дефолт: все projects/*)"
    )

    args = parser.parse_args(argv)
    if args.command is None:
        return _menu_command(llm, hitl, sandbox)
    if args.command == "extract":
        return _extract_command(args)
    elif args.command == "package":
        return _package_command(args, sandbox)
    elif args.command == "verify-acceptance":
        return _verify_acceptance_command(args)
    elif args.command == "assemble":
        return _assemble_command(args)
    elif args.command == "decompose":
        return _decompose_command(args)
    elif args.command == "wiki-check":
        return _wiki_check_command(args)
    elif args.command == "wiki-render":
        return _wiki_render_command(args)
    elif args.command == "wiki-apply":
        return _wiki_apply_command(args)
    elif args.command == "skill-export":
        return _skill_export_command(args)
    elif args.command == "shops":
        return _shops_command()
    elif args.command == "mcp-serve":
        # локальный импорт: mcp SDK нужен только серверу (решение §10 №15)
        from workshop.mcp_server import serve
        return serve()
    elif args.command == "status":
        return _status_command(args)
    elif args.command == "map":
        return _map_command(args, llm, hitl)
    return _run_command(args, llm, hitl)


def _resolve_graph_arg(graph_arg: str, autopilot: bool) -> str | None:
    """Имя цеха → путь к графу (TSK-1901); существующий путь возвращается как есть."""
    if Path(graph_arg).is_file():
        return graph_arg
    shops = discover_shops()
    if isinstance(shops, Err):
        return None
    for shop in shops.value:
        if shop.name == graph_arg and shop.error is None:
            if autopilot:
                return shop.autopilot_path  # None → у цеха нет autopilot
            return shop.graph_path
    return None


def _skill_export_command(args: argparse.Namespace) -> int:
    graph_path = _resolve_graph_arg(args.graph, autopilot=False)
    if graph_path is None:
        print(f"цех или граф не найден: {args.graph}", file=sys.stderr)
        return 1
    report = export_skill(
        graph_path,
        out_root=Path(args.out),
        wiki_root=Path(args.wiki),
        snapshot_date=args.date,
    )
    if isinstance(report, Err):
        print(f"{report.code}: {report.details}", file=sys.stderr)
        return 1
    print(f"скилл собран: {report.value.skill_dir}")
    print(f"  фазы: {', '.join(report.value.phases)}")
    print(f"  ревью: {', '.join(report.value.reviews) or '—'}")
    print(f"  справки: wiki {report.value.wiki_version}, области "
          f"{', '.join(report.value.areas)}")
    print("  ПЕРЕД коммитом в публичный репозиторий: прогнать проверку "
          "обезличивания (см. user_docs/skills_export_design.md §12)")
    return 0


def _shops_command() -> int:
    shops = discover_shops()
    if isinstance(shops, Err):
        print(f"реестр не собран: {shops.code}: {shops.details}", file=sys.stderr)
        return 1
    for shop in shops.value:
        if shop.error is not None:
            print(f"{shop.name}: ОШИБКА КОНФИГА — {shop.error}", file=sys.stderr)
            continue
        chain = " → ".join(
            f"{stage.node_id}[{stage.gates}]" for stage in shop.stages
        )
        autopilot = "autopilot: да" if shop.autopilot_path else "autopilot: нет"
        project = f"project: {shop.project}" if shop.project else "project: —"
        print(f"{shop.name} ({project}; {autopilot})\n  {chain}")
    return 0


def _status_command(args: argparse.Namespace) -> int:
    projects_root = Path("projects")
    if args.project is not None:
        targets = [projects_root / args.project]
    elif projects_root.is_dir():
        targets = sorted(d for d in projects_root.iterdir() if d.is_dir())
    else:
        print("каталог projects/ отсутствует", file=sys.stderr)
        return 1

    exit_code = 0
    for project_dir in targets:
        status = project_status(project_dir)
        if isinstance(status, Err):
            print(f"{project_dir.name}: {status.code}: {status.details}", file=sys.stderr)
            exit_code = 1
            continue
        print(f"[{project_dir.name}]")
        for name, version in status.value.artifacts:
            iterations = dict(status.value.journal).get(name)
            suffix = f" (итераций: {iterations})" if iterations else ""
            print(f"  {name} v{version}{suffix}")
        if not status.value.artifacts:
            print("  артефактов нет")
    return exit_code


def _menu_command(
    llm: LLMClient | None, hitl: HITL | None, sandbox: SandboxRunner | None
) -> int:
    shops = discover_shops()
    if isinstance(shops, Err):
        print(f"реестр не собран: {shops.code}: {shops.details}", file=sys.stderr)
        return 1

    def runner(graph_path: str, material: str) -> int:
        return main(["run", graph_path, material], llm=llm, hitl=hitl, sandbox=sandbox)

    return run_menu(shops.value, runner)


def _wiki_render_command(args: argparse.Namespace) -> int:
    result = render_wiki(Path(args.wiki), Path(args.out))
    if isinstance(result, Err):
        print(f"рендер не удался: {result.code}: {result.details}", file=sys.stderr)
        return 1
    print(f"wiki-render: {len(result.value.pages)} страниц → {result.value.out_dir}")
    for broken in result.value.broken_links:
        print(f"битая ссылка: {broken}", file=sys.stderr)
    return 0


def _wiki_check_command(args: argparse.Namespace) -> int:
    root = Path(args.wiki)
    if not root.is_dir():
        print(f"wiki не найдена: {root}", file=sys.stderr)
        return 1

    problems = collect_problems(root)
    if isinstance(problems, Err):
        print(f"проверка не выполнена: {problems.code}: {problems.details}", file=sys.stderr)
        return 1
    print(f"wiki-check: {len(sorted(root.rglob('*.md')))} страниц проверено")
    for problem in problems.value:
        print(problem, file=sys.stderr)
    if problems.value:
        print(f"wiki-check: {len(problems.value)} проблем", file=sys.stderr)
        return 1
    return 0


def _wiki_apply_command(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact)
    if not artifact_path.is_file():
        print(f"артефакт не найден: {artifact_path}", file=sys.stderr)
        return 1
    spec_content: str | None = None
    if args.spec is not None:
        spec_path = Path(args.spec)
        if not spec_path.is_file():
            print(f"спека не найдена: {spec_path}", file=sys.stderr)
            return 1
        spec_content = spec_path.read_text(encoding="utf-8")
    result = apply_file_map(
        artifact_path.read_text(encoding="utf-8"), Path(args.wiki), spec_content
    )
    if isinstance(result, Err):
        print(f"применение отклонено: {result.code}: {result.details}", file=sys.stderr)
        return 1
    for rel_path in result.value.written:
        print(f"записан: {args.wiki}/{rel_path}")
    print("строки для wiki/CHANGELOG.md:")
    for row in result.value.changelog_rows:
        print(row)
    return 0


def _decompose_command(args: argparse.Namespace) -> int:
    graph = load_graph_config(args.graph)
    if isinstance(graph, Err):
        print(f"ошибка конфига графа: {graph.code}: {graph.details}", file=sys.stderr)
        return 1
    project = graph.value.project if graph.value.project is not None else "default"
    store_dir = args.store if args.store is not None else f"projects/{project}/artifacts"
    out_dir = args.out if args.out is not None else f"projects/{project}/submodules"

    result = decompose(ArtifactStore(Path(store_dir)), project, Path(out_dir))
    if isinstance(result, Err):
        print(f"декомпозиция не удалась: {result.code}: {result.details}", file=sys.stderr)
        return 1
    for name in result.value.submodules:
        print(f"подмодуль: {name} → {out_dir}/{name}/input.xml")
    print(f"черновик продукта: {result.value.product_spec_path}")
    for fr_id in result.value.uncovered_frs:
        print(f"ВНИМАНИЕ: {fr_id} не покрыт ни одним доменом", file=sys.stderr)
    print(
        "дочерний прогон: python -m workshop run <цех.json> "
        f"{out_dir}/<имя>/input.xml --project {project}-<имя>"
    )
    return 0


def _assemble_command(args: argparse.Namespace) -> int:
    spec = load_product_spec(args.spec)
    if isinstance(spec, Err):
        print(f"ошибка спеки продукта: {spec.code}: {spec.details}", file=sys.stderr)
        return 1
    if args.out is not None:
        out_dir = Path(args.out)
    else:
        out_dir = Path(f"projects/{spec.value.product}/product")

    result = assemble_product(spec.value, out_dir)
    if isinstance(result, Err):
        print(f"сборка продукта не удалась: {result.code}: {result.details}", file=sys.stderr)
        return 1
    for name in result.value.services:
        print(f"сервис: {name}")
    print(f"git-коммит: {result.value.git_commit}")
    print(f"продукт: {result.value.out_dir}")
    return 0


def _verify_acceptance_command(args: argparse.Namespace) -> int:
    target = Path(args.target)
    changelog_path = target / "CHANGELOG.md" if target.is_dir() else target

    result = verify_acceptance(changelog_path)
    if isinstance(result, Err):
        print(f"проверка не выполнена: {result.code}: {result.details}", file=sys.stderr)
        return 1
    report = result.value
    print(f"по приёмке: {len(report.matched)} файлов актуальны")
    for rel_path in report.mismatched:
        print(f"ИЗМЕНЁН без приёмки: {rel_path}", file=sys.stderr)
    for rel_path in report.missing:
        print(f"ОТСУТСТВУЕТ: {rel_path}", file=sys.stderr)
    if not report.is_clean:
        print("приёмка НЕ актуальна — нужна новая запись в CHANGELOG", file=sys.stderr)
        return 1
    return 0


def _extract_command(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact)
    if not artifact_path.is_file():
        print(f"артефакт не найден: {artifact_path}", file=sys.stderr)
        return 1
    result = extract_files(
        artifact_path.read_text(encoding="utf-8"), Path(args.out_dir)
    )
    if isinstance(result, Err):
        print(f"извлечение не удалось: {result.code}: {result.details}", file=sys.stderr)
        return 1
    for rel_path in result.value:
        print(f"записан: {args.out_dir}/{rel_path}")
    return 0


def _package_command(args: argparse.Namespace, sandbox: SandboxRunner | None) -> int:
    graph = load_graph_config(args.graph)
    if isinstance(graph, Err):
        print(f"ошибка конфига графа: {graph.code}: {graph.details}", file=sys.stderr)
        return 1
    if graph.value.package is None:
        print("в конфиге графа нет блока package (FR-13)", file=sys.stderr)
        return 1
    project = graph.value.project if graph.value.project is not None else "default"

    store_dir = args.store if args.store is not None else f"projects/{project}/artifacts"
    log_path = args.log if args.log is not None else f"projects/{project}/runs/log.jsonl"
    out_dir = args.out if args.out is not None else f"projects/{project}/package"

    result = build_package(
        ArtifactStore(Path(store_dir)),
        graph.value.package,
        project,
        Path(log_path),
        Path(out_dir),
        sandbox if sandbox is not None else run_in_docker,
    )
    if isinstance(result, Err):
        print(f"сборка пакета не удалась: {result.code}: {result.details}", file=sys.stderr)
        return 1
    for name in result.value.files:
        print(f"в пакете: {name}")
    print(f"git-коммит: {result.value.git_commit}")
    print(f"пакет: {result.value.out_dir}")
    return 0


def _map_command(
    args: argparse.Namespace, llm: LLMClient | None, hitl: HITL | None
) -> int:
    # локальный импорт: PyYAML нужен только map-драйверу (прецедент mcp-serve)
    from workshop.map_driver import map_run, split_files, split_schema_tables

    graph_path = _resolve_graph_arg(args.graph, args.autopilot)
    if graph_path is None:
        print(
            f"не найден ни файл, ни цех с именем «{args.graph}» "
            f"(см. python -m workshop shops)",
            file=sys.stderr,
        )
        return 1
    graph = load_graph_config(graph_path)
    if isinstance(graph, Err):
        print(f"ошибка конфига графа: {graph.code}: {graph.details}", file=sys.stderr)
        return 1

    if args.files is not None:
        items = split_files(args.files)
    else:
        items = split_schema_tables(
            args.schema_tables, args.table_cards, args.tools, args.templates
        )
    if isinstance(items, Err):
        print(f"нарезка элементов не удалась: {items.code}: {items.details}", file=sys.stderr)
        return 1

    project = graph.value.project if graph.value.project is not None else "default"
    report = map_run(
        graph.value,
        items.value,
        llm if llm is not None else OpenAILLM(),
        hitl if hitl is not None else CliHITL(),
        Path(f"projects/{project}"),
        resume=args.resume,
        limit=args.limit,
        workers=args.workers,
    )
    if isinstance(report, Err):
        print(f"map остановлен: {report.code}: {report.details}", file=sys.stderr)
        return 1
    failed = 0
    for row in report.value.rows:
        print(f"{row.status}: {row.slug} — {row.details}")
        if row.status == "failed":
            failed += 1
    print(f"сводка: {report.value.summary_path}")
    return 1 if failed else 0


def _run_command(
    args: argparse.Namespace, llm: LLMClient | None, hitl: HITL | None
) -> int:
    graph_path = _resolve_graph_arg(args.graph, getattr(args, "autopilot", False))
    if graph_path is None:
        print(
            f"не найден ни файл, ни цех с именем «{args.graph}» "
            f"(см. python -m workshop shops)",
            file=sys.stderr,
        )
        return 1
    graph = load_graph_config(graph_path)
    if isinstance(graph, Err):
        print(f"ошибка конфига графа: {graph.code}: {graph.details}", file=sys.stderr)
        return 1

    project = args.project if args.project is not None else graph.value.project
    if args.store is not None:
        store_dir = args.store
    elif project is not None:
        store_dir = f"projects/{project}/artifacts"
    else:
        store_dir = "artifacts"
    if args.log is not None:
        log_path = args.log
    elif project is not None:
        log_path = f"projects/{project}/runs/log.jsonl"
    else:
        log_path = "runs/log.jsonl"

    input_path = Path(args.input)
    if input_path.is_file():
        initial_content = input_path.read_text(encoding="utf-8")
    else:
        initial_content = args.input

    result = run_pipeline(
        graph.value,
        initial_content,
        ArtifactStore(Path(store_dir)),
        llm if llm is not None else OpenAILLM(),
        RunLog(Path(log_path)),
        hitl if hitl is not None else CliHITL(),
        resume=args.resume,
    )
    if isinstance(result, Err):
        print(f"пайплайн остановлен: {result.code}: {result.details}", file=sys.stderr)
        return 1

    for ref in result.value.accepted_artifacts:
        print(f"принят: {ref.name} v{ref.version}")
    print(f"журнал: {result.value.log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
