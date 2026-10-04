"""Общие модели данных: конфиги (pydantic, внешний ввод) и артефакты (dataclass, внутренние значения)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMParams(BaseModel):
    provider: str
    model: str
    temperature: float = 0.0
    seed: int | None = None
    max_tokens: int = 4096
    # None → таймаут клиента-адаптера (у разных цехов разная длина вызова)
    timeout_s: float | None = None
    # усилие рассуждения reasoning-модели; None — поведение провайдера по умолчанию.
    # "none" оправдан ТОЛЬКО для вердиктных узлов (ревью, приёмка): там выход —
    # короткий вердикт по чеклисту, и рассуждение сжигается, а не оплачивается
    # пользой. Для генерирующих узлов отключать нельзя (заимствование из
    # .workflow_ai стороннего проекта: замер 0.86 ₽ → 0.05 ₽ за вызов при
    # неизменных вердиктах)
    reasoning_effort: str | None = None


class WikiRef(BaseModel):
    """Ссылка на wiki-материал с обязательной версией (FR-17: узел пиннит версию wiki)."""

    path: str
    version: str


class NodeConfig(BaseModel):
    base_prompt_path: str
    stage_map_path: str
    wiki_refs: list[WikiRef] = Field(default_factory=list)
    # FR-19: имя артефакта-источника динамических wiki-ссылок (стадия tech_selection);
    # рантайм резолвит его в wiki_refs перед запуском узла
    wiki_refs_from: str | None = None
    # TSK-1606: корень wiki для листинга дерева (пути всех страниц) в INPUTS —
    # видимость реального дерева ревьюеру ссылок; None — листинг не добавляется
    wiki_tree_root: str | None = None
    tools: list[str] = Field(default_factory=list)
    # источники LLM по приоритету: llm > llm_profile > политика по task_class (FR-16);
    # после load_node_config llm всегда заполнен
    llm: LLMParams | None = None
    llm_profile: str | None = None
    task_class: str | None = None
    # эксперимент «слабый рабочий + сильный консультант»: модель второго мнения
    # для codegen-узла; после load_node_config consultant_llm заполнен, если задан профиль
    consultant_llm: LLMParams | None = None
    consultant_profile: str | None = None
    # описание окружения песочницы для консультанта (предустановленные пакеты):
    # рантайм состав образа не знает, декларирует конфиг цеха
    sandbox_notes: str | None = None

    @model_validator(mode="after")
    def _at_most_one_explicit_llm_source(self) -> "NodeConfig":
        if self.llm is not None and self.llm_profile is not None:
            raise ValueError("llm и llm_profile заданы одновременно — оставьте один источник")
        if self.consultant_llm is not None and self.consultant_profile is not None:
            raise ValueError(
                "consultant_llm и consultant_profile заданы одновременно — оставьте один источник"
            )
        return self

    # wiki_refs и wiki_refs_from сосуществуют: динамические ссылки ДОБАВЛЯЮТСЯ
    # к статическим (кейс wiki_pages: постоянная методология + страницы из спеки)


class ModelPolicy(BaseModel):
    """FR-16: маппинг класса задачи узла на профиль модели."""

    by_class: dict[str, str] = Field(default_factory=dict)
    default: str | None = None


class ModelRegistry(BaseModel):
    """Содержимое models.json: профили + необязательная политика выбора (FR-16)."""

    profiles: dict[str, LLMParams] = Field(min_length=1)
    policy: ModelPolicy | None = None

    @model_validator(mode="after")
    def _policy_references_existing_profiles(self) -> "ModelRegistry":
        if self.policy is None:
            return self
        for task_class, profile_name in self.policy.by_class.items():
            if profile_name not in self.profiles:
                raise ValueError(
                    f"policy.by_class.{task_class}: профиль {profile_name} не объявлен"
                )
        if self.policy.default is not None and self.policy.default not in self.profiles:
            raise ValueError(f"policy.default: профиль {self.policy.default} не объявлен")
        return self


class GateSpec(BaseModel):
    review_config_path: str | None = None
    judge_config_path: str | None = None    # только для kind=codegen: автоцикл judge→codegen
    hitl: bool = False
    # TSK-2703: HITL этого узла обязателен по смыслу цеха (человек проверяет то,
    # что агент проверить не может) — экспорт в скилл помечает фазу «required»,
    # и режим autopilot её не пропускает. На движок не влияет: там autopilot —
    # отдельный graph.autopilot.json
    hitl_required: bool = False

    @model_validator(mode="after")
    def _required_implies_hitl(self) -> "GateSpec":
        if self.hitl_required and not self.hitl:
            raise ValueError("hitl_required=true без hitl=true")
        return self


class NodeSpec(BaseModel):
    id: str
    config_path: str
    kind: Literal["workshop", "codegen"] = "workshop"
    image: str | None = None                      # обязателен при kind=codegen
    test_command: str = "python -m pytest -q"
    gates: GateSpec = Field(default_factory=GateSpec)
    max_iterations: int = Field(default=3, ge=1)

    @model_validator(mode="after")
    def _codegen_constraints(self) -> "NodeSpec":
        if self.kind == "codegen":
            if self.image is None:
                raise ValueError("узел kind=codegen требует image")
            if self.gates.review_config_path is not None:
                raise ValueError(
                    "review-гейт не поддержан для kind=codegen — оценка кода это judge-гейт"
                )
        elif self.gates.judge_config_path is not None:
            raise ValueError("judge-гейт поддержан только для kind=codegen")
        return self


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")


class PackageSpec(BaseModel):
    """Параметры выходного пакета (FR-13, TSK-1201)."""

    code_node: str = "executor"
    image: str
    serve: str | None = None
    test_command: str = "python -m pytest -q"
    ports: list[str] = Field(default_factory=list)


class ServiceSpec(BaseModel):
    """Сервис продукта: откуда пакет и как он включается в compose (FR-14)."""

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")   # имя сервиса в compose/DNS
    package: str
    ports: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class ProductSpec(BaseModel):
    product: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    services: list[ServiceSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent_services(self) -> "ProductSpec":
        names = [service.name for service in self.services]
        if len(set(names)) != len(names):
            raise ValueError("имена сервисов не уникальны")
        for service in self.services:
            for dependency in service.depends_on:
                if dependency not in names:
                    raise ValueError(
                        f"{service.name}: depends_on на несуществующий сервис {dependency}"
                    )
        return self


class MaterialConfig(BaseModel):
    """TSK-2203: чанкование входного материала цеха (M-22)."""

    chunk_chars: int = Field(default=4000, ge=200)
    # TSK-2204: перекрытие при жёсткой нарезке переросших блоков —
    # решение на границе чанков не теряется (паттерн ailab: 1000/300)
    chunk_overlap: int = Field(default=400, ge=0)
    # материал не длиннее лимита идёт узлам инлайном; длиннее — оглавлением,
    # содержимое читается инструментами material_search/material_get.
    # TSK-2207: 0 — ВСЕГДА оглавлением (материал с двойными скобками ломает
    # сборку шаблона; tool-результаты идут в messages мимо неё)
    inline_limit_chars: int = Field(default=12000, ge=0)

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> "MaterialConfig":
        if self.chunk_overlap >= self.chunk_chars:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) обязан быть меньше "
                f"chunk_chars ({self.chunk_chars})"
            )
        return self


class GraphConfig(BaseModel):
    nodes: list[NodeSpec]
    edges: list[Edge] = Field(default_factory=list)
    llm_profiles_path: str | None = None
    # имя целевого проекта: выходы цеха по умолчанию идут в projects/<project>/
    project: str | None = None
    package: PackageSpec | None = None
    # TSK-2203: включает инжест материала M-22; None — вход идёт узлам как есть
    material: MaterialConfig | None = None
    # шкала весов находок ревью: p3_high — 🔴p3 высший (умолчание фабрики),
    # p0_high — обратная шкала цехов анализа безопасности (p0 блокирующий)
    severity_scale: Literal["p3_high", "p0_high"] = "p3_high"


@dataclass(frozen=True)
class ArtifactRef:
    name: str
    version: int


@dataclass(frozen=True)
class Artifact:
    ref: ArtifactRef
    content: str
    derived_from: ArtifactRef | None


@dataclass(frozen=True)
class CrosslinkReport:
    """Факты о ссылках, не вердикт: решение принимает гейт (WHY в TSK-0203)."""

    broken_links: tuple[str, ...]
    uncovered_ids: tuple[str, ...]
