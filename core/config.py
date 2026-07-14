from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path
    model_provider: str
    ollama_base_url: str
    ollama_model: str
    cloud_base_url: str
    cloud_api_key: str | None
    cloud_fast_model: str
    cloud_pro_model: str
    cloud_timeout_seconds: float
    research_topic: str
    source_file: Path
    memory_db: Path
    github_watchlist_file: Path
    paper_watchlist_file: Path
    domain_watchlist_file: Path
    fixture_root: Path
    github_token: str | None
    notion_token: str | None
    notion_parent_page_id: str | None
    notion_daily_briefs_database_id: str | None
    notion_papers_database_id: str | None
    notion_github_repos_database_id: str | None
    notion_ecosystem_database_id: str | None
    notion_decisions_database_id: str | None
    notion_radar_snapshots_database_id: str | None
    notion_radar_entities_database_id: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    interest_profile: str = ""
    relevance_threshold: int = 7
    obsidian_enabled_val: str | None = None
    obsidian_vault_path: Path | None = None
    synthesis_mode: str = "hybrid"
    pro_call_limit: int = 8

    @property
    def notion_enabled(self) -> bool:
        return bool(self.notion_token and self.notion_parent_page_id)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def obsidian_enabled(self) -> bool:
        return bool(self.obsidian_enabled_val and self.obsidian_vault_path)


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    if normalized.lower() in {"0", "false", "none", "null"}:
        return None
    return normalized


def _first_env(*names: str, default: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def _first_optional_env(*names: str) -> str | None:
    for name in names:
        value = _optional_env(name)
        if value:
            return value
    return None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def load_settings(project_root: Path) -> Settings:
    root = project_root.resolve()
    load_dotenv(root / ".env")

    obsidian_vault_path_raw = _first_optional_env("INTELLIGENCE_HUB_OBSIDIAN_VAULT_PATH", "OBSIDIAN_VAULT_PATH")
    obsidian_vault_path = None
    if obsidian_vault_path_raw:
        path = Path(obsidian_vault_path_raw)
        if not path.is_absolute():
            obsidian_vault_path = (root / path).resolve()
        else:
            obsidian_vault_path = path.resolve()

    return Settings(
        project_root=root,
        model_provider=_first_env("INTELLIGENCE_HUB_MODEL_PROVIDER", "HERMES_MODEL_PROVIDER", default="cloud").lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b").strip(),
        cloud_base_url=_first_env("INTELLIGENCE_HUB_CLOUD_BASE_URL", "HERMES_CLOUD_BASE_URL", "DEEPSEEK_BASE_URL", default="https://api.openai.com/v1").rstrip("/"),
        cloud_api_key=_first_optional_env("INTELLIGENCE_HUB_CLOUD_API_KEY", "HERMES_CLOUD_API_KEY", "DEEPSEEK_API_KEY"),
        cloud_fast_model=_first_env("INTELLIGENCE_HUB_FAST_MODEL", "HERMES_FAST_MODEL", "API_FAST_MODEL", "API_MODEL_NAME", default="fast-model-not-configured"),
        cloud_pro_model=_first_env("INTELLIGENCE_HUB_PRO_MODEL", "HERMES_PRO_MODEL", "API_PRO_MODEL", "API_MODEL_NAME", default="pro-model-not-configured"),
        cloud_timeout_seconds=float(_first_env("INTELLIGENCE_HUB_CLOUD_TIMEOUT_SECONDS", "HERMES_CLOUD_TIMEOUT_SECONDS", default="60")),
        research_topic=_first_env("INTELLIGENCE_HUB_RESEARCH_TOPIC", "HERMES_RESEARCH_TOPIC", default="local-first AI engineering workflows"),
        source_file=(root / _first_env("INTELLIGENCE_HUB_SOURCE_FILE", "HERMES_SOURCE_FILE", default="data/sources/ai_research_items.json")),
        memory_db=(root / _first_env("INTELLIGENCE_HUB_DB", "HERMES_MEMORY_DB", default="data/hermes_memory.sqlite")),
        github_watchlist_file=(
            root / _first_env("INTELLIGENCE_HUB_GITHUB_WATCHLIST_FILE", "HERMES_GITHUB_WATCHLIST_FILE", default="data/watchlists/github_repos.json")
        ),
        paper_watchlist_file=(root / _first_env("INTELLIGENCE_HUB_PAPER_WATCHLIST_FILE", "HERMES_PAPER_WATCHLIST_FILE", default="data/watchlists/papers.json")),
        domain_watchlist_file=(
            root / _first_env("INTELLIGENCE_HUB_DOMAIN_WATCHLIST_FILE", "HERMES_DOMAIN_WATCHLIST_FILE", default="data/watchlists/domain_signals.json")
        ),
        fixture_root=(root / _first_env("INTELLIGENCE_HUB_FIXTURE_ROOT", "HERMES_FIXTURE_ROOT", default="data/fixtures")),
        github_token=_first_optional_env("GITHUB_TOKEN", "GH_TOKEN"),
        notion_token=_optional_env("NOTION_TOKEN"),
        notion_parent_page_id=_optional_env("NOTION_PARENT_PAGE_ID"),
        notion_daily_briefs_database_id=_optional_env("NOTION_DAILY_BRIEFS_DATABASE_ID"),
        notion_papers_database_id=_optional_env("NOTION_PAPERS_DATABASE_ID"),
        notion_github_repos_database_id=_optional_env("NOTION_GITHUB_REPOS_DATABASE_ID"),
        notion_ecosystem_database_id=_optional_env("NOTION_ECOSYSTEM_DATABASE_ID"),
        notion_decisions_database_id=_optional_env("NOTION_DECISIONS_DATABASE_ID"),
        notion_radar_snapshots_database_id=_optional_env("NOTION_RADAR_SNAPSHOTS_DATABASE_ID"),
        notion_radar_entities_database_id=_optional_env("NOTION_RADAR_ENTITIES_DATABASE_ID"),
        telegram_bot_token=_first_optional_env("TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "TG_BOT_TOKEN"),
        telegram_chat_id=_first_optional_env("TELEGRAM_CHAT_ID", "TG_CHAT_ID"),
        interest_profile=_first_env("INTELLIGENCE_HUB_INTEREST_PROFILE", "HERMES_INTEREST_PROFILE", default=""),
        relevance_threshold=int(_first_env("INTELLIGENCE_HUB_RELEVANCE_THRESHOLD", "HERMES_RELEVANCE_THRESHOLD", default="7")),
        obsidian_enabled_val=_first_optional_env("INTELLIGENCE_HUB_OBSIDIAN_ENABLED", "OBSIDIAN_ENABLED"),
        obsidian_vault_path=obsidian_vault_path,
        synthesis_mode=_first_env("INTELLIGENCE_HUB_SYNTHESIS_MODE", "HERMES_SYNTHESIS_MODE", default="hybrid").lower(),
        pro_call_limit=_env_int("INTELLIGENCE_HUB_PRO_CALL_LIMIT", _env_int("HERMES_PRO_CALL_LIMIT", 8)),
    )
