"""M-20 mcp_server: MCP-сервер фабрики — асинхронные прогоны с дистанционным HITL (FR-23).

QueueHITL реализует Protocol M-08 поверх очередей: оркестратор не меняется.
Секреты (.env) не покидают процесс сервера; аргументы инструментов — недоверенный
ввод внешней LLM (имена валидируются реестрами, сырые пути не принимаются).
"""
from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.config_loader import load_graph_config
from workshop.factory_cli import ShopInfo, discover_shops, project_status
from workshop.hitl_cli import Accept, HITLDecision, Reject, Revise
from workshop.llm_client import LLMClient
from workshop.models import Artifact
from workshop.orchestrator import run_pipeline
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog
from workshop.wiki_applier import apply_file_map

RUN_IN_PROGRESS = "RUN_IN_PROGRESS"
UNKNOWN_RUN = "UNKNOWN_RUN"
NO_PENDING_INTERACTION = "NO_PENDING_INTERACTION"
WRONG_DECISION_KIND = "WRONG_DECISION_KIND"
UNKNOWN_SHOP = "UNKNOWN_SHOP"
UNKNOWN_PROJECT = "UNKNOWN_PROJECT"
WIKI_REF_ESCAPES_ROOT = "WIKI_REF_ESCAPES_ROOT"
INPUT_FILE_FORBIDDEN = "INPUT_FILE_FORBIDDEN"


@dataclass(frozen=True)
class PendingInteraction:
    kind: str                     # "decision" | "answer"
    artifact_name: str = ""
    artifact_content: str = ""
    reports: tuple[str, ...] = ()
    question: str = ""


@dataclass
class RunState:
    # running | awaiting_decision | awaiting_answer | done | rejected | failed
    status: str = "running"
    pending: PendingInteraction | None = None
    accepted: tuple[str, ...] = ()
    error: str = ""
    node: str = ""                # последний узел по журналу прогона
    iteration: int = 0


class _QueueHITL:
    """HITL Protocol (M-08) поверх очереди: публикует pending и блокируется до решения."""

    def __init__(self, run: "_Run") -> None:
        self._run = run

    def request_acceptance(
        self, artifact: Artifact, reports: list[str]
    ) -> Result[HITLDecision]:
        pending = PendingInteraction(
            kind="decision",
            artifact_name=artifact.ref.name,
            artifact_content=artifact.content,
            reports=tuple(reports),
        )
        decision = self._run.wait_for(pending, expected_status="awaiting_decision")
        return Ok(decision)

    def ask_clarification(self, question: str) -> Result[str]:
        pending = PendingInteraction(kind="answer", question=question)
        answer = self._run.wait_for(pending, expected_status="awaiting_answer")
        return Ok(answer)


class _Run:
    def __init__(self, run_id: str, project_key: str) -> None:
        self.run_id = run_id
        self.project_key = project_key
        self.state = RunState()
        self.lock = threading.Lock()
        self.decisions: queue.Queue = queue.Queue()
        self.thread: threading.Thread | None = None
        self.log_path: Path | None = None
        self.log_offset: int = 0      # журнал project общий — читаем только свой хвост

    def wait_for(self, pending: PendingInteraction, expected_status: str):
        with self.lock:
            self.state.pending = pending
            self.state.status = expected_status
        value = self.decisions.get()  # блокировка без таймаута (решение §10 №15)
        with self.lock:
            self.state.pending = None
            self.state.status = "running"
        return value


