"""M-22 material: материал цеха как чанк-стор — инжест, оглавление, ретривер (TSK-2201, TSK-2202).

Вход цеха llm_wiki: текст (выгрузка чатов) и/или строки-URL. Большой материал
не влезает в контекст узла — он дробится на чанки, а узел читает адресно через
инструменты material_search/material_get. Retriever — протокол (seam для RAG):
лексический по умолчанию, векторный RemoteBGEM3Retriever (TSK-2206) включается
через env BGE_M3_SERVICE_URL. Тот же стор служит wiki-страницам (TSK-2205):
wiki_search/wiki_get — адресная маршрутизация узла по wiki вместо бандла.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from workshop.llm_client import ToolSpec
from workshop.result import Err, Ok, Result

MATERIAL_EMPTY = "MATERIAL_EMPTY"
MATERIAL_FETCH_FAILED = "MATERIAL_FETCH_FAILED"
MATERIAL_TOO_LARGE = "MATERIAL_TOO_LARGE"
WIKI_STORE_EMPTY = "WIKI_STORE_EMPTY"
EMBEDDINGS_UNAVAILABLE = "EMBEDDINGS_UNAVAILABLE"

DEFAULT_CHUNK_CHARS = 4000
DEFAULT_CHUNK_OVERLAP = 400
_DOC_LIMIT_CHARS = 500_000
_FETCH_TIMEOUT_S = 30.0
_ENCODE_TIMEOUT_S = 120.0
_ENCODE_BATCH_SIZE = 8
_ENCODE_MAX_LENGTH = 512
_TITLE_LIMIT_CHARS = 60
_DEFAULT_SEARCH_CHUNKS = 3
_MAX_SEARCH_CHUNKS = 10
_SNIPPET_CHARS = 300
_PAGE_LIMIT_CHARS = 20_000

# TSK-2204 (паттерн ailab): стратегия повторов живёт в описании инструмента —
# модель применяет её сама, без программного цикла
_SEARCH_RETRY_HINT = (
    " Если ничего не найдено: переформулируй запрос синонимами, попробуй более "
    "общие или более узкие термины; после 3 неудачных попыток прекрати поиск "
    "и работай с оглавлением."
)

_URL_LINE_RE = re.compile(r"^https?://\S+$")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class Chunk:
    id: str
    source: str          # "inline" или URL документа
    title: str
    text: str


class Fetcher(Protocol):
    def fetch(self, url: str) -> Result[str]: ...


class HttpxFetcher:
    """TSK-2201: загрузка документа по URL — текст ответа, лимит размера."""

    def __init__(self, timeout_s: float = _FETCH_TIMEOUT_S) -> None:
        self._timeout_s = timeout_s

    def fetch(self, url: str) -> Result[str]:
        try:
            response = httpx.get(url, timeout=self._timeout_s, follow_redirects=True)
        except httpx.HTTPError as exc:
            return Err(MATERIAL_FETCH_FAILED, f"{url}: {exc}")
        if response.status_code != 200:
            return Err(MATERIAL_FETCH_FAILED, f"{url}: HTTP {response.status_code}")
        if len(response.text) > _DOC_LIMIT_CHARS:
            return Err(MATERIAL_TOO_LARGE, f"{url}: {len(response.text)} > {_DOC_LIMIT_CHARS}")
        return Ok(response.text)


class FakeFetcher:
    """Скриптованный загрузчик для тестов: url → заготовленный Result."""

    def __init__(self, scripted: dict[str, Result[str]]) -> None:
        self._scripted = dict(scripted)
        self.fetched: list[str] = []

    def fetch(self, url: str) -> Result[str]:
        self.fetched.append(url)
        if url not in self._scripted:
            return Err(MATERIAL_FETCH_FAILED, f"{url}: нет в сценарии FakeFetcher")
        return self._scripted[url]


class MaterialStore:
    """Чанки материала с оглавлением; содержимое читается инструментами адресно."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = list(chunks)
        self._by_id = {chunk.id: chunk for chunk in chunks}

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    @property
    def total_chars(self) -> int:
        return sum(len(chunk.text) for chunk in self._chunks)

    def get(self, chunk_id: str) -> Chunk | None:
        return self._by_id.get(chunk_id)

    def toc(self) -> str:
        lines = ["Оглавление материала (chunk_id | источник | заголовок | символов):"]
        for chunk in self._chunks:
            # TSK-2207: TOC попадает в шаблон промпта — литеральные двойные
            # скобки в заголовках уронили бы leftover-скан сборки M-03
            title = chunk.title.replace("{{", "{ {").replace("}}", "} }")
            lines.append(
                f"{chunk.id} | {chunk.source} | {title} | {len(chunk.text)}"
            )
        return "\n".join(lines)


