from __future__ import annotations

import json

from core.daily_pipeline import run_daily_pipeline
from core.memory import MemoryStore
from core.repository import SQLiteRepository
from core.watchlist import DomainWatchItem, GitHubWatchItem, PaperWatchItem
from connectors.domain import DomainSignalSnapshot
from connectors.papers import PaperSnapshot


class FakeNotionClient:
    def __init__(self) -> None:
        self.records = []
        self.paper_records = []
        self.repo_records = []
        self.ecosystem_records = []

    def create_brief_record(self, database_id, record):
        self.records.append((database_id, record))
        return type("Page", (), {"id": "page-id", "url": "https://notion.so/hermes-daily"})()

    def upsert_paper_record(self, database_id, record):
        self.paper_records.append((database_id, record))
        return type("Page", (), {"id": "paper-page-id", "url": "https://notion.so/paper"})()

    def upsert_github_repo_record(self, database_id, record):
        self.repo_records.append((database_id, record))
        return type("Page", (), {"id": "repo-page-id", "url": "https://notion.so/repo"})()

    def upsert_ecosystem_record(self, database_id, record):
        self.ecosystem_records.append((database_id, record))
        return type("Page", (), {"id": "ecosystem-page-id", "url": "https://notion.so/ecosystem"})()


class FakeTelegramClient:
    def __init__(self) -> None:
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        return type("TelegramResult", (), {"message_id": 42})()


class FailingStructuredNotionClient(FakeNotionClient):
    def upsert_github_repo_record(self, database_id, record):
        raise RuntimeError("repo database unavailable")


class FakeModelRouter:
    def __init__(self) -> None:
        self.calls = []

    def generate(self, prompt, *, tier="fast"):
        self.calls.append((prompt, tier))
        return "Model-written daily executive summary."


class FailingModelRouter:
    def generate(self, prompt, *, tier="fast"):
        raise RuntimeError("model unavailable")


class FakePaperClient:
    def __init__(self) -> None:
        self.calls = []

    def search(self, query, observed_at, max_results):
        self.calls.append((query, observed_at, max_results))
        return [
            PaperSnapshot(
                title="Live Agent Paper",
                url="https://arxiv.org/abs/2607.00002",
                published_at="2026-07-02",
                authors=("A. Researcher",),
                abstract="Agentic retrieval paper.",
                categories=("cs.AI",),
                technologies=("AI agents",),
                repositories=(),
                companies=(),
                observed_at=observed_at,
            )
        ]


class FakeDomainRssClient:
    def __init__(self) -> None:
        self.calls = []

    def fetch(self, item, observed_at):
        self.calls.append((item.domain, item.name, item.rss_url, observed_at))
        return [
            DomainSignalSnapshot(
                domain=item.domain,
                title="NVIDIA inference platform expands for AI agents",
                entity_name=item.name,
                entity_kind="trend",
                source_url="https://example.com/nvidia-inference",
                published_at="2026-07-02",
                summary="GPU inference tooling for agent deployment.",
                evidence="RSS item.",
                impact_score=80,
                confidence="medium",
                tags=("rss",),
                technologies=("Inference", "AI agents"),
                companies=("NVIDIA",),
                repositories=(),
                observed_at=observed_at,
                recommended_action="Read",
            )
        ]


def test_run_daily_pipeline_uses_fixture_without_external_credentials(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_path = fixture_root / "github" / "OpenHands.json"
    fixture_path.parent.mkdir(parents=True)
    fixture_path.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "All-Hands-AI"},
                    "name": "OpenHands",
                    "full_name": "All-Hands-AI/OpenHands",
                    "html_url": "https://github.com/All-Hands-AI/OpenHands",
                    "description": "AI software engineering agent.",
                    "language": "Python",
                    "stargazers_count": 25500,
                    "open_issues_count": 321,
                    "topics": ["ai-agent"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": {
                    "tag_name": "v1.2.0",
                    "html_url": "https://github.com/release",
                    "published_at": "2026-07-02T00:00:00Z",
                },
            }
        ),
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="All-Hands-AI", name="OpenHands", fixture="github/OpenHands.json")],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
            model_router=FailingModelRouter(),  # type: ignore[arg-type]
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "dry-run"
        assert result.proposal_metrics is not None
        assert result.proposal_metrics.proposals_created >= 1
        assert result.brief.brief_type == "daily"
        assert result.brief.notion_status == "dry-run"
        assert result.run.repository_results[0].entity.canonical_name == "All-Hands-AI/OpenHands"
        assert result.run.notification.decisions[0].startswith("Read:")
    finally:
        store.close()


