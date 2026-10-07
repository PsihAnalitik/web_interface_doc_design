"""Load passport workshop definitions from their Markdown knowledge pages."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Mapping

from pydantic import Field
import yaml

from .models import Payload, Text

DEFAULT_WIKI = Path(__file__).resolve().parent / 'wiki'
Identifier = Annotated[str, Field(pattern=r'^[a-z][a-z0-9_]*$')]


@dataclass(frozen=True)
class Check:
    id: str
    extract: str
    evaluate: str


@dataclass(frozen=True)
class PassportField:
    id: str
    title: str
    checks: tuple[Check, ...]
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Catalog:
    version: str
    fields: tuple[PassportField, ...]


class _Index(Payload):
    catalog_version: Text
    fields: list[Identifier] = Field(min_length=1)


class _Check(Payload):
    id: Text
    extract: Text
    evaluate: Text


class _Workshop(Payload):
    id: Identifier
    title: Text
    checks: list[_Check] = Field(min_length=1)
    depends_on: list[Identifier]


class _CatalogLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        # Catalog keys are strings; silently overwriting a rule is not allowed.
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in seen:
                raise ValueError(f'Non-string or duplicate catalog key: {key!r}')
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _metadata(text: str, path: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError(f'Missing catalog frontmatter: {path}')
    try:
        end = lines.index('---', 1)
    except ValueError as exc:
        raise ValueError(f'Unclosed catalog frontmatter: {path}') from exc
    try:
        data = yaml.load('\n'.join(lines[1:end]), Loader=_CatalogLoader)
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(f'Invalid catalog frontmatter in {path}: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError(f'Catalog frontmatter must be a mapping: {path}')
    return data


def catalog_from_pages(pages: Mapping[str, str]) -> Catalog:
    """Parse the same page contents that will be frozen into the run snapshot."""
    if 'index.md' not in pages:
        raise ValueError('Missing wiki pages: index.md')
    index = _Index.model_validate(_metadata(pages['index.md'], 'index.md'))
    ids = set(index.fields)
    if len(ids) != len(index.fields):
        raise ValueError('Duplicate catalog field IDs in index.md')
    expected = {f'fields/{identifier}.md' for identifier in index.fields}
    missing = expected - pages.keys()
    if missing:
        raise ValueError(f'Missing wiki pages: {sorted(missing)}')
    unlisted = {p for p in pages if p.startswith('fields/') and p.endswith('.md')} - expected
    if unlisted:
        raise ValueError(f'Unlisted workshop pages: {sorted(unlisted)}')
    fields = []
    for identifier in index.fields:
        path = f'fields/{identifier}.md'
        try:
            field = _Workshop.model_validate(_metadata(pages[path], path))
        except ValueError as exc:
            raise ValueError(f'Invalid workshop {path}: {exc}') from exc
        if field.id != identifier:
            raise ValueError(f'Workshop ID does not match index/path: {path}')
        if len(set(field.depends_on)) != len(field.depends_on) or not set(field.depends_on) <= ids:
            raise ValueError(f'Unknown or duplicate dependencies: {path}')
        check_ids = [check.id for check in field.checks]
        if len(set(check_ids)) != len(check_ids):
            raise ValueError(f'Duplicate check IDs: {path}')
        for check_id in check_ids:
            prefix, separator, name = check_id.partition('.')
            if prefix != identifier or not separator or not name.isascii() or not name.replace('_', '').isalnum():
                raise ValueError(f'Check ID must belong to its workshop: {path}: {check_id}')
        fields.append(PassportField(field.id, field.title,
                      tuple(Check(c.id, c.extract, c.evaluate) for c in field.checks),
                      tuple(field.depends_on)))
    return Catalog(index.catalog_version, tuple(fields))


def load_catalog(root: Path = DEFAULT_WIKI) -> Catalog:
    """Load a catalog on demand; importing this module never reads a wiki."""
    root = root.resolve(strict=True)
    paths = [root / 'index.md', *sorted((root / 'fields').rglob('*.md'))]
    pages = {}
    for path in paths:
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Wiki page escapes root: {path}')
        pages[path.relative_to(root).as_posix()] = path.read_text(encoding='utf-8')
    return catalog_from_pages(pages)
