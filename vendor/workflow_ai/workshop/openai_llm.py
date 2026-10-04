"""M-04 llm_client: адаптер провайдера OpenAI (TSK-0401, TSK-0402).

Конфигурация — только из окружения (см. .env.example):
OPENAI_API_KEY — ключ; OPENAI_BASE_URL — переопределение endpoint
(прокси, совместимые API), пусто → дефолт SDK.
"""
from __future__ import annotations

import json
import os
from typing import Sequence

from openai import APITimeoutError, OpenAI, OpenAIError

from workshop.llm_client import (
    PROVIDER_ERROR,
    TIMEOUT,
    TOOL_LOOP_EXCEEDED,
    LLMResponse,
    ToolSpec,
)
from workshop.models import LLMParams
from workshop.result import Err, Ok, Result

_PROVIDER_NAME = "openai"
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
# WHY: явный потолок раундов tool-calling — зацикленная модель иначе жгла бы
# токены и внешние запросы без остановки (TSK-0402)
MAX_TOOL_ROUNDS = 5


class OpenAILLM:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 300.0,
    ) -> None:
        if api_key is not None:
            self._api_key = api_key
        else:
            self._api_key = os.getenv("OPENAI_API_KEY")
        if base_url is not None:
            self._base_url = base_url
        else:
            # пустая строка в окружении = «не задан» → дефолтный endpoint SDK
            env_base_url = os.getenv("OPENAI_BASE_URL", "")
            self._base_url = env_base_url if env_base_url.strip() else None
        self._timeout_s = timeout_s
        self._client: OpenAI | None = None

    def complete(
        self, prompt: str, params: LLMParams, tools: Sequence[ToolSpec] = ()
    ) -> Result[LLMResponse]:
        # WHY: конфиг узла может указывать другого провайдера — молчаливый вызов
        # не того API хуже явного отказа
        if params.provider != _PROVIDER_NAME:
            return Err(
                PROVIDER_ERROR,
                f"адаптер openai получил provider={params.provider}",
            )
        if self._api_key is None or not self._api_key.strip():
            return Err(PROVIDER_ERROR, "не задан OPENAI_API_KEY")

        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        specs_by_name = {spec.name: spec for spec in tools}
        tools_payload = [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in tools
        ]
        usage: dict[str, int] = {}
        trace: list[str] = []

        # +1 раунд: после исчерпания лимита — принудительный финал. tools остаются
        # в запросе, но tool_choice="none" + явная инструкция: убрать tools целиком
        # нельзя — deepseek тогда эмитит сырую разметку вызова текстом
        # (живые прогоны 2026-07-10)
        for round_index in range(MAX_TOOL_ROUNDS + 1):
            allow_tool_calls = round_index < MAX_TOOL_ROUNDS
            if tools and not allow_tool_calls:
                messages.append(
                    {
                        "role": "user",
                        "content": "Раунды инструментов исчерпаны. Не вызывай "
                        "инструменты — дай финальный ответ на основе уже "
                        "полученных результатов.",
                    }
                )
            request_kwargs: dict[str, object] = {
                "model": params.model,
                "messages": messages,
                "temperature": params.temperature,
                "max_completion_tokens": params.max_tokens,
                "timeout": params.timeout_s
                if params.timeout_s is not None
                else self._timeout_s,
            }
            if params.seed is not None:
                request_kwargs["seed"] = params.seed
            if params.reasoning_effort is not None:
                request_kwargs["reasoning_effort"] = params.reasoning_effort
            if tools:
                request_kwargs["tools"] = tools_payload
                if not allow_tool_calls:
                    request_kwargs["tool_choice"] = "none"

            try:
                response = self._ensure_client().chat.completions.create(**request_kwargs)
            except APITimeoutError as exc:
                return Err(TIMEOUT, str(exc))
            except OpenAIError as exc:
                return Err(PROVIDER_ERROR, str(exc))

            if not response.choices:
                return Err(PROVIDER_ERROR, "ответ без choices")
            message = response.choices[0].message
            _accumulate_usage(usage, getattr(response, "usage", None))

            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                text = message.content
                if text is None or not text.strip():
                    return Err(PROVIDER_ERROR, "пустой ответ модели")
                return Ok(LLMResponse(text=text, usage=usage, tool_trace=tuple(trace)))
            if not allow_tool_calls:
                # tool_calls вопреки tool_choice="none" — провайдер сломан
                break

            messages.append(_assistant_tool_message(message, tool_calls))
            for call in tool_calls:
                result_text = _execute_tool_call(call, specs_by_name)
                trace.append(
                    f"{call.function.name}({call.function.arguments}) → {result_text}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result_text,
                    }
                )

        performed = "; ".join(entry.split(" → ")[0] for entry in trace)
        return Err(
            TOOL_LOOP_EXCEEDED,
            f"модель не завершила ответ за {MAX_TOOL_ROUNDS} раундов инструментов; "
            f"вызовы: {performed[:500]}",
        )

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            # WHY: base_url передаётся всегда явно — SDK сам читает OPENAI_BASE_URL
            # и пустую строку трактует как адрес, а не как «не задано»
            if self._base_url is not None:
                effective_base_url = self._base_url
            else:
                effective_base_url = _DEFAULT_BASE_URL
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=effective_base_url,
                timeout=self._timeout_s,
            )
        return self._client


def _accumulate_usage(usage: dict[str, int], raw_usage: object) -> None:
    """Суммирует токены по раундам tool-цикла в один usage ответа.

    cached_tokens — попадания в prompt-кэш провайдера. Без него неизвестно,
    работает кэш или нет: префикс промпта (методология из wiki + base-шаблон)
    у наших цехов стабилен байт в байт, и при работающем кэше вход дешевеет
    в разы. Поле стандартное для OpenAI-совместимых API; отсутствие поля НЕ
    означает отсутствия кэша — прокси может его не пробрасывать.
    """
    if raw_usage is None:
        return
    usage["prompt_tokens"] = usage.get("prompt_tokens", 0) + raw_usage.prompt_tokens
    usage["completion_tokens"] = (
        usage.get("completion_tokens", 0) + raw_usage.completion_tokens
    )
    details = getattr(raw_usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details is not None else None
    if cached is None:
        # Anthropic-стиль, если прокси отдаёт его вместо OpenAI-поля
        cached = getattr(raw_usage, "cache_read_input_tokens", None)
    if cached is not None:
        usage["cached_tokens"] = usage.get("cached_tokens", 0) + int(cached)


def _assistant_tool_message(message: object, tool_calls: object) -> dict[str, object]:
    """Ответ модели с tool_calls → словарь для messages следующего раунда."""
    return {
        "role": "assistant",
        "content": getattr(message, "content", None) or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in tool_calls
        ],
    }


def _execute_tool_call(call: object, specs_by_name: dict[str, ToolSpec]) -> str:
    """Выполнить один tool_call; любая проблема — ТЕКСТОМ модели (TSK-0402).

    WHY: невалидные аргументы или неизвестное имя — ошибка МОДЕЛИ, ей и
    исправлять в следующем раунде; отказ узла здесь ронял бы прогон впустую.
    """
    spec = specs_by_name.get(call.function.name)
    if spec is None:
        return f"ОШИБКА ИНСТРУМЕНТА: неизвестный инструмент {call.function.name}"
    try:
        args = json.loads(call.function.arguments)
    except (ValueError, TypeError):
        return "ОШИБКА ИНСТРУМЕНТА: аргументы не являются валидным JSON-объектом"
    if not isinstance(args, dict):
        return "ОШИБКА ИНСТРУМЕНТА: аргументы должны быть JSON-объектом"
    return spec.executor(args)
