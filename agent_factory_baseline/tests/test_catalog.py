"""Markdown is the catalog source; snapshots, gates and UI share its meaning."""

from dataclasses import asdict
import json
import shutil

import pytest
import yaml
from workshop.models import LLMParams

from agent_factory_baseline.catalog import DEFAULT_WIKI, load_catalog
from agent_factory_baseline.inputs import load_sources
from agent_factory_baseline.knowledge import prepare_knowledge
from agent_factory_baseline.runtime import ReplayLLM, build_graph, execute

PARAMS = LLMParams(provider="openai", model="test-fixture")


@pytest.fixture
def wiki(tmp_path):
    root = tmp_path / "wiki"
    shutil.copytree(DEFAULT_WIKI, root)
    return root


def edit_metadata(path, edit):
    _, frontmatter, body = path.read_text().split("---", 2)
    data = yaml.safe_load(frontmatter)
    edit(data)
    path.write_text("---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False) + "---" + body)


def document(tmp_path):
    path = tmp_path / "customer.md"
    path.write_text("# Project\nThe user reads an answer.\n")
    return load_sources([("customer", path)])


@pytest.mark.parametrize("fault", [
    "missing_page", "duplicate_field", "wrong_id", "unknown_dependency",
    "duplicate_dependency", "duplicate_check", "foreign_check", "empty_rule",
    "extra_key", "duplicate_key", "unsafe_yaml", "unclosed_frontmatter", "unlisted_page",
])
def test_invalid_markdown_catalog_stops_before_model(wiki, tmp_path, fault):
    page = wiki / "fields/users.md"
    if fault == "missing_page":
        page.unlink()
    elif fault == "duplicate_field":
        edit_metadata(wiki / "index.md", lambda d: d["fields"].append(d["fields"][0]))
    elif fault == "wrong_id":
        edit_metadata(page, lambda d: d.update(id="other"))
    elif fault == "unknown_dependency":
        edit_metadata(page, lambda d: d.update(depends_on=["absent"]))
    elif fault == "duplicate_dependency":
        edit_metadata(page, lambda d: d.update(depends_on=["scenarios", "scenarios"]))
    elif fault == "duplicate_check":
        edit_metadata(page, lambda d: d["checks"].append(d["checks"][0]))
    elif fault == "foreign_check":
        edit_metadata(page, lambda d: d["checks"][0].update(id="scenarios.flow"))
    elif fault == "empty_rule":
        edit_metadata(page, lambda d: d["checks"][0].update(evaluate=" "))
    elif fault == "extra_key":
        edit_metadata(page, lambda d: d["checks"][0].update(evaluatte="typo"))
    elif fault == "duplicate_key":
        page.write_text(page.read_text().replace("id: users\n", "id: users\nid: users\n", 1))
    elif fault == "unsafe_yaml":
        page.write_text("---\n!!python/object/apply:os.system ['false']\n---\n# Invalid\n")
    elif fault == "unclosed_frontmatter":
        page.write_text("---\nid: users\n")
    elif fault == "unlisted_page":
        shutil.copy(page, wiki / "fields/unlisted.md")
    client = ReplayLLM({})
    with pytest.raises(ValueError):
        execute(document(tmp_path), tmp_path / "run", PARAMS, client, wiki_root=wiki)
    assert client.calls == 0


def test_custom_wiki_drives_graph_gate_and_passport(wiki, tmp_path):
    edit_metadata(wiki / "index.md", lambda d: d.update(catalog_version="test.v2"))
    def change(data):
        data["title"] = "Участники тестового проекта"
        data["checks"][0].update(id="users.participants", extract="Найти участников теста.",
                                 evaluate="Проверить участников теста.")
    edit_metadata(wiki / "fields/users.md", change)
    replies = json.loads((DEFAULT_WIKI.parent / "examples/replay.json").read_text())
    # A real check ID change must be accepted by the graph's gate, not only its prompt.
    replies = json.loads(json.dumps(replies).replace("users.roles", "users.participants"))
    output = tmp_path / "run"
    sources = load_sources([("customer", DEFAULT_WIKI.parent / "examples/customer.md"),
                            ("team", DEFAULT_WIKI.parent / "examples/team.md")])
    result = execute(sources, output, PARAMS, ReplayLLM(replies),
                     mode="replay", wiki_root=wiki)
    assert result["status"] == "completed"
    assert result["catalog_version"] == "test.v2"
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["catalog_version"] == "test.v2"
    passport = json.loads((output / "passport.json").read_text())
    section = next(s for s in passport["sections"] if s["id"] == "users")
    assert section["title"] == "Участники тестового проекта"
    assert section["checklist"][0] == {"id": "users.participants", "extract": "Найти участников теста.",
                                        "evaluate": "Проверить участников теста."}
    prompt = (output / "config/extract_users.md").read_text()
    assert "users.participants" in prompt and "Найти участников теста." in prompt
    assert "test.v2" in prompt
    for changed in (wiki / "index.md", wiki / "fields/users.md"):
        assert (output / "wiki" / changed.relative_to(wiki)).read_bytes() == changed.read_bytes()


def test_new_workshop_is_added_without_python_catalog_edit(wiki, tmp_path):
    edit_metadata(wiki / "index.md", lambda d: d["fields"].append("additional"))
    page = wiki / "fields/additional.md"
    shutil.copy(wiki / "fields/users.md", page)
    def add(data):
        data.update(id="additional", title="Дополнительный цех", depends_on=[])
        data["checks"] = [{"id": "additional.check", "extract": "Найти основание.",
                           "evaluate": "Проверить основание."}]
    edit_metadata(page, add)
    output = tmp_path / "run"
    execute(document(tmp_path), output, PARAMS, mode="plan", wiki_root=wiki)
    graph = json.loads((output / "config/graph.json").read_text())
    assert len(graph["nodes"]) == 39
    assert {"extract_additional", "verdict_additional"} <= {n["id"] for n in graph["nodes"]}
    passport = json.loads((output / "passport.json").read_text())
    assert passport["sections"][-1]["id"] == "additional"


def test_dependencies_are_loaded_from_markdown(wiki, tmp_path):
    edit_metadata(wiki / "fields/current_process.md", lambda d: d.update(depends_on=[]))
    path = wiki / "methodology/relations.json"
    data = json.loads(path.read_text())
    data["rules"] = [r for r in data["rules"] if (r["source"], r["target"]) != ("users", "current_process")]
    path.write_text(json.dumps(data))
    knowledge = prepare_knowledge(tmp_path / "snapshot", wiki)
    field = next(f for f in knowledge.catalog.fields if f.id == "current_process")
    assert field.depends_on == ()
    assert len(knowledge.relations.rules) == 32


def test_frozen_catalog_is_used_after_original_wiki_changes(wiki, tmp_path):
    output = tmp_path / "snapshot"
    knowledge = prepare_knowledge(output, wiki)
    frozen = knowledge.catalog
    edit_metadata(wiki / "fields/users.md", lambda d: d.update(title="Changed later"))
    assert load_catalog(wiki) != frozen
    assert load_catalog(output / "wiki") == frozen
    build_graph(output, document(tmp_path), PARAMS, knowledge=knowledge)
    assert "Changed later" not in (output / "config/extract_users.md").read_text()


def test_catalog_metadata_does_not_depend_on_markdown_body(wiki):
    before = load_catalog(wiki)
    page = wiki / "fields/users.md"
    page.write_text(page.read_text() + "\nОбновлённое пояснение процедуры.\n")
    assert [asdict(f) for f in load_catalog(wiki).fields] == [asdict(f) for f in before.fields]
