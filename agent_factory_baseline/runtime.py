"""Build native factory nodes; gate their outputs against the passport contracts."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import time

from workshop.artifact_store import ArtifactStore
from workshop.hitl_cli import Accept, Revise
from workshop.llm_client import LLMResponse
from workshop.models import GraphConfig, LLMParams
from workshop.orchestrator import run_pipeline
from workshop.result import Err, Ok
from workshop.run_log import RunLog

from .catalog import CATALOG_VERSION, FIELDS
from .inputs import Source, wire_json
from .knowledge import DEFAULT_WIKI, Knowledge, prepare_knowledge
from .models import Extraction, FieldVerdict, Synthesis
from .passport import ProjectPassport, build_passport, render_passport
from .validation import validate_extraction, validate_synthesis, validate_verdict

PACKAGE = Path(__file__).resolve().parent
SCHEMAS = {"extract": Extraction, "verdict": FieldVerdict, "synthesis": Synthesis}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_graph(output: Path, sources: dict[str, Source], params: LLMParams,
                max_iterations: int = 3, fields=FIELDS,
                verdict_params: LLMParams | None = None,
                knowledge: Knowledge | None = None) -> GraphConfig:
    """Create each field's extraction/verdict pair plus a final evidence-aware synthesis."""
    knowledge = knowledge or prepare_knowledge(output, DEFAULT_WIKI, fields)
    directory = output / "config"
    directory.mkdir()
    stage_map = directory / "stage_map.md"
    stage_map.write_text("", encoding="utf-8")
    nodes, edges = [], []
    for field in fields:
        edges.extend([{"from": f"extract_{field.id}", "to": f"verdict_{field.id}"},
                      {"from": f"extract_{field.id}", "to": "synthesis"},
                      {"from": f"verdict_{field.id}", "to": "synthesis"}])
    stages = [(kind, f"{kind}_{f.id}", {"field": asdict(f)})
              for f in fields for kind in ("extract", "verdict")]
    stages.append(("synthesis", "synthesis", {"fields": [asdict(f) for f in fields]}))
    for kind, node_id, context in stages:
        field_id = context["field"]["id"] if "field" in context else None
        context["agent"] = {"id": node_id, "stage": kind,
                            "specialization": context["field"]["title"] if field_id else "Согласованность паспорта"}
        if kind != "extract":
            context["relation_rules"] = [r.model_dump() for r in knowledge.relations.rules
                if field_id is None or field_id in {r.source, r.target}]
        context.update({"catalog_version": CATALOG_VERSION,
                        "sources": [s.metadata() for s in sources.values()]})
        template = (PACKAGE / "prompts" / f"{kind}.md").read_text(encoding="utf-8")
        prompt = template.replace("@@SCHEMA@@", wire_json(SCHEMAS[kind].model_json_schema()))
        prompt = prompt.replace("@@CONTEXT@@", wire_json(context))
        prompt = f"<baseline_node>{node_id}</baseline_node>\n" + prompt
        prompt_path = directory / f"{node_id}.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        config_path = directory / f"{node_id}.json"
        write_json(config_path, {"base_prompt_path": str(prompt_path),
                                "stage_map_path": str(stage_map), "tools": ["wiki_search", "wiki_get"],
                                "wiki_tree_root": str(knowledge.root),
                                "wiki_refs": knowledge.refs(kind, field_id), "llm": (params if kind == "extract" else
                                    verdict_params or params).model_dump()})
        nodes.append({"id": node_id, "config_path": str(config_path),
                      "gates": {"hitl": True}, "max_iterations": max_iterations})
    graph = GraphConfig.model_validate({"nodes": nodes, "edges": edges})
    write_json(directory / "graph.json", graph.model_dump(by_alias=True))
    return graph


