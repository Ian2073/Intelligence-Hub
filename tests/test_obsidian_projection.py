from __future__ import annotations

import re
from pathlib import Path

from core.memory import MemoryStore
from core.proposal_service import ProposalTrustService
from core.proposals import InsightProposalPayload, Proposal
from core.obsidian_publisher import ObsidianPublisher, diagnose_vault_wikilinks
from core.obsidian_read_model import ObsidianReadModelBuilder
from core.obsidian_renderer import ObsidianRenderer, diagnose_broken_wikilinks
from core.repository import SQLiteRepository


def _seed_repository(store: MemoryStore) -> dict[str, str]:
    repo = store.upsert_entity(
        kind="repository",
        canonical_name="owner/repo",
        observed_at="2026-07-10",
        aliases=("repo", "https://github.com/owner/repo"),
        tags=("github", "agents"),
        summary="Agent repository.",
    )
    paper = store.upsert_entity(
        kind="paper",
        canonical_name="Agent Paper",
        observed_at="2026-07-10",
        aliases=("https://example.com/paper",),
        tags=("paper", "agents"),
        summary="Paper summary.",
    )
    tech = store.upsert_entity(
        kind="technology",
        canonical_name="agents",
        observed_at="2026-07-10",
        tags=("github-topic",),
        summary="Technology topic.",
    )
    store.link_entities(
        source_entity_id=repo.id,
        target_entity_id=tech.id,
        relation_type="tagged_with",
        evidence="Repository topic.",
        confidence="medium",
    )
    store.link_entities(
        source_entity_id=paper.id,
        target_entity_id=repo.id,
        relation_type="related_repository",
        evidence="Paper references the repository.",
        confidence="medium",
    )
    store.record_observation(
        entity_id=repo.id,
        observed_at="2026-07-10",
        source_type="github",
        source_url="https://github.com/owner/repo",
        metric_name="stars",
        previous_value=10,
        current_value=20,
        raw_evidence="GitHub stars snapshot.",
        confidence="high",
    )
    release = store.record_observation(
        entity_id=repo.id,
        observed_at="2026-07-10",
        source_type="github",
        source_url="https://github.com/owner/repo/releases/tag/v1",
        metric_name="latest_release",
        previous_value="",
        current_value="v1.0.0",
        raw_evidence="Release v1.0.0 observed.",
        confidence="high",
    )
    store.record_observation(
        entity_id=paper.id,
        observed_at="2026-07-10",
        source_type="paper",
        source_url="https://example.com/paper",
        metric_name="published",
        previous_value="",
        current_value="2026-07-10",
        raw_evidence="Paper metadata.",
        confidence="medium",
    )
    decision = store.record_decision(
        signal_id="github-repo:owner/repo:2026-07-10",
        action="Watch",
        rationale="Repository has a new release.",
        expected_payoff="Understand whether it matters.",
        risk="May be noisy.",
        revisit_date="2026-07-17",
        confidence="medium",
    )
    brief = store.record_brief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start="2026-07-10",
        period_end="2026-07-10",
        title="Daily Intelligence - 2026-07-10",
        executive_summary="Repository and paper signals are connected.",
        top_actions=("Watch: owner/repo",),
        notion_status="dry-run",
        notion_url="local://notion",
        telegram_status="dry-run",
        telegram_detail="not sent",
    )
    return {"repo": repo.id, "paper": paper.id, "tech": tech.id, "release": release.id, "decision": decision.id, "brief": brief.id}


def _build_model(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.sqlite")
    ids = _seed_repository(store)
    try:
        model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(store)).build()
        return model, ids
    finally:
        store.close()


def test_read_model_builds_note_graph_from_canonical_repository(tmp_path: Path) -> None:
    model, ids = _build_model(tmp_path)
    by_id = {note.canonical_id: note for note in model.notes}

    repo_note = by_id[f"entity:{ids['repo']}"]
    paper_note = by_id[f"source:{ids['paper']}"]
    release_note = by_id[f"event:{ids['release']}"]

    assert repo_note.note_type == "entity"
    assert repo_note.path.startswith("04 Entities/Repositories/")
    assert paper_note.note_type == "source"
    assert paper_note.path.startswith("05 Sources/Papers/")
    assert release_note.note_type == "event"
    assert not any(note.note_type == "event" and "stars" in note.title for note in model.notes)
    assert any(link.canonical_id == f"entity:{ids['tech']}" for link in repo_note.related_notes)
    assert any(link.canonical_id == f"entity:{ids['repo']}" for link in paper_note.related_notes)


