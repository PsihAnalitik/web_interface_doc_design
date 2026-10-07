"""Actual native wiki bundle/tools and stable passport integration, no remote model."""

import json
from pathlib import Path
import shutil

import pytest
from workshop.models import LLMParams

from agent_factory_baseline.catalog import load_catalog
from agent_factory_baseline.inputs import load_sources
from agent_factory_baseline.knowledge import DEFAULT_WIKI, prepare_knowledge
from agent_factory_baseline.passport import ProjectPassport
from agent_factory_baseline.runtime import PACKAGE, ReplayLLM, execute

PARAMS = LLMParams(provider='openai', model='offline-fixture')


def demo_sources():
    return load_sources([('customer', PACKAGE / 'examples/customer.md'),
                         ('team', PACKAGE / 'examples/team.md')])


def test_all_nodes_receive_native_wiki_and_tools_and_passport(tmp_path, monkeypatch):
    monkeypatch.delenv('BGE_M3_SERVICE_URL', raising=False)
    replies = json.loads((PACKAGE / 'examples/replay.json').read_text())

    class Inspect(ReplayLLM):
        def complete(self, prompt, params, tools=()):
            assert '=== wiki:' in prompt
            assert 'Основания, неопределённость и цена ошибок' in prompt
            specs = {t.name: t for t in tools}
            assert set(specs) == {'wiki_search', 'wiki_get'}
            page = specs['wiki_get'].executor({'path': 'fields/integrations.md'})
            assert 'integrations.interfaces' in page
            assert 'не данные проекта' in page
            assert 'страницы' in specs['wiki_get'].executor({'path': 'no-such-page.md'})
            found = specs['wiki_search'].executor({'query': 'интеграций', 'max_chunks': 2})
            assert 'fields/' in found or 'methodology/' in found
            return super().complete(prompt, params, tools)

    output = tmp_path / 'native'
    result = execute(demo_sources(), output, PARAMS, Inspect(replies), mode='replay')
    assert result['status'] == 'completed'
    knowledge = json.loads((output / 'knowledge.json').read_text())
    assert len(knowledge['node_wiki_refs']) == 37
    assert len(knowledge['relations']) == 33
    assert all(v for v in knowledge['node_wiki_refs'].values())
    for f in load_catalog().fields:
        assert all(c.id in (output / 'wiki/fields' / (f.id + '.md')).read_text() for c in f.checks)
        for kind in ('extract', 'verdict'):
            refs = knowledge['node_wiki_refs'][kind + '_' + f.id]
            assert any(r['path'].endswith('/fields/' + f.id + '.md') for r in refs)
    passport = ProjectPassport.model_validate_json((output / 'passport.json').read_text())
    assert len(passport.sections) == 18
    assert all(s.state == 'reviewed' for s in passport.sections)
    assert passport.synthesis is not None
    assert 'Учебный replay' in (output / 'passport.md').read_text()
    assert any(s['role'] == 'case' and s['id'].startswith('K_') for s in passport.sources)


def test_invalid_knowledge_prevents_any_model_call(tmp_path):
    wiki = tmp_path / 'bad-wiki'
    shutil.copytree(DEFAULT_WIKI, wiki)
    (wiki / 'fields/integrations.md').unlink()
    client = ReplayLLM({})
    with pytest.raises(ValueError, match='Missing wiki pages'):
        execute(demo_sources(), tmp_path / 'run', PARAMS, client, wiki_root=wiki)
    assert client.calls == 0


def test_relation_coverage_and_case_paths_are_validated(tmp_path):
    wiki = tmp_path / 'wiki'
    shutil.copytree(DEFAULT_WIKI, wiki)
    path = wiki / 'methodology/relations.json'
    relations = json.loads(path.read_text())
    relations['rules'].pop()
    path.write_text(json.dumps(relations))
    with pytest.raises(ValueError, match='dependencies exactly once'):
        prepare_knowledge(tmp_path / 'snapshot', wiki)
    shutil.copy(DEFAULT_WIKI / 'methodology/relations.json', path)
    (wiki / 'cases/registry.json').write_text(json.dumps({'version':'test', 'cases':[
        {'id':'bad', 'path':'../secret.md','status':'documented','fields':['deployment']}]}))
    with pytest.raises(ValueError, match='Invalid wiki case'):
        prepare_knowledge(tmp_path / 'snapshot', wiki)


def test_plan_freezes_knowledge_and_marks_unprocessed_sections(tmp_path):
    wiki = tmp_path / 'wiki'
    shutil.copytree(DEFAULT_WIKI, wiki)
    output = tmp_path / 'plan'
    execute(demo_sources(), output, PARAMS, mode='plan', wiki_root=wiki)
    old = (output / 'wiki/fields/integrations.md').read_text()
    (wiki / 'fields/integrations.md').write_text('Changed after planning')
    assert (output / 'wiki/fields/integrations.md').read_text() == old
    p = ProjectPassport.model_validate_json((output / 'passport.json').read_text())
    assert p.run_status == 'planned'
    assert all(s.state == 'not_processed' and s.extraction is None for s in p.sections)


def test_synthetic_cases_cannot_become_project_evidence(tmp_path):
    wiki = tmp_path / 'wiki'
    shutil.copytree(DEFAULT_WIKI, wiki)
    registry = wiki / 'cases/registry.json'
    data = json.loads(registry.read_text())
    data['cases'][0]['status'] = 'synthetic'
    registry.write_text(json.dumps(data))
    knowledge = prepare_knowledge(tmp_path / 'snapshot', wiki)
    assert knowledge.case_sources(demo_sources(), knowledge.catalog.fields) == demo_sources()


def test_partial_passport_keeps_extractions_when_verdict_provider_fails(tmp_path):
    from workshop.result import Err
    replies = json.loads((PACKAGE / 'examples/replay.json').read_text())

    class FailVerdicts(ReplayLLM):
        def complete(self, prompt, params, tools=()):
            if '<baseline_node>verdict_' in prompt:
                return Err('TIMEOUT', 'test provider unavailable')
            return super().complete(prompt, params, tools)

    output = tmp_path / 'partial'
    result = execute(demo_sources(), output, PARAMS, FailVerdicts(replies), mode='replay')
    assert result['status'] == 'failed'
    passport = ProjectPassport.model_validate_json((output / 'passport.json').read_text())
    assert all(s.state == 'extracted' and s.extraction is not None and s.verdict is None
               for s in passport.sections)
    assert passport.synthesis is None
    assert 'Итоговый синтез не принят' in (output / 'passport.md').read_text()
