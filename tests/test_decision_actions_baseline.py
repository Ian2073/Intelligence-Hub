from __future__ import annotations

import json
from pathlib import Path

from core.daily_pipeline import run_daily_pipeline
from core.memory import MemoryStore
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_fixture_daily_decision_actions_match_golden_baseline(tmp_path: Path) -> None:
    expected = tuple(
        json.loads((PROJECT_ROOT / "tests" / "fixtures" / "decision_actions_baseline.json").read_text(encoding="utf-8"))
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=load_github_watchlist(PROJECT_ROOT / "data" / "watchlists" / "github_repos.json"),
            paper_watchlist=load_paper_watchlist(PROJECT_ROOT / "data" / "watchlists" / "papers.json"),
            domain_watchlist=load_domain_watchlist(PROJECT_ROOT / "data" / "watchlists" / "domain_signals.json"),
            run_date="2026-07-10",
            revisit_date="2026-07-17",
            notion_url="local://notion/baseline",
            fixture_root=PROJECT_ROOT / "data" / "fixtures",
        )
    finally:
        store.close()

    assert result.run.notification.decisions == expected