def test_stable_identity_allows_rename_and_sanitize_collisions(tmp_path: Path) -> None:
    first = MemoryStore(tmp_path / "first.sqlite")
    try:
        entity = first.upsert_entity(kind="technology", canonical_name="A/B", observed_at="2026-07-10")
        model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(first)).build()
        original_path = next(note.path for note in model.notes if note.canonical_id == f"entity:{entity.id}")
        first._connection.execute("UPDATE entities SET canonical_name = ? WHERE id = ?", ("A:B", entity.id))
        first._connection.commit()
        renamed_model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(first)).build()
        renamed_path = next(note.path for note in renamed_model.notes if note.canonical_id == f"entity:{entity.id}")
    finally:
        first.close()

    second = MemoryStore(tmp_path / "second.sqlite")
    try:
        collision = second.upsert_entity(kind="technology", canonical_name="A/B", observed_at="2026-07-11")
        model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(second)).build()
        paths = {
            note.canonical_id: note.path
            for note in model.notes
            if note.note_type == "entity" and note.title in {"A:B", "A/B"}
        }
        collision_path = paths[f"entity:{collision.id}"]
    finally:
        second.close()

    assert renamed_path == original_path
    assert renamed_path != collision_path


def test_renderer_outputs_platform_neutral_frontmatter_and_full_path_wikilinks(tmp_path: Path) -> None:
    model, _ = _build_model(tmp_path)
    renderer = ObsidianRenderer()
    rendered = {note.path: renderer.render(note) for note in model.notes}

    assert all('generated_by: "intelligence_hub.obsidian.v1"' in text for text in rendered.values())
    assert not any("generated_by: hermes." in text for text in rendered.values())
    assert not any("Hermes Daily Intelligence" in text for text in rendered.values())
    assert any("[[04 Entities/Repositories/" in text for text in rendered.values())
    assert not any(re.search(r"\[\[[^\]|]+\.md(?:\||\]\])", text) for text in rendered.values())
    assert diagnose_broken_wikilinks(rendered) == []

    entity_markdown = next(text for path, text in rendered.items() if path.startswith("04 Entities/Repositories/"))
    assert "canonical_id:" in entity_markdown
    assert "## Observations" in entity_markdown
    assert "## Related Notes" in entity_markdown


def test_publisher_preserves_user_notes_writes_manifest_and_no_starter_files(tmp_path: Path) -> None:
    model, _ = _build_model(tmp_path)
    vault = tmp_path / "vault"
    publisher = ObsidianPublisher(vault)
    first = publisher.publish(model)
    repo_path = next(path for path in first.written if "04 Entities" in path.as_posix())
    repo_text = repo_path.read_text(encoding="utf-8")
    repo_path.write_text(
        repo_text.replace("<!-- intelligence_hub:user:end -->", "Manual note.\n<!-- intelligence_hub:user:end -->"),
        encoding="utf-8",
    )
    stale_path = vault / "04 Entities" / "Other" / "old--12345678.md"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text(
        '---\ngenerated_by: "intelligence_hub.obsidian.v1"\n---\n# Old\n',
        encoding="utf-8",
    )

    result = publisher.publish(model)

    assert "Manual note." in repo_path.read_text(encoding="utf-8")
    assert stale_path in result.stale
    assert "04 Entities/Other/old--12345678.md" in (vault / "90 System" / "Stale Notes.md").read_text(encoding="utf-8")
    assert not list(vault.rglob("歡迎*.md"))
    assert not list(vault.rglob("建立連接*.md"))
    assert diagnose_vault_wikilinks(vault) == []
    assert not list(vault.rglob("*.tmp"))


