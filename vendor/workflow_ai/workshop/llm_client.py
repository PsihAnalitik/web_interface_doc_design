"""M-04 llm_client: единый интерфейс вызова LLM-провайдеров (TSK-0401, TSK-0402).

Реальный провайдер-адаптер подключается на этапе 6 (первое реальное включение);
до того используется FakeLLM — та же сигнатура, скриптованные ответы.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from workshop.models import LLMParams
from workshop.result import Err, Ok, Result

PROVIDER_ERROR = "PROVIDER_ERROR"
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
PROVIDER_QUOTA = "PROVIDER_QUOTA"
TIMEOUT = "TIMEOUT"
TOOL_LOOP_EXCEEDED = "TOOL_LOOP_EXCEEDED"

_QUOTA_CODES = frozenset({
    "insufficient_quota",
    "billing_not_active",
    "billing_hard_limit_reached",
})


def classify_provider_failure(status_code: int | None, error_code: str | None) -> str:
    """Map an HTTP status and provider error code to a stable failure code.

    A plain 429 rate limit stays PROVIDER_ERROR. Quota and billing limits do not.
    """
    code = error_code.strip().lower() if isinstance(error_code, str) else ""
    if status_code == 404 or code == "model_not_found":
        return MODEL_UNAVAILABLE
    quota = code in _QUOTA_CODES or "billing" in code
    if status_code == 402 or (status_code == 429 and quota):
        return PROVIDER_QUOTA
    return PROVIDER_ERROR


@dataclass(frozen=True)
class ToolSpec:
    """TSK-0402: инструмент узла — JSON-схема function calling + исполнитель.

    executor всегда возвращает str: ошибка инструмента — текст для модели
    («ОШИБКА ПОИСКА …»), не отказ узла — сбой внешнего сервиса не роняет конвейер.
    """

    name: str
    description: str
    parameters: dict[str, object]
    executor: Callable[[dict[str, object]], str]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: dict[str, int] = field(default_factory=dict)
    # TSK-0402: вызовы инструментов «имя(аргументы) → результат» — в журнал (NFR-04)
    tool_trace: tuple[str, ...] = ()


class LLMClient(Protocol):
    def complete(
        self, prompt: str, params: LLMParams, tools: Sequence[ToolSpec] = ()
    ) -> Result[LLMResponse]: ...


class FakeLLM:
    """Скриптованный клиент: отдаёт заготовленные ответы по порядку, запоминает промпты."""

    def __init__(self, scripted: list[Result[LLMResponse]]) -> None:
        self._scripted = list(scripted)
        self.prompts: list[str] = []
        self.tools_seen: list[tuple[str, ...]] = []

    def complete(
        self, prompt: str, params: LLMParams, tools: Sequence[ToolSpec] = ()
    ) -> Result[LLMResponse]:
        self.prompts.append(prompt)
        self.tools_seen.append(tuple(spec.name for spec in tools))
        if not self._scripted:
            return Err(PROVIDER_ERROR, "сценарий FakeLLM исчерпан")
        return self._scripted.pop(0)


def fake_ok(text: str) -> Ok[LLMResponse]:
    return Ok(LLMResponse(text=text))
