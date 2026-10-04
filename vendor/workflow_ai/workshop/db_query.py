"""M-24 db_query: read-only запрос к БД как инструмент узла (TSK-2401, TSK-2402).

Назначение — сверка описаний таблиц (schema.yaml, table_cards) с фактической
структурой и значениями. Валидация запроса выполняется ДО обращения к БД:
только одиночный SELECT, LIMIT дописывается принудительно. DSN — ТОЛЬКО из
env WORKSHOP_DB_DSN (образец TAVILY_API_KEY). MVP-драйвер — psycopg (Postgres);
Vertica подключается новой реализацией DbClient без изменения инструмента.
"""
from __future__ import annotations

import os
import re
from typing import Protocol, Sequence

from workshop.llm_client import ToolSpec
from workshop.result import Err, Ok, Result

DB_DSN_MISSING = "DB_DSN_MISSING"
DB_QUERY_REJECTED = "DB_QUERY_REJECTED"
DB_QUERY_FAILED = "DB_QUERY_FAILED"

DEFAULT_ROW_LIMIT = 100
_QUERY_TIMEOUT_S = 30
_CELL_LIMIT_CHARS = 200

_SELECT_RE = re.compile(r"^\s*select\b", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\blimit\s+\d+\s*$", re.IGNORECASE)

_DB_QUERY_DESCRIPTION = (
    "Read-only SELECT к базе данных — сверка ОПИСАНИЯ таблицы с фактом. "
    "TRIGGER: проверить существование колонки, реальные значения "
    "(SELECT DISTINCT col FROM t), диапазоны (MIN/MAX). "
    "SKIP: аналитика и агрегация данных ради ответа пользователю — это не "
    "твоя задача; описание проверяется точечными выборками. "
    f"LIMIT {DEFAULT_ROW_LIMIT} добавляется автоматически."
)


class DbClient(Protocol):
    def execute(self, query: str) -> Result[list[tuple]]:
        """Выполнить проверенный SELECT; первая строка результата — имена колонок."""
        ...


class PsycopgClient:
    """TSK-2401: MVP-клиент Postgres; читает DSN из WORKSHOP_DB_DSN."""

    def __init__(self, dsn: str | None = None, timeout_s: int = _QUERY_TIMEOUT_S) -> None:
        if dsn is not None:
            self._dsn = dsn
        else:
            self._dsn = os.getenv("WORKSHOP_DB_DSN")
        self._timeout_s = timeout_s

    def execute(self, query: str) -> Result[list[tuple]]:
        if self._dsn is None or not self._dsn.strip():
            return Err(DB_DSN_MISSING, "не задан WORKSHOP_DB_DSN")
        # локальный импорт: psycopg нужен только при живом обращении к БД
        import psycopg

        try:
            with psycopg.connect(
                self._dsn, connect_timeout=self._timeout_s, autocommit=True
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    header = tuple(
                        description.name for description in cursor.description or ()
                    )
                    rows = cursor.fetchall()
        except psycopg.Error as exc:
            return Err(DB_QUERY_FAILED, str(exc))
        return Ok([header, *rows])


class FakeDbClient:
    """Скриптованный клиент для тестов: запоминает запросы, отдаёт заготовки."""

    def __init__(self, scripted: list[Result[list[tuple]]]) -> None:
        self._scripted = list(scripted)
        self.queries: list[str] = []

    def execute(self, query: str) -> Result[list[tuple]]:
        self.queries.append(query)
        if not self._scripted:
            return Err(DB_QUERY_FAILED, "сценарий FakeDbClient исчерпан")
        return self._scripted.pop(0)


def validate_query(query: str, row_limit: int = DEFAULT_ROW_LIMIT) -> Result[str]:
    """TSK-2401: только одиночный SELECT; LIMIT дописывается, если отсутствует."""
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return Err(DB_QUERY_REJECTED, "пустой запрос")
    if ";" in stripped:
        return Err(DB_QUERY_REJECTED, "несколько statement'ов запрещены")
    if not _SELECT_RE.match(stripped):
        return Err(DB_QUERY_REJECTED, "разрешён только SELECT")
    if not _LIMIT_RE.search(stripped):
        stripped = f"{stripped} LIMIT {row_limit}"
    return Ok(stripped)


def build_db_tools(client: DbClient | None = None) -> list[ToolSpec]:
    """TSK-2402: инструмент db_query; сбои — ТЕКСТОМ модели (контракт TSK-0402)."""
    active_client = client if client is not None else PsycopgClient()
    return [
        ToolSpec(
            name="db_query",
            description=_DB_QUERY_DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "одиночный SELECT"},
                },
                "required": ["query"],
            },
            executor=_make_db_executor(active_client),
        )
    ]


def _make_db_executor(client: DbClient):
    def executor(args: dict[str, object]) -> str:
        raw_query = str(args.get("query", ""))
        validated = validate_query(raw_query)
        if isinstance(validated, Err):
            return f"ОШИБКА ИНСТРУМЕНТА {validated.code}: {validated.details}"
        result = client.execute(validated.value)
        if isinstance(result, Err):
            return f"ОШИБКА ИНСТРУМЕНТА {result.code}: {result.details}"
        return _format_rows(result.value)

    return executor


def _format_rows(rows: Sequence[tuple]) -> str:
    if not rows:
        return "Пустой результат."
    lines = []
    for row in rows:
        cells = [str(cell)[:_CELL_LIMIT_CHARS] for cell in row]
        lines.append(" | ".join(cells))
    if len(lines) == 1:
        return f"{lines[0]}\n(строк нет)"
    return "\n".join(lines)
