"""Text-only sources and lossless JSON transport for the factory templates."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Literal

SourceRole = Literal["customer", "team", "rules", "case"]


@dataclass(frozen=True)
class Source:
    id: str
    role: SourceRole
    path: str
    text: str
    sha256: str

    def metadata(self) -> dict:
        return {"id": self.id, "role": self.role, "path": self.path, "sha256": self.sha256}

    def payload(self) -> dict:
        return {**self.metadata(), "lines": [
            {"number": n, "text": line}
            for n, line in enumerate(self.text.splitlines(), 1)
        ]}


def load_sources(entries: list[tuple[SourceRole, Path]]) -> dict[str, Source]:
    """Read UTF-8 Markdown; never fetch links or silently ignore visual content."""
    sources = {}
    paths = set()
    for index, (role, path) in enumerate(entries, 1):
        path = path.resolve(strict=True)
        if role not in {"customer", "team", "rules", "case"}:
            raise ValueError(f"Unknown source role: {role}")
        if path.suffix.lower() != ".md":
            raise ValueError(f"Only .md documents are supported: {path.name}")
        if path in paths:
            raise ValueError(f"Source supplied more than once: {path}")
        text = path.read_text(encoding="utf-8-sig")
        if not text.strip():
            raise ValueError(f"Empty document: {path.name}")
        if re.search(r"!\[|<(?:img|picture|svg|video|audio|iframe|object|embed)\b|data:image/", text, re.I):
            raise ValueError(f"Visual/embedded content in {path.name}; prepare text-only Markdown first")
        source_id = f"S{index}"
        sources[source_id] = Source(source_id, role, str(path), text, sha256(text.encode()).hexdigest())
        paths.add(path)
    if not any(source.role == "customer" for source in sources.values()):
        raise ValueError("At least one customer .md document is required")
    return sources


def wire_json(value: object) -> str:
    """Escape only JSON strings, preserving quotes through factory interpolation/fences."""
    raw = json.dumps(value, ensure_ascii=False, indent=2)
    escapes = {"`": r"\u0060", "{": r"\u007b", "}": r"\u007d",
               "<": r"\u003c", ">": r"\u003e"}
    return re.sub(r'"(?:[^"\\]|\\.)*"',
                  lambda match: "".join(escapes.get(char, char) for char in match[0]), raw)
