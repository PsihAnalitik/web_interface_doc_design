"""M-15 decomposer: подмодули-проекты из доменов принятого domains.xml (FR-15, TSK-1501/1502).

Детерминированный разрез без LLM: один уровень вложенности; дочерние пайплайны —
обычные прогоны цеха с переопределением project.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.result import Err, Ok, Result

DECOMPOSE_NO_DOMAINS = "DECOMPOSE_NO_DOMAINS"
DECOMPOSE_TARGET_EXISTS = "DECOMPOSE_TARGET_EXISTS"
DECOMPOSE_IO_ERROR = "DECOMPOSE_IO_ERROR"

_DOMAIN_RE = re.compile(
    r'<domain\s+id="(D-[\w-]+)"\s+name="([\w-]+)".*?</domain>', re.DOTALL
)
_COVERS_RE = re.compile(r"<covers>([^<]+)</covers>")
_EDGE_RE = re.compile(
    r'<edge\s+from="(D-[\w-]+)"\s+to="(D-[\w-]+)"\s+kind="(\w+)"(?:\s+via="(C-[\w-]+)")?'
)
_FR_ID_RE = re.compile(r"\bFR-\d+\b")
_NFR_BLOCK_RE = re.compile(r"<nonfunctional>.*?</nonfunctional>", re.DOTALL)


@dataclass(frozen=True)
class DomainInfo:
    domain_id: str
    name: str
    covers: tuple[str, ...]
    block: str          # исходный XML-блок домена целиком


@dataclass(frozen=True)
class DomainEdge:
    from_domain: str
    to_domain: str
    kind: str
    via: str | None


@dataclass(frozen=True)
class DecomposeReport:
    submodules: tuple[str, ...]
    product_spec_path: str
    uncovered_frs: tuple[str, ...]


def parse_domains(content: str) -> Result[tuple[list[DomainInfo], list[DomainEdge]]]:
    """TSK-1501: домены и рёбра из domains.xml (чистая функция)."""
    domains: list[DomainInfo] = []
    for match in _DOMAIN_RE.finditer(content):
        block = match.group(0)
        covers = tuple(_FR_ID_RE.findall(" ".join(_COVERS_RE.findall(block))))
        domains.append(DomainInfo(
            domain_id=match.group(1), name=match.group(2), covers=covers, block=block,
        ))
    if not domains:
        return Err(DECOMPOSE_NO_DOMAINS, 'нет ни одного <domain id="D-..">')

    edges = [
        DomainEdge(
            from_domain=match.group(1), to_domain=match.group(2),
            kind=match.group(3), via=match.group(4),
        )
        for match in _EDGE_RE.finditer(content)
    ]
    return Ok((domains, edges))


def decompose(store: ArtifactStore, project: str, out_dir: Path) -> Result[DecomposeReport]:
    """TSK-1502: входной материал per домен + черновик product.json."""
    if out_dir.exists() and any(out_dir.iterdir()):
        return Err(DECOMPOSE_TARGET_EXISTS, str(out_dir))

    domains_artifact = _load_latest(store, "domains")
    if isinstance(domains_artifact, Err):
        return domains_artifact
    requirements_artifact = _load_latest(store, "input")
    if isinstance(requirements_artifact, Err):
        return requirements_artifact

    parsed = parse_domains(domains_artifact.value)
    if isinstance(parsed, Err):
        return parsed
    domains, edges = parsed.value

    requirements = requirements_artifact.value
    covered = {fr for domain in domains for fr in domain.covers}
    uncovered = tuple(sorted(set(_FR_ID_RE.findall(requirements)) - covered))

    try:
        submodule_names: list[str] = []
        for domain in domains:
            submodule_dir = out_dir / domain.name
            submodule_dir.mkdir(parents=True)
            (submodule_dir / "input.xml").write_text(
                _submodule_input(project, domain, edges, domains, requirements),
                encoding="utf-8",
            )
            submodule_names.append(domain.name)

        product_spec_path = out_dir / "product.json"
        product_spec_path.write_text(
            _product_spec(project, domains, edges), encoding="utf-8"
        )
    except OSError as exc:
        return Err(DECOMPOSE_IO_ERROR, str(exc))

    return Ok(DecomposeReport(
        submodules=tuple(submodule_names),
        product_spec_path=str(product_spec_path),
        uncovered_frs=uncovered,
    ))


def _load_latest(store: ArtifactStore, name: str) -> Result[str]:
    latest = store.latest_version(name)
    if isinstance(latest, Err):
        return latest
    loaded = store.load_artifact(latest.value)
    if isinstance(loaded, Err):
        return loaded
    return Ok(loaded.value.content)


def _submodule_input(
    project: str,
    domain: DomainInfo,
    edges: list[DomainEdge],
    domains: list[DomainInfo],
    requirements: str,
) -> str:
    names_by_id = {item.domain_id: item.name for item in domains}

    fr_blocks: list[str] = []
    for fr_id in domain.covers:
        fr_match = re.search(rf'<fr id="{fr_id}".*?</fr>', requirements, re.DOTALL)
        if fr_match is not None:
            fr_blocks.append(fr_match.group(0))
    nfr_match = _NFR_BLOCK_RE.search(requirements)

    interface_lines: list[str] = []
    for edge in edges:
        via = edge.via if edge.via is not None else "?"
        # семантика ребра from→to: from ЗАВИСИТ от контракта to
        if edge.to_domain == domain.domain_id:
            consumer = names_by_id.get(edge.from_domain, edge.from_domain)
            interface_lines.append(
                f'    <provides via="{via}" kind="{edge.kind}" to="{consumer}"/>'
            )
        elif edge.from_domain == domain.domain_id:
            provider = names_by_id.get(edge.to_domain, edge.to_domain)
            interface_lines.append(
                f'    <consumes via="{via}" kind="{edge.kind}" from="{provider}"/>'
            )

    parts = [
        "<input>",
        f'  <submodule domain="{domain.domain_id}" name="{domain.name}" of_project="{project}"/>',
        "  <requirements_subset>",
        *(f"    {block}" for block in fr_blocks),
        *( [f"    {nfr_match.group(0)}"] if nfr_match is not None else [] ),
        "  </requirements_subset>",
        f"  {domain.block}",
        "  <interfaces>",
        *interface_lines,
        "  </interfaces>",
        "</input>",
    ]
    return "\n".join(parts) + "\n"


def _service_name(domain_name: str) -> str:
    return domain_name.replace("_", "-").lower()


def _product_spec(project: str, domains: list[DomainInfo], edges: list[DomainEdge]) -> str:
    names_by_id = {item.domain_id: item.name for item in domains}
    services = []
    for domain in domains:
        service_name = _service_name(domain.name)
        env: dict[str, str] = {}
        depends_on: list[str] = []
        for edge in edges:
            if edge.from_domain == domain.domain_id:
                provider = _service_name(names_by_id[edge.to_domain])
                env[f"{provider.replace('-', '_').upper()}_URL"] = f"http://{provider}:8000"
                depends_on.append(provider)
        service: dict[str, object] = {
            "name": service_name,
            "package": f"projects/{project}-{service_name}/package",
        }
        if env:
            service["env"] = env
        if depends_on:
            service["depends_on"] = depends_on
        services.append(service)
    return json.dumps({"product": project, "services": services}, ensure_ascii=False, indent=2) + "\n"
