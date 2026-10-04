"""M-02 artifact_store: версионированные артефакты и кросс-ссылки (TSK-0201..0203)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from workshop.models import Artifact, ArtifactRef, CrosslinkReport
from workshop.result import Err, Ok, Result

VERSION_EXISTS = "VERSION_EXISTS"
STORE_IO_ERROR = "STORE_IO_ERROR"
ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
UPSTREAM_UNPARSEABLE = "UPSTREAM_UNPARSEABLE"

# WHY: извлечение id регэкспами, а не XML-парсером — реальные артефакты могут быть
# частично невалидным XML (или HTML, §10.5 постановки); id-схемы при этом стабильны.
_DEFINED_ID_RE = re.compile(r'\bid="([A-Za-z]+-[A-Za-z0-9-]+)"')
_ID_TOKEN_RE = re.compile(r"\b((?:FR|NFR|D|C|OP)-[A-Za-z0-9][A-Za-z0-9-]*)\b")

_VERSION_FILE_RE = re.compile(r"^v(\d+)\.xml$")


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def save_artifact(
        self,
        name: str,
        content: str,
        derived_from: ArtifactRef | None = None,
    ) -> Result[ArtifactRef]:
        artifact_dir = self._root / name
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            version = self._next_version(artifact_dir)
            content_path = artifact_dir / f"v{version}.xml"
            # WHY: режим "x" — эксклюзивное создание; гонка или внешнее вмешательство
            # в стор проявляются как VERSION_EXISTS, а не молчаливая перезапись
            with content_path.open("x", encoding="utf-8") as stream:
                stream.write(content)
            self._write_meta(artifact_dir, version, derived_from)
        except FileExistsError:
            return Err(VERSION_EXISTS, f"{name} v{version}")
        except OSError as exc:
            return Err(STORE_IO_ERROR, str(exc))
        return Ok(ArtifactRef(name=name, version=version))

    def list_artifacts(self) -> list[ArtifactRef]:
        """TSK-0205: все артефакты стора (имя, версия), отсортированы; пустой стор → []."""
        refs: list[ArtifactRef] = []
        if not self._root.is_dir():
            return refs
        for child in sorted(self._root.iterdir()):
            if not child.is_dir():
                continue
            for entry in sorted(child.iterdir()):
                match = _VERSION_FILE_RE.match(entry.name)
                if match is not None:
                    refs.append(ArtifactRef(name=child.name, version=int(match.group(1))))
        return refs

    def latest_version(self, name: str) -> Result[ArtifactRef]:
        """TSK-0204: последняя версия артефакта по имени (для resume, TSK-0905)."""
        artifact_dir = self._root / name
        if not artifact_dir.is_dir():
            return Err(ARTIFACT_NOT_FOUND, name)
        versions = [
            int(match.group(1))
            for entry in artifact_dir.iterdir()
            if (match := _VERSION_FILE_RE.match(entry.name)) is not None
        ]
        if not versions:
            return Err(ARTIFACT_NOT_FOUND, name)
        return Ok(ArtifactRef(name=name, version=max(versions)))

    def load_artifact(self, ref: ArtifactRef) -> Result[Artifact]:
        content_path = self._root / ref.name / f"v{ref.version}.xml"
        if not content_path.is_file():
            return Err(ARTIFACT_NOT_FOUND, f"{ref.name} v{ref.version}")
        try:
            content = content_path.read_text(encoding="utf-8")
            derived_from = self._read_meta(content_path.parent, ref.version)
        except OSError as exc:
            return Err(STORE_IO_ERROR, str(exc))
        return Ok(Artifact(ref=ref, content=content, derived_from=derived_from))

    def _next_version(self, artifact_dir: Path) -> int:
        versions = [
            int(match.group(1))
            for entry in artifact_dir.iterdir()
            if (match := _VERSION_FILE_RE.match(entry.name)) is not None
        ]
        if versions:
            return max(versions) + 1
        return 1

    def _write_meta(
        self, artifact_dir: Path, version: int, derived_from: ArtifactRef | None
    ) -> None:
        if derived_from is None:
            meta = {"derived_from": None}
        else:
            meta = {
                "derived_from": {
                    "name": derived_from.name,
                    "version": derived_from.version,
                }
            }
        meta_path = artifact_dir / f"v{version}.meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def _read_meta(self, artifact_dir: Path, version: int) -> ArtifactRef | None:
        meta_path = artifact_dir / f"v{version}.meta.json"
        if not meta_path.is_file():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        upstream = meta.get("derived_from")
        if upstream is None:
            return None
        return ArtifactRef(name=upstream["name"], version=upstream["version"])


def validate_crosslinks(artifact: Artifact, upstream: Artifact) -> Result[CrosslinkReport]:
    upstream_defined = set(_DEFINED_ID_RE.findall(upstream.content))
    if not upstream_defined:
        return Err(UPSTREAM_UNPARSEABLE, 'в старшем артефакте нет ни одного id="..."')

    artifact_defined = set(_DEFINED_ID_RE.findall(artifact.content))
    referenced = set(_ID_TOKEN_RE.findall(artifact.content)) - artifact_defined

    # WHY: битой считается только ссылка на класс id, которым владеет старший документ;
    # ссылки «вперёд» (via="C-.." из domains до появления contracts) — не дефект
    upstream_prefixes = {identifier.split("-", 1)[0] for identifier in upstream_defined}
    broken = sorted(
        reference
        for reference in referenced
        if reference.split("-", 1)[0] in upstream_prefixes
        and reference not in upstream_defined
    )
    uncovered = sorted(
        identifier
        for identifier in upstream_defined
        if identifier not in artifact.content
    )
    return Ok(CrosslinkReport(broken_links=tuple(broken), uncovered_ids=tuple(uncovered)))
