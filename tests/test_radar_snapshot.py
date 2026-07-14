from __future__ import annotations

from core.memory import MemoryStore
from core.radar_pipeline import _entity_type_label, run_radar_pipeline
from workflows.radar_snapshot import build_radar_snapshot


class FakeNotionClient:
    def __init__(self) -> None:
        self.pages = []
        self.radar_records = []
        self.radar_entity_records = []
        self.decision_records = []

    def create_page(self, title, body):
        self.pages.append((title, body))
        return type("Page", (), {"id": "radar-page-id", "url": "https://notion.so/hermes-radar"})()

    def create_radar_snapshot_record(self, database_id, record):
        self.radar_records.append((database_id, record))
        return type("Page", (), {"id": "radar-record-id", "url": "https://notion.so/hermes-radar-record"})()

    def upsert_radar_entity_record(self, database_id, record):
        self.radar_entity_records.append((database_id, record))
        return type("Page", (), {"id": "radar-entity-id", "url": "https://notion.so/hermes-radar-entity"})()

    def upsert_decision_record(self, database_id, record):
        self.decision_records.append((database_id, record))
        return type("Page", (), {"id": "decision-record-id", "url": "https://notion.so/hermes-decision"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 77})()


def _seed_radar_memory(store: MemoryStore) -> None:
    repo = store.upsert_entity(
        kind="repository",
        canonical_name="All-Hands-AI/OpenHands",
        observed_at="2026-07-02",
        tags=("github", "ai-agent"),
        summary="AI software engineering agent.",
    )
    technology = store.upsert_entity(
        kind="technology",
        canonical_name="AI agents",
        observed_at="2026-07-02",
        tags=("agent",),
        summary="Agentic software systems.",
    )
    store.record_observation(
        entity_id=repo.id,
        observed_at="2026-07-02",
        source_type="github",
        source_url="https://github.com/All-Hands-AI/OpenHands",
        metric_name="stars",
        previous_value=24000,
        current_value=25500,
        raw_evidence="GitHub repository snapshot.",
        confidence="high",
    )
    store.link_entities(
        source_entity_id=repo.id,
        target_entity_id=technology.id,
        relation_type="tagged_with",
        evidence="GitHub topic.",
        confidence="medium",
    )
    store.record_decision(
        signal_id="github-repo:All-Hands-AI/OpenHands:2026-07-02",
        action="Prototype",
        rationale="OpenHands momentum can reveal agent workflow patterns.",
        expected_payoff="Find reusable architecture patterns.",
        risk="Momentum may be noisy.",
        revisit_date="2026-07-09",
        confidence="medium",
    )


def test_build_radar_snapshot_uses_memory_entities_and_decisions(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        _seed_radar_memory(store)

        snapshot = build_radar_snapshot(store, as_of="2026-07-09", since="2026-07-01")

        assert snapshot.title == "Intelligence Hub Radar Snapshot - 2026-07-09"
        assert snapshot.entries[0].name == "All-Hands-AI/OpenHands"
        assert snapshot.entries[0].recent_metrics == ("stars: 24000 -> 25500",)
        assert snapshot.top_actions[0].startswith("Prototype: All-Hands-AI/OpenHands")
        assert len(snapshot.top_actions[0]) < 180
        assert snapshot.decisions[0].action == "Prototype"
    finally:
        store.close()


def test_run_radar_pipeline_publishes_page_and_sends_telegram(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    try:
        _seed_radar_memory(store)

        result = run_radar_pipeline(
            store=store,
            as_of="2026-07-09",
            since="2026-07-01",
            notion_url="local://notion/radar",
            notion_client=notion,  # type: ignore[arg-type]
            notion_radar_database_id="radar-db",
            notion_radar_entities_database_id="radar-entities-db",
            notion_decisions_database_id="decisions-db",
            telegram_client=telegram,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.telegram.status == "sent"
        assert result.brief.brief_type == "radar"
        assert notion.pages == []
        assert notion.radar_records[0][0] == "radar-db"
        assert notion.radar_records[0][1].top_actions == ("Prototype",)
        assert notion.radar_entity_records[0][0] == "radar-entities-db"
        assert notion.radar_entity_records[0][1].name == "All-Hands-AI/OpenHands"
        assert notion.radar_entity_records[0][1].type == "Repository"
        assert notion.decision_records[0][0] == "decisions-db"
        assert notion.decision_records[0][1].action == "Prototype"
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-radar-record"
    finally:
        store.close()


def test_radar_entity_type_label_normalizes_internal_kinds() -> None:
    assert _entity_type_label("company_strategy") == "Company"
    assert _entity_type_label("repository") == "Repository"
    assert _entity_type_label("unknown_kind") == "Concept"