class Retriever(Protocol):
    """Seam для RAG: векторная реализация заменяет лексическую без правки инструментов.

    Err — отказ инфраструктуры поиска (недоступный сервис эмбеддингов),
    Ok([]) — поиск отработал, релевантного не нашлось.
    """

    def retrieve(self, query: str, k: int) -> Result[list[Chunk]]: ...


class LexicalRetriever:
    """TSK-2202: MVP-ретривер — сумма вхождений токенов запроса, детерминированный порядок."""

    def __init__(self, store: MaterialStore) -> None:
        self._store = store

    def retrieve(self, query: str, k: int) -> Result[list[Chunk]]:
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return Ok([])
        scored: list[tuple[int, int, Chunk]] = []
        for order, chunk in enumerate(self._store.chunks):
            chunk_tokens = _tokenize(chunk.text)
            score = sum(1 for token in chunk_tokens if token in query_tokens)
            if score > 0:
                scored.append((score, order, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return Ok([chunk for _, _, chunk in scored[:k]])


class EncodeClient(Protocol):
    """Клиент сервиса эмбеддингов (контракт bge-m3-service из стороннего проекта)."""

    def encode(self, texts: list[str]) -> Result[list[list[float]]]: ...


class HttpxBGEEncodeClient:
    """TSK-2206: POST /encode {texts, ...} → items[].dense_vec (dense-only)."""

    def __init__(
        self,
        base_url: str,
        timeout_s: float = _ENCODE_TIMEOUT_S,
        batch_size: int = _ENCODE_BATCH_SIZE,
        max_length: int = _ENCODE_MAX_LENGTH,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._batch_size = batch_size
        self._max_length = max_length

    def encode(self, texts: list[str]) -> Result[list[list[float]]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start:start + self._batch_size]
            try:
                response = httpx.post(
                    f"{self._base_url}/encode",
                    json={
                        "texts": batch,
                        "batch_size": len(batch),
                        "max_length": self._max_length,
                        "return_dense": True,
                        "return_sparse": False,
                        "return_colbert_vecs": False,
                    },
                    timeout=self._timeout_s,
                )
            except httpx.HTTPError as exc:
                return Err(EMBEDDINGS_UNAVAILABLE, f"{self._base_url}: {exc}")
            if response.status_code != 200:
                return Err(
                    EMBEDDINGS_UNAVAILABLE,
                    f"{self._base_url}: HTTP {response.status_code}",
                )
            try:
                items = response.json().get("items")
            except ValueError as exc:
                return Err(EMBEDDINGS_UNAVAILABLE, f"невалидный JSON ответа: {exc}")
            if not isinstance(items, list) or len(items) != len(batch):
                return Err(EMBEDDINGS_UNAVAILABLE, "ответ /encode не совпал с батчем")
            vectors.extend(item["dense_vec"] for item in items)
        return Ok(vectors)


class RemoteBGEM3Retriever:
    """TSK-2206: dense-эмбеддинги через bge-m3-service, косинус, детерминированный топ-k.

    Эмбеддинги чанков считаются лениво при первом retrieve и кэшируются на время
    жизни ретривера; неудачное кодирование не кэшируется — следующий вызов повторит.
    """

    def __init__(self, store: MaterialStore, client: EncodeClient) -> None:
        self._store = store
        self._client = client
        self._chunk_vectors: list[list[float]] | None = None

    def retrieve(self, query: str, k: int) -> Result[list[Chunk]]:
        if not query.strip():
            return Ok([])
        if self._chunk_vectors is None:
            encoded = self._client.encode([chunk.text for chunk in self._store.chunks])
            if isinstance(encoded, Err):
                return encoded
            self._chunk_vectors = encoded.value
        query_encoded = self._client.encode([query])
        if isinstance(query_encoded, Err):
            return query_encoded
        query_vector = query_encoded.value[0]

        scored: list[tuple[float, int, Chunk]] = []
        for order, (chunk, vector) in enumerate(
            zip(self._store.chunks, self._chunk_vectors)
        ):
            scored.append((_cosine(query_vector, vector), order, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return Ok([chunk for _, _, chunk in scored[:k]])


def default_retriever(store: MaterialStore) -> Retriever:
    """TSK-2206: env BGE_M3_SERVICE_URL задан → векторный, иначе лексический."""
    service_url = os.getenv("BGE_M3_SERVICE_URL")
    if service_url is not None and service_url.strip():
        return RemoteBGEM3Retriever(store, HttpxBGEEncodeClient(service_url))
    return LexicalRetriever(store)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    if norm == 0.0:
        return 0.0
    return dot / norm


def ingest(
    raw: str,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    fetcher: Fetcher | None = None,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> Result[MaterialStore]:
    """TSK-2201: текст + строки-URL → документы → чанки со стабильными id d<N>:<NN>."""
    if not raw.strip():
        return Err(MATERIAL_EMPTY, "пустой входной материал")

    inline_lines: list[str] = []
    urls: list[str] = []
    for line in raw.splitlines():
        if _URL_LINE_RE.match(line.strip()):
            urls.append(line.strip())
        else:
            inline_lines.append(line)

    documents: list[tuple[str, str]] = []  # (источник, текст)
    inline_text = "\n".join(inline_lines).strip()
    if inline_text:
        documents.append(("inline", inline_text))
    if urls:
        active_fetcher = fetcher if fetcher is not None else HttpxFetcher()
        for url in urls:
            fetched = active_fetcher.fetch(url)
            if isinstance(fetched, Err):
                return fetched
            documents.append((url, fetched.value))

    chunks: list[Chunk] = []
    for doc_number, (source, text) in enumerate(documents, start=1):
        pieces = _split_document(text, chunk_chars, chunk_overlap)
        for chunk_number, piece in enumerate(pieces, start=1):
            chunks.append(
                Chunk(
                    id=f"d{doc_number}:{chunk_number:02d}",
                    source=source,
                    title=_title_of(piece),
                    text=piece,
                )
            )
    return Ok(MaterialStore(chunks))


def load_wiki_store(
    root: Path,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> Result[tuple[MaterialStore, dict[str, str]]]:
    """TSK-2205: wiki как чанк-стор — страница = документ, id чанка = <путь>:NN.

    Возвращает (стор для поиска, {путь: полный текст страницы} для wiki_get).
    """
    if not root.is_dir():
        return Err(WIKI_STORE_EMPTY, f"{root}: не директория")
    pages: dict[str, str] = {}
    for page_file in sorted(root.rglob("*.md")):
        rel_path = page_file.relative_to(root).as_posix()
        try:
            pages[rel_path] = page_file.read_text(encoding="utf-8")
        except OSError as exc:
            return Err(WIKI_STORE_EMPTY, f"{rel_path}: {exc}")
    if not pages:
        return Err(WIKI_STORE_EMPTY, f"{root}: нет страниц *.md")

    chunks: list[Chunk] = []
    for rel_path, text in pages.items():
        pieces = _split_document(text, chunk_chars, chunk_overlap)
        for chunk_number, piece in enumerate(pieces, start=1):
            chunks.append(
                Chunk(
                    id=f"{rel_path}:{chunk_number:02d}",
                    source=rel_path,
                    title=_title_of(piece),
                    text=piece,
                )
            )
    return Ok((MaterialStore(chunks), pages))


def build_material_tools(store: MaterialStore, retriever: Retriever | None = None) -> list[ToolSpec]:
    """TSK-2202: инструменты узла поверх стора; сбои аргументов — текстом (TSK-0402)."""
    active_retriever = retriever if retriever is not None else default_retriever(store)
    return [
        ToolSpec(
            name="material_search",
            description=(
                "Поиск по загруженному материалу (чатам/документам). Возвращает "
                "релевантные чанки с id; полный текст чанка — через material_get."
                + _SEARCH_RETRY_HINT
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "поисковый запрос"},
                    "max_chunks": {
                        "type": "integer",
                        "description": f"число чанков, 1..{_MAX_SEARCH_CHUNKS} "
                                       f"(дефолт {_DEFAULT_SEARCH_CHUNKS})",
                    },
                },
                "required": ["query"],
            },
            executor=_make_search_executor(active_retriever),
        ),
        ToolSpec(
            name="material_get",
            description="Полный текст чанка материала по chunk_id из оглавления или поиска.",
            parameters={
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "string", "description": "id чанка, например d1:03"},
                },
                "required": ["chunk_id"],
            },
            executor=_make_get_executor(store),
        ),
    ]


def build_wiki_tools(
    store: MaterialStore,
    pages: dict[str, str],
    retriever: Retriever | None = None,
) -> list[ToolSpec]:
    """TSK-2205: адресная маршрутизация узла по wiki — поиск чанков + чтение страниц."""
    active_retriever = retriever if retriever is not None else default_retriever(store)
    return [
        ToolSpec(
            name="wiki_search",
            description=(
                "Поиск по страницам wiki. Возвращает релевантные фрагменты с путём "
                "страницы; страницу целиком читай через wiki_get."
                + _SEARCH_RETRY_HINT
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "поисковый запрос"},
                    "max_chunks": {
                        "type": "integer",
                        "description": f"число фрагментов, 1..{_MAX_SEARCH_CHUNKS} "
                                       f"(дефолт {_DEFAULT_SEARCH_CHUNKS})",
                    },
                },
                "required": ["query"],
            },
            executor=_make_search_executor(active_retriever),
        ),
        ToolSpec(
            name="wiki_get",
            description=(
                "Полный текст страницы wiki по её пути от корня wiki "
                "(например python/httpx/index.md) — пути есть в дереве wiki и в wiki_search."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "путь страницы от корня wiki"},
                },
                "required": ["path"],
            },
            executor=_make_page_executor(pages),
        ),
    ]


