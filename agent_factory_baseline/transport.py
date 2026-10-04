"""Observe provider metadata without replacing the factory's request/error handling."""

import json

from openai import DefaultHttpxClient
from workshop.openai_llm import OpenAILLM


class ObservedOpenAILLM(OpenAILLM):
    def __init__(self, *, http_client=None, **kwargs):
        super().__init__(**kwargs)
        self.last_responses = []
        self._observed_http = http_client if http_client is not None else DefaultHttpxClient()
        self._observed_http.event_hooks["response"].append(self._observe)

    def _ensure_client(self):
        if self._client is None:
            original = super()._ensure_client()
            self._client = original.with_options(http_client=self._observed_http)
            original.close()
        return self._client

    def _observe(self, response):
        response.read()
        metadata = {"http_status": response.status_code}
        self.last_responses.append(metadata)
        try:
            body = response.json()
        except json.JSONDecodeError:
            return  # The factory/SDK still handles the unmodified invalid response.
        if not isinstance(body, dict):
            return
        metadata["returned_model"] = body.get("model")
        usage = body.get("usage")
        metadata["usage"] = ({key: usage[key] for key in (
            "prompt_tokens", "completion_tokens", "total_tokens", "completion_tokens_details",
            "prompt_tokens_details", "cost_rub") if key in usage} if isinstance(usage, dict) else None)
        metadata["choices"] = []
        choices = body.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if isinstance(choice, dict):
                    message = choice.get("message")
                    metadata["choices"].append({
                        "finish_reason": choice.get("finish_reason"),
                        "content_present": bool(message.get("content")) if isinstance(message, dict) else False,
                    })

    def complete(self, prompt, params, tools=()):
        self.last_responses = []
        return super().complete(prompt, params, tools)

    def close(self):
        if self._client is not None:
            self._client.close()
        else:
            self._observed_http.close()
