from __future__ import annotations

import httpx

from connectors.cloud_llm import OpenAICompatibleClient


def test_openai_compatible_client_posts_chat_completion_payload(monkeypatch) -> None:
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "cloud answer"}}]}

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return FakeResponse()

    monkeypatch.setattr("connectors.cloud_llm.httpx.post", fake_post)

    client = OpenAICompatibleClient(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="fast-model",
        timeout=12,
    )

    assert client.generate("Hello") == "cloud answer"
    assert calls[0][0] == "https://api.example.com/v1/chat/completions"
    assert calls[0][1]["Authorization"] == "Bearer secret"
    assert calls[0][2]["model"] == "fast-model"
    assert calls[0][2]["messages"] == [{"role": "user", "content": "Hello"}]
    assert calls[0][3] == 12


def test_openai_compatible_client_retries_transient_status(monkeypatch) -> None:
    calls = []
    request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")

    class FakeResponse:
        def __init__(self, status_code: int, body: dict | None = None) -> None:
            self.status_code = status_code
            self.text = "rate limited" if status_code != 200 else "ok"
            self._body = body or {}
            self.headers = {}

        def raise_for_status(self):
            if self.status_code >= 400:
                response = httpx.Response(self.status_code, request=request, text=self.text)
                raise httpx.HTTPStatusError("transient failure", request=request, response=response)

        def json(self):
            return self._body

    responses = [
        FakeResponse(429),
        FakeResponse(200, {"choices": [{"message": {"content": "cloud answer after retry"}}]}),
    ]

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return responses[len(calls) - 1]

    monkeypatch.setattr("connectors.cloud_llm.httpx.post", fake_post)
    monkeypatch.setattr("connectors.retry.time.sleep", lambda delay: None)

    client = OpenAICompatibleClient(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="pro-model",
    )

    assert client.generate("Hello") == "cloud answer after retry"
    assert len(calls) == 2