def _make_page_executor(pages: dict[str, str]):
    def executor(args: dict[str, object]) -> str:
        path = str(args.get("path", "")).strip().lstrip("/")
        if not path:
            return "ОШИБКА ИНСТРУМЕНТА: пустой path"
        text = pages.get(path)
        if text is None:
            return f"ОШИБКА ИНСТРУМЕНТА: страницы {path} нет (см. дерево wiki или wiki_search)"
        if len(text) > _PAGE_LIMIT_CHARS:
            return text[:_PAGE_LIMIT_CHARS] + "\n[...страница обрезана по лимиту...]"
        return f"[{path}]\n{text}"

    return executor


def _make_search_executor(retriever: Retriever):
    def executor(args: dict[str, object]) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            return "ОШИБКА ИНСТРУМЕНТА: пустой query"
        raw_max = args.get("max_chunks", _DEFAULT_SEARCH_CHUNKS)
        if isinstance(raw_max, int) and not isinstance(raw_max, bool):
            k = min(max(raw_max, 1), _MAX_SEARCH_CHUNKS)
        else:
            k = _DEFAULT_SEARCH_CHUNKS
        found = retriever.retrieve(query, k)
        if isinstance(found, Err):
            # сбой инфраструктуры поиска — текст модели, не отказ узла (TSK-0402)
            return f"ОШИБКА ИНСТРУМЕНТА {found.code}: {found.details}"
        if not found.value:
            return "Ничего не найдено."
        lines = []
        for chunk in found.value:
            snippet = chunk.text[:_SNIPPET_CHARS].strip()
            lines.append(f"{chunk.id} | {chunk.title}\n{snippet}")
        return "\n---\n".join(lines)

    return executor


