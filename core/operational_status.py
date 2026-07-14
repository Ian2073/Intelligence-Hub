from __future__ import annotations

from dataclasses import dataclass

from core.config import Settings
from core.memory import BriefRecord, MemoryStore, RunRecord
from core.memory_engine import MemoryEngine
from core.proposal_store import SQLiteProposalStore
from core.proposals import ProposalMetrics


BRIEF_TYPES: tuple[str, ...] = ("daily", "weekly", "monthly", "dashboard", "radar", "decision_review")


@dataclass(frozen=True)
class CredentialGap:
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class LatestBriefStatus:
    brief_type: str
    title: str
    period_start: str
    period_end: str
    notion_status: str
    notion_url: str
    telegram_status: str
    telegram_detail: str
    source: str


@dataclass(frozen=True)
class HermesOperationalStatus:
    go_live_ready: bool
    credential_gaps: tuple[CredentialGap, ...]
    latest_briefs: tuple[LatestBriefStatus, ...]
    entity_count: int
    observation_count: int
    decision_count: int
    pending_notification_count: int
    next_commands: tuple[str, ...]
    db_size_bytes: int = 0
    schema_version: str = "1"
    synthesis_policy: str = "hybrid"
    pro_call_limit: int = 8
    synthesis_metadata_count: int = 0
    proposal_metrics: ProposalMetrics | None = None


@dataclass(frozen=True)
class HealthMetrics:
    pipeline_runs: int
    failed_runs: int
    pending_notifications: int
    table_counts: dict[str, int]


def get_health_metrics(
    store: MemoryStore,
    *,
    since: str | None = None,
    until: str | None = None,
) -> HealthMetrics:
    runs = store.list_runs(since=since, until=until)
    return HealthMetrics(
        pipeline_runs=len(runs),
        failed_runs=sum(1 for run in runs if run.status == "failed"),
        pending_notifications=len(store.list_notification_outbox(status="pending")),
        table_counts=store.get_table_stats(),
    )


def render_health_metrics(metrics: HealthMetrics) -> tuple[str, ...]:
    return (
        f"Pipeline runs: {metrics.pipeline_runs} total, {metrics.failed_runs} failed.",
        f"Pending Telegram notifications: {metrics.pending_notifications}.",
        "Memory tables: "
        + ", ".join(f"{name}={count}" for name, count in metrics.table_counts.items()),
    )


def build_operational_status(
    settings: Settings,
    store: MemoryStore,
    *,
    as_of: str | None = None,
    include_future: bool = False,
) -> HermesOperationalStatus:
    gaps = _credential_gaps(settings)
    memory_engine = MemoryEngine(store)
    memory_stats = memory_engine.stats()
    synthesis_metadata_count = _synthesis_metadata_count(store)
    proposal_metrics = SQLiteProposalStore.from_memory_store(store).latest_metrics()
    latest_briefs = tuple(_latest_status(store, brief_type, as_of=as_of, include_future=include_future) for brief_type in BRIEF_TYPES)
    latest_briefs = tuple(status for status in latest_briefs if status is not None)
    return HermesOperationalStatus(
        go_live_ready=not gaps,
        credential_gaps=tuple(gaps),
        latest_briefs=latest_briefs,
        entity_count=len(store.list_entities()),
        observation_count=len(store.list_observations()),
        decision_count=len(store.list_decisions()),
        pending_notification_count=len(store.list_notification_outbox(status="pending")),
        db_size_bytes=memory_stats.db_size_bytes,
        schema_version=memory_stats.schema_version,
        synthesis_policy=settings.synthesis_mode,
        pro_call_limit=settings.pro_call_limit,
        synthesis_metadata_count=synthesis_metadata_count,
        proposal_metrics=proposal_metrics,
        next_commands=_next_commands(gaps),
    )


def render_operational_status(status: HermesOperationalStatus) -> str:
    lines = ["# Hermes Operational Status", ""]
    readiness = "ready" if status.go_live_ready else "not ready"
    lines.append(f"Go-live: {readiness}")
    lines.append(
        f"Memory: {status.entity_count} entities, {status.observation_count} observations, "
        f"{status.decision_count} decisions, {status.pending_notification_count} pending notifications"
    )
    lines.append(
        f"Memory DB: {status.db_size_bytes} bytes, schema v{status.schema_version}, "
        f"synthesis metadata records={status.synthesis_metadata_count}"
    )
    lines.append(f"Synthesis policy: mode={status.synthesis_policy}, pro_call_limit={status.pro_call_limit}")
    if status.proposal_metrics is not None:
        metrics = status.proposal_metrics
        lines.append(
            "Proposal metrics: "
            f"created={metrics.proposals_created}, accepted={metrics.proposals_accepted}, "
            f"rejected={metrics.proposals_rejected}, needs_review={metrics.proposals_needing_review}, "
            f"canonical_created={metrics.canonical_records_created}, "
            f"canonical_updated={metrics.canonical_records_updated}, insights={metrics.insight_count}"
        )
    lines.append("")
    lines.append("## Latest Briefs")
    if not status.latest_briefs:
        lines.append("- No briefs recorded yet.")
    else:
        for brief in status.latest_briefs:
            url = brief.notion_url or "(no Notion URL)"
            lines.append(
                f"- {brief.brief_type}: {brief.title} ({brief.period_start} to {brief.period_end}) "
                f"Notion={brief.notion_status} Telegram={brief.telegram_status} URL={url} source={brief.source}"
            )

    lines.append("")
    lines.append("## Go-Live Gaps")
    if not status.credential_gaps:
        lines.append("- None.")
    else:
        for gap in status.credential_gaps:
            aliases = f" aliases: {', '.join(gap.aliases)}" if gap.aliases else ""
            lines.append(f"- {gap.name}{aliases}")

    lines.append("")
    lines.append("## Next Commands")
    for command in status.next_commands:
        lines.append(f"- `{command}`")
    return "\n".join(lines)