class ValidationGate:
    """Programmatic acceptance, NOT an expert approval, using the factory's bounded rework."""

    def __init__(self, sources: dict[str, Source], fields=FIELDS):
        self.sources = sources
        self.fields = {f.id: f for f in fields}
        self.extractions: dict[str, Extraction] = {}
        self.verdicts: dict[str, FieldVerdict] = {}
        self.synthesis: Synthesis | None = None
        self.rejections: list[dict] = []

    def request_acceptance(self, artifact, reports):
        node_id = artifact.ref.name
        try:
            if node_id.startswith("extract_"):
                field = self.fields[node_id.removeprefix("extract_")]
                value = Extraction.model_validate_json(artifact.content)
                validate_extraction(value, field, self.sources)
                self.extractions[field.id] = value
            elif node_id.startswith("verdict_"):
                field = self.fields[node_id.removeprefix("verdict_")]
                value = FieldVerdict.model_validate_json(artifact.content)
                validate_verdict(value, field, self.extractions[field.id])
                self.verdicts[field.id] = value
            elif node_id == "synthesis":
                value = Synthesis.model_validate_json(artifact.content)
                validate_synthesis(value, tuple(self.fields.values()), self.extractions,
                                   self.verdicts, self.sources)
                self.synthesis = value
            else:
                return Err("UNKNOWN_BASELINE_NODE", node_id)
        except (ValueError, KeyError) as exc:
            issue = {"node": node_id, "error": str(exc)}
            self.rejections.append(issue)
            return Ok(Revise(comments=wire_json({"validation_error": issue,
                "action": "Исправь контракт/ссылки/цитаты; не выдумывай отсутствующие сведения."})))
        return Ok(Accept())

    def ask_clarification(self, question):
        return Err("UNEXPECTED_CLARIFICATION", "Return insufficient_data in the contract instead")


class RecordingLLM:
    """Record every attempt and encode JSON for the native template/fence parser."""

    def __init__(self, delegate, path: Path, gate: ValidationGate | None = None):
        self.delegate = delegate
        self.path = path
        self.gate = gate
        self.calls = 0

    def complete(self, prompt, params, tools=()):
        match = re.search(r"<baseline_node>([a-z_]+)</baseline_node>", prompt)
        node = match[1] if match else ""
        context_block = "<source_context>\n@@SOURCE_CONTEXT@@\n</source_context>"
        if (self.gate is not None and context_block in prompt
                and (node == "synthesis" or node.startswith("verdict_"))):
            extractions = (self.gate.extractions.values() if node == "synthesis" else
                           [self.gate.extractions[node.removeprefix("verdict_")]])
            originals = []
            for extraction in extractions:
                for item in extraction.items:
                    for evidence in item.evidence:
                        source = self.gate.sources[evidence.source_id]
                        originals.append({
                            "evidence_id": evidence.id, "source_id": source.id,
                            "start_line": evidence.start_line, "end_line": evidence.end_line,
                            "source_text": "\n".join(source.text.splitlines()[
                                evidence.start_line - 1:evidence.end_line]),
                        })
            prompt = prompt.replace(context_block, "<source_context>\n" + wire_json({
                "originals": originals,
                "sources": [s.payload() for s in self.gate.sources.values()],
            }) + "\n</source_context>", 1)
        started = time.monotonic()
        result = self.delegate.complete(prompt, params, tools)
        self.calls += 1
        record = {"call": self.calls, "params": params.model_dump(), "prompt": prompt,
                  "elapsed_seconds": time.monotonic() - started,
                  "status": "ok" if isinstance(result, Ok) else "failed"}
        if hasattr(self.delegate, "last_responses"):
            record["provider_responses"] = self.delegate.last_responses
        if isinstance(result, Err):
            record.update({"code": result.code, "details": result.details})
        else:
            record.update({"response": result.value.text, "usage": result.value.usage,
                           "tool_trace": list(result.value.tool_trace)})
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if isinstance(result, Err):
            return result
        raw = result.value.text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", raw, re.S)
        if fenced:
            raw = fenced[1]
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = {"_format_error": "Expected one JSON object", "_raw_response": result.value.text}
        text = "```json\n" + wire_json(value) + "\n```"
        return Ok(LLMResponse(text=text, usage=result.value.usage, tool_trace=result.value.tool_trace))


