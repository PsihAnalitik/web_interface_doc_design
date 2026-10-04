"""M-12 packager: детерминированная сборка выходного пакета проекта (FR-13, TSK-1201).

Пакет — следствие уже принятых артефактов стора и журнала прогонов; LLM не вызывается.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.codegen_loop import SandboxRunner, extract_files
from workshop.models import PackageSpec
from workshop.result import Err, Ok, Result
from workshop.review_gate import parse_verdict
from workshop.sandbox import ExecLimits, run_in_docker

PACKAGE_TARGET_EXISTS = "PACKAGE_TARGET_EXISTS"
PACKAGE_NO_CODE_ARTIFACT = "PACKAGE_NO_CODE_ARTIFACT"
PACKAGE_NO_RUN_LOG = "PACKAGE_NO_RUN_LOG"
PACKAGE_IO_ERROR = "PACKAGE_IO_ERROR"
FREEZE_FAILED = "FREEZE_FAILED"
GIT_FAILED = "GIT_FAILED"

_GIT_IDENTITY = ["-c", "user.name=agent-workshop", "-c", "user.email=workshop@local"]


@dataclass(frozen=True)
class PackageReport:
    out_dir: str
    files: tuple[str, ...]
    git_commit: str


def build_package(
    store: ArtifactStore,
    spec: PackageSpec,
    project: str,
    log_path: Path,
    out_dir: Path,
    sandbox: SandboxRunner = run_in_docker,
) -> Result[PackageReport]:
    if out_dir.exists() and any(out_dir.iterdir()):
        return Err(PACKAGE_TARGET_EXISTS, str(out_dir))
    if not log_path.is_file():
        return Err(PACKAGE_NO_RUN_LOG, str(log_path))

    latest = store.latest_version(spec.code_node)
    if isinstance(latest, Err):
        return Err(PACKAGE_NO_CODE_ARTIFACT, spec.code_node)
    code = store.load_artifact(latest.value)
    if isinstance(code, Err):
        return code

    extraction = extract_files(code.value.content, out_dir)
    if isinstance(extraction, Err):
        return extraction
    files = list(extraction.value)

    # WHY: freeze из образа песочницы — фиксируется ровно та среда, где тесты зелёные
    freeze = sandbox(spec.image, {}, "pip freeze", ExecLimits(timeout_s=120))
    if isinstance(freeze, Err):
        return freeze
    if freeze.value.exit_code != 0:
        return Err(FREEZE_FAILED, freeze.value.stderr[:300])

    documents: dict[str, str] = {"requirements.txt": freeze.value.stdout}
    if spec.serve is not None:
        documents["Dockerfile"] = _dockerfile(spec)
        documents["docker-compose.yml"] = _compose(spec)
    documents["CHANGELOG.md"] = _changelog(store)
    documents["report.md"] = _report(log_path, store, spec, latest.value.version)
    documents["README.md"] = _readme(project, spec, files)

    try:
        for name, content in documents.items():
            (out_dir / name).write_text(content, encoding="utf-8")
            files.append(name)
    except OSError as exc:
        return Err(PACKAGE_IO_ERROR, str(exc))

    commit = git_commit_dir(out_dir, f"chore(package): выходной пакет {project}")
    if isinstance(commit, Err):
        return commit
    return Ok(PackageReport(
        out_dir=str(out_dir), files=tuple(sorted(files)), git_commit=commit.value
    ))


def _dockerfile(spec: PackageSpec) -> str:
    return (
        f"FROM {spec.image}\n"
        "WORKDIR /app\n"
        "COPY . /app\n"
        f'CMD ["sh", "-c", "{spec.serve}"]\n'
    )


def _compose(spec: PackageSpec) -> str:
    lines = [
        "services:",
        "  app:",
        "    build: .",
    ]
    if spec.ports:
        lines.append("    ports:")
        lines.extend(f'      - "{port}"' for port in spec.ports)
    return "\n".join(lines) + "\n"


def _changelog(store: ArtifactStore) -> str:
    lines = [
        "# CHANGELOG — артефакты проекта",
        "",
        "Полная цепочка версий из стора (артефакт ← старший артефакт):",
        "",
    ]
    for ref in store.list_artifacts():
        loaded = store.load_artifact(ref)
        if isinstance(loaded, Ok) and loaded.value.derived_from is not None:
            upstream = loaded.value.derived_from
            origin = f" ← {upstream.name} v{upstream.version}"
        else:
            origin = ""
        lines.append(f"- {ref.name} v{ref.version}{origin}")
    return "\n".join(lines) + "\n"


def _report(log_path: Path, store: ArtifactStore, spec: PackageSpec, code_version: int) -> str:
    runs: dict[str, dict[str, object]] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        node_stats = runs.setdefault(
            entry["node_id"], {"calls": 0, "max_iteration": 0, "model": ""}
        )
        node_stats["calls"] = int(node_stats["calls"]) + 1
        node_stats["max_iteration"] = max(int(node_stats["max_iteration"]), entry["iteration"])
        node_stats["model"] = entry.get("params", {}).get("model", "")

    lines = [
        "# Отчёт о работах",
        "",
        f"Пакет собран из артефакта `{spec.code_node} v{code_version}`.",
        "",
        "| Узел | Вызовов LLM | Макс. итерация | Модель |",
        "|---|---|---|---|",
    ]
    for node_id in sorted(runs):
        stats = runs[node_id]
        lines.append(
            f"| {node_id} | {stats['calls']} | {stats['max_iteration']} | {stats['model']} |"
        )

    verdict_latest = store.latest_version(f"{spec.code_node}_verdict")
    if isinstance(verdict_latest, Ok):
        verdict_artifact = store.load_artifact(verdict_latest.value)
        if isinstance(verdict_artifact, Ok):
            verdict = parse_verdict(verdict_artifact.value.content)
            if isinstance(verdict, Ok):
                decision = "READY" if verdict.value.ready else "NOT_READY"
                lines += ["", f"Вердикт Judge: **{decision}**"]
                if verdict.value.reasons:
                    lines.append(f"Причины: {verdict.value.reasons}")
    return "\n".join(lines) + "\n"


def _readme(project: str, spec: PackageSpec, code_files: list[str]) -> str:
    lines = [
        f"# {project}",
        "",
        "Сгенерировано агентской мастерской из цепочки принятых артефактов",
        "(происхождение — CHANGELOG.md, свод прогонов — report.md).",
        "",
        "## Быстрый старт",
        "",
        "Тесты (та же среда, где они принимались):",
        "```bash",
        # WHY --user: без него файлы кэша (__pycache__) в примонтированном каталоге
        # создаются от root и ломают последующую работу с каталогом пакета
        f'docker run --rm --user "$(id -u):$(id -g)" -v $PWD:/app -w /app '
        f"{spec.image} {spec.test_command}",
        "```",
        "Либо локально: `pip install -r requirements.txt && " + spec.test_command + "`",
    ]
    if spec.serve is not None:
        lines += [
            "",
            "Запуск сервиса:",
            "```bash",
            "docker compose up --build",
            "```",
        ]
    lines += ["", "## Состав", ""]
    lines += [f"- `{name}`" for name in sorted(code_files)]
    return "\n".join(lines) + "\n"


def git_commit_dir(out_dir: Path, message: str) -> Result[str]:
    """git init + add + commit каталога; используется packager (M-12) и assembler (M-14)."""
    if shutil.which("git") is None:
        return Err(GIT_FAILED, "git не найден в PATH")
    commands = [
        ["git", "init", "-q"],
        ["git", *_GIT_IDENTITY, "add", "-A"],
        ["git", *_GIT_IDENTITY, "commit", "-q", "-m", message],
        ["git", "rev-parse", "HEAD"],
    ]
    head = ""
    for command in commands:
        completed = subprocess.run(command, cwd=out_dir, capture_output=True, text=True)
        if completed.returncode != 0:
            return Err(GIT_FAILED, completed.stderr.strip()[:300])
        head = completed.stdout.strip()
    return Ok(head)
