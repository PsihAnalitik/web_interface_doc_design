"""M-10 sandbox: изолированный запуск кода и тестов в Docker (TSK-1001)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from workshop.result import Err, Ok, Result

DOCKER_UNAVAILABLE = "DOCKER_UNAVAILABLE"
IMAGE_UNAVAILABLE = "IMAGE_UNAVAILABLE"
SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT"
SANDBOX_INVALID_PATH = "SANDBOX_INVALID_PATH"


@dataclass(frozen=True)
class ExecLimits:
    timeout_s: int = 120
    mem_mb: int = 512


@dataclass(frozen=True)
class ExecReport:
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float


def run_in_docker(
    image: str,
    files: dict[str, str],
    command: str,
    limits: ExecLimits = ExecLimits(),
) -> Result[ExecReport]:
    if shutil.which("docker") is None:
        return Err(DOCKER_UNAVAILABLE, "docker не найден в PATH")

    with tempfile.TemporaryDirectory(prefix="workshop-sandbox-") as workdir:
        root = Path(workdir).resolve()
        for rel_path, content in files.items():
            target = (root / rel_path).resolve()
            # WHY: пути генерирует LLM — недоверенный ввод; выход за пределы
            # рабочего каталога («../…», абсолютные пути) отклоняем
            if not target.is_relative_to(root):
                return Err(SANDBOX_INVALID_PATH, rel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        docker_command = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", f"{limits.mem_mb}m",
            # WHY: контейнер под текущим uid — иначе файлы, созданные процессом
            # в /work, принадлежат root и ломают очистку временного каталога
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{root}:/work",
            "-w", "/work",
            image,
            "sh", "-c", command,
        ]
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                docker_command, capture_output=True, text=True, timeout=limits.timeout_s
            )
        except subprocess.TimeoutExpired:
            return Err(SANDBOX_TIMEOUT, f"превышен лимит {limits.timeout_s}s")
        duration_s = round(time.monotonic() - started_at, 3)

    if completed.returncode == 125:
        # 125 — отказ самого docker (не команды в контейнере)
        stderr = completed.stderr.strip()
        if "Unable to find image" in stderr or "pull access denied" in stderr:
            return Err(IMAGE_UNAVAILABLE, stderr[:300])
        return Err(DOCKER_UNAVAILABLE, stderr[:300])

    # WHY: ненулевой exit_code (в т.ч. упавшие тесты) — валидный Ok-результат;
    # Err — только отказ механизма песочницы (контракт TSK-1001)
    return Ok(
        ExecReport(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_s=duration_s,
        )
    )