def test_run_daily_pipeline_does_not_send_telegram_without_published_notion(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_path = fixture_root / "github" / "OpenHands.json"
    fixture_path.parent.mkdir(parents=True)
    fixture_path.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "All-Hands-AI"},
                    "name": "OpenHands",
                    "full_name": "All-Hands-AI/OpenHands",
                    "html_url": "https://github.com/All-Hands-AI/OpenHands",
                    "description": "AI software engineering agent.",
                    "language": "Python",
                    "stargazers_count": 25500,
                    "open_issues_count": 321,
                    "topics": ["ai-agent"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": None,
            }
        ),
        encoding="utf-8",
    )
    telegram = FakeTelegramClient()
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="All-Hands-AI", name="OpenHands", fixture="github/OpenHands.json")],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
            telegram_client=telegram,  # type: ignore[arg-type]
            send_telegram=True,
        )

        assert result.notion.status == "dry-run"
        assert result.telegram.status == "skipped"
        assert result.telegram.detail == "Notion status is dry-run; notification not sent."
        assert telegram.notifications == []
    finally:
        store.close()


def test_run_daily_pipeline_publishes_structured_notion_and_sends_telegram_link(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    github_fixture = fixture_root / "github" / "OpenHands.json"
    paper_fixture = fixture_root / "papers" / "paper.json"
    github_fixture.parent.mkdir(parents=True)
    paper_fixture.parent.mkdir(parents=True)
    github_fixture.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "All-Hands-AI"},
                    "name": "OpenHands",
                    "full_name": "All-Hands-AI/OpenHands",
                    "html_url": "https://github.com/All-Hands-AI/OpenHands",
                    "description": "AI software engineering agent.",
                    "language": "Python",
                    "stargazers_count": 25500,
                    "open_issues_count": 321,
                    "topics": ["ai-agent"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": None,
            }
        ),
        encoding="utf-8",
    )
    paper_fixture.write_text(
        json.dumps(
            {
                "title": "Agentic Retrieval for Code Editing",
                "url": "https://arxiv.org/abs/2607.00001",
                "published_at": "2026-07-01",
                "authors": ["A. Researcher"],
                "abstract": "A paper about agentic retrieval for code editing.",
                "categories": ["cs.AI"],
                "technologies": ["AI agents"],
                "repositories": ["All-Hands-AI/OpenHands"],
                "companies": ["Anthropic"],
            }
        ),
        encoding="utf-8",
    )
    notion = FakeNotionClient()
    telegram = FakeTelegramClient()
    model_router = FakeModelRouter()
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="All-Hands-AI", name="OpenHands", fixture="github/OpenHands.json")],
            paper_watchlist=[
                PaperWatchItem(
                    title="Agentic Retrieval for Code Editing",
                    fixture="papers/paper.json",
                    query="all:agentic",
                    max_results=3,
                )
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            notion_papers_database_id="papers-db",
            notion_github_repos_database_id="repos-db",
            telegram_client=telegram,  # type: ignore[arg-type]
            model_router=model_router,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        assert result.notion.status == "published"
        assert result.brief.executive_summary == "Model-written daily executive summary."
        assert model_router.calls[0][1] == "pro"
        assert result.telegram.status == "sent"
        assert result.brief.notion_url == "https://notion.so/hermes-daily"
        assert result.brief.telegram_status == "sent"
        assert notion.records[0][0] == "database-id"
        assert "Prototype" in notion.records[0][1].recommended_actions
        assert notion.repo_records[0][0] == "repos-db"
        assert notion.repo_records[0][1].name == "All-Hands-AI/OpenHands"
        assert notion.paper_records[0][0] == "papers-db"
        assert notion.paper_records[0][1].recommended_action == "Prototype"
        structured = {status.channel: status.status for status in result.structured_notion}
        assert structured["notion:github_repos"] == "published"
        assert structured["notion:papers"] == "published"
        assert structured["notion:ecosystem"] == "skipped"
        assert telegram.notifications[0].notion_url == "https://notion.so/hermes-daily"
    finally:
        store.close()


def test_run_daily_pipeline_enqueues_outbox_when_telegram_requested_but_missing(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    github_fixture = fixture_root / "github" / "OpenHands.json"
    github_fixture.parent.mkdir(parents=True)
    github_fixture.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "All-Hands-AI"},
                    "name": "OpenHands",
                    "full_name": "All-Hands-AI/OpenHands",
                    "html_url": "https://github.com/All-Hands-AI/OpenHands",
                    "description": "AI software engineering agent.",
                    "language": "Python",
                    "stargazers_count": 25500,
                    "open_issues_count": 321,
                    "topics": ["ai-agent"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": None,
            }
        ),
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    notion = FakeNotionClient()
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="All-Hands-AI", name="OpenHands", fixture="github/OpenHands.json")],
            paper_watchlist=[],
            domain_watchlist=[],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            publish_notion=True,
            send_telegram=True,
        )

        pending = store.list_notification_outbox(status="pending")
        assert result.notion.status == "published"
        assert result.telegram.status == "skipped"
        assert len(pending) == 1
        assert pending[0].title == "Intelligence Hub Daily Brief - 2026-07-02"
        assert pending[0].notion_url == "https://notion.so/hermes-daily"
    finally:
        store.close()


