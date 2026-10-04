"""M-21 web_search: веб-поиск как инструмент узла (TSK-2101, TSK-2102).

Провайдер MVP — Tavily (REST, без SDK); ключ ТОЛЬКО из TAVILY_API_KEY
(см. .env.example). Реестр инструментов отдаёт ToolSpec для tool-цикла TSK-0402.
"""
from __future__ import annotations

import os
from typing import Protocol, Sequence

import httpx

from workshop.llm_client import ToolSpec
from workshop.result import Err, Ok, Result

SEARCH_KEY_MISSING = "SEARCH_KEY_MISSING"
SEARCH_TIMEOUT = "SEARCH_TIMEOUT"
SEARCH_PROVIDER_ERROR = "SEARCH_PROVIDER_ERROR"
UNKNOWN_TOOL = "UNKNOWN_TOOL"

_TAVILY_URL = "https://api.tavily.com/search"
_MAX_RESULTS_LIMIT = 10
_DEFAULT_MAX_RESULTS = 5

_WEB_SEARCH_DESCRIPTION = (
    "Поиск в интернете. Используй для проверки фактов, версий библиотек "
    "и актуальной документации; в query формулируй конкретный запрос."
)
_WEB_SEARCH_PARAMETERS: dict[str, object] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "поисковый запрос"},
        "max_results": {
            "type": "integer",
            "description": f"число результатов, 1..{_MAX_RESULTS_LIMIT} (дефолт {_DEFAULT_MAX_RESULTS})",
        },
    },
    "required": ["query"],
}


class SearchClient(Protocol):
    def search(self, query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> Result[str]: ...


class TavilySearch:
    """TSK-2101: клиент Tavily — нумерованные результаты «заголовок / URL / сниппет»."""

    def __init__(self, api_key: str | None = None, timeout_s: float = 30.0) -> None:
        if api_key is not None:
            self._api_key = api_key
        else:
            self._api_key = os.getenv("TAVILY_API_KEY")
        self._timeout_s = timeout_s

    def search(self, query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> Result[str]:
        if self._api_key is None or not self._api_key.strip():
            return Err(SEARCH_KEY_MISSING, "не задан TAVILY_API_KEY")
        try:
            response = httpx.post(
                _TAVILY_URL,
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                },
                timeout=self._timeout_s,
            )
        except httpx.TimeoutException as exc:
            return Err(SEARCH_TIMEOUT, str(exc))
        except httpx.HTTPError as exc:
            return Err(SEARCH_PROVIDER_ERROR, str(exc))

        if response.status_code != 200:
            return Err(
                SEARCH_PROVIDER_ERROR,
                f"HTTP {response.status_code}: {response.text[:200]}",
            )
        try:
            payload = response.json()
        except ValueError as exc:
            return Err(SEARCH_PROVIDER_ERROR, f"невалидный JSON ответа: {exc}")
        return Ok(_format_results(payload))


class FakeSearch:
    """Скриптованный клиент: отдаёт заготовленные результаты, запоминает запросы."""

    def __init__(self, scripted: list[Result[str]]) -> None:
        self._scripted = list(scripted)
        self.queries: list[str] = []

    def search(self, query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> Result[str]:
        self.queries.append(query)
        if not self._scripted:
            return Err(SEARCH_PROVIDER_ERROR, "сценарий FakeSearch исчерпан")
        return self._scripted.pop(0)


def build_tools(
    names: Sequence[str], search: SearchClient | None = None
) -> Result[list[ToolSpec]]:
    """TSK-2102: имена из NodeConfig.tools → ToolSpec для tool-цикла TSK-0402."""
    specs: list[ToolSpec] = []
    for name in names:
        if name != "web_search":
            # WHY: опечатка в конфиге узла ловится ДО вызова LLM, а не молчаливым
            # отсутствием инструмента у модели
            return Err(UNKNOWN_TOOL, name)
        client = search if search is not None else TavilySearch()
        specs.append(
            ToolSpec(
                name="web_search",
                description=_WEB_SEARCH_DESCRIPTION,
                parameters=_WEB_SEARCH_PARAMETERS,
                executor=_make_web_search_executor(client),
            )
        )
    return Ok(specs)


def _make_web_search_executor(client: SearchClient):
    def executor(args: dict[str, object]) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            return "ОШИБКА ИНСТРУМЕНТА: пустой query"
        raw_max = args.get("max_results", _DEFAULT_MAX_RESULTS)
        if isinstance(raw_max, int) and not isinstance(raw_max, bool):
            max_results = min(max(raw_max, 1), _MAX_RESULTS_LIMIT)
        else:
            max_results = _DEFAULT_MAX_RESULTS
        result = client.search(query, max_results)
        if isinstance(result, Err):
            # WHY: сбой поиска — текст модели, не отказ узла: агент может
            # завершить артефакт из своих знаний (контракт TSK-0402)
            return f"ОШИБКА ПОИСКА {result.code}: {result.details}"
        return result.value

    return executor


def _format_results(payload: dict[str, object]) -> str:
    lines: list[str] = []
    answer = payload.get("answer")
    if isinstance(answer, str) and answer.strip():
        lines.append(f"Ответ провайдера: {answer.strip()}")
    results = payload.get("results")
    if isinstance(results, list):
        for number, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            content = str(item.get("content", "")).strip()
            lines.append(f"{number}. {title}\n   {url}\n   {content}")
    if not lines:
        return "Ничего не найдено."
    return "\n".join(lines)
