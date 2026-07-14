from __future__ import annotations

from pathlib import Path

from core.memory import MemoryStore
from core.repository import Repository, SQLiteRepository


def test_sqlite_repository_wraps_existing_memory_store_contract(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        repo = store.upsert_entity(
            kind="repository",
            canonical_name="owner/repo",
            observed_at="2026-07-10",
            tags=("ai-agent",),
        )
        tech = store.upsert_entity(
            kind="technology",
            canonical_name="agents",
            observed_at="2026-07-10",
        )
        observation = store.record_observation(
            entity_id=repo.id,
            observed_at="2026-07-10",
            source_type="github",
            source_url="https://github.com/owner/repo",
            metric_name="stars",
            previous_value=10,
            current_value=20,
            raw_evidence="GitHub snapshot.",
            confidence="high",
        )
        relationship = store.link_entities(
            source_entity_id=repo.id,
            target_entity_id=tech.id,
            relation_type="tagged_with",
            evidence="GitHub topic.",
            confidence="medium",
        )
        decision = store.record_decision(
            signal_id="github-repo:owner/repo:2026-07-10",
            action="Watch",
            rationale="Momentum is visible.",
            expected_payoff="Keep tracking.",
            risk="Signal may be noisy.",
            revisit_date="2026-07-17",
            confidence="medium",
        )
        brief = store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-10",
            period_end="2026-07-10",
            title="Daily Intelligence - 2026-07-10",
            executive_summary="Repository momentum is visible.",
            top_actions=("Watch: owner/repo",),
            notion_status="dry-run",
            notion_url="local://notion",
            telegram_status="dry-run",
            telegram_detail="not sent",
        )
        run = store.record_run(
            run_date="2026-07-10",
            stage="daily",
            title="Daily Intelligence - 2026-07-10",
            period_start="2026-07-10",
            period_end="2026-07-10",
            status="completed",
            notion_status="dry-run",
            notion_url="local://notion",
            telegram_status="dry-run",
            telegram_detail="not sent",
        )

        repository: Repository = SQLiteRepository.from_memory_store(store)

        assert repository.list_entities(kind="repository") == [repo]
        assert repository.list_entities(tag="ai-agent") == [repo]
        assert repository.list_observations() == [observation]
        assert repository.list_relationships(source_entity_id=repo.id) == [relationship]
        assert repository.list_decisions() == [decision]
        assert repository.list_briefs() == [brief]
        assert repository.list_runs() == [run]
    finally:
        store.close()


def test_sqlite_repository_can_open_memory_store_path(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.sqlite"
    store = MemoryStore(db_path)
    try:
        entity = store.upsert_entity(
            kind="company",
            canonical_name="OpenAI",
            observed_at="2026-07-10",
        )
    finally:
        store.close()

    repository = SQLiteRepository.open(db_path)
    try:
        assert repository.list_entities() == [entity]
    finally:
        repository.close()