def test_run_daily_pipeline_records_structured_notion_failure_without_losing_brief(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    github_fixture = fixture_root / "github" / "OpenHands.json"
    github_fixture.parent.mkdir(parents=True)
    github_fixture.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "All-Hands-AI"},
                    "name": "OpenHands",
                    "full_name": "All-Hands-AI/OpenHands",
                    "html_url": "https://github.com/All-Hands-AI/OpenHands",
                    "description": "AI software engineering agent.",
                    "language": "Python",
                    "stargazers_count": 25500,
                    "open_issues_count": 321,
                    "topics": ["ai-agent"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": None,
            }
        ),
        encoding="utf-8",
    )
    notion = FailingStructuredNotionClient()
    telegram = FakeTelegramClient()
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="All-Hands-AI", name="OpenHands", fixture="github/OpenHands.json")],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
            notion_client=notion,  # type: ignore[arg-type]
            notion_database_id="database-id",
            notion_github_repos_database_id="repos-db",
            telegram_client=telegram,  # type: ignore[arg-type]
            publish_notion=True,
            send_telegram=True,
        )

        structured = {status.channel: status for status in result.structured_notion}
        assert result.notion.status == "published"
        assert result.telegram.status == "sent"
        assert structured["notion:github_repos"].status == "failed"
        assert "repo database unavailable" in structured["notion:github_repos"].detail
        assert result.brief.notion_status == "published"
    finally:
        store.close()


