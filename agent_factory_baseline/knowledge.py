"""Snapshot domain knowledge and bind native workflow_ai wiki capabilities."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import Field
from workshop.result import Err
from workshop.wiki_loader import build_bundle

from .catalog import FIELDS
from .inputs import Source
from .models import Payload, Text

DEFAULT_WIKI = Path(__file__).resolve().parent / 'wiki'


class RelationRule(Payload):
    id: Text
    source: Text
    target: Text
    when: Text
    compare: Text
    conflict: Text
    missing: Text
    impact: Text
    not_applicable: Text


class RelationCatalog(Payload):
    version: Text
    rules: list[RelationRule]


class CaseEntry(Payload):
    id: Text
    path: Text
    status: Literal['documented', 'draft', 'synthetic']
    fields: list[Text] = Field(min_length=1)


class CaseRegistry(Payload):
    version: Text
    cases: list[CaseEntry]


@dataclass
class Knowledge:
    root: Path
    pages: dict[str, str]
    relations: RelationCatalog
    cases: CaseRegistry

    def refs(self, kind: str, field_id: str | None = None) -> list[dict]:
        paths = ['methodology/evidence.md', 'domains/llm-agents.md']
        if field_id and f'fields/{field_id}.md' in self.pages:
            paths.append(f'fields/{field_id}.md')
        if kind == 'synthesis':
            paths += ['methodology/relations.md', 'methodology/relations-catalog.md']
        if kind != 'extract':
            paths.append('cases/index.md')
        return [{'path': str(self.root / path), 'version': 'sha256:' + self.pages[path]}
                for path in paths]

    def case_sources(self, sources: dict[str, Source], fields) -> dict[str, Source]:
        result = dict(sources)
        selected = {f.id for f in fields}
        for case in self.cases.cases:
            if case.status != 'documented' or not selected.intersection(case.fields):
                continue
            identifier = 'K_' + case.id
            if identifier in result:
                raise ValueError(f'Duplicate wiki case source: {identifier}')
            path = self.root / case.path
            text = path.read_text(encoding='utf-8')
            result[identifier] = Source(identifier, 'case', str(path), text,
                                        sha256(text.encode()).hexdigest())
        return result


def prepare_knowledge(output: Path, root: Path, fields=FIELDS) -> Knowledge:
    """Validate, then freeze knowledge; use native bundle loading, not a second retriever."""
    root = root.resolve(strict=True)
    pages = {}
    contents = {}
    for path in sorted(root.rglob('*')):
        if path.suffix not in {'.md', '.json'} or not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Wiki page escapes root: {path}')
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8')
        if not text.strip() or '{{' in text:
            raise ValueError(f'Empty wiki page or forbidden template marker: {relative}')
        contents[relative] = text
        if path.suffix == '.md':
            pages[relative] = sha256(text.encode()).hexdigest()
    required = {'index.md', 'methodology/evidence.md', 'methodology/relations.md',
                'domains/llm-agents.md', 'cases/index.md', 'passport.md'}
    known_ids = {f.id for f in FIELDS}
    required |= {f'fields/{f.id}.md' for f in fields if f.id in known_ids}
    missing = required - pages.keys()
    if missing:
        raise ValueError(f'Missing wiki pages: {sorted(missing)}')
    try:
        relations = RelationCatalog.model_validate_json(contents['methodology/relations.json'])
        cases = CaseRegistry.model_validate_json(contents['cases/registry.json'])
    except KeyError as exc:
        raise ValueError(f'Missing wiki registry: {exc.args[0]}') from exc
    expected = {(source, f.id) for f in FIELDS for source in f.depends_on}
    actual = {(r.source, r.target) for r in relations.rules}
    if actual != expected or len(actual) != len(relations.rules):
        raise ValueError('Wiki relation rules must cover catalog dependencies exactly once')
    if len({r.id for r in relations.rules}) != len(relations.rules):
        raise ValueError('Duplicate relation rule IDs')
    if len({c.id for c in cases.cases}) != len(cases.cases):
        raise ValueError('Duplicate wiki case IDs')
    for case in cases.cases:
        if (case.path not in pages or not case.path.startswith('cases/')
                or not set(case.fields) <= known_ids
                or not all(c.isalnum() or c in '_-' for c in case.id)):
            raise ValueError(f'Invalid wiki case registration: {case.id}')
    # Generated views share canonical identifiers and cannot silently drift from the catalog.
    lines = ['# Каталог полей и проверок', '', 'Сгенерировано из catalog.py; редактировать следует каталог.', '']
    for f in fields:
        lines += [f'## {f.id} — {f.title}', '', f'Зависит от: {", ".join(f.depends_on) or "—"}', '']
        for c in f.checks:
            lines += [f'### {c.id}', f'Извлечение: {c.extract}', f'Оценка: {c.evaluate}', '']
    contents['catalog.md'] = '\n'.join(lines)
    lines = ['# Правила связей', '', 'Сгенерировано из methodology/relations.json.', '']
    for rule in relations.rules:
        lines += [f'## {rule.id}: {rule.source} → {rule.target}', '']
        lines += [f'{key}: {value}' for key, value in rule.model_dump().items()
                  if key not in {'id', 'source', 'target'}]
        lines.append('')
    contents['methodology/relations-catalog.md'] = '\n'.join(lines)
    snapshot = output / 'wiki'
    for relative, text in contents.items():
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        if target.suffix == '.md':
            pages[relative] = sha256(text.encode()).hexdigest()
    knowledge = Knowledge(snapshot, pages, relations, cases)
    for kind, field_id in [('extract', f.id) for f in fields] + [('verdict', f.id) for f in fields] + [('synthesis', None)]:
        bundle = build_bundle(Path('.'), [r['path'] for r in knowledge.refs(kind, field_id)])
        if isinstance(bundle, Err):
            raise ValueError(f'{bundle.code}: {bundle.details}')
    return knowledge
