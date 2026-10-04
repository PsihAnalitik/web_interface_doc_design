"""Dotenv bootstrapping is shell-independent and never executes shell expressions."""

import os
import pytest

from agent_factory_baseline import __main__ as cli


@pytest.mark.parametrize('override', [False, True])
def test_run_loads_local_dotenv_before_validation_without_network(tmp_path, monkeypatch, override):
    env = tmp_path / '.env'
    env.write_text('OPENAI_API_KEY=test-only-key\nOPENAI_BASE_URL=https://example.invalid/v1\nBASELINE_MODEL=file-model\nUNRELATED_VARIABLE=ignored\n')
    monkeypatch.setattr(cli, 'ENV_FILE', env)
    for key in ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'BASELINE_MODEL', 'UNRELATED_VARIABLE']:
        monkeypatch.delenv(key, raising=False)
    if override:
        monkeypatch.setenv('OPENAI_API_KEY', 'exported-test-key')
        monkeypatch.setenv('BASELINE_MODEL', 'exported-model')
    doc = tmp_path / 'document.md'
    doc.write_text('Test document')

    class Client:
        def __init__(self, **kwargs):
            assert os.environ['OPENAI_API_KEY'] == ('exported-test-key' if override else 'test-only-key')
        def close(self):
            pass

    def execute(sources, output, params, llm, **kwargs):
        assert params.model == ('exported-model' if override else 'file-model')
        assert os.environ['OPENAI_BASE_URL'] == 'https://example.invalid/v1'
        assert 'UNRELATED_VARIABLE' not in os.environ
        return {'status': 'completed', 'mode': 'live'}

    monkeypatch.setattr('agent_factory_baseline.transport.ObservedOpenAILLM', Client)
    monkeypatch.setattr(cli, 'execute', execute)
    assert cli.main(['run', '--document', str(doc), '--output', str(tmp_path / 'run')]) == 0


def test_dotenv_does_not_expand_shell_or_environment(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    marker = tmp_path / 'must-not-exist'
    literal = '${HOME}$(touch ' + str(marker) + ')'
    env.write_text('OPENAI_API_KEY=' + literal + '\n')
    monkeypatch.setattr(cli, 'ENV_FILE', env)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(SystemExit) as result:
        cli.main(['--help'])
    assert result.value.code == 0
    assert os.environ['OPENAI_API_KEY'] == literal
    assert not marker.exists()
