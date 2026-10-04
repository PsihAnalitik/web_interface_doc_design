"""M-11 codegen_loop: генерация кода → прогон тестов в песочнице → улучшение (TSK-1101)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from workshop.llm_client import LLMClient
from workshop.models import Artifact, NodeConfig
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog, RunRecord
from workshop.sandbox import ExecLimits, ExecReport, run_in_docker
from workshop.workshop_node import LLM_FAILED, OUTPUT_UNPARSEABLE, build_node_prompt

MAX_ITERATIONS_EXCEEDED = "MAX_ITERATIONS_EXCEEDED"
NO_FILE_BLOCKS = "NO_FILE_BLOCKS"
EXTRACT_INVALID_PATH = "EXTRACT_INVALID_PATH"
EXTRACT_TARGET_EXISTS = "EXTRACT_TARGET_EXISTS"
EXTRACT_IO_ERROR = "EXTRACT_IO_ERROR"

# формат file map в ответе LLM: fenced-блоки ```file:<путь> ... ``` (см. TSK-1101).
# Закрывающий ``` — только перед следующим ```file: или концом текста (lookahead):
# вложенные fenced-блоки внутри файла легальны (wiki-страницы с примерами кода)
_FILE_BLOCK_RE = re.compile(
    r"```file:([^\s`]+)\n(.*?)```(?=\s*(?:```file:|$))", re.DOTALL
)

type SandboxRunner = Callable[[str, dict[str, str], str, ExecLimits], Result[ExecReport]]


@dataclass(frozen=True)
class CodeArtifact:
    files: dict[str, str]
    test_report: ExecReport


def parse_file_map(content: str) -> dict[str, str]:
    """Разбор file map ```file:путь``` (общий для M-11 и M-18)."""
    return {path: body for path, body in _FILE_BLOCK_RE.findall(content)}


def serialize_files(files: dict[str, str]) -> str:
    """Каноничная сериализация file map — тем же форматом ```file:путь```, что и парсится."""
    blocks: list[str] = []
    for path in sorted(files):
        content = files[path]
        if not content.endswith("\n"):
            content += "\n"
        blocks.append(f"```file:{path}\n{content}```")
    return "\n\n".join(blocks)


def extract_files(content: str, out_dir: Path) -> Result[list[str]]:
    """TSK-1102: распаковать file map артефакта в каталог как обычные файлы."""
    files = {path: body for path, body in _FILE_BLOCK_RE.findall(content)}
    if not files:
        return Err(NO_FILE_BLOCKS, "в артефакте нет блоков ```file:<путь>")

    root = out_dir.resolve()
    targets: dict[str, Path] = {}
    for rel_path in files:
        target = (root / rel_path).resolve()
        # пути пришли из ответа LLM — недоверенный ввод (как в M-10)
        if not target.is_relative_to(root):
            return Err(EXTRACT_INVALID_PATH, rel_path)
        if target.exists():
            return Err(EXTRACT_TARGET_EXISTS, str(target))
        targets[rel_path] = target

    written: list[str] = []
    try:
        for rel_path, target in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as stream:
                stream.write(files[rel_path])
            written.append(rel_path)
    except FileExistsError:
        return Err(EXTRACT_TARGET_EXISTS, rel_path)
    except OSError as exc:
        return Err(EXTRACT_IO_ERROR, str(exc))
    return Ok(sorted(written))


def run_codegen(
    node_id: str,
    config: NodeConfig,
    c4: Artifact,
    llm: LLMClient,
    run_log: RunLog,
    image: str,
    test_command: str = "python -m pytest -q",
    max_iterations: int = 3,
    sandbox: SandboxRunner = run_in_docker,
    limits: ExecLimits = ExecLimits(),
    initial_context: str | None = None,
) -> Result[CodeArtifact]:
    iteration_context: str | None = initial_context

    for iteration in range(1, max_iterations + 1):
        prompt = build_node_prompt(config, c4, iteration_context)
        if isinstance(prompt, Err):
            return prompt

        llm_result = llm.complete(prompt.value, config.llm)
        if isinstance(llm_result, Ok):
            response_text = llm_result.value.text
            usage = dict(llm_result.value.usage)
        else:
            response_text = f"<LLM ERROR {llm_result.code}: {llm_result.details}>"
            usage = {}

        log_result = run_log.append(
            RunRecord(
                node_id=f"{node_id}:codegen",
                iteration=iteration,
                prompt=prompt.value,
                input_ref=f"{c4.ref.name}@v{c4.ref.version}",
                params=config.llm.model_dump(),
                response=response_text,
                usage=usage,
            )
        )
        if isinstance(log_result, Err):
            return log_result
        if isinstance(llm_result, Err):
            return Err(LLM_FAILED, f"{llm_result.code}: {llm_result.details}")

        files = {path: content for path, content in _FILE_BLOCK_RE.findall(llm_result.value.text)}
        if not files:
            return Err(OUTPUT_UNPARSEABLE, "в ответе нет ни одного блока ```file:<путь>")

        exec_result = sandbox(image, files, test_command, limits)
        if isinstance(exec_result, Err):
            return exec_result
        if exec_result.value.exit_code == 0:
            return Ok(CodeArtifact(files=files, test_report=exec_result.value))

        # консультант второго мнения: один вызов перед последней попыткой,
        # свежий контекст (C4 + текущий file map + отчёт), без цепочки rework.
        # Best-effort: ошибка консультанта логируется, но узел не роняет
        advice = ""
        if config.consultant_llm is not None and iteration == max_iterations - 1:
            sandbox_env = (
                f"\n<sandbox_env>\n{config.sandbox_notes}\n</sandbox_env>\n"
                if config.sandbox_notes is not None
                else ""
            )
            consult_prompt = (
                "Ты консультант по отладке. Кодогенератор дважды не смог пройти тесты.\n"
                "Найди первопричину и дай короткие директивы по исправлению "
                "(без полного кода).\n"
                f"Тесты выполняются командой `{test_command}` в docker-образе "
                f"`{image}`: набор пакетов фиксирован образом, pip install / "
                "requirements не выполняются — не диагностируй отсутствие пакета, "
                "если он не указан в <sandbox_env>.\n"
                "Сначала проверь полноту file map в <current_files>: артефакт обязан "
                "содержать ВСЕ файлы (модули и тесты по контракту); если файлов не "
                "хватает, первая директива — выдать полный file map.\n"
                f"{sandbox_env}\n"
                f"<contract>\n{c4.content}\n</contract>\n"
                f"<current_files>\n{serialize_files(files)}\n</current_files>\n"
                f"<test_report>\nexit_code={exec_result.value.exit_code}\n"
                f"stdout:\n{exec_result.value.stdout}\n"
                f"stderr:\n{exec_result.value.stderr}\n</test_report>"
            )
            consult_result = llm.complete(consult_prompt, config.consultant_llm)
            if isinstance(consult_result, Ok):
                consult_response = consult_result.value.text
                consult_usage = dict(consult_result.value.usage)
                advice = f"\n<consultant_advice>\n{consult_response}\n</consultant_advice>"
            else:
                consult_response = (
                    f"<LLM ERROR {consult_result.code}: {consult_result.details}>"
                )
                consult_usage = {}
            consult_log = run_log.append(
                RunRecord(
                    node_id=f"{node_id}:consult",
                    iteration=iteration,
                    prompt=consult_prompt,
                    input_ref=f"{c4.ref.name}@v{c4.ref.version}",
                    params=config.consultant_llm.model_dump(),
                    response=consult_response,
                    usage=consult_usage,
                )
            )
            if isinstance(consult_log, Err):
                return consult_log

        # rework-контекст (TSK-1101): прошлый file map дословно + отчёт тестов —
        # кодогенератор правит адресно, нетронутые файлы копирует
        iteration_context = (
            f"<previous_artifact>\n{serialize_files(files)}\n</previous_artifact>\n"
            f"<test_report>\nТесты не прошли (exit_code={exec_result.value.exit_code}).\n"
            f"stdout:\n{exec_result.value.stdout}\n"
            f"stderr:\n{exec_result.value.stderr}\n</test_report>{advice}"
        )

    return Err(MAX_ITERATIONS_EXCEEDED, node_id)
