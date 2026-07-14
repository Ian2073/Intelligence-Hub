from __future__ import annotations

from core.config import load_settings


def test_load_settings_defaults_to_cloud_first(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HERMES_MODEL_PROVIDER", raising=False)

    settings = load_settings(tmp_path)

    assert settings.model_provider == "cloud"


def test_load_settings_allows_explicit_ollama_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_MODEL_PROVIDER", "ollama")

    settings = load_settings(tmp_path)

    assert settings.model_provider == "ollama"


def test_load_settings_accepts_legacy_deepseek_cloud_env(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HERMES_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("HERMES_CLOUD_BASE_URL", raising=False)
    monkeypatch.delenv("HERMES_FAST_MODEL", raising=False)
    monkeypatch.delenv("HERMES_PRO_MODEL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.example")
    monkeypatch.setenv("API_MODEL_NAME", "deepseek-pro")

    settings = load_settings(tmp_path)

    assert settings.cloud_api_key == "deepseek-key"
    assert settings.cloud_base_url == "https://api.deepseek.example"
    assert settings.cloud_fast_model == "deepseek-pro"
    assert settings.cloud_pro_model == "deepseek-pro"


def test_load_settings_prefers_hermes_cloud_env_over_legacy_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HERMES_CLOUD_API_KEY", "hermes-key")
    monkeypatch.setenv("HERMES_CLOUD_BASE_URL", "https://api.hermes.example/v1")
    monkeypatch.setenv("HERMES_FAST_MODEL", "fast")
    monkeypatch.setenv("HERMES_PRO_MODEL", "pro")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.example")
    monkeypatch.setenv("API_MODEL_NAME", "deepseek-pro")

    settings = load_settings(tmp_path)

    assert settings.cloud_api_key == "hermes-key"
    assert settings.cloud_base_url == "https://api.hermes.example/v1"
    assert settings.cloud_fast_model == "fast"
    assert settings.cloud_pro_model == "pro"


def test_load_settings_accepts_github_and_telegram_aliases(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("GH_TOKEN", "gh-token")
    monkeypatch.setenv("TG_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TG_CHAT_ID", "tg-chat")

    settings = load_settings(tmp_path)

    assert settings.github_token == "gh-token"
    assert settings.telegram_bot_token == "tg-token"
    assert settings.telegram_chat_id == "tg-chat"


def test_load_settings_prefers_standard_github_and_telegram_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("GH_TOKEN", "gh-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_TOKEN", "legacy-telegram-token")
    monkeypatch.setenv("TG_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "telegram-chat")
    monkeypatch.setenv("TG_CHAT_ID", "tg-chat")

    settings = load_settings(tmp_path)

    assert settings.github_token == "github-token"
    assert settings.telegram_bot_token == "telegram-token"
    assert settings.telegram_chat_id == "telegram-chat"
