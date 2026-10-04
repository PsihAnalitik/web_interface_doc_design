"""M-14 assembler: adapters — сборка продукта из независимых сервисов-пакетов (FR-14, TSK-1401).

Детерминированная compose-сборка без LLM: продукт — следствие уже собранных пакетов (FR-13).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from workshop.models import ProductSpec, ServiceSpec
from workshop.packager import git_commit_dir
from workshop.result import Err, Ok, Result

PRODUCT_TARGET_EXISTS = "PRODUCT_TARGET_EXISTS"
SERVICE_PACKAGE_NOT_FOUND = "SERVICE_PACKAGE_NOT_FOUND"
SERVICE_NO_DOCKERFILE = "SERVICE_NO_DOCKERFILE"
PRODUCT_IO_ERROR = "PRODUCT_IO_ERROR"


@dataclass(frozen=True)
class ProductReport:
    out_dir: str
    services: tuple[str, ...]
    git_commit: str


def assemble_product(spec: ProductSpec, out_dir: Path) -> Result[ProductReport]:
    if out_dir.exists() and any(out_dir.iterdir()):
        return Err(PRODUCT_TARGET_EXISTS, str(out_dir))

    # валидация ВСЕХ пакетов до первого копирования — нет частичного результата
    package_dirs: dict[str, Path] = {}
    for service in spec.services:
        package_dir = Path(service.package)
        if not package_dir.is_dir():
            return Err(SERVICE_PACKAGE_NOT_FOUND, f"{service.name}: {service.package}")
        if not (package_dir / "Dockerfile").is_file():
            # WHY: пакет без Dockerfile (цех без serve) — не сервис, в compose ему нечего делать
            return Err(SERVICE_NO_DOCKERFILE, f"{service.name}: {service.package}")
        package_dirs[service.name] = package_dir

    try:
        for service in spec.services:
            shutil.copytree(
                package_dirs[service.name],
                out_dir / "services" / service.name,
                # WHY: .git пакета не копируется — у продукта собственная история
                ignore=shutil.ignore_patterns(".git"),
            )
        (out_dir / "docker-compose.yml").write_text(_compose(spec), encoding="utf-8")
        (out_dir / "README.md").write_text(_readme(spec), encoding="utf-8")
    except OSError as exc:
        return Err(PRODUCT_IO_ERROR, str(exc))

    commit = git_commit_dir(out_dir, f"chore(product): сборка продукта {spec.product}")
    if isinstance(commit, Err):
        return commit
    return Ok(ProductReport(
        out_dir=str(out_dir),
        services=tuple(service.name for service in spec.services),
        git_commit=commit.value,
    ))


def _compose(spec: ProductSpec) -> str:
    lines = ["services:"]
    for service in spec.services:
        lines.append(f"  {service.name}:")
        lines.append(f"    build: ./services/{service.name}")
        if service.ports:
            lines.append("    ports:")
            lines.extend(f'      - "{port}"' for port in service.ports)
        if service.env:
            lines.append("    environment:")
            lines.extend(
                f'      {key}: "{service.env[key]}"' for key in sorted(service.env)
            )
        if service.depends_on:
            lines.append("    depends_on:")
            lines.extend(f"      - {name}" for name in service.depends_on)
    return "\n".join(lines) + "\n"


def _readme(spec: ProductSpec) -> str:
    lines = [
        f"# {spec.product}",
        "",
        "Продукт собран из независимых сервисов-пакетов агентской мастерской (FR-14).",
        "",
        "## Запуск",
        "```bash",
        "docker compose up --build",
        "```",
        "",
        "## Сервисы",
        "",
        "| Сервис | Пакет-источник | Порты |",
        "|---|---|---|",
    ]
    for service in spec.services:
        ports = ", ".join(service.ports) if service.ports else "—"
        lines.append(f"| {service.name} | `{service.package}` | {ports} |")
    lines += [
        "",
        "Детали каждого сервиса — в `services/<имя>/README.md`,",
        "происхождение — в `services/<имя>/CHANGELOG.md` и `report.md`.",
    ]
    return "\n".join(lines) + "\n"
