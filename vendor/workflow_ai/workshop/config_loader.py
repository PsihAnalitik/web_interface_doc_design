"""M-01 config_loader: загрузка и валидация конфигов узлов и графа (TSK-0101, TSK-0102)."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from workshop.models import Edge, GraphConfig, ModelRegistry, NodeConfig, ProductSpec
from workshop.result import Err, Ok, Result

CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
CONFIG_INVALID = "CONFIG_INVALID"
GRAPH_CYCLE = "GRAPH_CYCLE"
UNKNOWN_NODE_REF = "UNKNOWN_NODE_REF"
UNKNOWN_LLM_PROFILE = "UNKNOWN_LLM_PROFILE"


def load_node_config(
    path: str, registry: ModelRegistry | None = None
) -> Result[NodeConfig]:
    raw = _read_json_object(path)
    if isinstance(raw, Err):
        return raw
    try:
        config = NodeConfig.model_validate(raw.value)
    except ValidationError as exc:
        return Err(CONFIG_INVALID, f"{path}: {_first_error(exc)}")

    # консультант резолвится до ветвления по llm: ветка inline-llm возвращает
    # конфиг сразу и иначе оставила бы consultant_profile неразрешённым
    if config.consultant_profile is not None:
        if registry is None:
            return Err(
                CONFIG_INVALID,
                f"{path}: указан consultant_profile, но реестр не подключён "
                f"(llm_profiles_path в конфиге графа)",
            )
        consultant = registry.profiles.get(config.consultant_profile)
        if consultant is None:
            return Err(UNKNOWN_LLM_PROFILE, config.consultant_profile)
        config = config.model_copy(update={"consultant_llm": consultant})

    # приоритет источников: inline llm > llm_profile > политика по task_class (FR-16)
    if config.llm is not None:
        return Ok(config)

    if config.llm_profile is not None:
        if registry is None:
            return Err(
                CONFIG_INVALID,
                f"{path}: указан llm_profile, но реестр не подключён "
                f"(llm_profiles_path в конфиге графа)",
            )
        profile = registry.profiles.get(config.llm_profile)
        if profile is None:
            return Err(UNKNOWN_LLM_PROFILE, config.llm_profile)
        return Ok(config.model_copy(update={"llm": profile}))

    if config.task_class is not None:
        if registry is None or registry.policy is None:
            return Err(
                CONFIG_INVALID,
                f"{path}: указан task_class, но политика выбора модели "
                f"не объявлена в реестре (policy в models.json)",
            )
        profile_name = registry.policy.by_class.get(
            config.task_class, registry.policy.default
        )
        if profile_name is None:
            return Err(
                CONFIG_INVALID,
                f"{path}: класс {config.task_class} не покрыт policy.by_class "
                f"и policy.default не задан",
            )
        # валидатор ModelRegistry гарантирует существование профиля
        return Ok(config.model_copy(update={"llm": registry.profiles[profile_name]}))

    return Err(
        CONFIG_INVALID,
        f"{path}: нет источника модели (llm | llm_profile | task_class + policy)",
    )


def load_product_spec(path: str) -> Result[ProductSpec]:
    """TSK-0104: спека продукта для сборки FR-14."""
    raw = _read_json_object(path)
    if isinstance(raw, Err):
        return raw
    try:
        return Ok(ProductSpec.model_validate(raw.value))
    except ValidationError as exc:
        return Err(CONFIG_INVALID, f"{path}: {_first_error(exc)}")


def load_model_registry(path: str) -> Result[ModelRegistry]:
    """TSK-0103: профили моделей + политика выбора FR-16 (класс задачи → профиль)."""
    raw = _read_json_object(path)
    if isinstance(raw, Err):
        return raw
    try:
        return Ok(ModelRegistry.model_validate(raw.value))
    except ValidationError as exc:
        return Err(CONFIG_INVALID, f"{path}: {_first_error(exc)}")


def load_graph_config(path: str) -> Result[GraphConfig]:
    raw = _read_json_object(path)
    if isinstance(raw, Err):
        return raw
    try:
        graph = GraphConfig.model_validate(raw.value)
    except ValidationError as exc:
        return Err(CONFIG_INVALID, f"{path}: {_first_error(exc)}")

    node_ids = {node.id for node in graph.nodes}
    if len(node_ids) != len(graph.nodes):
        return Err(CONFIG_INVALID, f"{path}: id узлов не уникальны")

    for edge in graph.edges:
        if edge.from_node not in node_ids:
            return Err(UNKNOWN_NODE_REF, edge.from_node)
        if edge.to_node not in node_ids:
            return Err(UNKNOWN_NODE_REF, edge.to_node)

    cycle_members = _find_cycle_members(node_ids, graph.edges)
    if cycle_members:
        return Err(GRAPH_CYCLE, ", ".join(cycle_members))
    return Ok(graph)


def _read_json_object(path: str) -> Result[dict]:
    file = Path(path)
    if not file.is_file():
        return Err(CONFIG_NOT_FOUND, path)
    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Err(CONFIG_INVALID, f"{path}: {exc}")
    if not isinstance(raw, dict):
        return Err(CONFIG_INVALID, f"{path}: ожидается JSON-объект")
    return Ok(raw)


def _first_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}"


def _find_cycle_members(node_ids: set[str], edges: list[Edge]) -> list[str]:
    """Алгоритм Кана: узлы, не вошедшие в топологический порядок, лежат на циклах."""
    incoming_count: dict[str, int] = {node_id: 0 for node_id in node_ids}
    successors: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        incoming_count[edge.to_node] += 1
        successors[edge.from_node].append(edge.to_node)

    ready = sorted(node_id for node_id, count in incoming_count.items() if count == 0)
    while ready:
        current = ready.pop(0)
        for successor in successors[current]:
            incoming_count[successor] -= 1
            if incoming_count[successor] == 0:
                ready.append(successor)

    return sorted(node_id for node_id, count in incoming_count.items() if count > 0)
