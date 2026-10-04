import json

import httpx
import pytest
from openai import DefaultHttpxClient
from workshop.models import LLMParams
from workshop.result import Err, Ok

from agent_factory_baseline.runtime import RecordingLLM
from agent_factory_baseline.transport import ObservedOpenAILLM


@pytest.mark.parametrize("content,finish,reasoning", [('{}', 'stop', 0), (None, 'length', 512)])
def test_provider_metadata_survives_empty_content(tmp_path, content, finish, reasoning):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "reasoning": "private chain"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 512, "total_tokens": 522,
                      "completion_tokens_details": {"reasoning_tokens": reasoning},
                      "cost_rub": 1, "balance": 123},
        })

    http = httpx.Client(transport=httpx.MockTransport(respond))
    client = ObservedOpenAILLM(http_client=http, api_key="test-key", base_url="https://test.invalid/v1")
    recorded = RecordingLLM(client, tmp_path / "calls.jsonl")
    params = LLMParams(provider="openai", model="test-model", reasoning_effort="none", max_tokens=512)
    try:
        result = recorded.complete("test", params)
        assert isinstance(result, Ok if content else Err)
        assert requests[0]["reasoning_effort"] == "none"
        assert requests[0]["max_completion_tokens"] == 512
        row = json.loads((tmp_path / "calls.jsonl").read_text())
        meta = row["provider_responses"][0]
        assert meta["usage"]["completion_tokens_details"]["reasoning_tokens"] == reasoning
        assert meta["choices"][0]["finish_reason"] == finish
        assert "balance" not in meta["usage"]
        assert "private chain" not in json.dumps(row)
        assert "test-key" not in json.dumps(row)
        recorded.complete("second", params)
        assert len(client.last_responses) == 1
    finally:
        client.close()
    assert http.is_closed


def test_default_transport_preserves_sdk_redirects(monkeypatch):
    paths = []

    def respond(request):
        paths.append(request.url.path)
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(307, headers={"location": "/v1/redirected"})
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "ok"}}],
        })

    monkeypatch.setattr("agent_factory_baseline.transport.DefaultHttpxClient",
                        lambda: DefaultHttpxClient(transport=httpx.MockTransport(respond)))
    client = ObservedOpenAILLM(api_key="test-key", base_url="https://test.invalid/v1")
    try:
        result = client.complete("test", LLMParams(provider="openai", model="test-model"))
        assert isinstance(result, Ok)
        assert result.value.text == "ok"
        assert paths == ["/v1/chat/completions", "/v1/redirected"]
        assert [r["http_status"] for r in client.last_responses] == [307, 200]
    finally:
        client.close()
