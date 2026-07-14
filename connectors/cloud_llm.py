from __future__ import annotations

import httpx

from connectors.retry import retry_on_transient


class CloudLlmError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        temperature: float = 0.2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.temperature = temperature

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        def post_completion() -> httpx.Response:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response

        try:
            response = retry_on_transient(
                post_completion,
                operation_name="Cloud LLM API",
                base_delay=2.0,
            )
        except httpx.HTTPStatusError as exc:
            raise CloudLlmError(
                f"Cloud model returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise CloudLlmError(f"Cloud model request failed: {exc}") from exc

        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise CloudLlmError("Cloud model response did not include choices.")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise CloudLlmError("Cloud model choice did not include a message.")
        text = str(message.get("content") or "").strip()
        if not text:
            raise CloudLlmError("Cloud model returned an empty response.")
        return text