class RunManager:
    """TSK-2001: реестр асинхронных прогонов; ≤1 живого прогона на project."""

    def __init__(self, llm_factory=None) -> None:
        self._runs: dict[str, _Run] = {}
        self._lock = threading.Lock()
        # DI для тестов: фабрика LLM-клиента (None → OpenAILLM при старте прогона)
        self._llm_factory = llm_factory

    def start_run(
        self,
        shop: ShopInfo,
        input_material: str,
        mode: str = "interactive",
        project: str | None = None,
        llm: LLMClient | None = None,
    ) -> Result[str]:
        graph_path = shop.graph_path
        if mode == "autopilot":
            if shop.autopilot_path is None:
                return Err(UNKNOWN_SHOP, f"{shop.name}: нет autopilot-графа")
            graph_path = shop.autopilot_path

        graph = load_graph_config(graph_path)
        if isinstance(graph, Err):
            return graph
        project_key = project or graph.value.project or shop.name

        with self._lock:
            for run in self._runs.values():
                if run.project_key == project_key and run.state.status not in ("done", "failed"):
                    return Err(RUN_IN_PROGRESS, project_key)
            run = _Run(run_id=uuid.uuid4().hex[:12], project_key=project_key)
            self._runs[run.run_id] = run

        if llm is None:
            if self._llm_factory is not None:
                llm = self._llm_factory()
            else:
                from workshop.openai_llm import OpenAILLM
                llm = OpenAILLM()

        store = ArtifactStore(Path(f"projects/{project_key}/artifacts"))
        log_path = Path(f"projects/{project_key}/runs/log.jsonl")
        run_log = RunLog(log_path)
        run.log_path = log_path
        run.log_offset = log_path.stat().st_size if log_path.is_file() else 0

        def worker() -> None:
            try:
                result = run_pipeline(
                    graph.value, input_material, store, llm, run_log, _QueueHITL(run)
                )
            except Exception as exc:  # поток не должен умереть молча
                with run.lock:
                    run.state.status = "failed"
                    run.state.error = f"INTERNAL: {exc}"
                return
            with run.lock:
                if isinstance(result, Ok):
                    run.state.status = "done"
                    run.state.accepted = tuple(
                        f"{ref.name}@v{ref.version}"
                        for ref in result.value.accepted_artifacts
                    )
                elif result.code == "REJECTED_BY_USER":
                    # решение пользователя — терминальный исход, не сбой
                    run.state.status = "rejected"
                    run.state.error = result.details
                else:
                    run.state.status = "failed"
                    run.state.error = f"{result.code}: {result.details}"

        run.thread = threading.Thread(target=worker, daemon=True)
        run.thread.start()
        return Ok(run.run_id)

    def get_state(self, run_id: str) -> Result[RunState]:
        run = self._runs.get(run_id)
        if run is None:
            return Err(UNKNOWN_RUN, run_id)
        node, iteration = _last_journal_entry(run)
        with run.lock:
            return Ok(RunState(
                status=run.state.status, pending=run.state.pending,
                accepted=run.state.accepted, error=run.state.error,
                node=node, iteration=iteration,
            ))

    def pending(self, run_id: str) -> Result[PendingInteraction]:
        state = self.get_state(run_id)
        if isinstance(state, Err):
            return state
        if state.value.pending is None:
            return Err(NO_PENDING_INTERACTION, run_id)
        return Ok(state.value.pending)

    def decide(self, run_id: str, decision) -> Result[None]:
        run = self._runs.get(run_id)
        if run is None:
            return Err(UNKNOWN_RUN, run_id)
        with run.lock:
            pending = run.state.pending
        if pending is None:
            return Err(NO_PENDING_INTERACTION, run_id)
        is_answer = isinstance(decision, str)
        if pending.kind == "answer" and not is_answer:
            return Err(WRONG_DECISION_KIND, "прогон ждёт answer(text), не решение гейта")
        if pending.kind == "decision" and is_answer:
            return Err(WRONG_DECISION_KIND, "прогон ждёт accept/revise/reject, не answer")
        run.decisions.put(decision)
        return Ok(None)


def _last_journal_entry(run: _Run) -> tuple[str, int]:
    """Последний узел/итерация ЭТОГО прогона по журналу (записи после offset старта)."""
    import json
    if run.log_path is None or not run.log_path.is_file():
        return "", 0
    with run.log_path.open("r", encoding="utf-8") as stream:
        stream.seek(run.log_offset)
        tail = stream.read()
    node, iteration = "", 0
    for line in tail.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        node = str(record.get("node_id", ""))
        iteration = int(record.get("iteration", 0))
    return node, iteration


def _resolve_shop(name: str) -> Result[ShopInfo]:
    shops = discover_shops()
    if isinstance(shops, Err):
        return shops
    for shop in shops.value:
        if shop.name == name and shop.error is None:
            return Ok(shop)
    return Err(UNKNOWN_SHOP, name)