def _credential_gaps(settings: Settings) -> list[CredentialGap]:
    gaps: list[CredentialGap] = []
    if not settings.github_token:
        gaps.append(CredentialGap("GITHUB_TOKEN", ("GH_TOKEN",)))
    if not settings.telegram_bot_token:
        gaps.append(CredentialGap("TELEGRAM_BOT_TOKEN", ("TELEGRAM_TOKEN", "TG_BOT_TOKEN")))
    if not settings.telegram_chat_id:
        gaps.append(CredentialGap("TELEGRAM_CHAT_ID", ("TG_CHAT_ID",)))
    return gaps


def _latest_status(
    store: MemoryStore,
    brief_type: str,
    *,
    as_of: str | None,
    include_future: bool,
) -> LatestBriefStatus | None:
    candidates: list[LatestBriefStatus] = []
    run = _latest_run(store, brief_type, as_of=as_of, include_future=include_future, published_only=True)
    if run is not None:
        candidates.append(_run_status(brief_type, run))
    brief = _latest_brief(store, brief_type, as_of=as_of, include_future=include_future, published_only=True)
    if brief is not None:
        candidates.append(_brief_status(brief_type, brief))
    if candidates:
        return max(candidates, key=_status_sort_key)

    run = _latest_run(store, brief_type, as_of=as_of, include_future=include_future, published_only=False)
    if run is not None:
        return _run_status(brief_type, run)
    brief = _latest_brief(store, brief_type, as_of=as_of, include_future=include_future, published_only=False)
    if brief is not None:
        return _brief_status(brief_type, brief)
    return None


def _latest_run(
    store: MemoryStore,
    stage: str,
    *,
    as_of: str | None,
    include_future: bool,
    published_only: bool,
) -> RunRecord | None:
    runs = store.list_runs(stage=stage)
    if as_of and not include_future:
        runs = [run for run in runs if run.run_date <= as_of]
    if published_only:
        runs = [run for run in runs if run.notion_status == "published"]
    if not runs:
        return None
    return max(runs, key=lambda run: (run.created_at, run.id))


def _latest_brief(
    store: MemoryStore,
    brief_type: str,
    *,
    as_of: str | None,
    include_future: bool,
    published_only: bool,
) -> BriefRecord | None:
    briefs = store.list_briefs(brief_type=brief_type)
    if as_of and not include_future:
        briefs = [brief for brief in briefs if brief.period_start <= as_of]
    if not briefs:
        return None
    if published_only:
        briefs = [brief for brief in briefs if brief.notion_status == "published"]
    if not briefs:
        return None
    return max(
        briefs,
        key=lambda brief: (
            brief.period_end,
            brief.period_start,
            1 if brief.telegram_status == "sent" else 0,
        ),
    )


def _status_sort_key(status: LatestBriefStatus) -> tuple[int, str, str]:
    return (1 if status.source == "run" else 0, status.period_end, status.period_start)


def _brief_status(brief_type: str, brief: BriefRecord) -> LatestBriefStatus:
    return LatestBriefStatus(
        brief_type=brief_type,
        title=brief.title,
        period_start=brief.period_start,
        period_end=brief.period_end,
        notion_status=brief.notion_status,
        notion_url=brief.notion_url,
        telegram_status=brief.telegram_status,
        telegram_detail=brief.telegram_detail,
        source="brief",
    )


def _run_status(brief_type: str, run: RunRecord) -> LatestBriefStatus:
    return LatestBriefStatus(
        brief_type=brief_type,
        title=run.title,
        period_start=run.period_start,
        period_end=run.period_end,
        notion_status=run.notion_status,
        notion_url=run.notion_url,
        telegram_status=run.telegram_status,
        telegram_detail=run.telegram_detail,
        source="run",
    )


def _next_commands(gaps: list[CredentialGap]) -> tuple[str, ...]:
    commands = []
    gap_names = {gap.name for gap in gaps}
    if "GITHUB_TOKEN" in gap_names:
        commands.append(".\\hub_env\\Scripts\\python.exe scripts\\github_check.py")
    if "TELEGRAM_BOT_TOKEN" in gap_names or "TELEGRAM_CHAT_ID" in gap_names:
        commands.append(".\\hub_env\\Scripts\\python.exe scripts\\telegram_check.py")
    commands.append(".\\hub_env\\Scripts\\python.exe scripts\\go_live_check.py")
    commands.append(
        ".\\scripts\\install_scheduled_tasks.ps1 -DryRun -LiveGitHub -LivePapersWithCode -LiveDomainRss "
        "-PublishNotion -SendTelegram -ModelSynthesis -IncludeWeekly -IncludeMonthly -IncludeDashboard "
        "-IncludeRadar -IncludeDecisionReview"
    )
    return tuple(commands)


def _synthesis_metadata_count(store: MemoryStore) -> int:
    row = store._connection.execute("SELECT COUNT(*) AS count FROM synthesis_metadata").fetchone()
    return int(row["count"]) if row is not None else 0