def test_run_daily_pipeline_uses_live_paper_client_when_available(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    paper_client = FakePaperClient()
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[],
            paper_watchlist=[
                PaperWatchItem(title="Agent papers", fixture="", query="all:agent", max_results=2)
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=tmp_path / "fixtures",
            paper_client=paper_client,  # type: ignore[arg-type]
        )

        assert paper_client.calls == [("all:agent", "2026-07-02", 2)]
        assert len(result.run.paper_results) == 1
        assert result.run.paper_results[0].entity.canonical_name == "Live Agent Paper"
    finally:
        store.close()


def test_run_daily_pipeline_includes_domain_signals(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    domain_fixture = fixture_root / "domains" / "cybersecurity.json"
    domain_fixture.parent.mkdir(parents=True)
    domain_fixture.write_text(
        json.dumps(
            {
                "domain": "Cybersecurity Intelligence",
                "title": "Agentic systems need security evaluation",
                "entity_name": "Agentic security evaluation",
                "entity_kind": "technology",
                "source_url": "local://signals/cybersecurity/agentic-security-evaluation",
                "published_at": "2026-07-02",
                "summary": "Agents need security evaluation.",
                "evidence": "Tool permissions expand the attack surface.",
                "impact_score": 88,
                "confidence": "high",
                "technologies": ["AI agents"],
                "recommended_action": "Prototype",
            }
        ),
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[],
            paper_watchlist=[],
            domain_watchlist=[
                DomainWatchItem(
                    domain="Cybersecurity Intelligence",
                    name="Agentic security evaluation",
                    fixture="domains/cybersecurity.json",
                )
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
        )

        assert len(result.run.domain_results) == 1
        assert result.run.notification.top_action == "Prototype"
        assert result.run.notification.decisions[0].startswith("Prototype: [Cybersecurity Intelligence]")
        assert result.brief.domain == "AI Intelligence"
        assert "Agentic security evaluation" in result.brief.executive_summary
        assert "建議行動：Prototype" in result.brief.executive_summary
    finally:
        store.close()


def test_run_daily_pipeline_adds_cross_signal_insights(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    github_fixture = fixture_root / "github" / "agent_repo.json"
    paper_fixture = fixture_root / "papers" / "agent_paper.json"
    domain_fixture = fixture_root / "domains" / "agent_domain.json"
    github_fixture.parent.mkdir(parents=True)
    paper_fixture.parent.mkdir(parents=True)
    domain_fixture.parent.mkdir(parents=True)
    github_fixture.write_text(
        json.dumps(
            {
                "repo": {
                    "owner": {"login": "example"},
                    "name": "agent-framework",
                    "full_name": "example/agent-framework",
                    "html_url": "https://github.com/example/agent-framework",
                    "description": "Agent framework.",
                    "language": "Python",
                    "stargazers_count": 1000,
                    "open_issues_count": 10,
                    "topics": ["ai-agent", "tool-use"],
                    "pushed_at": "2026-07-02T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "default_branch": "main",
                },
                "latest_release": None,
            }
        ),
        encoding="utf-8",
    )
    paper_fixture.write_text(
        json.dumps(
            {
                "title": "Agentic Tool Use for Workflows",
                "url": "https://arxiv.org/abs/2607.02000",
                "published_at": "2026-07-02",
                "authors": ["A. Researcher"],
                "abstract": "A new method for agentic tool use and workflow planning.",
                "categories": ["cs.AI"],
                "technologies": ["AI agents", "Tool use"],
                "repositories": [],
                "companies": [],
            }
        ),
        encoding="utf-8",
    )
    domain_fixture.write_text(
        json.dumps(
            {
                "domain": "AI Intelligence",
                "title": "Agent platforms add tool use workflows",
                "entity_name": "Agent workflow acceleration",
                "entity_kind": "trend",
                "source_url": "local://signals/agents",
                "published_at": "2026-07-02",
                "summary": "Agent workflow tooling is moving into production.",
                "evidence": "Multiple platforms shipped tool use updates.",
                "impact_score": 78,
                "confidence": "medium",
                "technologies": ["AI agents", "Tool use"],
            }
        ),
        encoding="utf-8",
    )

    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="example", name="agent-framework", fixture="github/agent_repo.json")],
            paper_watchlist=[
                PaperWatchItem(title="Agentic Tool Use for Workflows", fixture="papers/agent_paper.json", query="", max_results=1)
            ],
            domain_watchlist=[
                DomainWatchItem(domain="AI Intelligence", name="Agent workflow acceleration", fixture="domains/agent_domain.json")
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
        )

        assert result.run.cross_signal_insights
        assert result.proposal_metrics is not None
        assert result.proposal_metrics.insight_count >= 1
        assert result.proposal_metrics.proposals_accepted >= 1
        assert SQLiteRepository.from_memory_store(store).list_insights()
        assert "跨來源加速" in result.brief.executive_summary
        assert len(result.run.notification.decisions) <= 7

        first_insight_count = len(SQLiteRepository.from_memory_store(store).list_insights())
        run_daily_pipeline(
            store=store,
            watchlist=[GitHubWatchItem(owner="example", name="agent-framework", fixture="github/agent_repo.json")],
            paper_watchlist=[
                PaperWatchItem(title="Agentic Tool Use for Workflows", fixture="papers/agent_paper.json", query="", max_results=1)
            ],
            domain_watchlist=[
                DomainWatchItem(domain="AI Intelligence", name="Agent workflow acceleration", fixture="domains/agent_domain.json")
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
        )
        assert len(SQLiteRepository.from_memory_store(store).list_insights()) == first_insight_count
    finally:
        store.close()


def test_run_daily_pipeline_condenses_duplicate_summary_highlights(tmp_path) -> None:
    fixture_root = tmp_path / "fixtures"
    paper_fixture = fixture_root / "papers" / "rag_anything.json"
    paper_fixture.parent.mkdir(parents=True)
    paper_fixture.write_text(
        json.dumps(
            {
                "title": "RAG-Anything: All-in-One RAG Framework",
                "url": "https://arxiv.org/abs/2607.01000",
                "published_at": "2026-07-02",
                "authors": ["A. Researcher"],
                "abstract": (
                    "RAG-Anything is a unified framework that enhances multimodal knowledge retrieval "
                    "by integrating cross-modal relationships and semantic matching"
                ),
                "categories": ["cs.AI"],
                "technologies": ["RAG", "VLM"],
                "repositories": ["HKUDS/RAG-Anything"],
                "companies": [],
            }
        ),
        encoding="utf-8",
    )
    store = MemoryStore(tmp_path / "memory.sqlite")
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[],
            paper_watchlist=[
                PaperWatchItem(title="RAG-Anything", fixture="papers/rag_anything.json", query="", max_results=1),
                PaperWatchItem(title="RAG-Anything duplicate", fixture="papers/rag_anything.json", query="", max_results=1),
            ],
            domain_watchlist=[],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=fixture_root,
        )

        assert result.brief.executive_summary.count("RAG-Anything") == 2
        assert "on c" not in result.brief.executive_summary
        assert "，is " not in result.brief.executive_summary
        assert "重點是：is " not in result.brief.executive_summary
        assert len([line for line in result.run.notification.decisions if "RAG-Anything" in line]) == 1
    finally:
        store.close()


def test_run_daily_pipeline_uses_domain_rss_client_when_available(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    rss_client = FakeDomainRssClient()
    try:
        result = run_daily_pipeline(
            store=store,
            watchlist=[],
            paper_watchlist=[],
            domain_watchlist=[
                DomainWatchItem(
                    domain="NVIDIA Intelligence",
                    name="Inference platform moat",
                    fixture="",
                    rss_url="https://example.com/feed.xml",
                    max_results=1,
                )
            ],
            run_date="2026-07-02",
            revisit_date="2026-07-09",
            notion_url="local://notion/dry-run",
            fixture_root=tmp_path / "fixtures",
            domain_rss_client=rss_client,  # type: ignore[arg-type]
        )

        assert rss_client.calls == [
            ("NVIDIA Intelligence", "Inference platform moat", "https://example.com/feed.xml", "2026-07-02")
        ]
        assert len(result.run.domain_results) == 1
        assert result.run.notification.decisions[0].startswith("Read: [NVIDIA Intelligence]")
    finally:
        store.close()
