"""M-19 factory_cli: реестр цехов, статус проектов, интерактивное меню (FR-22)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from workshop.artifact_store import ArtifactStore
from workshop.config_loader import load_graph_config
from workshop.result import Err, Ok, Result

SHOPS_ROOT_NOT_FOUND = "SHOPS_ROOT_NOT_FOUND"
PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"

_GRAPH_NAME = "graph.json"
_AUTOPILOT_NAME = "graph.autopilot.json"


@dataclass(frozen=True)
class StageInfo:
    node_id: str
    kind: str
    gates: str  # человекочитаемо: "review+hitl" / "judge" / "—"


@dataclass(frozen=True)
class ShopInfo:
    name: str
    graph_path: str
    autopilot_path: str | None
    project: str | None
    stages: tuple[StageInfo, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class ProjectStatus:
    artifacts: tuple[tuple[str, int], ...]   # (имя, макс. версия)
    journal: tuple[tuple[str, int], ...]     # (узел журнала, макс. итерация)


def discover_shops(configs_root: Path = Path("configs")) -> Result[list[ShopInfo]]:
    """TSK-1901: реестр цехов; битый graph.json одного цеха не валит остальные."""
    if not configs_root.is_dir():
        return Err(SHOPS_ROOT_NOT_FOUND, str(configs_root))

    shops: list[ShopInfo] = []
    for shop_dir in sorted(d for d in configs_root.iterdir() if d.is_dir()):
        graph_path = shop_dir / _GRAPH_NAME
        if not graph_path.is_file():
            continue  # каталог без графа (например, products/) — не цех
        autopilot = shop_dir / _AUTOPILOT_NAME
        autopilot_path = str(autopilot) if autopilot.is_file() else None

        graph = load_graph_config(str(graph_path))
        if isinstance(graph, Err):
            shops.append(ShopInfo(
                name=shop_dir.name, graph_path=str(graph_path),
                autopilot_path=autopilot_path, project=None,
                error=f"{graph.code}: {graph.details}",
            ))
            continue

        stages = tuple(
            StageInfo(node_id=node.id, kind=node.kind, gates=_render_gates(node))
            for node in graph.value.nodes
        )
        shops.append(ShopInfo(
            name=shop_dir.name, graph_path=str(graph_path),
            autopilot_path=autopilot_path, project=graph.value.project,
            stages=stages,
        ))
    return Ok(shops)


def project_status(project_dir: Path) -> Result[ProjectStatus]:
    """TSK-1902: артефакты стора + агрегат журнала прогонов проекта."""
    if not project_dir.is_dir():
        return Err(PROJECT_NOT_FOUND, str(project_dir))

    artifacts: tuple[tuple[str, int], ...] = ()
    store_dir = project_dir / "artifacts"
    if store_dir.is_dir():
        refs = ArtifactStore(store_dir).list_artifacts()
        latest: dict[str, int] = {}
        for ref in refs:
            latest[ref.name] = max(latest.get(ref.name, 0), ref.version)
        artifacts = tuple(sorted(latest.items()))

    journal: dict[str, int] = {}
    log_path = project_dir / "runs" / "log.jsonl"
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # битая строка журнала статус не валит
            node = str(record.get("node_id", "?"))
            journal[node] = max(journal.get(node, 0), int(record.get("iteration", 0)))

    return Ok(ProjectStatus(artifacts=artifacts, journal=tuple(sorted(journal.items()))))


def run_menu(
    shops: list[ShopInfo],
    runner: Callable[[str, str], int],
    projects_root: Path = Path("projects"),
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> int:
    """TSK-1903: интерактивное меню фабрики; EOF/Ctrl-C — выход 0.

    runner(graph_path, input_material) — запуск цеха (DI для тестируемости).
    """
    try:
        while True:
            print_fn("\n=== Фабрика: выбери действие ===")
            print_fn(" 1) запустить цех")
            print_fn(" 2) статус проектов")
            print_fn(" 3) выход")
            choice = input_fn("> ").strip()
            if choice == "1":
                _menu_run_shop(shops, runner, input_fn, print_fn)
            elif choice == "2":
                _menu_status(projects_root, print_fn)
            elif choice == "3":
                return 0
            else:
                print_fn("Ожидаю 1 / 2 / 3.")
    except (EOFError, KeyboardInterrupt):
        return 0


def _menu_run_shop(
    shops: list[ShopInfo],
    runner: Callable[[str, str], int],
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> None:
    usable = [shop for shop in shops if shop.error is None]
    if not usable:
        print_fn("Нет исправных цехов.")
        return
    print_fn("Цеха:")
    for number, shop in enumerate(usable, start=1):
        chain = "→".join(stage.node_id for stage in shop.stages)
        print_fn(f" {number}) {shop.name} ({chain})")
    choice = input_fn("> ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(usable):
        print_fn("Нет такого цеха.")
        return
    shop = usable[int(choice) - 1]

    graph_path = shop.graph_path
    if shop.autopilot_path is not None:
        mode = input_fn("[i] интерактивный (HITL) / [a] autopilot: ").strip().lower()
        if mode == "a":
            graph_path = shop.autopilot_path
    material = input_fn("Вход (текст или путь к файлу): ").strip()
    if not material:
        print_fn("Пустой вход — отмена.")
        return
    exit_code = runner(graph_path, material)
    print_fn(f"Цех завершён (exit={exit_code}).")


def _menu_status(projects_root: Path, print_fn: Callable[[str], None]) -> None:
    if not projects_root.is_dir():
        print_fn("Каталог projects/ отсутствует.")
        return
    for project_dir in sorted(d for d in projects_root.iterdir() if d.is_dir()):
        status = project_status(project_dir)
        if isinstance(status, Err):
            continue
        print_fn(f"\n[{project_dir.name}]")
        if not status.value.artifacts:
            print_fn("  артефактов нет")
        for name, version in status.value.artifacts:
            print_fn(f"  {name} v{version}")


def _render_gates(node) -> str:
    parts: list[str] = []
    if node.gates.review_config_path is not None:
        parts.append("review")
    if node.gates.judge_config_path is not None:
        parts.append("judge")
    if node.gates.hitl:
        parts.append("hitl")
    if not parts:
        return "—"
    return "+".join(parts)