def _make_get_executor(store: MaterialStore):
    def executor(args: dict[str, object]) -> str:
        chunk_id = str(args.get("chunk_id", "")).strip()
        if not chunk_id:
            return "ОШИБКА ИНСТРУМЕНТА: пустой chunk_id"
        chunk = store.get(chunk_id)
        if chunk is None:
            return f"ОШИБКА ИНСТРУМЕНТА: неизвестный chunk_id {chunk_id} (см. оглавление)"
        return f"[{chunk.id} | {chunk.source} | {chunk.title}]\n{chunk.text}"

    return executor


def _split_document(text: str, chunk_chars: int, chunk_overlap: int = 0) -> list[str]:
    """Блоки по markdown-заголовкам, жадная упаковка до chunk_chars; переросший блок режется жёстко.

    TSK-2204: жёсткая нарезка идёт с перекрытием chunk_overlap (решение на границе
    не теряется); упаковка целых блоков — без перекрытия (семантические единицы).
    """
    # ограждение шага: overlap ждёт валидатор MaterialConfig, но функция публична
    step = max(chunk_chars - chunk_overlap, 1)

    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if _HEADING_RE.match(line) and current:
            blocks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    blocks = [block for block in blocks if block]

    pieces: list[str] = []
    buffer = ""
    for block in blocks:
        if len(block) > chunk_chars:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            start = 0
            while start < len(block):
                pieces.append(block[start:start + chunk_chars])
                start += step
        elif buffer and len(buffer) + len(block) + 2 > chunk_chars:
            pieces.append(buffer)
            buffer = block
        elif buffer:
            buffer = f"{buffer}\n\n{block}"
        else:
            buffer = block
    if buffer:
        pieces.append(buffer)
    return pieces


def _title_of(piece: str) -> str:
    for line in piece.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:_TITLE_LIMIT_CHARS]
    return "(без заголовка)"


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]