def _resolve_project_dir(project: str) -> Result[Path]:
    project_dir = Path("projects") / project
    # имя валидируется существованием в projects/ — сырые пути не принимаются
    if "/" in project or ".." in project or not project_dir.is_dir():
        return Err(UNKNOWN_PROJECT, project)
    return Ok(project_dir)


def _resolve_input_material(raw: str) -> Result[str]:
    """Текст ИЛИ путь к файлу (семантика CLI run): клиенты MCP передают пути.

    Недоверенный ввод: файл читается ТОЛЬКО внутри корня фабрики и без скрытых
    компонент пути (.env и т.п. — запрещены). Не-файл возвращается как текст.
    """
    candidate = Path(raw)
    if not candidate.is_file():
        return Ok(raw)
    resolved = candidate.resolve()
    root = Path.cwd().resolve()
    if not resolved.is_relative_to(root):
        return Err(INPUT_FILE_FORBIDDEN, f"{raw}: файл вне корня фабрики")
    if any(part.startswith(".") for part in resolved.relative_to(root).parts):
        return Err(INPUT_FILE_FORBIDDEN, f"{raw}: скрытые файлы запрещены")
    return Ok(resolved.read_text(encoding="utf-8"))


def _resolve_wiki_ref(ref: str, root: Path = Path("wiki")) -> Result[str]:
    candidate = (root / ref).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return Err(WIKI_REF_ESCAPES_ROOT, ref)
    return Ok(ref)


def _err_text(error: Err) -> str:
    return f"ошибка {error.code}: {error.details}"


