from __future__ import annotations

import json

from connectors.github import GitHubRepoSnapshot
from connectors.domain import DomainSignalSnapshot
from connectors.notion import PublishedPage
from connectors.papers import PaperSnapshot
from connectors.telegram import TelegramBotInfo
from core.config import Settings
from core.doctor import run_doctor, run_go_live_check


def _settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "project_root": tmp_path,
        "model_provider": "ollama",
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:14b",
        "cloud_base_url": "https://api.example.com/v1",
        "cloud_api_key": None,
        "cloud_fast_model": "cheap-fast",
        "cloud_pro_model": "strong-pro",
        "cloud_timeout_seconds": 60.0,
        "research_topic": "AI agents",
        "source_file": tmp_path / "data" / "sources" / "ai_research_items.json",
        "memory_db": tmp_path / "data" / "hermes_memory.sqlite",
        "github_watchlist_file": tmp_path / "data" / "watchlists" / "github_repos.json",
        "paper_watchlist_file": tmp_path / "data" / "watchlists" / "papers.json",
        "domain_watchlist_file": tmp_path / "data" / "watchlists" / "domain_signals.json",
        "fixture_root": tmp_path / "data" / "fixtures",
        "github_token": None,
        "notion_token": None,
        "notion_parent_page_id": None,
        "notion_daily_briefs_database_id": None,
        "notion_papers_database_id": None,
        "notion_github_repos_database_id": None,
        "notion_ecosystem_database_id": None,
        "notion_decisions_database_id": None,
        "notion_radar_snapshots_database_id": None,
        "notion_radar_entities_database_id": None,
        "telegram_bot_token": None,
        "telegram_chat_id": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _write_minimal_files(tmp_path) -> None:
    (tmp_path / "data" / "sources").mkdir(parents=True)
    (tmp_path / "data" / "watchlists").mkdir(parents=True)
    (tmp_path / "data" / "fixtures" / "github").mkdir(parents=True)
    (tmp_path / "data" / "fixtures" / "papers").mkdir(parents=True)
    (tmp_path / "data" / "fixtures" / "domains").mkdir(parents=True)
    (tmp_path / "data" / "sources" / "ai_research_items.json").write_text("[]", encoding="utf-8")
    (tmp_path / "data" / "watchlists" / "github_repos.json").write_text(
        json.dumps([{"repo": "All-Hands-AI/OpenHands", "fixture": "github/OpenHands.json"}]),
        encoding="utf-8",
    )
    (tmp_path / "data" / "watchlists" / "papers.json").write_text(
        json.dumps([{"title": "Agent papers", "fixture": "papers/paper.json", "query": "all:agent"}]),
        encoding="utf-8",
    )
    (tmp_path / "data" / "watchlists" / "domain_signals.json").write_text(
        json.dumps(
            [
                {
                    "domain": "Startup Intelligence",
                    "name": "AI tools",
                    "fixture": "domains/signal.json",
                    "rss_url": "https://example.com/feed.xml",
                    "max_results": 1,
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "data" / "fixtures" / "github" / "OpenHands.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "fixtures" / "papers" / "paper.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "fixtures" / "domains" / "signal.json").write_text("{}", encoding="utf-8")


def test_doctor_dry_run_allows_missing_external_credentials(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    report = run_doctor(_settings(tmp_path))

    assert report.ok is True
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["model_provider"] == "ok"
    assert statuses["github_token"] == "skipped"
    assert statuses["notion_token"] == "skipped"
    assert statuses["telegram_bot_token"] == "skipped"
    assert statuses["live_checks"] == "skipped"


def test_doctor_demo_profile_checks_only_demo_readiness(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    report = run_doctor(_settings(tmp_path, model_provider="cloud"), profile="demo")

    assert report.ok is True
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["profile"] == "ok"
    assert statuses["project_root"] == "ok"
    assert statuses["fixture_root"] == "ok"
    assert statuses["github_watchlist"] == "ok"
    assert statuses["paper_watchlist"] == "ok"
    assert statuses["domain_watchlist"] == "ok"
    assert statuses["github_token"] == "skipped"
    assert statuses["notion_token"] == "skipped"
    assert statuses["telegram_bot_token"] == "skipped"
    assert "cloud_api_key" not in statuses


def test_go_live_check_requires_production_configuration(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    report = run_go_live_check(_settings(tmp_path))

    assert report.ok is False
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["github_token"] == "skipped"
    assert statuses["go_live_model_provider"] == "failed"
    assert statuses["go_live_cloud_api_key"] == "failed"
    assert statuses["go_live_github_token"] == "failed"
    assert statuses["go_live_notion_daily_briefs_database_id"] == "failed"
    assert statuses["go_live_telegram_chat_id"] == "failed"
    assert statuses["go_live_schedule_plan"] == "ok"


def test_go_live_check_requires_distinct_fast_and_pro_cloud_models(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    report = run_go_live_check(
        _settings(
            tmp_path,
            model_provider="cloud",
            cloud_api_key="cloud-key",
            cloud_fast_model="same-model",
            cloud_pro_model="same-model",
            github_token="gh-token",
            notion_token="notion-token",
            notion_parent_page_id="parent-page-id",
            notion_daily_briefs_database_id="briefs-id",
            notion_papers_database_id="papers-id",
            notion_github_repos_database_id="repos-id",
            notion_ecosystem_database_id="ecosystem-id",
            notion_decisions_database_id="decisions-id",
            notion_radar_snapshots_database_id="radar-id",
            notion_radar_entities_database_id="radar-entities-id",
            telegram_bot_token="tg-token",
            telegram_chat_id="chat-id",
        )
    )

    statuses = {check.name: check.status for check in report.checks}
    assert report.ok is False
    assert statuses["go_live_model_tier_split"] == "failed"


def test_doctor_reports_missing_fixture_as_failure(tmp_path) -> None:
    _write_minimal_files(tmp_path)
    (tmp_path / "data" / "fixtures" / "github" / "OpenHands.json").unlink()

    report = run_doctor(_settings(tmp_path))

    assert report.ok is False
    assert any(check.name == "github_fixture" and check.status == "failed" for check in report.checks)


def test_doctor_live_checks_use_clients_without_writes(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    class FakeGitHubClient:
        def fetch_repository(self, owner, name, observed_at):
            return GitHubRepoSnapshot(
                owner=owner,
                name=name,
                full_name=f"{owner}/{name}",
                url="https://github.com/All-Hands-AI/OpenHands",
                description="AI agent",
                language="Python",
                stars=1,
                open_issues=0,
                topics=(),
                pushed_at="2026-07-01T00:00:00Z",
                updated_at="2026-07-01T00:00:00Z",
                default_branch="main",
                observed_at=observed_at,
                latest_release="",
                latest_release_url="",
                latest_release_published_at="",
                latest_pull_request="",
                latest_pull_request_url="",
                latest_pull_request_updated_at="",
                latest_issue="",
                latest_issue_url="",
                latest_issue_updated_at="",
                contributor_count=0,
            )

    class FakePaperClient:
        def search(self, query, observed_at, max_results):
            return [
                PaperSnapshot(
                    title="Agent paper",
                    url="https://arxiv.org/abs/2607.00001",
                    published_at="2026-07-01",
                    authors=("A. Researcher",),
                    abstract="Agent paper.",
                    categories=("cs.AI",),
                    technologies=("AI agents",),
                    repositories=(),
                    companies=(),
                    observed_at=observed_at,
                )
            ]

    class FakeNotionClient:
        def retrieve_page(self):
            return PublishedPage(id="page-id", url="https://notion.so/page-id")

        def retrieve_database(self, database_id):
            return PublishedPage(id=database_id, url="https://notion.so/database-id")

    class FakeTelegramClient:
        def get_me(self):
            return TelegramBotInfo(id=123, username="hermes_bot")

    class FakeDomainRssClient:
        def fetch(self, item, observed_at):
            return [
                DomainSignalSnapshot(
                    domain=item.domain,
                    title="AI tools RSS item",
                    entity_name=item.name,
                    entity_kind="trend",
                    source_url=item.rss_url,
                    published_at="2026-07-01",
                    summary="RSS summary.",
                    evidence="RSS evidence.",
                    impact_score=70,
                    confidence="medium",
                    tags=("rss",),
                    technologies=("AI agents",),
                    companies=(),
                    repositories=(),
                    observed_at=observed_at,
                    recommended_action="Watch",
                )
            ]

    class FakePapersWithCodeClient:
        def search(self, query, observed_at, max_results):
            return [
                PaperSnapshot(
                    title="Agent paper with code",
                    url="https://paperswithcode.com/paper/agent-paper",
                    published_at="2026-07-01",
                    authors=("A. Researcher",),
                    abstract="Agent paper with code.",
                    categories=("Code Editing",),
                    technologies=("AI agents",),
                    repositories=("All-Hands-AI/OpenHands",),
                    companies=(),
                    observed_at=observed_at,
                )
            ]

    class FakeModelRouter:
        def generate(self, prompt, *, tier="fast"):
            return "ok"

    report = run_doctor(
        _settings(
            tmp_path,
            github_token="gh-token",
            notion_token="notion-token",
            notion_parent_page_id="parent-page-id",
            notion_daily_briefs_database_id="database-id",
            notion_papers_database_id="papers-id",
            notion_github_repos_database_id="repos-id",
            notion_ecosystem_database_id="ecosystem-id",
            notion_decisions_database_id="decisions-id",
            notion_radar_snapshots_database_id="radar-id",
            notion_radar_entities_database_id="radar-entities-id",
        telegram_bot_token="tg-token",
        telegram_chat_id="chat-id",
        ),
        live=True,
        github_client=FakeGitHubClient(),  # type: ignore[arg-type]
        paper_client=FakePaperClient(),  # type: ignore[arg-type]
        papers_with_code_client=FakePapersWithCodeClient(),  # type: ignore[arg-type]
        domain_rss_client=FakeDomainRssClient(),  # type: ignore[arg-type]
        notion_client=FakeNotionClient(),  # type: ignore[arg-type]
        telegram_client=FakeTelegramClient(),  # type: ignore[arg-type]
        model_router=FakeModelRouter(),  # type: ignore[arg-type]
    )

    assert report.ok is True
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["live_github"] == "ok"
    assert statuses["live_arxiv"] == "ok"
    assert statuses["live_papers_with_code"] == "ok"
    assert statuses["live_domain_rss"] == "ok"
    assert statuses["live_cloud_model"] == "skipped"
    assert statuses["live_notion_parent"] == "ok"
    assert statuses["live_notion_briefs_database"] == "ok"
    assert statuses["live_notion_papers_database"] == "ok"
    assert statuses["live_notion_github_repos_database"] == "ok"
    assert statuses["live_notion_ecosystem_database"] == "ok"
    assert statuses["live_notion_decisions_database"] == "ok"
    assert statuses["live_notion_radar_database"] == "ok"
    assert statuses["live_notion_radar_entities_database"] == "ok"
    assert statuses["live_telegram"] == "ok"


def test_go_live_check_passes_with_required_config_and_live_clients(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    class FakeGitHubClient:
        def fetch_repository(self, owner, name, observed_at):
            return GitHubRepoSnapshot(
                owner=owner,
                name=name,
                full_name=f"{owner}/{name}",
                url="https://github.com/All-Hands-AI/OpenHands",
                description="AI agent",
                language="Python",
                stars=1,
                open_issues=0,
                topics=(),
                pushed_at="2026-07-01T00:00:00Z",
                updated_at="2026-07-01T00:00:00Z",
                default_branch="main",
                observed_at=observed_at,
                latest_release="",
                latest_release_url="",
                latest_release_published_at="",
                latest_pull_request="",
                latest_pull_request_url="",
                latest_pull_request_updated_at="",
                latest_issue="",
                latest_issue_url="",
                latest_issue_updated_at="",
                contributor_count=0,
            )

    class FakePaperClient:
        def search(self, query, observed_at, max_results):
            return [
                PaperSnapshot(
                    title="Agent paper",
                    url="https://arxiv.org/abs/2607.00001",
                    published_at="2026-07-01",
                    authors=("A. Researcher",),
                    abstract="Agent paper.",
                    categories=("cs.AI",),
                    technologies=("AI agents",),
                    repositories=(),
                    companies=(),
                    observed_at=observed_at,
                )
            ]

    class FakePapersWithCodeClient(FakePaperClient):
        pass

    class FakeDomainRssClient:
        def fetch(self, item, observed_at):
            return [
                DomainSignalSnapshot(
                    domain=item.domain,
                    title="AI tools RSS item",
                    entity_name=item.name,
                    entity_kind="trend",
                    source_url=item.rss_url,
                    published_at="2026-07-01",
                    summary="RSS summary.",
                    evidence="RSS evidence.",
                    impact_score=70,
                    confidence="medium",
                    tags=("rss",),
                    technologies=("AI agents",),
                    companies=(),
                    repositories=(),
                    observed_at=observed_at,
                    recommended_action="Watch",
                )
            ]

    class FakeNotionClient:
        def retrieve_page(self):
            return PublishedPage(id="page-id", url="https://notion.so/page-id")

        def retrieve_database(self, database_id):
            return PublishedPage(id=database_id, url="https://notion.so/database-id")

    class FakeTelegramClient:
        def get_me(self):
            return TelegramBotInfo(id=123, username="hermes_bot")

    class FakeModelRouter:
        def generate(self, prompt, *, tier="fast"):
            return "ok"

    report = run_go_live_check(
        _settings(
            tmp_path,
            model_provider="cloud",
            cloud_api_key="cloud-key",
            cloud_fast_model="cheap-fast",
            cloud_pro_model="strong-pro",
            github_token="gh-token",
            notion_token="notion-token",
            notion_parent_page_id="parent-page-id",
            notion_daily_briefs_database_id="briefs-id",
            notion_papers_database_id="papers-id",
            notion_github_repos_database_id="repos-id",
            notion_ecosystem_database_id="ecosystem-id",
            notion_decisions_database_id="decisions-id",
            notion_radar_snapshots_database_id="radar-id",
            notion_radar_entities_database_id="radar-entities-id",
            telegram_bot_token="tg-token",
            telegram_chat_id="chat-id",
        ),
        live=True,
        github_client=FakeGitHubClient(),  # type: ignore[arg-type]
        paper_client=FakePaperClient(),  # type: ignore[arg-type]
        papers_with_code_client=FakePapersWithCodeClient(),  # type: ignore[arg-type]
        domain_rss_client=FakeDomainRssClient(),  # type: ignore[arg-type]
        notion_client=FakeNotionClient(),  # type: ignore[arg-type]
        telegram_client=FakeTelegramClient(),  # type: ignore[arg-type]
        model_router=FakeModelRouter(),  # type: ignore[arg-type]
    )

    assert report.ok is True
    statuses = {check.name: check.status for check in report.checks}
    assert statuses["go_live_model_provider"] == "ok"
    assert statuses["go_live_cloud_api_key"] == "ok"
    assert statuses["go_live_model_tier_split"] == "ok"
    assert statuses["go_live_schedule_plan"] == "ok"
    assert statuses["live_cloud_model"] == "ok"


def test_doctor_live_check_failure_marks_report_failed(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    class FailingGitHubClient:
        def fetch_repository(self, owner, name, observed_at):
            raise RuntimeError("bad token")

    report = run_doctor(
        _settings(tmp_path, github_token="gh-token"),
        live=True,
        github_client=FailingGitHubClient(),  # type: ignore[arg-type]
    )

    assert report.ok is False
    assert any(check.name == "live_github" and check.status == "failed" for check in report.checks)


def test_doctor_live_github_can_use_public_unauthenticated_access(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    class FakeGitHubClient:
        def fetch_repository(self, owner, name, observed_at):
            return GitHubRepoSnapshot(
                owner=owner,
                name=name,
                full_name=f"{owner}/{name}",
                url="https://github.com/All-Hands-AI/OpenHands",
                description="AI agent",
                language="Python",
                stars=1,
                open_issues=0,
                topics=(),
                pushed_at="2026-07-01T00:00:00Z",
                updated_at="2026-07-01T00:00:00Z",
                default_branch="main",
                observed_at=observed_at,
                latest_release="",
                latest_release_url="",
                latest_release_published_at="",
                latest_pull_request="",
                latest_pull_request_url="",
                latest_pull_request_updated_at="",
                latest_issue="",
                latest_issue_url="",
                latest_issue_updated_at="",
                contributor_count=0,
            )

    report = run_doctor(
        _settings(tmp_path, github_token=None),
        live=True,
        github_client=FakeGitHubClient(),  # type: ignore[arg-type]
    )

    live_github = next(check for check in report.checks if check.name == "live_github")
    assert live_github.status == "ok"
    assert "unauthenticated" in live_github.detail


def test_doctor_live_checks_cloud_model_when_cloud_provider_selected(tmp_path) -> None:
    _write_minimal_files(tmp_path)

    class FakeModelRouter:
        def __init__(self) -> None:
            self.calls = []

        def generate(self, prompt, *, tier="fast"):
            self.calls.append((prompt, tier))
            return "ok"

    router = FakeModelRouter()

    report = run_doctor(
        _settings(
            tmp_path,
            model_provider="cloud",
            cloud_api_key="cloud-key",
            cloud_fast_model="cheap-fast",
            cloud_pro_model="strong-pro",
        ),
        live=True,
        model_router=router,  # type: ignore[arg-type]
    )

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["cloud_api_key"] == "ok"
    assert statuses["live_cloud_model"] == "ok"
    assert router.calls == [("Return exactly: ok", "fast")]
