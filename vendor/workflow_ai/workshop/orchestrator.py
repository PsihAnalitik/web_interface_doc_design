"""M-09 orchestrator: FSM переходов между узлами, гейты, итерационные циклы (TSK-0901, TSK-0902)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workshop.artifact_store import ArtifactStore
from workshop.codegen_loop import SandboxRunner, run_codegen, serialize_files
from workshop.config_loader import load_model_registry, load_node_config
from workshop.hitl_cli import HITL, Accept, Reject, Revise
from workshop.llm_client import LLMClient
from workshop.material import MaterialStore, ingest
from workshop.models import (
    Artifact,
    ArtifactRef,
    CrosslinkReport,
    GraphConfig,
    ModelRegistry,
    NodeSpec,
)
from workshop.result import Err, Ok, Result
from workshop.models import NodeConfig
from workshop.review_gate import (
    SCALE_P3_HIGH,
    GateDecision,
    evaluate_gate,
    findings_as_context,
    parse_verdict,
    run_review,
)
from workshop.models import WikiRef
from workshop.run_log import RunLog
from workshop.sandbox import run_in_docker
from workshop.wiki_loader import parse_wiki_refs_source
from workshop.workshop_node import (
    OUTPUT_UNPARSEABLE,
    ArtifactOutcome,
    ClarificationOutcome,
    run_workshop,
)

NODE_FAILED = "NODE_FAILED"
MAX_ITERATIONS_EXCEEDED = "MAX_ITERATIONS_EXCEEDED"
REJECTED_BY_USER = "REJECTED_BY_USER"
INVALID_TRANSITION = "INVALID_TRANSITION"
RESUME_STALE_UPSTREAM = "RESUME_STALE_UPSTREAM"


class NodeState(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    HITL = "HITL"
    CLARIFICATION = "CLARIFICATION"
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"


class Event(Enum):
    START = "START"
    ARTIFACT_PRODUCED = "ARTIFACT_PRODUCED"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
    ANSWER_PROVIDED = "ANSWER_PROVIDED"
    REVIEW_PASSED = "REVIEW_PASSED"
    REVIEW_FAILED = "REVIEW_FAILED"
    HITL_ACCEPTED = "HITL_ACCEPTED"
    HITL_REVISED = "HITL_REVISED"
    HITL_REJECTED = "HITL_REJECTED"
    NODE_ERROR = "NODE_ERROR"


# WHY: явная таблица вместо разбросанной логики — недопустимый переход невозможен
# по построению, а не «не должен случиться» (TSK-0902)
_TRANSITIONS: dict[tuple[NodeState, Event], NodeState] = {
    (NodeState.PENDING, Event.START): NodeState.RUNNING,
    (NodeState.RUNNING, Event.ARTIFACT_PRODUCED): NodeState.REVIEW,
    (NodeState.RUNNING, Event.CLARIFICATION_REQUESTED): NodeState.CLARIFICATION,
    (NodeState.CLARIFICATION, Event.ANSWER_PROVIDED): NodeState.RUNNING,
    (NodeState.REVIEW, Event.REVIEW_PASSED): NodeState.HITL,
    (NodeState.REVIEW, Event.REVIEW_FAILED): NodeState.RUNNING,
    (NodeState.HITL, Event.HITL_ACCEPTED): NodeState.ACCEPTED,
    (NodeState.HITL, Event.HITL_REVISED): NodeState.RUNNING,
    (NodeState.HITL, Event.HITL_REJECTED): NodeState.FAILED,
    (NodeState.RUNNING, Event.NODE_ERROR): NodeState.FAILED,
    (NodeState.REVIEW, Event.NODE_ERROR): NodeState.FAILED,
    (NodeState.HITL, Event.NODE_ERROR): NodeState.FAILED,
    (NodeState.CLARIFICATION, Event.NODE_ERROR): NodeState.FAILED,
}


def transition(state: NodeState, event: Event) -> Result[NodeState]:
    next_state = _TRANSITIONS.get((state, event))
    if next_state is None:
        return Err(INVALID_TRANSITION, f"{state.value} + {event.value}")
    return Ok(next_state)


@dataclass(frozen=True)
class PipelineResult:
    accepted_artifacts: tuple[ArtifactRef, ...]
    log_path: str


def run_pipeline(
    graph: GraphConfig,
    initial_content: str,
    store: ArtifactStore,
    llm: LLMClient,
    run_log: RunLog,
    hitl: HITL,
    sandbox: SandboxRunner = run_in_docker,
    resume: bool = False,
) -> Result[PipelineResult]:
    registry: ModelRegistry | None = None
    if graph.llm_profiles_path is not None:
        registry_result = load_model_registry(graph.llm_profiles_path)
        if isinstance(registry_result, Err):
            return registry_result
        registry = registry_result.value

    # артефакт "input" — всегда сырой материал (NFR-04, воспроизводимость);
    # укороченная TOC-версия живёт только в памяти прогона
    saved_input = store.save_artifact("input", initial_content)
    if isinstance(saved_input, Err):
        return saved_input
    input_content = initial_content
    material_store: MaterialStore | None = None
    if graph.material is not None:
        ingested = ingest(
            initial_content,
            chunk_chars=graph.material.chunk_chars,
            chunk_overlap=graph.material.chunk_overlap,
        )
        if isinstance(ingested, Err):
            return ingested
        material_store = ingested.value
        if material_store.total_chars > graph.material.inline_limit_chars:
            # TSK-2203: большой материал не влезает в контекст узла — вместо
            # raw узлы получают оглавление, содержимое читают через material_*
            input_content = (
                material_store.toc()
                + "\n\nМатериал целиком в промпт не включён: содержимое чанков "
                "читай инструментами material_search / material_get."
            )
    input_artifact = Artifact(
        ref=saved_input.value, content=input_content, derived_from=None
    )

    nodes_by_id = {node.id: node for node in graph.nodes}
    predecessors = {
        node.id: [edge.from_node for edge in graph.edges if edge.to_node == node.id]
        for node in graph.nodes
    }
    produced: dict[str, Artifact] = {}
    accepted: list[ArtifactRef] = []

    # TSK-0905: пропускаем принятые узлы, пока не встретим первый отсутствующий;
    # дальше всё выполняется живьём — новый upstream означает новую генерацию
    still_skipping = resume
    for node_id in _topological_order(graph):
        node = nodes_by_id[node_id]
        if still_skipping:
            latest = store.latest_version(node.id)
            if isinstance(latest, Ok):
                loaded = store.load_artifact(latest.value)
                if isinstance(loaded, Err):
                    return loaded
                if loaded.value.derived_from is not None:
                    upstream_present = store.load_artifact(loaded.value.derived_from)
                    if isinstance(upstream_present, Err):
                        return Err(RESUME_STALE_UPSTREAM, node.id)
                # гейты не повторяются: артефакт был принят в исходном прогоне
                produced[node_id] = loaded.value
                accepted.append(loaded.value.ref)
                continue
            still_skipping = False
        upstream = _upstream_for(node_id, predecessors[node_id], produced, input_artifact)
        node_result = _run_node(
            node, upstream, store, llm, run_log, hitl, registry, sandbox,
            material_store, graph.severity_scale,
        )
        if isinstance(node_result, Err):
            return node_result
        produced[node_id] = node_result.value
        accepted.append(node_result.value.ref)

    return Ok(PipelineResult(accepted_artifacts=tuple(accepted), log_path=run_log.path))


def _run_node(
    node: NodeSpec,
    upstream: Artifact,
    store: ArtifactStore,
    llm: LLMClient,
    run_log: RunLog,
    hitl: HITL,
    registry: ModelRegistry | None = None,
    sandbox: SandboxRunner = run_in_docker,
    material: MaterialStore | None = None,
    severity_scale: str = SCALE_P3_HIGH,
) -> Result[Artifact]:
    config_result = _load_config_with_wiki(node.config_path, node.id, registry, store)
    if isinstance(config_result, Err):
        return config_result
    config = config_result.value

    if node.kind == "codegen":
        judge_config = None
        if node.gates.judge_config_path is not None:
            judge_result = _load_config_with_wiki(
                node.gates.judge_config_path, node.id, registry, store
            )
            if isinstance(judge_result, Err):
                return judge_result
            judge_config = judge_result.value
        return _run_codegen_node(
            node, config, judge_config, upstream, store, llm, run_log, hitl, sandbox
        )

    review_config = None
    if node.gates.review_config_path is not None:
        review_result = _load_config_with_wiki(
            node.gates.review_config_path, node.id, registry, store
        )
        if isinstance(review_result, Err):
            return review_result
        review_config = review_result.value

    state = _advance(NodeState.PENDING, Event.START)
    iteration = 1
    iteration_context: str | None = None
    prior_findings_context: str | None = None

    while True:
        if iteration > node.max_iterations:
            return Err(MAX_ITERATIONS_EXCEEDED, node.id)

        outcome = run_workshop(
            node.id, config, upstream, llm, run_log, iteration, iteration_context,
            material=material,
        )
        if isinstance(outcome, Err):
            if outcome.code == OUTPUT_UNPARSEABLE:
                # ответ без блока артефакта — rework, а не отказ узла: модель на
                # больших входах изредка теряет fenced-обёртку; лимит — max_iterations
                iteration_context = (
                    "<format_reminder>\nПредыдущий ответ не принят: в нём не было "
                    "блока артефакта. Выдай артефакт строго по <output_format> — "
                    "fenced-блоком (или file-блоками подряд), без текста вне блоков.\n"
                    "</format_reminder>"
                )
                iteration += 1
                continue
            return Err(NODE_FAILED, f"{node.id}: {outcome.code}: {outcome.details}")

        if isinstance(outcome.value, ClarificationOutcome):
            state = _advance(state, Event.CLARIFICATION_REQUESTED)
            answer = hitl.ask_clarification(outcome.value.question)
            if isinstance(answer, Err):
                return answer
            iteration_context = (
                f"Ответ пользователя на вопрос «{outcome.value.question}»: {answer.value}"
            )
            state = _advance(state, Event.ANSWER_PROVIDED)
            iteration += 1
            continue

        artifact_outcome: ArtifactOutcome = outcome.value
        draft = Artifact(
            ref=ArtifactRef(name=node.id, version=0),  # version=0 — черновик до приёмки
            content=artifact_outcome.content,
            derived_from=upstream.ref,
        )
        state = _advance(state, Event.ARTIFACT_PRODUCED)

        reports: list[str] = []
        if artifact_outcome.crosslink_report is not None:
            reports.append(_render_crosslinks(artifact_outcome.crosslink_report))

        if review_config is not None:
            review = run_review(
                node.id, review_config, draft, llm, run_log, iteration,
                prior_context=prior_findings_context,
            )
            if isinstance(review, Err):
                return Err(NODE_FAILED, f"{node.id}: {review.code}: {review.details}")
            gate = evaluate_gate(review.value, severity_scale)
            reports.append(_render_review_gate(gate))
            if not gate.passed:
                state = _advance(state, Event.REVIEW_FAILED)
                # rework-контекст (TSK-0601): черновик + находки с якорями-id —
                # генератор правит адресно, а не перегенерирует с нуля
                iteration_context = _render_rework_context(
                    draft.content, gate.open_findings
                )
                prior_findings_context = _render_prior_findings(gate.open_findings)
                iteration += 1
                continue
        state = _advance(state, Event.REVIEW_PASSED)

        if node.gates.hitl:
            decision = hitl.request_acceptance(draft, reports)
            if isinstance(decision, Err):
                return decision
            if isinstance(decision.value, Reject):
                _advance(state, Event.HITL_REJECTED)
                return Err(REJECTED_BY_USER, f"{node.id}: {decision.value.reason}")
            if isinstance(decision.value, Revise):
                state = _advance(state, Event.HITL_REVISED)
                iteration_context = (
                    f"<previous_artifact>\n{draft.content}\n</previous_artifact>\n"
                    f"<user_comments>\n{decision.value.comments}\n</user_comments>"
                )
                iteration += 1
                continue
        state = _advance(state, Event.HITL_ACCEPTED)

        saved = store.save_artifact(node.id, artifact_outcome.content, derived_from=upstream.ref)
        if isinstance(saved, Err):
            return Err(NODE_FAILED, f"{node.id}: {saved.code}: {saved.details}")
        return Ok(
            Artifact(ref=saved.value, content=artifact_outcome.content, derived_from=upstream.ref)
        )


def _run_codegen_node(
    node: NodeSpec,
    config: NodeConfig,
    judge_config: NodeConfig | None,
    upstream: Artifact,
    store: ArtifactStore,
    llm: LLMClient,
    run_log: RunLog,
    hitl: HITL,
    sandbox: SandboxRunner,
) -> Result[Artifact]:
    state = _advance(NodeState.PENDING, Event.START)
    iteration = 1
    context: str | None = None

    while True:
        if iteration > node.max_iterations:
            return Err(MAX_ITERATIONS_EXCEEDED, node.id)

        code_result = run_codegen(
            node.id,
            config,
            upstream,
            llm,
            run_log,
            image=node.image,
            test_command=node.test_command,
            max_iterations=node.max_iterations,
            sandbox=sandbox,
            initial_context=context,
        )
        if isinstance(code_result, Err):
            return Err(NODE_FAILED, f"{node.id}: {code_result.code}: {code_result.details}")

        content = serialize_files(code_result.value.files)
        draft = Artifact(
            ref=ArtifactRef(name=node.id, version=0),
            content=content,
            derived_from=upstream.ref,
        )
        state = _advance(state, Event.ARTIFACT_PRODUCED)

        test_report = code_result.value.test_report
        reports = [
            f"Тесты в песочнице: exit={test_report.exit_code}, "
            f"{test_report.duration_s}s\n{test_report.stdout}"
        ]

        # judge-гейт: автоцикл judge→codegen внутри узла (TSK-0901)
        verdict_content: str | None = None
        if judge_config is not None:
            judge_upstream = Artifact(
                ref=draft.ref,
                content=upstream.content + "\n\n" + content,
                derived_from=upstream.ref,
            )
            judge_outcome = run_workshop(
                f"{node.id}:judge", judge_config, judge_upstream, llm, run_log, iteration
            )
            if isinstance(judge_outcome, Err):
                return Err(NODE_FAILED, f"{node.id}: {judge_outcome.code}: {judge_outcome.details}")
            if not isinstance(judge_outcome.value, ArtifactOutcome):
                return Err(NODE_FAILED, f"{node.id}: judge вернул не артефакт-вердикт")
            verdict_content = judge_outcome.value.content
            verdict = parse_verdict(verdict_content)
            if isinstance(verdict, Err):
                return Err(NODE_FAILED, f"{node.id}: {verdict.code}: {verdict.details}")
            if not verdict.value.ready:
                state = _advance(state, Event.REVIEW_FAILED)
                # WHY: в контекст идёт ПОЛНЫЙ вердикт — таблица покрытия говорит
                # кодогенератору, ЧТО именно missing; плюс прошлый file map —
                # доработка адресная, а не перегенерация (TSK-0901)
                context = (
                    f"<previous_artifact>\n{content}\n</previous_artifact>\n"
                    f"<judge_verdict>\n{verdict_content}\n</judge_verdict>"
                )
                iteration += 1
                continue
            reports.append(f"Judge: READY\n{verdict.value.reasons}".rstrip())
        state = _advance(state, Event.REVIEW_PASSED)

        if node.gates.hitl:
            decision = hitl.request_acceptance(draft, reports)
            if isinstance(decision, Err):
                return decision
            if isinstance(decision.value, Reject):
                _advance(state, Event.HITL_REJECTED)
                return Err(REJECTED_BY_USER, f"{node.id}: {decision.value.reason}")
            if isinstance(decision.value, Revise):
                state = _advance(state, Event.HITL_REVISED)
                context = (
                    f"<previous_artifact>\n{content}\n</previous_artifact>\n"
                    f"<user_comments>\n{decision.value.comments}\n</user_comments>"
                )
                iteration += 1
                continue
        state = _advance(state, Event.HITL_ACCEPTED)

        saved = store.save_artifact(node.id, content, derived_from=upstream.ref)
        if isinstance(saved, Err):
            return Err(NODE_FAILED, f"{node.id}: {saved.code}: {saved.details}")
        if verdict_content is not None:
            saved_verdict = store.save_artifact(
                f"{node.id}_verdict", verdict_content, derived_from=saved.value
            )
            if isinstance(saved_verdict, Err):
                return Err(NODE_FAILED, f"{node.id}: {saved_verdict.code}: {saved_verdict.details}")
        return Ok(Artifact(ref=saved.value, content=content, derived_from=upstream.ref))


def _load_config_with_wiki(
    config_path: str,
    node_id: str,
    registry: ModelRegistry | None,
    store: ArtifactStore,
) -> Result[NodeConfig]:
    """Загрузка конфига + резолв wiki_refs_from в статические wiki_refs (FR-19).

    Динамические ссылки берутся из ПОСЛЕДНЕЙ принятой версии артефакта-источника
    (стадия tech_selection); отсутствие артефакта или непарсибельность — NODE_FAILED.
    """
    config_result = load_node_config(config_path, registry)
    if isinstance(config_result, Err):
        return Err(NODE_FAILED, f"{node_id}: {config_result.code}: {config_result.details}")
    config = config_result.value
    if config.wiki_refs_from is None:
        return Ok(config)

    latest = store.latest_version(config.wiki_refs_from)
    if isinstance(latest, Err):
        return Err(
            NODE_FAILED,
            f"{node_id}: wiki_refs_from: артефакт {config.wiki_refs_from} не найден в сторе",
        )
    loaded = store.load_artifact(latest.value)
    if isinstance(loaded, Err):
        return Err(NODE_FAILED, f"{node_id}: {loaded.code}: {loaded.details}")
    dynamic_refs = parse_wiki_refs_source(loaded.value.content)
    if isinstance(dynamic_refs, Err):
        return Err(NODE_FAILED, f"{node_id}: {dynamic_refs.code}: {dynamic_refs.details}")

    # union: статические ссылки узла + динамические из артефакта (TSK-0901);
    # дедупликацию по пути делает бандл TSK-1602
    version_label = f"{config.wiki_refs_from}@v{latest.value.version}"
    resolved = list(config.wiki_refs) + [
        WikiRef(path=f"wiki/{ref}", version=version_label) for ref in dynamic_refs.value
    ]
    return Ok(config.model_copy(update={"wiki_refs": resolved, "wiki_refs_from": None}))


def _advance(state: NodeState, event: Event) -> NodeState:
    result = transition(state, event)
    if isinstance(result, Err):
        # WHY: недопустимый переход недостижим при корректном коде оркестратора —
        # это нарушение инварианта (баг), а не бизнес-ошибка → исключение, не Err
        raise RuntimeError(f"нарушение FSM: {result.details}")
    return result.value


def _topological_order(graph: GraphConfig) -> list[str]:
    incoming_count = {node.id: 0 for node in graph.nodes}
    successors: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        incoming_count[edge.to_node] += 1
        successors[edge.from_node].append(edge.to_node)

    ready = sorted(node_id for node_id, count in incoming_count.items() if count == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor in successors[current]:
            incoming_count[successor] -= 1
            if incoming_count[successor] == 0:
                ready.append(successor)
    return order


def _upstream_for(
    node_id: str,
    predecessor_ids: list[str],
    produced: dict[str, Artifact],
    input_artifact: Artifact,
) -> Artifact:
    if len(predecessor_ids) == 0:
        return input_artifact
    elif len(predecessor_ids) == 1:
        return produced[predecessor_ids[0]]
    else:
        # несколько старших: контенты конкатенируются, ссылка — на первого (MVP)
        combined = "\n\n".join(produced[pred].content for pred in predecessor_ids)
        first = produced[predecessor_ids[0]]
        return Artifact(ref=first.ref, content=combined, derived_from=first.derived_from)


def _render_rework_context(previous_content: str, findings: tuple) -> str:
    """TSK-0601: rework-контекст — черновик дословно + находки F-NN с anchor=локация-id."""
    finding_lines = "\n".join(
        f'  <finding id="F-{index:02d}" weight="p{finding.weight}" '
        f'rule="{finding.rule}" anchor="{finding.location}">{finding.text}</finding>'
        for index, finding in enumerate(findings, start=1)
    )
    return (
        f"<previous_artifact>\n{previous_content}\n</previous_artifact>\n"
        f"<review_findings>\n{finding_lines}\n</review_findings>"
    )


def _render_prior_findings(findings: tuple) -> str:
    """TSK-0701: прошлые находки для повторного прохода ревьюера (те же F-NN)."""
    finding_lines = "\n".join(
        f"  F-{index:02d} [{finding.rule}] {finding.location}: {finding.text}"
        for index, finding in enumerate(findings, start=1)
    )
    return f"<prior_findings>\n{finding_lines}\n</prior_findings>"


def _render_crosslinks(report: CrosslinkReport) -> str:
    lines = ["Проверка кросс-ссылок:"]
    if report.broken_links:
        lines.append("  битые ссылки: " + ", ".join(report.broken_links))
    if report.uncovered_ids:
        lines.append("  незакрытые id старшего: " + ", ".join(report.uncovered_ids))
    if not report.broken_links and not report.uncovered_ids:
        lines.append("  ok")
    return "\n".join(lines)


def _render_review_gate(gate: GateDecision) -> str:
    if gate.passed:
        return "Ревью: PASS"
    return "Ревью: FAIL\n" + findings_as_context(gate.open_findings)
