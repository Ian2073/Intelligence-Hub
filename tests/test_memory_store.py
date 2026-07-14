from __future__ import annotations

import pytest

from core.memory import MemoryStore


def test_upsert_entity_reuses_existing_repository_and_updates_memory(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        first = store.upsert_entity(
            kind="repository",
            canonical_name="All-Hands-AI/OpenHands",
            observed_at="2026-07-01",
            aliases=("OpenHands",),
            tags=("agent", "developer-tools"),
            summary="Open-source software engineering agent.",
        )

        second = store.upsert_entity(
            kind="repository",
            canonical_name="openhands",
            observed_at="2026-07-02",
            aliases=("All-Hands-AI/OpenHands",),
            tags=("agent", "coding-agent"),
            summary="",
        )

        assert second.id == first.id
        assert second.first_seen == "2026-07-01"
        assert second.last_seen == "2026-07-02"
        assert "OpenHands" in second.aliases
        assert "All-Hands-AI/OpenHands" in second.aliases
        assert second.summary == "Open-source software engineering agent."
        assert set(second.tags) == {"agent", "developer-tools", "coding-agent"}
    finally:
        store.close()


def test_record_observation_preserves_entity_history_in_time_order(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        entity = store.upsert_entity(
            kind="repository",
            canonical_name="All-Hands-AI/OpenHands",
            observed_at="2026-07-01",
        )

        store.record_observation(
            entity_id=entity.id,
            observed_at="2026-07-02",
            source_type="github",
            source_url="https://github.com/All-Hands-AI/OpenHands",
            metric_name="stars",
            previous_value=24000,
            current_value=25500,
            raw_evidence="GitHub repository metadata snapshot.",
            confidence="high",
        )
        store.record_observation(
            entity_id=entity.id,
            observed_at="2026-07-01",
            source_type="github",
            source_url="https://github.com/All-Hands-AI/OpenHands/releases",
            metric_name="release",
            previous_value="none",
            current_value="v1.0.0",
            raw_evidence="GitHub release list snapshot.",
            confidence="medium",
        )

        history = store.get_entity_history(entity.id)

        assert [item.observed_at for item in history] == ["2026-07-01", "2026-07-02"]
        assert history[0].metric_name == "release"
        assert history[1].metric_name == "stars"
        assert history[1].previous_value == "24000"
        assert history[1].current_value == "25500"
    finally:
        store.close()


def test_link_entities_and_record_decision(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        repo = store.upsert_entity(
            kind="repository",
            canonical_name="All-Hands-AI/OpenHands",
            observed_at="2026-07-01",
        )
        technology = store.upsert_entity(
            kind="technology",
            canonical_name="AI agents",
            observed_at="2026-07-01",
        )

        relationship = store.link_entities(
            source_entity_id=repo.id,
            target_entity_id=technology.id,
            relation_type="implements",
            evidence="Repository describes itself as an AI software engineering agent.",
            confidence="medium",
        )
        duplicate = store.link_entities(
            source_entity_id=repo.id,
            target_entity_id=technology.id,
            relation_type="implements",
            evidence="Duplicate relationship should reuse the existing record.",
            confidence="medium",
        )
        decision = store.record_decision(
            signal_id="signal-openhands-momentum",
            action="Prototype",
            rationale="High repository momentum can reveal useful agent workflow patterns.",
            expected_payoff="Find implementation patterns Hermes can reuse.",
            risk="Momentum may reflect hype rather than stable engineering value.",
            revisit_date="2026-07-08",
            confidence="medium",
        )

        assert relationship.id == duplicate.id
        assert relationship.relation_type == "implements"
        assert decision.action == "Prototype"
    finally:
        store.close()


def test_record_decision_rejects_actions_outside_product_contract(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        with pytest.raises(ValueError, match="Unsupported decision action"):
            store.record_decision(
                signal_id="signal-1",
                action="Summarize",  # type: ignore[arg-type]
                rationale="Invalid product action.",
                expected_payoff="None.",
                risk="Breaks the decision contract.",
                revisit_date="2026-07-08",
                confidence="low",
            )
    finally:
        store.close()


def test_record_and_list_briefs_preserves_delivery_status(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        brief = store.record_brief(
            brief_type="daily",
            domain="AI Intelligence",
            period_start="2026-07-02",
            period_end="2026-07-02",
            title="Hermes Daily Intelligence - 2026-07-02",
            executive_summary="Prototype actions increased.",
            top_actions=("Prototype: Paper connects to radar entities.",),
            notion_status="published",
            notion_url="https://notion.so/hermes-daily",
            telegram_status="sent",
            telegram_detail="42",
        )

        briefs = store.list_briefs(brief_type="daily", since="2026-07-01", until="2026-07-07")

        assert len(briefs) == 1
        assert briefs[0].id == brief.id
        assert briefs[0].top_actions == ("Prototype: Paper connects to radar entities.",)
        assert briefs[0].notion_url == "https://notion.so/hermes-daily"
    finally:
        store.close()


def test_record_and_list_runs_preserves_runtime_delivery_status(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        run = store.record_run(
            run_date="2026-07-03",
            stage="dashboard",
            title="Hermes Executive Dashboard - 2026-07-03",
            period_start="2026-06-03",
            period_end="2026-07-03",
            status="completed",
            notion_status="published",
            notion_url="https://notion.so/hermes-dashboard",
            telegram_status="dry-run",
            telegram_detail="Telegram send not requested.",
            created_at="2026-07-03T01:00:00+00:00",
        )

        runs = store.list_runs(stage="dashboard", since="2026-07-01", until="2026-07-03")

        assert len(runs) == 1
        assert runs[0].id == run.id
        assert runs[0].title == "Hermes Executive Dashboard - 2026-07-03"
        assert runs[0].notion_url == "https://notion.so/hermes-dashboard"
        assert runs[0].created_at == "2026-07-03T01:00:00+00:00"
    finally:
        store.close()


def test_notification_outbox_tracks_pending_sent_and_failed_notifications(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        record = store.enqueue_notification(
            title="Hermes Daily Intelligence",
            decisions=("Read: important paper",),
            top_action="Read",
            notion_url="https://notion.so/hermes",
            last_error="skipped: Missing Telegram client.",
            created_at="2026-07-03T01:00:00+00:00",
        )

        pending = store.list_notification_outbox(status="pending")
        assert pending[0].id == record.id
        assert pending[0].decisions == ("Read: important paper",)
        assert pending[0].attempts == 0

        failed = store.mark_notification_failed(record.id, error="Telegram unavailable")
        assert failed.status == "pending"
        assert failed.attempts == 1
        assert failed.last_error == "Telegram unavailable"

        sent = store.mark_notification_sent(record.id, sent_at="2026-07-03T02:00:00+00:00")
        assert sent.status == "sent"
        assert sent.sent_at == "2026-07-03T02:00:00+00:00"
        assert store.list_notification_outbox(status="pending") == []
    finally:
        store.close()


def test_list_entities_relationships_and_decisions_support_radar_queries(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        repo = store.upsert_entity(
            kind="repository",
            canonical_name="All-Hands-AI/OpenHands",
            observed_at="2026-07-01",
            tags=("github", "ai-agent"),
        )
        tech = store.upsert_entity(
            kind="technology",
            canonical_name="AI agents",
            observed_at="2026-07-01",
            tags=("ai-agent",),
        )
        relationship = store.link_entities(
            source_entity_id=repo.id,
            target_entity_id=tech.id,
            relation_type="tagged_with",
            evidence="GitHub topic.",
            confidence="medium",
        )
        decision = store.record_decision(
            signal_id="github-repo:All-Hands-AI/OpenHands:2026-07-01",
            action="Watch",
            rationale="Repository is active enough to keep on radar.",
            expected_payoff="Observe whether stronger momentum appears.",
            risk="May remain noisy.",
            revisit_date="2026-07-08",
            confidence="medium",
        )

        assert [entity.id for entity in store.list_entities(kind="repository")] == [repo.id]
        assert {entity.id for entity in store.list_entities(tag="ai-agent")} == {repo.id, tech.id}
        assert store.list_relationships(source_entity_id=repo.id)[0].id == relationship.id
        assert store.list_decisions(since="2026-07-01", until="2026-07-31")[0].id == decision.id
    finally:
        store.close()
