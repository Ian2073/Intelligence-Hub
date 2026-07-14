from __future__ import annotations

from connectors.notion import (
    NotionBriefRecord,
    NotionClient,
    NotionDecisionRecord,
    NotionEcosystemRecord,
    NotionGitHubRepoRecord,
    NotionPaperRecord,
    NotionRadarEntityRecord,
    NotionRadarSnapshotRecord,
    PublishedPage,
    build_brief_database_payload,
    build_database_rich_text_query_payload,
    build_decision_database_payload,
    build_decision_update_payload,
    build_database_title_query_payload,
    build_database_url_query_payload,
    build_database_payload,
    build_ecosystem_database_payload,
    build_github_repo_database_payload,
    build_github_repo_update_payload,
    build_paper_database_payload,
    build_paper_update_payload,
    build_radar_entity_database_payload,
    build_radar_entity_update_payload,
    build_radar_snapshot_database_payload,
    build_ecosystem_update_payload,
    notion_workspace_database_specs,
    _rich_body_blocks,
)
from core.notion_provisioning import provision_notion_workspace


def test_build_brief_database_payload_uses_structured_properties() -> None:
    payload = build_brief_database_payload(
        "database-id",
        NotionBriefRecord(
            title="Intelligence Hub Daily Brief - 2026-07-02",
            date="2026-07-02",
            executive_summary="Open-source AI engineering accelerated.",
            recommended_actions=("Prototype", "Watch"),
            intelligence_score=84,
            confidence="medium",
            status="Published",
            tags=("AI Intelligence", "GitHub Radar"),
            body="Prototype: OpenHands momentum surged.",
        ),
    )

    assert payload["parent"] == {"database_id": "database-id"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Intelligence Hub Daily Brief - 2026-07-02"
    assert payload["properties"]["Date"]["date"]["start"] == "2026-07-02"
    assert payload["properties"]["Intelligence Score"]["number"] == 84
    assert payload["properties"]["Confidence"]["select"]["name"] == "medium"
    assert payload["properties"]["Recommended Actions"]["multi_select"] == [
        {"name": "Prototype"},
        {"name": "Watch"},
    ]
    assert payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"].startswith("Prototype:")


def test_rich_body_blocks_use_summary_callout_and_rationale_toggle() -> None:
    blocks = _rich_body_blocks(
        """> [!summary]
> **Executive Summary**
> OpenHands is notable.

## GitHub Repositories
- [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) — **Prototype**.
  - Rationale: Release and PR activity support a prototype.
"""
    )

    assert any(block["type"] == "callout" for block in blocks)
    assert any(block["type"] == "toggle" for block in blocks)


def test_notion_workspace_database_specs_include_core_databases() -> None:
    specs = notion_workspace_database_specs()
    keys = [spec.key for spec in specs]

    assert keys == ["briefs", "papers", "github_repos", "ecosystem", "decisions", "radar_snapshots", "radar_entities"]
    briefs = specs[0]
    assert briefs.properties["Name"] == {"title": {}}
    assert "Recommended Actions" in briefs.properties
    assert "Intelligence Score" in briefs.properties


def test_build_database_payload_targets_parent_page() -> None:
    spec = notion_workspace_database_specs()[0]

    payload = build_database_payload("parent-page-id", spec)

    assert payload["parent"] == {"type": "page_id", "page_id": "parent-page-id"}
    assert payload["title"][0]["text"]["content"] == "AI Intelligence Briefs"
    assert payload["properties"]["Name"] == {"title": {}}


def test_build_decision_database_payload_uses_decision_schema() -> None:
    payload = build_decision_database_payload(
        "decisions-db",
        NotionDecisionRecord(
            title="Prototype: github-repo:OpenHands",
            action="Prototype",
            rationale="OpenHands momentum can reveal useful patterns.",
            expected_payoff="Find reusable agent architecture.",
            risk="Momentum may be noisy.",
            revisit_date="2026-07-09",
            confidence="medium",
            signal_id="github-repo:OpenHands:2026-07-02",
            status="Open",
        ),
    )

    assert payload["parent"] == {"database_id": "decisions-db"}
    assert payload["properties"]["Action"]["select"]["name"] == "Prototype"
    assert payload["properties"]["Revisit Date"]["date"]["start"] == "2026-07-09"
    assert payload["properties"]["Status"]["select"]["name"] == "Open"


def test_build_decision_update_payload_updates_properties_only() -> None:
    payload = build_decision_update_payload(
        NotionDecisionRecord(
            title="Prototype: github-repo:OpenHands",
            action="Prototype",
            rationale="Updated rationale.",
            expected_payoff="Validate architecture.",
            risk="Could be noisy.",
            revisit_date="2026-07-16",
            confidence="high",
            signal_id="github-repo:OpenHands:2026-07-02",
            status="Open",
        )
    )

    assert set(payload) == {"properties"}
    assert payload["properties"]["Action"]["select"]["name"] == "Prototype"
    assert payload["properties"]["Signal ID"]["rich_text"][0]["text"]["content"] == "github-repo:OpenHands:2026-07-02"
    assert payload["properties"]["Revisit Date"]["date"]["start"] == "2026-07-16"


def test_build_radar_snapshot_database_payload_uses_snapshot_schema() -> None:
    payload = build_radar_snapshot_database_payload(
        "radar-db",
        NotionRadarSnapshotRecord(
            title="Intelligence Hub Radar Snapshot - 2026-07-09",
            as_of="2026-07-09",
            executive_summary="Radar summary.",
            entity_count=12,
            top_actions=("Prototype", "Read"),
            status="Published",
            body="Radar body.",
        ),
    )

    assert payload["parent"] == {"database_id": "radar-db"}
    assert payload["properties"]["As Of"]["date"]["start"] == "2026-07-09"
    assert payload["properties"]["Entity Count"]["number"] == 12
    assert payload["properties"]["Top Actions"]["multi_select"] == [{"name": "Prototype"}, {"name": "Read"}]
    assert payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"] == "Radar body."


def test_build_radar_entity_database_payload_uses_entity_schema() -> None:
    payload = build_radar_entity_database_payload(
        "radar-entities-db",
        NotionRadarEntityRecord(
            name="AI agents",
            type="Technology",
            status="active",
            last_seen="2026-07-09",
            summary="Agentic software systems.",
            tags=("agent", "workflow"),
            observation_count=7,
            relationship_count=3,
            recent_metrics=("papers: 4 -> 7", "repos: 2 -> 3"),
        ),
    )

    assert payload["parent"] == {"database_id": "radar-entities-db"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "AI agents"
    assert payload["properties"]["Type"]["select"]["name"] == "Technology"
    assert payload["properties"]["Status"]["select"]["name"] == "active"
    assert payload["properties"]["Last Seen"]["date"]["start"] == "2026-07-09"
    assert payload["properties"]["Observation Count"]["number"] == 7
    assert payload["properties"]["Relationship Count"]["number"] == 3
    assert "papers: 4 -> 7" in payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"]


def test_build_radar_entity_update_payload_updates_properties_only() -> None:
    payload = build_radar_entity_update_payload(
        NotionRadarEntityRecord(
            name="AI agents",
            type="Technology",
            status="active",
            last_seen="2026-07-10",
            summary="Updated summary.",
            tags=("agent",),
            observation_count=8,
            relationship_count=4,
            recent_metrics=("ignored in property update body",),
        )
    )

    assert set(payload) == {"properties"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "AI agents"
    assert payload["properties"]["Last Seen"]["date"]["start"] == "2026-07-10"
    assert payload["properties"]["Observation Count"]["number"] == 8


def test_build_database_title_query_payload_uses_exact_title_filter() -> None:
    payload = build_database_title_query_payload("Name", "AI agents")

    assert payload == {
        "filter": {
            "property": "Name",
            "title": {
                "equals": "AI agents",
            },
        },
        "page_size": 1,
    }


def test_build_database_rich_text_query_payload_uses_exact_text_filter() -> None:
    payload = build_database_rich_text_query_payload("Signal ID", "github-repo:OpenHands:2026-07-02")

    assert payload == {
        "filter": {
            "property": "Signal ID",
            "rich_text": {
                "equals": "github-repo:OpenHands:2026-07-02",
            },
        },
        "page_size": 1,
    }


def test_notion_client_upsert_decision_creates_when_missing(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionDecisionRecord(
        title="Watch: signal",
        action="Watch",
        rationale="Rationale.",
        expected_payoff="Payoff.",
        risk="Risk.",
        revisit_date="2026-07-10",
        confidence="medium",
        signal_id="signal:1",
        status="Open",
    )

    monkeypatch.setattr(client, "find_database_page_by_rich_text", lambda database_id, property_name, text: None)

    def create(database_id, incoming):
        calls.append(("create", database_id, incoming.signal_id))
        return PublishedPage(id="created-decision", url="https://notion.so/created-decision")

    monkeypatch.setattr(client, "create_decision_record", create)

    page = client.upsert_decision_record("decisions-db", record)

    assert page.id == "created-decision"
    assert calls == [("create", "decisions-db", "signal:1")]


def test_notion_client_upsert_decision_updates_when_existing(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionDecisionRecord(
        title="Prototype: signal",
        action="Prototype",
        rationale="Rationale.",
        expected_payoff="Payoff.",
        risk="Risk.",
        revisit_date="2026-07-10",
        confidence="high",
        signal_id="signal:1",
        status="Open",
    )

    monkeypatch.setattr(
        client,
        "find_database_page_by_rich_text",
        lambda database_id, property_name, text: PublishedPage(id="existing-decision", url="https://notion.so/existing-decision"),
    )

    def update(page_id, incoming):
        calls.append(("update", page_id, incoming.action, incoming.signal_id))
        return PublishedPage(id=page_id, url="https://notion.so/existing-decision")

    monkeypatch.setattr(client, "update_decision_record", update)

    page = client.upsert_decision_record("decisions-db", record)

    assert page.id == "existing-decision"
    assert calls == [("update", "existing-decision", "Prototype", "signal:1")]


def test_notion_client_upsert_radar_entity_creates_when_missing(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionRadarEntityRecord(
        name="AI agents",
        type="Technology",
        status="active",
        last_seen="2026-07-10",
        summary="Summary.",
        tags=(),
        observation_count=1,
        relationship_count=0,
        recent_metrics=(),
    )

    monkeypatch.setattr(client, "find_database_page_by_title", lambda database_id, property_name, title: None)

    def create(database_id, incoming):
        calls.append(("create", database_id, incoming.name))
        return PublishedPage(id="created-page", url="https://notion.so/created")

    monkeypatch.setattr(client, "create_radar_entity_record", create)

    page = client.upsert_radar_entity_record("radar-entities-db", record)

    assert page.id == "created-page"
    assert calls == [("create", "radar-entities-db", "AI agents")]


def test_notion_client_upsert_radar_entity_updates_when_existing(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionRadarEntityRecord(
        name="AI agents",
        type="Technology",
        status="active",
        last_seen="2026-07-10",
        summary="Summary.",
        tags=(),
        observation_count=1,
        relationship_count=0,
        recent_metrics=(),
    )

    monkeypatch.setattr(
        client,
        "find_database_page_by_title",
        lambda database_id, property_name, title: PublishedPage(id="existing-page", url="https://notion.so/existing"),
    )

    def update(page_id, incoming):
        calls.append(("update", page_id, incoming.name))
        return PublishedPage(id=page_id, url="https://notion.so/existing")

    monkeypatch.setattr(client, "update_radar_entity_record", update)

    page = client.upsert_radar_entity_record("radar-entities-db", record)

    assert page.id == "existing-page"
    assert calls == [("update", "existing-page", "AI agents")]


def test_notion_client_upsert_paper_updates_by_url(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionPaperRecord(
        title="Agentic Retrieval for Code Editing",
        authors="A. Researcher",
        url="https://arxiv.org/abs/2607.00001",
        published_date="2026-07-01",
        summary="Summary.",
        why_it_matters="Reason.",
        technology_area=("AI agents",),
        intelligence_score=85,
        recommended_action="Prototype",
        confidence="medium",
    )

    monkeypatch.setattr(
        client,
        "find_database_page_by_url",
        lambda database_id, property_name, url: PublishedPage(id="existing-paper", url="https://notion.so/paper"),
    )

    def update(page_id, incoming):
        calls.append(("update", page_id, incoming.url))
        return PublishedPage(id=page_id, url="https://notion.so/paper")

    monkeypatch.setattr(client, "update_paper_record", update)

    page = client.upsert_paper_record("papers-db", record)

    assert page.id == "existing-paper"
    assert calls == [("update", "existing-paper", "https://arxiv.org/abs/2607.00001")]


def test_notion_client_upsert_github_repo_updates_by_name(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionGitHubRepoRecord(
        name="All-Hands-AI/OpenHands",
        url="https://github.com/All-Hands-AI/OpenHands",
        owner="All-Hands-AI",
        stars=25500,
        category="AI Agent",
        summary="Summary.",
        why_it_matters="Reason.",
        engineering_value="medium",
        adoption_potential="high",
        recommended_action="Watch",
    )

    monkeypatch.setattr(
        client,
        "find_database_page_by_title",
        lambda database_id, property_name, title: PublishedPage(id="existing-repo", url="https://notion.so/repo"),
    )

    def update(page_id, incoming):
        calls.append(("update", page_id, incoming.name))
        return PublishedPage(id=page_id, url="https://notion.so/repo")

    monkeypatch.setattr(client, "update_github_repo_record", update)

    page = client.upsert_github_repo_record("repos-db", record)

    assert page.id == "existing-repo"
    assert calls == [("update", "existing-repo", "All-Hands-AI/OpenHands")]


def test_notion_client_upsert_ecosystem_updates_by_name(monkeypatch) -> None:
    client = NotionClient("token", "parent")
    calls = []
    record = NotionEcosystemRecord(
        name="Agentic security evaluation",
        type="Technology",
        company_or_maintainer="",
        category=("AI agents",),
        summary="Summary.",
        why_it_matters="Reason.",
        impact="high",
        momentum="rising",
    )

    monkeypatch.setattr(
        client,
        "find_database_page_by_title",
        lambda database_id, property_name, title: PublishedPage(id="existing-ecosystem", url="https://notion.so/ecosystem"),
    )

    def update(page_id, incoming):
        calls.append(("update", page_id, incoming.name))
        return PublishedPage(id=page_id, url="https://notion.so/ecosystem")

    monkeypatch.setattr(client, "update_ecosystem_record", update)

    page = client.upsert_ecosystem_record("ecosystem-db", record)

    assert page.id == "existing-ecosystem"
    assert calls == [("update", "existing-ecosystem", "Agentic security evaluation")]


def test_build_paper_database_payload_uses_paper_schema() -> None:
    payload = build_paper_database_payload(
        "papers-db",
        NotionPaperRecord(
            title="Agentic Retrieval for Code Editing",
            authors="A. Researcher",
            url="https://arxiv.org/abs/2607.00001",
            published_date="2026-07-01",
            summary="Paper summary.",
            why_it_matters="Connects research to implementation.",
            technology_area=("AI agents", "RAG"),
            intelligence_score=85,
            recommended_action="Prototype",
            confidence="medium",
        ),
    )

    assert payload["parent"] == {"database_id": "papers-db"}
    assert payload["properties"]["Title"]["title"][0]["text"]["content"] == "Agentic Retrieval for Code Editing"
    assert payload["properties"]["URL"]["url"] == "https://arxiv.org/abs/2607.00001"
    assert payload["properties"]["Technology Area"]["multi_select"] == [{"name": "AI agents"}, {"name": "RAG"}]
    assert payload["properties"]["Recommended Action"]["select"]["name"] == "Prototype"


def test_build_paper_update_payload_updates_properties_only() -> None:
    payload = build_paper_update_payload(
        NotionPaperRecord(
            title="Agentic Retrieval for Code Editing",
            authors="A. Researcher",
            url="https://arxiv.org/abs/2607.00001",
            published_date="2026-07-02",
            summary="Updated paper summary.",
            why_it_matters="Updated reasoning.",
            technology_area=("AI agents",),
            intelligence_score=91,
            recommended_action="Read",
            confidence="high",
        )
    )

    assert set(payload) == {"properties"}
    assert payload["properties"]["URL"]["url"] == "https://arxiv.org/abs/2607.00001"
    assert payload["properties"]["Intelligence Score"]["number"] == 91


def test_build_github_repo_database_payload_uses_repo_schema() -> None:
    payload = build_github_repo_database_payload(
        "repos-db",
        NotionGitHubRepoRecord(
            name="All-Hands-AI/OpenHands",
            url="https://github.com/All-Hands-AI/OpenHands",
            owner="All-Hands-AI",
            stars=25500,
            category="AI Agent",
            summary="AI software engineering agent.",
            why_it_matters="Momentum is active.",
            engineering_value="medium",
            adoption_potential="high",
            recommended_action="Watch",
        ),
    )

    assert payload["parent"] == {"database_id": "repos-db"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "All-Hands-AI/OpenHands"
    assert payload["properties"]["Stars"]["number"] == 25500
    assert payload["properties"]["Category"]["select"]["name"] == "AI Agent"


def test_build_github_repo_update_payload_updates_properties_only() -> None:
    payload = build_github_repo_update_payload(
        NotionGitHubRepoRecord(
            name="All-Hands-AI/OpenHands",
            url="https://github.com/All-Hands-AI/OpenHands",
            owner="All-Hands-AI",
            stars=26000,
            category="AI Agent",
            summary="Updated summary.",
            why_it_matters="Updated rationale.",
            engineering_value="high",
            adoption_potential="high",
            recommended_action="Prototype",
        )
    )

    assert set(payload) == {"properties"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "All-Hands-AI/OpenHands"
    assert payload["properties"]["Stars"]["number"] == 26000


def test_build_ecosystem_database_payload_uses_ecosystem_schema() -> None:
    payload = build_ecosystem_database_payload(
        "ecosystem-db",
        NotionEcosystemRecord(
            name="Agentic security evaluation",
            type="Technology",
            company_or_maintainer="",
            category=("Cybersecurity Intelligence", "AI agents"),
            summary="Agents need security evaluation.",
            why_it_matters="Tool permissions expand risk.",
            impact="high",
            momentum="rising",
        ),
    )

    assert payload["parent"] == {"database_id": "ecosystem-db"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Agentic security evaluation"
    assert payload["properties"]["Type"]["select"]["name"] == "Technology"
    assert payload["properties"]["Impact"]["select"]["name"] == "high"


def test_build_ecosystem_update_payload_updates_properties_only() -> None:
    payload = build_ecosystem_update_payload(
        NotionEcosystemRecord(
            name="Agentic security evaluation",
            type="Technology",
            company_or_maintainer="",
            category=("Cybersecurity Intelligence",),
            summary="Updated summary.",
            why_it_matters="Updated rationale.",
            impact="medium",
            momentum="active",
        )
    )

    assert set(payload) == {"properties"}
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Agentic security evaluation"
    assert payload["properties"]["Momentum"]["select"]["name"] == "active"


def test_build_database_url_query_payload_uses_exact_url_filter() -> None:
    payload = build_database_url_query_payload("URL", "https://arxiv.org/abs/2607.00001")

    assert payload == {
        "filter": {
            "property": "URL",
            "url": {
                "equals": "https://arxiv.org/abs/2607.00001",
            },
        },
        "page_size": 1,
    }


def test_provision_notion_workspace_dry_run_does_not_require_client() -> None:
    results = provision_notion_workspace(notion_client=None, apply=False)

    assert len(results) == 7
    assert results[0].status == "dry-run"
    assert results[0].key == "briefs"


def test_provision_notion_workspace_apply_uses_client() -> None:
    class FakeNotionClient:
        def __init__(self) -> None:
            self.specs = []

        def create_database(self, spec):
            self.specs.append(spec)
            return type("Page", (), {"id": f"id-{spec.key}", "url": f"https://notion.so/{spec.key}"})()

    client = FakeNotionClient()

    results = provision_notion_workspace(notion_client=client, apply=True)  # type: ignore[arg-type]

    assert [spec.key for spec in client.specs] == [
        "briefs",
        "papers",
        "github_repos",
        "ecosystem",
        "decisions",
        "radar_snapshots",
        "radar_entities",
    ]
    assert results[0].status == "created"
    assert results[0].id == "id-briefs"


def test_provision_notion_workspace_apply_skips_existing_database_ids() -> None:
    class FakeNotionClient:
        def __init__(self) -> None:
            self.specs = []

        def create_database(self, spec):
            self.specs.append(spec)
            return type("Page", (), {"id": f"id-{spec.key}", "url": f"https://notion.so/{spec.key}"})()

    client = FakeNotionClient()

    results = provision_notion_workspace(
        notion_client=client,  # type: ignore[arg-type]
        apply=True,
        existing_database_ids={
            "briefs": "existing-briefs-id",
            "papers": "existing-papers-id",
        },
    )

    assert [spec.key for spec in client.specs] == [
        "github_repos",
        "ecosystem",
        "decisions",
        "radar_snapshots",
        "radar_entities",
    ]
    assert results[0].status == "existing"
    assert results[0].id == "existing-briefs-id"
    assert results[1].status == "existing"
    assert results[1].id == "existing-papers-id"
    assert results[2].status == "created"