def test_daily_pipeline_fixture_generates_repository_driven_vault(tmp_path: Path) -> None:
    from connectors.obsidian import ObsidianClient
    from core.daily_pipeline import run_daily_pipeline
    from core.watchlist import GitHubWatchItem, PaperWatchItem

    fixture_root = tmp_path / "fixtures"
    (fixture_root / "github").mkdir(parents=True)
    (fixture_root / "papers").mkdir(parents=True)
    (fixture_root / "github" / "repo.json").write_text(
        """
        {
          "repo": {
            "owner": {"login": "owner"},
            "name": "repo",
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
            "description": "Agent repository.",
            "language": "Python",
            "stargazers_count": 20,
            "open_issues_count": 1,
            "topics": ["agents"],
            "pushed_at": "2026-07-10T00:00:00Z",
            "updated_at": "2026-07-10T00:00:00Z",
            "default_branch": "main"
          },
          "latest_release": {
            "tag_name": "v1.0.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "published_at": "2026-07-10T00:00:00Z"
          }
        }
        """,
        encoding="utf-8",
    )
    (fixture_root / "papers" / "paper.json").write_text(
        """
        {
          "title": "Agent Paper",
          "url": "https://example.com/paper",
          "abstract": "Agent paper references owner/repo.",
          "published_at": "2026-07-10",
          "categories": ["cs.AI"],
          "technologies": ["agents"],
          "repositories": ["owner/repo"],
          "companies": []
        }
        """,
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=(GitHubWatchItem(owner="owner", name="repo", fixture="github/repo.json"),),
            paper_watchlist=(PaperWatchItem(title="Agent Paper", fixture="papers/paper.json", query="", max_results=1),),
            run_date="2026-07-10",
            revisit_date="2026-07-17",
            notion_url="local://notion",
            fixture_root=fixture_root,
            obsidian_client=ObsidianClient(tmp_path / "vault"),
            publish_obsidian=True,
        )
    finally:
        store.close()

    vault = tmp_path / "vault"
    assert result.obsidian is not None
    assert result.obsidian.status == "published"
    assert result.proposal_metrics is not None
    assert result.proposal_metrics.proposals_created > 0
    assert result.proposal_metrics.insight_count >= 1
    assert (vault / "00 Dashboard" / "Home.md").is_file()
    assert list((vault / "02 Insights").glob("*.md"))
    assert list((vault / "01 Briefs" / "Daily").glob("*.md"))
    assert list((vault / "04 Entities" / "Repositories").glob("*.md"))
    assert list((vault / "05 Sources" / "Papers").glob("*.md"))
    assert diagnose_vault_wikilinks(vault) == []

    outbound_counts = {
        path.relative_to(vault).as_posix(): len(re.findall(r"\[\[[^\]]+\]\]", path.read_text(encoding="utf-8")))
        for folder in ("04 Entities", "05 Sources")
        for path in (vault / folder).rglob("*.md")
    }
    assert any(path.startswith("04 Entities/Repositories/") and count > 0 for path, count in outbound_counts.items())
    assert any(path.startswith("05 Sources/Papers/") and count > 0 for path, count in outbound_counts.items())
    daily = next((vault / "01 Briefs" / "Daily").glob("*.md"))
    daily_text = daily.read_text(encoding="utf-8")
    assert "Hermes Daily Intelligence" not in daily_text
    assert "[[02 Insights/" in daily_text
    assert "[[06 Decisions/" in daily_text
    assert "[[04 Entities/Repositories/" in daily_text or "[[05 Sources/Papers/" in daily_text


def test_obsidian_outputs_insight_and_proposal_review_surfaces(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    ids = _seed_repository(store)
    try:
        service = ProposalTrustService(store=store)
        accepted = service.submit(
            Proposal.create(
                proposal_type="insight",
                payload=InsightProposalPayload(
                    claim="owner/repo and Agent Paper converge on agents.",
                    summary="Repository and paper evidence point to the same agent theme.",
                    why_it_matters="Cross-source convergence is stronger than a single source.",
                    evidence_refs=("observation:1", "relationship:1"),
                    related_entity_refs=(f"entity:{ids['repo']}", f"source:{ids['paper']}"),
                    possible_actions=("Read",),
                    confidence="medium",
                    generated_at="2026-07-10",
                ),
                evidence_refs=("observation:1", "relationship:1"),
                confidence="medium",
                proposed_by="intelligence_hub.insight_engine",
            )
        )
        rejected = service.submit(
            Proposal.create(
                proposal_type="insight",
                payload=InsightProposalPayload(
                    claim="Unsupported claim",
                    summary="No evidence.",
                    why_it_matters="No evidence.",
                    evidence_refs=(),
                    confidence="medium",
                    generated_at="2026-07-10",
                ),
                evidence_refs=(),
                confidence="medium",
                proposed_by="intelligence_hub.insight_engine",
            )
        )
        model = ObsidianReadModelBuilder(SQLiteRepository.from_memory_store(store)).build()
        result = ObsidianPublisher(tmp_path / "vault").publish(model)
    finally:
        store.close()

    vault = tmp_path / "vault"
    insight_note = next((vault / "02 Insights").glob("*.md"))
    insight_text = insight_note.read_text(encoding="utf-8")

    assert accepted.proposal.validation_status == "accepted"
    assert rejected.proposal.validation_status == "rejected"
    assert "## Claim" in insight_text
    assert "## Why It Matters" in insight_text
    assert "[[04 Entities/Repositories/" in insight_text
    assert (vault / "90 System" / "Rejected Proposals.md").is_file()
    assert rejected.proposal.id in (vault / "90 System" / "Rejected Proposals.md").read_text(encoding="utf-8")
    assert (vault / "90 System" / "Needs Review.md").is_file()
    assert result.broken_wikilinks == ()
