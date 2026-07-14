from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from connectors.notion import NotionClient
from connectors.obsidian import ObsidianClient
from connectors.telegram import TelegramClient
from core.agent_runtime import AgentRegistry, build_default_registry
from core.config import Settings, load_settings
from core.daily_pipeline import DailyPipelineResult, run_daily_pipeline
from core.memory import MemoryStore
from core.memory_engine import MemoryEngine, MemoryStats
from core.model_router import ModelRouter
from core.repository import SQLiteRepository
from core.synthesis_policy import SynthesisPolicy
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


@dataclass
class PlatformRuntime:
    settings: Settings
    store: MemoryStore
    memory_engine: MemoryEngine
    repository: SQLiteRepository
    synthesis_policy: SynthesisPolicy
    agent_registry: AgentRegistry

    @classmethod
    def create(cls, project_root: Path) -> "PlatformRuntime":
        settings = load_settings(project_root)
        store = MemoryStore(settings.memory_db)
        memory_engine = MemoryEngine(store)
        repository = SQLiteRepository.from_memory_store(store)
        synthesis_policy = SynthesisPolicy.from_env()
        registry = build_default_registry(daily_runner=run_daily_pipeline)
        return cls(
            settings=settings,
            store=store,
            memory_engine=memory_engine,
            repository=repository,
            synthesis_policy=synthesis_policy,
            agent_registry=registry,
        )

    def close(self) -> None:
        self.store.close()

    def model_router(self) -> ModelRouter | None:
        if self.synthesis_policy.mode == "off":
            return None
        if self.settings.model_provider in {"cloud", "openai-compatible"}:
            if not self.settings.cloud_api_key:
                return None
            if self.settings.cloud_fast_model.endswith("not-configured"):
                return None
            if self.settings.cloud_pro_model.endswith("not-configured"):
                return None
        return ModelRouter(self.settings)

    def notion_client(self, enabled: bool) -> NotionClient | None:
        if not enabled or not self.settings.notion_token:
            return None
        return NotionClient(token=self.settings.notion_token, parent_page_id=self.settings.notion_parent_page_id or "")

    def obsidian_client(self, enabled: bool) -> ObsidianClient | None:
        if not enabled or not self.settings.obsidian_enabled:
            return None
        return ObsidianClient(vault_path=self.settings.obsidian_vault_path or "")

    def telegram_client(self, enabled: bool) -> TelegramClient | None:
        if not enabled or not self.settings.telegram_enabled:
            return None
        return TelegramClient(
            bot_token=self.settings.telegram_bot_token or "",
            chat_id=self.settings.telegram_chat_id or "",
        )

    def memory_status(self) -> MemoryStats:
        return self.memory_engine.stats()

    def run_fixture_daily(
        self,
        *,
        run_date: str,
        output_path: str | Path,
        notion_url: str = "local://notion/demo",
    ) -> DailyPipelineResult:
        resolved_output = Path(output_path)
        if not resolved_output.is_absolute():
            resolved_output = self.settings.project_root / resolved_output
        return self.agent_registry.get("ai_intelligence").run(
            store=self.store,
            watchlist=load_github_watchlist(self.settings.github_watchlist_file),
            paper_watchlist=load_paper_watchlist(self.settings.paper_watchlist_file),
            domain_watchlist=load_domain_watchlist(self.settings.domain_watchlist_file),
            run_date=run_date,
            revisit_date=(date.fromisoformat(run_date) + timedelta(days=7)).isoformat(),
            notion_url=notion_url,
            fixture_root=self.settings.fixture_root,
            obsidian_client=ObsidianClient(resolved_output),
            publish_obsidian=True,
        )
