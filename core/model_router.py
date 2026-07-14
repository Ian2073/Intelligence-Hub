from __future__ import annotations

from typing import Protocol

from connectors.cloud_llm import OpenAICompatibleClient
from connectors.ollama import OllamaClient
from core.config import Settings
from core.model_policy import ModelTier


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class ModelRouter:
    def __init__(self, settings: Settings, generator: TextGenerator | None = None) -> None:
        self.settings = settings
        # Injected generator serves as a universal fallback (ignores tier).
        # Used primarily for testing.
        self._generator = generator
        # Per-tier cache for cloud and ollama clients to avoid re-creation.
        self._tier_cache: dict[ModelTier, TextGenerator] = {}

    def generate(self, prompt: str, *, tier: ModelTier = "fast") -> str:
        if self._generator is not None:
            return self._generator.generate(prompt)
        return self._get_generator(tier).generate(prompt)

    def _get_generator(self, tier: ModelTier) -> TextGenerator:
        if self._generator is not None:
            return self._generator

        if tier in self._tier_cache:
            return self._tier_cache[tier]

        gen = self._build_generator(tier)
        self._tier_cache[tier] = gen
        return gen

    def _build_generator(self, tier: ModelTier) -> TextGenerator:
        if self.settings.model_provider == "ollama":
            # Ollama only supports a single model; both tiers share it.
            return OllamaClient(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_model,
            )

        if self.settings.model_provider in {"cloud", "openai-compatible"}:
            if not self.settings.cloud_api_key:
                raise ValueError("HERMES_CLOUD_API_KEY is required when HERMES_MODEL_PROVIDER=cloud.")
            model = self.settings.cloud_pro_model if tier == "pro" else self.settings.cloud_fast_model
            if model.endswith("not-configured"):
                raise ValueError(f"HERMES_{tier.upper()}_MODEL must be configured for cloud model routing.")
            return OpenAICompatibleClient(
                base_url=self.settings.cloud_base_url,
                api_key=self.settings.cloud_api_key,
                model=model,
                timeout=self.settings.cloud_timeout_seconds,
            )

        raise ValueError(
            f"Unsupported HERMES_MODEL_PROVIDER={self.settings.model_provider!r}. "
            "Supported providers: ollama, cloud, openai-compatible."
        )
