from __future__ import annotations

from pathlib import Path

from core.memory import MemoryStore
from core.orchestrator import run_hermes_orchestration
from core.watchlist import GitHubWatchItem, PaperWatchItem


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_hermes_orchestration_runs_selected_stages_in_order(tmp_path: Path) -> None:
    fixture_root = PROJECT_ROOT / "data" / "fixtures"
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_hermes_orchestration(
            store=store,
            run_date="2026-07-10",
            github_watchlist=[
                GitHubWatchItem(
                    owner="All-Hands-AI",
                    name="OpenHands",
                    fixture="github/All-Hands-AI_OpenHands.json",
                )
            ],
            paper_watchlist=[
                PaperWatchItem(
                    title="Agentic Retrieval for Code Editing",
                    fixture="papers/agentic_retrieval_for_code_editing.json",
                    query="all:agentic",
                    max_results=3,
                )
            ],
            fixture_root=fixture_root,
            notion_url="local://notion/orchestration-dry-run",
            run_weekly=True,
            run_monthly=True,
            run_dashboard=True,
        )

        assert result.daily.run.title == "Intelligence Hub Daily Brief - 2026-07-10"
        assert result.weekly is not None
        assert result.monthly is not None
        assert result.dashboard is not None
        assert result.radar is not None
        assert store.list_briefs(brief_type="daily")
        assert store.list_briefs(brief_type="weekly")
        assert store.list_briefs(brief_type="monthly")
        assert store.list_briefs(brief_type="radar")
    finally:
        store.close()


def test_run_hermes_orchestration_can_skip_dashboard(tmp_path: Path) -> None:
    fixture_root = PROJECT_ROOT / "data" / "fixtures"
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_hermes_orchestration(
            store=store,
            run_date="2026-07-10",
            github_watchlist=[
                GitHubWatchItem(
                    owner="All-Hands-AI",
                    name="OpenHands",
                    fixture="github/All-Hands-AI_OpenHands.json",
                )
            ],
            paper_watchlist=[],
            fixture_root=fixture_root,
            notion_url="local://notion/orchestration-dry-run",
            run_dashboard=False,
            run_radar=False,
        )

        assert result.weekly is None
        assert result.monthly is None
        assert result.dashboard is None
        assert result.radar is None
    finally:
        store.close()
