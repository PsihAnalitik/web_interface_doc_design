"""M-08 hitl_cli: human-in-the-loop приёмка через CLI (TSK-0801, TSK-0802)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from workshop.models import Artifact
from workshop.result import Err, Ok, Result

INPUT_ABORTED = "INPUT_ABORTED"


@dataclass(frozen=True)
class Accept:
    pass


@dataclass(frozen=True)
class Revise:
    comments: str


@dataclass(frozen=True)
class Reject:
    reason: str


type HITLDecision = Accept | Revise | Reject


class HITL(Protocol):
    def request_acceptance(
        self, artifact: Artifact, reports: list[str]
    ) -> Result[HITLDecision]: ...

    def ask_clarification(self, question: str) -> Result[str]: ...


class CliHITL:
    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._print = print_fn

    def request_acceptance(
        self, artifact: Artifact, reports: list[str]
    ) -> Result[HITLDecision]:
        # отчёты гейтов ПЕРЕД артефактом: решение чаще принимается по ним (FR-22)
        self._print(f"=== Приёмка: {artifact.ref.name} ===")
        for report in reports:
            self._print("--- отчёт ---")
            self._print(report)
        self._print("--- артефакт ---")
        self._print(artifact.content)
        try:
            while True:
                answer = self._input("[a] принять / [r] правки / [x] отклонить: ").strip().lower()
                if answer == "a":
                    return Ok(Accept())
                elif answer == "r":
                    comments = self._input("Комментарии: ").strip()
                    if comments:
                        return Ok(Revise(comments=comments))
                    self._print("Комментарии пустые — повторите.")
                elif answer == "x":
                    reason = self._input("Причина отклонения: ").strip()
                    return Ok(Reject(reason=reason))
                else:
                    self._print("Ожидаю a / r / x.")
        except (EOFError, KeyboardInterrupt):
            return Err(INPUT_ABORTED)

    def ask_clarification(self, question: str) -> Result[str]:
        self._print(f"Вопрос мастерской: {question}")
        try:
            while True:
                answer = self._input("> ").strip()
                if answer:
                    return Ok(answer)
                self._print("Ответ пустой — повторите.")
        except (EOFError, KeyboardInterrupt):
            return Err(INPUT_ABORTED)
