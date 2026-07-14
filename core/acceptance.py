from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from connectors.notion import PublishedPage
from connectors.telegram import TelegramResult
from core.config import Settings
from core.decision_review_pipeline import run_decision_review_pipeline
from core.memory import MemoryStore
from core.orchestrator import run_hermes_orchestration
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


@dataclass(frozen=True)
class AcceptanceStage:
    name: str
    notion_status: str
    telegram_status: str


@dataclass(frozen=True)
class AcceptanceReport:
    ok: bool
    stages: tuple[AcceptanceStage, ...]
    entity_count: int
    observation_count: int
    decision_count: int
    brief_count: int
    run_count: int
    failures: tuple[str, ...]


class FakeNotionPublisher:
    def __init__(self) -> None:
        self.counter = 0
        self.pages: list[tuple[str, str]] = []
        self.records: list[tuple[str, object]] = []

    def create_page(self, title: str, body: str) -> PublishedPage:
        self.pages.append((title, body))
        return self._page(title)

    def create_brief_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "title", "brief")))

    def upsert_paper_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "title", "paper")))

    def upsert_github_repo_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "name", "repo")))

    def upsert_ecosystem_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "name", "ecosystem")))

    def create_radar_snapshot_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "title", "radar")))

    def upsert_radar_entity_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "name", "radar-entity")))

    def upsert_decision_record(self, database_id: str, record: object) -> PublishedPage:
        self.records.append((database_id, record))
        return self._page(str(getattr(record, "title", "decision")))

    def _page(self, title: str) -> PublishedPage:
        self.counter += 1
        slug = "".join(char if char.isalnum() else "-" for char in title.strip().lower()).strip("-") or "page"
        return PublishedPage(id=f"fake-page-{self.counter}", url=f"https://notion.local/{self.counter}-{slug[:80]}")


class FakeTelegramPublisher:
    def __init__(self) -> None:
        self.counter = 0
        self.notifications: list[object] = []

    def send_notification(self, notification: object) -> TelegramResult:
        self.counter += 1
        self.notifications.append(notification)
        return TelegramResult(message_id=self.counter)


def run_acceptance_check(settings: Settings, *, run_date: str = "2026-07-02") -> AcceptanceReport:
    with TemporaryDirectory(prefix="hermes-acceptance-") as temp_dir:
        db_path = Path(temp_dir) / "hermes_acceptance.sqlite"
        store = MemoryStore(db_path)
        notion = FakeNotionPublisher()
        telegram = FakeTelegramPublisher()
        try:
            orchestration = run_hermes_orchestration(
                store=store,
                run_date=run_date,
                github_watchlist=load_github_watchlist(settings.github_watchlist_file),
                paper_watchlist=load_paper_watchlist(settings.paper_watchlist_file),
                domain_watchlist=load_domain_watchlist(settings.domain_watchlist_file),
                fixture_root=settings.fixture_root,
                notion_url="local://notion/acceptance",
                notion_client=notion,  # type: ignore[arg-type]
                notion_database_id="acceptance-briefs-db",
                notion_papers_database_id="acceptance-papers-db",
                notion_github_repos_database_id="acceptance-github-db",
                notion_ecosystem_database_id="acceptance-ecosystem-db",
                notion_decisions_database_id="acceptance-decisions-db",
                notion_radar_database_id="acceptance-radar-db",
                notion_radar_entities_database_id="acceptance-radar-entities-db",
                telegram_client=telegram,  # type: ignore[arg-type]
                publish_notion=True,
                send_telegram=True,
                run_weekly=True,
                run_monthly=True,
                run_dashboard=True,
                run_radar=True,
            )
            decision_review = run_decision_review_pipeline(
                store=store,
                as_of="2026-07-09",
                since=run_date,
                notion_url="local://notion/acceptance-decision-review",
                notion_client=notion,  # type: ignore[arg-type]
                notion_database_id="acceptance-briefs-db",
                telegram_client=telegram,  # type: ignore[arg-type]
                publish_notion=True,
                send_telegram=True,
            )
            stages = (
                AcceptanceStage("daily", orchestration.daily.notion.status, orchestration.daily.telegram.status),
                AcceptanceStage("weekly", _status(orchestration.weekly, "notion"), _status(orchestration.weekly, "telegram")),
                AcceptanceStage("monthly", _status(orchestration.monthly, "notion"), _status(orchestration.monthly, "telegram")),
                AcceptanceStage("dashboard", _status(orchestration.dashboard, "notion"), _status(orchestration.dashboard, "telegram")),
                AcceptanceStage("radar", _status(orchestration.radar, "notion"), _status(orchestration.radar, "telegram")),
                AcceptanceStage("decision_review", decision_review.notion.status, decision_review.telegram.status),
            )
            failures = _failures(store, stages)
            return AcceptanceReport(
                ok=not failures,
                stages=stages,
                entity_count=len(store.list_entities()),
                observation_count=len(store.list_observations()),
                decision_count=len(store.list_decisions()),
                brief_count=len(store.list_briefs()),
                run_count=len(store.list_runs()),
                failures=tuple(failures),
            )
        finally:
            store.close()


def render_acceptance_report(report: AcceptanceReport) -> str:
    lines = ["# Hermes Acceptance Check", ""]
    lines.append(f"Result: {'passed' if report.ok else 'failed'}")
    lines.append(
        f"Memory: {report.entity_count} entities, {report.observation_count} observations, "
        f"{report.decision_count} decisions, {report.brief_count} briefs, {report.run_count} runs"
    )
    lines.append("")
    lines.append("## Stages")
    for stage in report.stages:
        lines.append(f"- {stage.name}: Notion={stage.notion_status} Telegram={stage.telegram_status}")
    lines.append("")
    lines.append("## Failures")
    if report.failures:
        lines.extend(f"- {failure}" for failure in report.failures)
    else:
        lines.append("- None.")
    return "\n".join(lines)


def _status(result: object | None, channel: str) -> str:
    if result is None:
        return "missing"
    delivery = getattr(result, channel)
    return str(delivery.status)


def _failures(store: MemoryStore, stages: tuple[AcceptanceStage, ...]) -> list[str]:
    failures: list[str] = []
    for stage in stages:
        if stage.notion_status != "published":
            failures.append(f"{stage.name} Notion status is {stage.notion_status}, expected published.")
        if stage.telegram_status != "sent":
            failures.append(f"{stage.name} Telegram status is {stage.telegram_status}, expected sent.")
    if not store.list_entities():
        failures.append("No entities were written to memory.")
    if not store.list_observations():
        failures.append("No observations were written to memory.")
    if not store.list_decisions():
        failures.append("No decisions were written to memory.")
    for brief_type in ("daily", "weekly", "monthly", "dashboard", "radar", "decision_review"):
        if not store.list_briefs(brief_type=brief_type):
            failures.append(f"No {brief_type} brief was written to memory.")
        if not store.list_runs(stage=brief_type):
            failures.append(f"No {brief_type} run was written to memory.")
    return failures
