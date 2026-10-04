"""M-07 review_gate: агентское ревью артефакта и вычисление гейта (TSK-0701, TSK-0702)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from workshop.llm_client import LLMClient
from workshop.models import Artifact, NodeConfig
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog, RunRecord
from workshop.workshop_node import LLM_FAILED, build_node_prompt

REPORT_UNPARSEABLE = "REPORT_UNPARSEABLE"
VERDICT_UNPARSEABLE = "VERDICT_UNPARSEABLE"

# Шкалы весов находок: p3_high — 🔴p3 высший (умолчание всех цехов фабрики);
# p0_high — обратная шкала цехов анализа безопасности (p0 блокирующий)
SCALE_P3_HIGH = "p3_high"
SCALE_P0_HIGH = "p0_high"

# формат находки — из prompts/artifacts/*: «🟠p2 [R2] <локация>: <текст>»
_FINDING_RE = re.compile(
    r"^[^\S\n]*(?:🔴|🟠|🟡|🟢|🔵)\s*p([0-3])\s*\[([^\]]+)\]\s*([^:\n]+):\s*(.+)$",
    re.MULTILINE,
)
_GATE_RE = re.compile(r"Гейт:\s*(PASS|FAIL)", re.IGNORECASE)
_DECISION_RE = re.compile(r"<decision>\s*(READY|NOT_READY)\s*</decision>")
_REASONS_RE = re.compile(r"<reasons>(.*?)</reasons>", re.DOTALL)


@dataclass(frozen=True)
class Finding:
    weight: int
    rule: str
    location: str
    text: str


@dataclass(frozen=True)
class ReviewReport:
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    open_findings: tuple[Finding, ...]


@dataclass(frozen=True)
class VerdictDecision:
    ready: bool
    reasons: str


def parse_verdict(content: str) -> Result[VerdictDecision]:
    """TSK-0703: распарсить вердикт judge из verdict.xml (чистая функция)."""
    decision_match = _DECISION_RE.search(content)
    if decision_match is None:
        return Err(VERDICT_UNPARSEABLE, "нет <decision>READY|NOT_READY</decision>")
    reasons_match = _REASONS_RE.search(content)
    if reasons_match is not None:
        reasons = reasons_match.group(1).strip()
    else:
        reasons = ""
    return Ok(VerdictDecision(ready=decision_match.group(1) == "READY", reasons=reasons))


def run_review(
    node_id: str,
    review_config: NodeConfig,
    artifact: Artifact,
    llm: LLMClient,
    run_log: RunLog,
    iteration: int = 1,
    prior_context: str | None = None,
) -> Result[ReviewReport]:
    # ревью — тоже мастерская: INPUTS = проверяемый артефакт;
    # на повторном проходе — плюс прошлые находки F-NN (TSK-0701)
    prompt = build_node_prompt(review_config, artifact, prior_context)
    if isinstance(prompt, Err):
        return prompt

    llm_result = llm.complete(prompt.value, review_config.llm)
    if isinstance(llm_result, Ok):
        response_text = llm_result.value.text
        usage = dict(llm_result.value.usage)
    else:
        response_text = f"<LLM ERROR {llm_result.code}: {llm_result.details}>"
        usage = {}

    log_result = run_log.append(
        RunRecord(
            node_id=f"{node_id}:review",
            iteration=iteration,
            prompt=prompt.value,
            input_ref=f"{artifact.ref.name}@v{artifact.ref.version}",
            params=review_config.llm.model_dump(),
            response=response_text,
            usage=usage,
        )
    )
    if isinstance(log_result, Err):
        return log_result
    if isinstance(llm_result, Err):
        return Err(LLM_FAILED, f"{llm_result.code}: {llm_result.details}")
    return _parse_report(llm_result.value.text)


def evaluate_gate(
    report: ReviewReport, severity_scale: str = SCALE_P3_HIGH
) -> GateDecision:
    """Блокирующие находки по шкале цеха; шкала объявлена в графе.

    WHY: у цехов анализа безопасности шкала обратная (p0 — высший вес,
    постановка задачи FR-0.2), и без явного объявления гейт пропускал бы
    ровно те находки, ради которых цех существует.
    """
    if severity_scale == SCALE_P0_HIGH:
        open_findings = tuple(f for f in report.findings if f.weight <= 1)
    else:
        open_findings = tuple(f for f in report.findings if f.weight >= 2)
    return GateDecision(passed=len(open_findings) == 0, open_findings=open_findings)


def findings_as_context(findings: tuple[Finding, ...]) -> str:
    return "\n".join(
        f"p{finding.weight} [{finding.rule}] {finding.location}: {finding.text}"
        for finding in findings
    )


def _parse_report(response: str) -> Result[ReviewReport]:
    findings = tuple(
        Finding(weight=int(weight), rule=rule.strip(), location=location.strip(), text=text.strip())
        for weight, rule, location, text in _FINDING_RE.findall(response)
    )
    if findings:
        return Ok(ReviewReport(findings=findings))
    if _GATE_RE.search(response) is not None:
        # находок нет, но гейт заявлен явно — валидный пустой отчёт
        return Ok(ReviewReport(findings=()))
    return Err(REPORT_UNPARSEABLE, "нет ни находок, ни строки «Гейт: PASS/FAIL»")