def build_server(manager: RunManager | None = None):
    """TSK-2002: FastMCP-сервер с инструментами фабрики (описания — TRIGGER/SKIP)."""
    from mcp.server.fastmcp import FastMCP

    if manager is None:
        manager = RunManager()
    server = FastMCP("agent-workshop")

    @server.tool()
    def list_shops() -> str:
        """Реестр цехов фабрики: стадии с гейтами, project, наличие autopilot.
        TRIGGER: перед run_shop — узнать доступные цеха и их конвейеры.
        SKIP: состояние конкретного проекта — это project_status."""
        shops = discover_shops()
        if isinstance(shops, Err):
            return _err_text(shops)
        lines = []
        for shop in shops.value:
            if shop.error is not None:
                lines.append(f"{shop.name}: ОШИБКА КОНФИГА — {shop.error}")
                continue
            chain = " → ".join(f"{s.node_id}[{s.gates}]" for s in shop.stages)
            autopilot = "да" if shop.autopilot_path else "нет"
            lines.append(f"{shop.name} (project: {shop.project}; autopilot: {autopilot}): {chain}")
        return "\n".join(lines)

    @server.tool()
    def run_shop(shop: str, input_material: str, mode: str = "interactive",
                 project: str = "") -> str:
        """Запустить конвейер цеха АСИНХРОННО; вернёт run_id для run_status.
        input_material — текст входа ИЛИ путь к файлу внутри фабрики.
        TRIGGER: пользователь ставит задачу фабрике (имя цеха — из list_shops).
        SKIP: обогащение wiki — используй wiki_update (он же применит результат)."""
        resolved = _resolve_shop(shop)
        if isinstance(resolved, Err):
            return _err_text(resolved)
        material = _resolve_input_material(input_material)
        if isinstance(material, Err):
            return _err_text(material)
        started = manager.start_run(
            resolved.value, material.value, mode=mode, project=project or None
        )
        if isinstance(started, Err):
            return _err_text(started)
        return f"run_id: {started.value}"

    @server.tool()
    def run_status(run_id: str) -> str:
        """Состояние прогона: running(узел, итерация) | awaiting_decision |
        awaiting_answer | done(артефакты) | rejected(причина) | failed(причина).
        TRIGGER: после run_shop — опрос до терминального статуса или awaiting_*.
        SKIP: содержимое ожидающего гейта — это get_pending_interaction."""
        state = manager.get_state(run_id)
        if isinstance(state, Err):
            return _err_text(state)
        value = state.value
        if value.status == "done":
            return "done; принято: " + ", ".join(value.accepted)
        if value.status == "rejected":
            return f"rejected; {value.error}"
        if value.status == "failed":
            return f"failed; {value.error}"
        progress = f" (узел {value.node}, итерация {value.iteration})" if value.node else ""
        return value.status + progress

    @server.tool()
    def get_pending_interaction(run_id: str) -> str:
        """Содержимое ожидающего гейта: отчёты + артефакт, либо вопрос мастерской.
        TRIGGER: run_status вернул awaiting_decision или awaiting_answer.
        SKIP: прогон running/done — ждать или читать артефакты."""
        pending = manager.pending(run_id)
        if isinstance(pending, Err):
            return _err_text(pending)
        value = pending.value
        if value.kind == "answer":
            return f"Вопрос мастерской: {value.question}"
        parts = [f"=== Приёмка: {value.artifact_name} ==="]
        for report in value.reports:
            parts.append("--- отчёт ---\n" + report)
        parts.append("--- артефакт ---\n" + value.artifact_content)
        return "\n".join(parts)

    @server.tool()
    def submit_decision(run_id: str, decision: str, text: str = "") -> str:
        """Решение по ожидающему гейту: decision = accept | revise | reject | answer;
        text — комментарии (revise), причина (reject) или ответ (answer).
        TRIGGER: после get_pending_interaction, когда решение принято.
        SKIP: прогон ничего не ждёт — решение отклонится."""
        if decision == "accept":
            payload: object = Accept()
        elif decision == "revise":
            payload = Revise(comments=text)
        elif decision == "reject":
            payload = Reject(reason=text)
        elif decision == "answer":
            payload = text
        else:
            return f"ошибка {WRONG_DECISION_KIND}: неизвестное решение {decision}"
        result = manager.decide(run_id, payload)
        if isinstance(result, Err):
            return _err_text(result)
        return "принято"

    @server.tool()
    def list_artifacts(project: str) -> str:
        """Артефакты стора проекта (имя@версия).
        TRIGGER: посмотреть, что произвёл и принял конвейер.
        SKIP: содержимое артефакта — это get_artifact."""
        project_dir = _resolve_project_dir(project)
        if isinstance(project_dir, Err):
            return _err_text(project_dir)
        refs = ArtifactStore(project_dir.value / "artifacts").list_artifacts()
        return "\n".join(f"{ref.name}@v{ref.version}" for ref in refs) or "стор пуст"

    @server.tool()
    def get_artifact(project: str, name: str, version: int = 0) -> str:
        """Содержимое артефакта; version=0 — последняя версия.
        TRIGGER: прочитать принятый артефакт (ТЗ, код, вердикт).
        SKIP: список имён — это list_artifacts."""
        project_dir = _resolve_project_dir(project)
        if isinstance(project_dir, Err):
            return _err_text(project_dir)
        store = ArtifactStore(project_dir.value / "artifacts")
        if version <= 0:
            latest = store.latest_version(name)
            if isinstance(latest, Err):
                return _err_text(latest)
            ref = latest.value
        else:
            from workshop.models import ArtifactRef
            ref = ArtifactRef(name=name, version=version)
        loaded = store.load_artifact(ref)
        if isinstance(loaded, Err):
            return _err_text(loaded)
        return loaded.value.content

    @server.tool()
    def get_project_status(project: str) -> str:
        """Сводка проекта: версии артефактов + итерации журнала.
        TRIGGER: обзор состояния проекта после прогонов.
        SKIP: живой прогон — это run_status(run_id)."""
        project_dir = _resolve_project_dir(project)
        if isinstance(project_dir, Err):
            return _err_text(project_dir)
        status = project_status(project_dir.value)
        if isinstance(status, Err):
            return _err_text(status)
        lines = [f"{name} v{version}" for name, version in status.value.artifacts]
        return "\n".join(lines) or "артефактов нет"

    @server.tool()
    def verify_acceptance_tool(target: str) -> str:
        """Сверка sha256 файлов цеха/wiki с приёмочными записями CHANGELOG (FR-17).
        TRIGGER: проверить актуальность приёмки цеха (имя из list_shops) или wiki.
        SKIP: проверка структуры wiki — это wiki_check."""
        from workshop.acceptance import verify_acceptance
        if target == "wiki":
            changelog = Path("wiki/CHANGELOG.md")
        else:
            shop = _resolve_shop(target)
            if isinstance(shop, Err):
                return _err_text(shop)
            changelog = Path(shop.value.graph_path).parent / "CHANGELOG.md"
        report = verify_acceptance(changelog)
        if isinstance(report, Err):
            return _err_text(report)
        value = report.value
        if value.is_clean:
            return f"чисто: {len(value.matched)} файлов актуальны"
        problems = [f"ИЗМЕНЁН: {p}" for p in value.mismatched]
        problems += [f"ОТСУТСТВУЕТ: {p}" for p in value.missing]
        return "\n".join(problems)

    @server.tool()
    def wiki_update(request: str, material: str = "") -> str:
        """Обогатить wiki через цех wiki_maintainer: прогон + авто-apply + CHANGELOG.
        Синхронный (минуты). material — исходный текст/доки для verified-страниц;
        без него страница будет помечена unverified.
        TRIGGER: добавить/обновить знания wiki (технология, область, страница).
        SKIP: чтение wiki — это wiki_read; произвольные цеха — run_shop."""
        shop = _resolve_shop("wiki_maintainer")
        if isinstance(shop, Err):
            return _err_text(shop)
        input_material = request if not material else f"{request}\nМатериал: {material}"
        started = manager.start_run(shop.value, input_material, mode="autopilot")
        if isinstance(started, Err):
            return _err_text(started)
        run = manager._runs[started.value]
        run.thread.join()  # синхронно по ТЗ FR-23
        state = manager.get_state(started.value).value
        if state.status != "done":
            return f"прогон цеха не прошёл: {state.error}"

        store = ArtifactStore(Path("projects/wiki_maintainer/artifacts"))
        latest = store.latest_version("wiki_pages")
        if isinstance(latest, Err):
            return _err_text(latest)
        pages = store.load_artifact(latest.value)
        if isinstance(pages, Err):
            return _err_text(pages)
        spec_content: str | None = None
        latest_spec = store.latest_version("wiki_spec")
        if not isinstance(latest_spec, Err):
            spec = store.load_artifact(latest_spec.value)
            if not isinstance(spec, Err):
                spec_content = spec.value.content
        applied = apply_file_map(pages.value.content, Path("wiki"), spec_content)
        if isinstance(applied, Err):
            return _err_text(applied)
        _append_wiki_changelog(applied.value.changelog_rows, latest.value.version)
        return "применено:\n" + "\n".join(applied.value.written)

    @server.tool()
    def wiki_read(ref: str) -> str:
        """Страница wiki по ссылке (директория → её index.md).
        TRIGGER: прочитать знания wiki (например, python/duckdb или agents/prompts).
        SKIP: изменение wiki — это wiki_update."""
        from workshop.wiki_loader import load_page
        safe_ref = _resolve_wiki_ref(ref)
        if isinstance(safe_ref, Err):
            return _err_text(safe_ref)
        page = load_page(Path("wiki"), safe_ref.value)
        if isinstance(page, Err):
            return _err_text(page)
        return page.value

    @server.tool()
    def wiki_check() -> str:
        """Механическая проверка wiki: индексы, ссылки, сироты, линт скобок.
        TRIGGER: диагностика структуры wiki.
        SKIP: сверка приёмки — это verify_acceptance_tool("wiki")."""
        from workshop.wiki_loader import collect_problems
        problems = collect_problems(Path("wiki"))
        if isinstance(problems, Err):
            return _err_text(problems)
        return "\n".join(problems.value) or "чисто"

    return server


def _append_wiki_changelog(changelog_rows: tuple[str, ...], version: int) -> None:
    """Авто-запись приёмки wiki после apply (правило автора от 09.07.2026)."""
    entry = (
        f"\n## {date.today().isoformat()} — обновление через MCP wiki_update "
        f"(артефакт wiki_pages v{version})\n\n"
        "**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**\n\n"
        "| Файл | Роль | sha256[:16] |\n|---|---|---|\n"
        + "\n".join(changelog_rows) + "\n"
    )
    changelog = Path("wiki/CHANGELOG.md")
    changelog.write_text(
        changelog.read_text(encoding="utf-8") + entry, encoding="utf-8"
    )


def serve() -> int:
    """TSK-2003: stdio-serve (блокирует до EOF клиента)."""
    build_server().run()
    return 0