class ReplayLLM:
    """Explicit scripted fixture; contains no model or automatic document analysis."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls = 0

    def complete(self, prompt, params, tools=()):
        self.calls += 1
        match = re.search(r"<baseline_node>([a-z_]+)</baseline_node>", prompt)
        if not match or match[1] not in self.responses:
            return Err("REPLAY_MISSING", match[1] if match else "no node marker")
        return Ok(LLMResponse(text=json.dumps(self.responses[match[1]], ensure_ascii=False)))


def factory_revision() -> dict:
    import workshop
    root = Path(workshop.__file__).resolve().parent.parent
    snapshot = root / "SNAPSHOT.json"
    if snapshot.exists():
        return {"path": str(root), "snapshot": json.loads(snapshot.read_text(encoding="utf-8"))}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    state = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           cwd=root, capture_output=True, text=True)
    return {"path": str(root), "commit": revision.stdout.strip() if revision.returncode == 0 else None,
            "tracked_changes": bool(state.stdout.strip()) if state.returncode == 0 else None}


def render_report(result: dict, sources: dict[str, Source] | None = None) -> str:
    parts = ["# Результат анализа паспорта", "",
             f"Режим: **{result['mode']}**. Статус: **{result['status']}**.",
             "Программная проверка формата и ссылок не заменяет проверку выводов человеком.", ""]
    if result["mode"] == "replay":
        parts.extend(["Демонстрация по записанному сценарию; LLM не вызывалась. Качество анализа не измерялось.", ""])
    if result.get("error"):
        parts.extend(["Анализ не завершён. Частичные результаты нельзя считать полным заключением.",
                      f"Ошибка: {result['error']}", ""])
    synthesis = result.get("synthesis")
    if synthesis:
        parts.extend([synthesis["summary"], "", "## Замечания в порядке приоритета", ""])
        for index, finding in enumerate(synthesis["findings"], 1):
            parts.extend([f"### {index}. [{finding['severity']}] {finding['statement']}", "",
                          f"Вопрос: {finding['question']}", f"Влияние: {finding['impact']}",
                          f"Поля: {', '.join(finding['field_ids'])}",
                          f"Зависимые поля: {', '.join(finding['affected_fields']) or 'не указаны'}",
                          f"Основания: {', '.join(finding['evidence_ids']) or 'зафиксированный недостаток данных'}", ""])
        parts.extend(["## Проработанность по компонентам", ""])
        for assessment in synthesis["maturity"]:
            parts.append(f"- {assessment['component']}: **{assessment['level']}** — {assessment['reason']}")
        parts.extend(["", "## Исключённые локальные замечания", ""])
        for exclusion in synthesis["excluded_findings"]:
            parts.append(f"- {exclusion['finding_id']}: {exclusion['reason']}")
    parts.extend(["", "## Сведения по полям паспорта", ""])
    for field_id, extraction in result["extractions"].items():
        parts.extend([f"### {field_id}", ""])
        for item in extraction["items"]:
            parts.append(f"- {item['check_id']}: {item['status']}")
            for evidence in item["evidence"]:
                target = f"sources/{evidence['source_id']}.md#L{evidence['start_line']}"
                parts.extend([f"  - {evidence['id']}: [{evidence['source_id']}:{evidence['start_line']}–{evidence['end_line']}]({target})",
                              "", "Текст модели (пересказ или цитата):", ""])
                parts.extend("> " + line for line in evidence["quote"].splitlines())
                parts.append("")
                if sources is not None:
                    source = sources[evidence["source_id"]]
                    parts.extend(["Оригинал по ссылке (подтянут кодом):", ""])
                    parts.extend("> " + line for line in source.text.splitlines()[
                        evidence["start_line"] - 1:evidence["end_line"]])
                    parts.append("")
        verdict = result["verdicts"].get(field_id)
        if verdict:
            for check in verdict["checks"]:
                parts.append(f"- Заключение {check['check_id']}: **{check['status']}** — {check['reason']}")
        parts.append("")
    return "\n".join(parts) + "\n"


def execute(sources: dict[str, Source], output: Path, params: LLMParams, llm=None,
            mode: str = "live", max_iterations: int = 3, fields=FIELDS,
            verdict_params: LLMParams | None = None, wiki_root: Path | None = None) -> dict:
    """Run native workflow_ai. A new directory owns each run; no resume/overwrite."""
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    knowledge = prepare_knowledge(output, wiki_root or DEFAULT_WIKI, fields)
    sources = knowledge.case_sources(sources, fields)
    (output / "sources").mkdir()
    for source in sources.values():
        (output / "sources" / f"{source.id}.md").write_text(source.text, encoding="utf-8")
    graph = build_graph(output, sources, params, max_iterations, fields, verdict_params, knowledge)
    assignments = {node.id: json.loads(Path(node.config_path).read_text())["wiki_refs"]
                   for node in graph.nodes}
    write_json(output / "knowledge.json", {
        "original_root": str((wiki_root or DEFAULT_WIKI).resolve()),
        "snapshot_root": str(knowledge.root), "pages_sha256": knowledge.pages,
        "relation_version": knowledge.relations.version,
        "relations": [r.model_dump() for r in knowledge.relations.rules],
        "case_registry": knowledge.cases.model_dump(), "node_wiki_refs": assignments,
        "case_sources": [s.metadata() for s in sources.values() if s.id.startswith("K_")],
    })
    write_json(output / "passport.schema.json", ProjectPassport.model_json_schema())
    configuration = {p.name: sha256(p.read_bytes()).hexdigest()
                     for p in sorted((output / "config").iterdir())}
    manifest = {"schema_version": "baseline.v0.1", "catalog_version": CATALOG_VERSION,
                "mode": mode, "status": "planned" if mode == "plan" else "running",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "factory": factory_revision(), "model": params.model_dump(),
                "stage_models": {"extract": params.model_dump(),
                                 "verdict": (verdict_params or params).model_dump(),
                                 "synthesis": (verdict_params or params).model_dump()},
                "sources": [s.metadata() for s in sources.values()],
                "knowledge_sha256": sha256((output / "knowledge.json").read_bytes()).hexdigest(),
                "configuration_sha256": configuration,
                "parents": {n.id: [e.from_node for e in graph.edges if e.to_node == n.id]
                            for n in graph.nodes}, "max_iterations": max_iterations}
    write_json(output / "manifest.json", manifest)
    if mode == "plan":
        planned = {"status": "planned", "mode": "plan", "extractions": {}, "verdicts": {}, "synthesis": None}
        passport = build_passport(planned, sources, fields)
        write_json(output / "passport.json", passport.model_dump())
        (output / "passport.md").write_text(render_passport(passport, sources), encoding="utf-8")
        return manifest
    if llm is None:
        raise ValueError("A model client or explicit replay client is required")
    gate = ValidationGate(sources, fields)
    client = RecordingLLM(llm, output / "calls.jsonl", gate)
    result = {"schema_version": "baseline.v0.1", "catalog_version": CATALOG_VERSION,
              "mode": mode, "status": "interrupted", "error": None,
              "extractions": {}, "verdicts": {}, "synthesis": None}
    started = time.monotonic()
    try:
        run = run_pipeline(graph, wire_json({"sources": [s.payload() for s in sources.values()]}),
                           ArtifactStore(output / "artifacts"), client,
                           RunLog(output / "factory.jsonl"), gate)
        if isinstance(run, Err):
            result.update(status="failed", error=f"{run.code}: {run.details}")
        elif gate.synthesis is None:
            result.update(status="failed", error="SYNTHESIS_MISSING")
        else:
            result.update(status="completed", synthesis=gate.synthesis.model_dump())
    except (OSError, ValueError) as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result["extractions"] = {key: value.model_dump() for key, value in gate.extractions.items()}
        result["verdicts"] = {key: value.model_dump() for key, value in gate.verdicts.items()}
        manifest.update(status=result["status"], calls=client.calls, error=result["error"],
                        elapsed_seconds=time.monotonic() - started,
                        finished_at=datetime.now(timezone.utc).isoformat())
        write_json(output / "manifest.json", manifest)
        write_json(output / "result.json", result)
        write_json(output / "validation.json", gate.rejections)
        (output / "report.md").write_text(render_report(result, sources), encoding="utf-8")
        passport = build_passport(result, sources, fields)
        write_json(output / "passport.json", passport.model_dump())
        (output / "passport.md").write_text(render_passport(passport, sources), encoding="utf-8")
    return result
