from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from connectors.domain import DomainSignalSnapshot, parse_domain_signal_snapshot
from connectors.domain_rss import DomainRssClient
from connectors.github import GitHubClient, GitHubRepoSnapshot, parse_repository_snapshot
from connectors.notion import (
    NotionBriefRecord,
    NotionClient,
    NotionEcosystemRecord,
    NotionGitHubRepoRecord,
    NotionPaperRecord,
)
from connectors.obsidian import ObsidianClient
from connectors.papers import ArxivClient, PaperSnapshot, PapersWithCodeClient, parse_paper_snapshot
from connectors.telegram import TelegramClient, TelegramResult
from core.delivery import DeliveryStatus, failed_delivery, telegram_blocked_by_notion
from core.decision_engine import ACTION_RANK
from core.intelligence_brief import IntelligenceBrief, SynthesisMetadata
from core.intelligence_engine import IntelligenceBuildInput, IntelligenceEngine
from core.insight_engine import CanonicalInsightEngine
from core.memory import BriefRecord, MemoryStore
from core.memory_engine import MemoryEngine
from core.notification_outbox import enqueue_unsent_telegram_notification
from core.obsidian_publisher import ObsidianPublisher
from core.obsidian_read_model import ObsidianReadModelBuilder
from core.obsidian_renderer import ObsidianRenderer
from core.proposal_service import ProposalTrustService
from core.proposal_store import SQLiteProposalStore
from core.proposals import ProposalMetrics
from core.repository import SQLiteRepository
from core.intelligence_synthesis import TieredGenerator, synthesize_daily_summary
from core.knowledge_loader import load_knowledge_context
from core.watchlist import DomainWatchItem, GitHubWatchItem, PaperWatchItem
from workflows.daily_intelligence import DailyIntelligenceRun, run_daily_intelligence


@dataclass(frozen=True)
class DailyPipelineResult:
    run: DailyIntelligenceRun
    brief: BriefRecord
    intelligence_brief: IntelligenceBrief
    notion: DeliveryStatus
    telegram: DeliveryStatus
    structured_notion: tuple[DeliveryStatus, ...] = ()
    obsidian: DeliveryStatus | None = None
    proposal_metrics: ProposalMetrics | None = None


_log = logging.getLogger(__name__)


def run_daily_pipeline(
    *,
    store: MemoryStore,
    watchlist: list[GitHubWatchItem],
    paper_watchlist: list[PaperWatchItem] | None = None,
    domain_watchlist: list[DomainWatchItem] | None = None,
    run_date: str,
    revisit_date: str,
    notion_url: str,
    fixture_root: Path | None = None,
    github_client: GitHubClient | None = None,
    paper_client: ArxivClient | PapersWithCodeClient | None = None,
    domain_rss_client: DomainRssClient | None = None,
    github_trending_client=None,
    notion_client: NotionClient | None = None,
    notion_database_id: str | None = None,
    notion_papers_database_id: str | None = None,
    notion_github_repos_database_id: str | None = None,
    notion_ecosystem_database_id: str | None = None,
    telegram_client: TelegramClient | None = None,
    model_router: TieredGenerator | None = None,
    publish_notion: bool = False,
    send_telegram: bool = False,
    obsidian_client: ObsidianClient | None = None,
    publish_obsidian: bool = False,
) -> DailyPipelineResult:
    snapshots = _fetch_all_snapshots(
        watchlist, run_date=run_date, fixture_root=fixture_root, github_client=github_client,
    )
    paper_snapshots = _fetch_all_paper_snapshots(
        paper_watchlist or [], run_date=run_date, fixture_root=fixture_root, paper_client=paper_client,
    )
    domain_snapshots = _fetch_all_domain_snapshots(
        domain_watchlist or [], run_date=run_date, fixture_root=fixture_root, domain_rss_client=domain_rss_client,
    )
    trending_snapshots = _fetch_trending_snapshots(
        github_trending_client=github_trending_client,
        run_date=run_date,
        existing_names={item.full_name for item in watchlist},
    )
    snapshots.extend(trending_snapshots)
    run = run_daily_intelligence(
        store,
        snapshots,
        run_date=run_date,
        revisit_date=revisit_date,
        notion_url=notion_url,
        paper_snapshots=paper_snapshots,
        domain_snapshots=domain_snapshots,
    )
    executive_summary = synthesize_daily_summary(
        title=run.title,
        fallback_summary=_executive_summary(run),
        decisions=run.notification.decisions,
        router=model_router,
    )
    proposal_metrics = _process_daily_proposals(
        store=store,
        run=run,
        run_date=run_date,
        executive_summary=executive_summary,
    )
    knowledge = _load_decision_knowledge()
    intelligence_brief = IntelligenceEngine(generator=model_router).build_brief(
        IntelligenceBuildInput(
            brief_type="daily",
            domain="AI Intelligence",
            period_start=run_date,
            period_end=run_date,
            title=run.title,
            fallback_summary=executive_summary,
            repository_results=run.repository_results,
            paper_results=run.paper_results,
            domain_results=run.domain_results,
            knowledge_context=knowledge.render_context(),
            knowledge_used=knowledge.used_keys,
        )
    )
    intelligence_brief = type(intelligence_brief)(
        brief_type=intelligence_brief.brief_type,
        domain=intelligence_brief.domain,
        period_start=intelligence_brief.period_start,
        period_end=intelligence_brief.period_end,
        title=intelligence_brief.title,
        executive_summary=intelligence_brief.executive_summary,
        signals=intelligence_brief.signals,
        cross_signals=intelligence_brief.cross_signals,
        memory_links=intelligence_brief.memory_links,
        synthesis_metadata=SynthesisMetadata(
            mode=intelligence_brief.synthesis_metadata.mode,
            tier="pro" if model_router is not None else "deterministic",
            fallback_used=False,
            fallback_reason="",
            pro_calls_used=intelligence_brief.synthesis_metadata.pro_calls_used,
            pro_call_limit=intelligence_brief.synthesis_metadata.pro_call_limit,
            knowledge_used=intelligence_brief.synthesis_metadata.knowledge_used,
        ),
        delivery_hints=intelligence_brief.delivery_hints,
    )
    notion_status = _publish_notion(
        run=run,
        run_date=run_date,
        executive_summary=executive_summary,
        notion_client=notion_client,
        notion_database_id=notion_database_id,
        publish_notion=publish_notion,
    )
    structured_notion = _publish_structured_notion(
        run=run,
        notion_client=notion_client,
        notion_papers_database_id=notion_papers_database_id,
        notion_github_repos_database_id=notion_github_repos_database_id,
        notion_ecosystem_database_id=notion_ecosystem_database_id,
        publish_notion=publish_notion,
    )
    notification = run.notification
    if notion_status.status == "published" and notion_status.detail:
        notification = type(notification)(
            title=notification.title,
            decisions=notification.decisions,
            top_action=notification.top_action,
            notion_url=notion_status.detail,
            executive_summary=executive_summary,
        )
    else:
        notification = type(notification)(
            title=notification.title,
            decisions=notification.decisions,
            top_action=notification.top_action,
            notion_url=notification.notion_url,
            executive_summary=executive_summary,
        )
    telegram_status = _send_telegram(
        notification=notification,
        telegram_client=telegram_client,
        send_telegram=send_telegram,
        notion_status=notion_status,
    )
    enqueue_unsent_telegram_notification(
        store=store,
        notification=notification,
        notion_status=notion_status,
        telegram_status=telegram_status,
        send_telegram=send_telegram,
    )
    brief = store.record_brief(
        brief_type="daily",
        domain="AI Intelligence",
        period_start=run_date,
        period_end=run_date,
        title=run.title,
        executive_summary=executive_summary,
        top_actions=run.notification.decisions,
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    MemoryEngine(store).record_synthesis_metadata(
        "brief",
        brief.id,
        intelligence_brief.synthesis_metadata.as_dict(),
    )
    store.record_run(
        run_date=run_date,
        stage="daily",
        title=run.title,
        period_start=run_date,
        period_end=run_date,
        status="completed",
        notion_status=notion_status.status,
        notion_url=notion_status.detail if notion_status.status == "published" else notion_url,
        telegram_status=telegram_status.status,
        telegram_detail=telegram_status.detail,
    )
    obsidian_status = _publish_obsidian(
        run=run,
        run_date=run_date,
        executive_summary=executive_summary,
        store=store,
        obsidian_client=obsidian_client,
        publish_obsidian=publish_obsidian,
    )
    return DailyPipelineResult(
        run=run,
        brief=brief,
        intelligence_brief=intelligence_brief,
        notion=notion_status,
        telegram=telegram_status,
        structured_notion=structured_notion,
        obsidian=obsidian_status,
        proposal_metrics=proposal_metrics,
    )


def _fetch_snapshot(
    item: GitHubWatchItem,
    *,
    run_date: str,
    fixture_root: Path | None,
    github_client: GitHubClient | None,
) -> GitHubRepoSnapshot:
    if github_client is not None:
        return github_client.fetch_repository(item.owner, item.name, run_date)
    if fixture_root is not None and item.fixture:
        return _load_fixture_snapshot(fixture_root / item.fixture, run_date)
    raise ValueError(f"No fixture or GitHub client available for {item.full_name}.")


def _load_decision_knowledge():
    knowledge_dir = Path(__file__).resolve().parents[1] / "knowledge"
    return load_knowledge_context(
        knowledge_dir,
        keys=("decision_framework", "signal_compression"),
        char_limit=4000,
    )


def _fetch_all_snapshots(
    watchlist: list[GitHubWatchItem],
    *,
    run_date: str,
    fixture_root: Path | None,
    github_client: GitHubClient | None,
) -> list[GitHubRepoSnapshot]:
    results: list[GitHubRepoSnapshot] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {
            executor.submit(
                _fetch_snapshot, item, run_date=run_date, fixture_root=fixture_root, github_client=github_client
            ): item
            for item in watchlist
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                snapshot = future.result()
                results.append(snapshot)
            except Exception as exc:
                _log.warning("Failed to fetch snapshot for %s: %s", item.full_name, exc)
    return results


def _fetch_paper_snapshots_single(
    item: PaperWatchItem,
    *,
    run_date: str,
    fixture_root: Path | None,
    paper_client: ArxivClient | PapersWithCodeClient | None,
) -> list[PaperSnapshot]:
    if paper_client is not None and item.query:
        return paper_client.search(item.query, observed_at=run_date, max_results=item.max_results)
    if fixture_root is not None and item.fixture:
        return [_load_paper_fixture_snapshot(fixture_root / item.fixture, run_date)]
    raise ValueError(f"No fixture or paper client/query available for {item.title}.")


def _fetch_all_paper_snapshots(
    watchlist: list[PaperWatchItem],
    *,
    run_date: str,
    fixture_root: Path | None,
    paper_client: ArxivClient | PapersWithCodeClient | None,
) -> list[PaperSnapshot]:
    results: list[PaperSnapshot] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {
            executor.submit(
                _fetch_paper_snapshots_single, item, run_date=run_date, fixture_root=fixture_root, paper_client=paper_client
            ): item
            for item in watchlist
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                snapshots = future.result()
                results.extend(snapshots)
            except Exception as exc:
                _log.warning("Failed to fetch paper snapshot for %s: %s", item.title, exc)
    return results


def _fetch_domain_snapshots_single(
    item: DomainWatchItem,
    *,
    run_date: str,
    fixture_root: Path | None,
    domain_rss_client: DomainRssClient | None,
) -> list[DomainSignalSnapshot]:
    if domain_rss_client is not None and item.rss_url:
        return domain_rss_client.fetch(item, observed_at=run_date)
    if fixture_root is not None and item.fixture:
        return [_load_domain_fixture_snapshot(fixture_root / item.fixture, run_date)]
    raise ValueError(f"No fixture or RSS client available for domain signal {item.domain}/{item.name}.")


def _fetch_all_domain_snapshots(
    watchlist: list[DomainWatchItem],
    *,
    run_date: str,
    fixture_root: Path | None,
    domain_rss_client: DomainRssClient | None,
) -> list[DomainSignalSnapshot]:
    results: list[DomainSignalSnapshot] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {
            executor.submit(
                _fetch_domain_snapshots_single, item, run_date=run_date, fixture_root=fixture_root, domain_rss_client=domain_rss_client
            ): item
            for item in watchlist
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                snapshots = future.result()
                results.extend(snapshots)
            except Exception as exc:
                _log.warning("Failed to fetch domain snapshot for %s: %s", item.name, exc)
    return results


def _fetch_trending_snapshots(
    *,
    github_trending_client,
    run_date: str,
    existing_names: set[str],
) -> list[GitHubRepoSnapshot]:
    if github_trending_client is None:
        return []
    try:
        trending = github_trending_client.fetch_trending(run_date, max_results=10)
        return [s for s in trending if s.full_name not in existing_names]
    except Exception as exc:
        _log.warning("Failed to fetch GitHub trending repos: %s", exc)
        return []


def _format_brief_body(run: DailyIntelligenceRun, executive_summary: str) -> str:
    sections = []

    # 1. Executive Summary Callout Box
    sections.append("> [!summary]")
    sections.append("> **Executive Summary**")
    for line in executive_summary.split("\n"):
        if line.strip():
            sections.append(f"> {line.strip()}")
    sections.append("")

    # 2. GitHub Repositories Table
    if run.repository_results:
        sections.append("## 🚀 GitHub Repositories")
        sections.append("")
        for result in run.repository_results:
            name_link = _entity_link(result.entity.canonical_name, result.entity.aliases, 1)
            release = _observation_text(result.observations, "latest_release") or "n/a"
            sections.append(f"### 🚀 {name_link} — {result.decision.action}")
            sections.append(
                f"> Stars: {_observation_int(result.observations, 'stars'):,} "
                f"({result.star_delta:+d} {_star_trend(result.star_delta)}) | "
                f"Release: {release} | Momentum: {result.momentum}"
            )
            sections.append(f"> {result.decision.rationale}")
            sections.append("")
        sections.append("")

    # 3. Research Papers Table
    if run.paper_results:
        sections.append("## 📖 Research Papers")
        sections.append("")
        for result in run.paper_results:
            title_link = _entity_link(result.entity.canonical_name, result.entity.aliases, 0)
            sections.append(f"### 📖 {title_link} — {result.decision.action}")
            sections.append(f"> Confidence: {result.decision.confidence} | Radar links: {len(result.relationships)}")
            sections.append(f"> {result.decision.rationale}")
            sections.append("")
        sections.append("")

    # 4. Domain Signals Table
    if run.domain_results:
        sections.append("## 🌐 Domain Signals")
        sections.append("")
        for result in run.domain_results:
            sections.append(f"> [{_domain_callout(result.decision.action)}] {result.signal_title} — {result.decision.action}")
            sections.append(f"> Entity: {result.entity.canonical_name} | Impact: {result.priority_score}")
            sections.append(f"> {result.decision.rationale}")
            sections.append("")
        sections.append("")

    if run.cross_signal_insights:
        sections.append("## 🔗 趨勢交叉分析")
        sections.append("")
        for insight in run.cross_signal_insights:
            sections.append(f"> [!tip] {insight.title}")
            sections.append(f"> Sources: {', '.join(insight.sources)} | Confidence: {insight.confidence}")
            sections.append(f"> {insight.rationale}")
            sections.append("")
        sections.append("")

    # 5. Top Decisions & Action Postures Section
    if run.notification.decisions:
        sections.append("---")
        sections.append("")
        sections.append("## 🎯 Top Decisions & Action Postures")
        sections.append("")
        for decision in run.notification.decisions:
            sections.append(f"- {decision}")

    if not sections:
        return "No daily signals."
    return "\n".join(sections)


def _entity_link(name: str, aliases: tuple[str, ...], url_index: int) -> str:
    if len(aliases) > url_index and aliases[url_index].startswith(("http://", "https://")):
        return f"[{name}]({aliases[url_index]})"
    return name


def _star_trend(delta: int) -> str:
    if delta > 0:
        return "⬆️"
    if delta < 0:
        return "⬇️"
    return "➡️"


def _domain_callout(action: str) -> str:
    if action == "Prototype":
        return "!warning"
    if action == "Read":
        return "!tip"
    return "!note"


def _load_fixture_snapshot(path: Path, run_date: str) -> GitHubRepoSnapshot:
    data = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"GitHub fixture must contain an object: {path}")
    repo_data = data.get("repo")
    if not isinstance(repo_data, dict):
        raise ValueError(f"GitHub fixture must include a repo object: {path}")
    release_data = data.get("latest_release")
    if release_data is not None and not isinstance(release_data, dict):
        raise ValueError(f"GitHub fixture latest_release must be an object or null: {path}")
    pull_data = _optional_dict_list(data.get("latest_pull_requests"), path, "latest_pull_requests")
    if not pull_data and isinstance(data.get("latest_pull_request"), dict):
        pull_data = [data["latest_pull_request"]]
    issue_data = _optional_dict_list(data.get("latest_issues"), path, "latest_issues")
    if not issue_data and isinstance(data.get("latest_issue"), dict):
        issue_data = [data["latest_issue"]]
    contributor_count = data.get("contributors_count")
    contributor_data = [{} for _ in range(contributor_count)] if isinstance(contributor_count, int) and contributor_count >= 0 else None
    return parse_repository_snapshot(repo_data, release_data, run_date, pull_data, issue_data, contributor_data)


def _optional_dict_list(value, path: Path, key: str) -> list[dict] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"GitHub fixture {key} must be a list of objects: {path}")
    return value


def _load_paper_fixture_snapshot(path: Path, run_date: str) -> PaperSnapshot:
    data = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Paper fixture must contain an object: {path}")
    return parse_paper_snapshot(data, run_date)


def _load_domain_fixture_snapshot(path: Path, run_date: str) -> DomainSignalSnapshot:
    data = json.loads(path.resolve().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Domain signal fixture must contain an object: {path}")
    return parse_domain_signal_snapshot(data, run_date)


def _publish_notion(
    *,
    run: DailyIntelligenceRun,
    run_date: str,
    executive_summary: str,
    notion_client: NotionClient | None,
    notion_database_id: str | None,
    publish_notion: bool,
) -> DeliveryStatus:
    if not publish_notion:
        return DeliveryStatus(channel="notion", status="dry-run", detail="Notion publishing not requested.")
    if notion_client is None or not notion_database_id:
        return DeliveryStatus(channel="notion", status="skipped", detail="Missing Notion client or database id.")

    try:
        record = _brief_record(run, run_date, executive_summary)
        page = notion_client.create_brief_record(notion_database_id, record)
        return DeliveryStatus(channel="notion", status="published", detail=page.url or page.id)
    except Exception as exc:
        return failed_delivery("notion", exc)


def _publish_structured_notion(
    *,
    run: DailyIntelligenceRun,
    notion_client: NotionClient | None,
    notion_papers_database_id: str | None,
    notion_github_repos_database_id: str | None,
    notion_ecosystem_database_id: str | None,
    publish_notion: bool,
) -> tuple[DeliveryStatus, ...]:
    if not publish_notion:
        return (DeliveryStatus("notion:structured", "dry-run", "Structured Notion publishing not requested."),)
    if notion_client is None:
        return (DeliveryStatus("notion:structured", "skipped", "Missing Notion client."),)

    statuses: list[DeliveryStatus] = []
    if notion_github_repos_database_id:
        try:
            count = 0
            for result in run.repository_results:
                notion_client.upsert_github_repo_record(notion_github_repos_database_id, _github_repo_record(result))
                count += 1
            statuses.append(DeliveryStatus("notion:github_repos", "published", f"{count} GitHub repo record(s)."))
        except Exception as exc:
            statuses.append(failed_delivery("notion:github_repos", exc))
    else:
        statuses.append(DeliveryStatus("notion:github_repos", "skipped", "NOTION_GITHUB_REPOS_DATABASE_ID is missing."))

    if notion_papers_database_id:
        try:
            count = 0
            for result in run.paper_results:
                notion_client.upsert_paper_record(notion_papers_database_id, _paper_record(result))
                count += 1
            statuses.append(DeliveryStatus("notion:papers", "published", f"{count} paper record(s)."))
        except Exception as exc:
            statuses.append(failed_delivery("notion:papers", exc))
    else:
        statuses.append(DeliveryStatus("notion:papers", "skipped", "NOTION_PAPERS_DATABASE_ID is missing."))

    if notion_ecosystem_database_id:
        try:
            count = 0
            for result in run.domain_results:
                notion_client.upsert_ecosystem_record(notion_ecosystem_database_id, _ecosystem_record(result))
                count += 1
            statuses.append(DeliveryStatus("notion:ecosystem", "published", f"{count} ecosystem record(s)."))
        except Exception as exc:
            statuses.append(failed_delivery("notion:ecosystem", exc))
    else:
        statuses.append(DeliveryStatus("notion:ecosystem", "skipped", "NOTION_ECOSYSTEM_DATABASE_ID is missing."))
    return tuple(statuses)


def _brief_record(run: DailyIntelligenceRun, run_date: str, executive_summary: str) -> NotionBriefRecord:
    actions = tuple(
        dict.fromkeys(
            result.decision.action for result in (*run.repository_results, *run.paper_results, *run.domain_results)
        )
    )
    score = _daily_score(run)
    body = _format_brief_body(run, executive_summary)
    return NotionBriefRecord(
        title=run.title,
        date=run_date,
        executive_summary=executive_summary,
        recommended_actions=actions,
        intelligence_score=score,
        confidence="medium" if (run.repository_results or run.paper_results or run.domain_results) else "low",
        status="Published",
        tags=("AI Intelligence", "GitHub Radar", "Domain Radar"),
        body=body,
    )


def _github_repo_record(result) -> NotionGitHubRepoRecord:
    name = result.entity.canonical_name
    owner = name.split("/", 1)[0] if "/" in name else ""
    stars = _observation_int(result.observations, "stars")
    return NotionGitHubRepoRecord(
        name=name,
        url=_source_url(result.observations, "github"),
        owner=owner,
        stars=stars,
        category=_repo_category(result.entity.tags),
        summary=result.entity.summary,
        why_it_matters=result.decision.rationale,
        engineering_value=_value_label(result.decision.action),
        adoption_potential=_adoption_label(stars, result.momentum),
        recommended_action=result.decision.action,
    )


def _paper_record(result) -> NotionPaperRecord:
    published = _observation_text(result.observations, "published")
    technology_area = tuple(tag for tag in result.entity.tags if tag not in {"paper"})
    return NotionPaperRecord(
        title=result.entity.canonical_name,
        authors="",
        url=_source_url(result.observations, "paper"),
        published_date=published[:10] or result.entity.last_seen,
        summary=result.entity.summary,
        why_it_matters=result.decision.rationale,
        technology_area=technology_area,
        intelligence_score=min(100, 55 + len(result.relationships) * 10),
        recommended_action=result.decision.action,
        confidence=result.decision.confidence,
    )


def _ecosystem_record(result) -> NotionEcosystemRecord:
    return NotionEcosystemRecord(
        name=result.entity.canonical_name,
        type=result.entity.kind.title(),
        company_or_maintainer="",
        category=result.entity.tags,
        summary=result.entity.summary,
        why_it_matters=result.decision.rationale,
        impact=_impact_label(result.priority_score),
        momentum="rising" if result.priority_score >= 85 else "active",
    )


def _send_telegram(
    *,
    notification,
    telegram_client: TelegramClient | None,
    send_telegram: bool,
    notion_status: DeliveryStatus,
) -> DeliveryStatus:
    if not send_telegram:
        return DeliveryStatus(channel="telegram", status="dry-run", detail="Telegram send not requested.")
    blocked = telegram_blocked_by_notion(notion_status)
    if blocked is not None:
        return blocked
    if telegram_client is None:
        return DeliveryStatus(channel="telegram", status="skipped", detail="Missing Telegram client.")
    try:
        result: TelegramResult = telegram_client.send_notification(notification)
        return DeliveryStatus(channel="telegram", status="sent", detail=str(result.message_id))
    except Exception as exc:
        return failed_delivery("telegram", exc)


def _source_url(observations, source_type: str) -> str:
    for observation in observations:
        if observation.source_type == source_type or observation.source_type.startswith(f"{source_type}:"):
            return observation.source_url
    return ""


def _observation_int(observations, metric_name: str) -> int:
    value = _observation_text(observations, metric_name)
    try:
        return int(value)
    except ValueError:
        return 0


def _observation_text(observations, metric_name: str) -> str:
    for observation in observations:
        if observation.metric_name == metric_name:
            return observation.current_value
    return ""


def _repo_category(tags: tuple[str, ...]) -> str:
    text = " ".join(tags).casefold()
    if "agent" in text:
        return "AI Agent"
    if "rag" in text:
        return "RAG"
    if "inference" in text:
        return "Inference"
    if "developer" in text or "tool" in text:
        return "Developer Tool"
    return "Infrastructure"


def _value_label(action: str) -> str:
    if action in {"Prototype", "Implement"}:
        return "high"
    if action in {"Read", "Watch"}:
        return "medium"
    return "low"


def _adoption_label(stars: int, momentum: str) -> str:
    if stars >= 10000 or momentum in {"surging", "rising"}:
        return "high"
    if stars >= 1000 or momentum == "active":
        return "medium"
    return "low"


def _impact_label(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def _executive_summary(run: DailyIntelligenceRun) -> str:
    if not run.repository_results and not run.paper_results and not run.domain_results:
        return "No daily signals were processed."
    highlights = _summary_highlights(run)
    if not highlights:
        return "今天沒有需要立即行動的強訊號；維持觀察即可。"

    sentences = []
    if run.cross_signal_insights:
        insight = run.cross_signal_insights[0]
        sentences.append(f"{insight.subject} 出現跨來源加速：{insight.rationale}")
    selected = highlights[:2]
    sentences.extend(_summary_sentence(item) for item in selected)
    actions = ", ".join(dict.fromkeys(f"{item.decision.action} {item.entity.canonical_name}" for item in selected))
    sentences.append(f"建議行動：{actions}。")
    return " ".join(sentences)


def _summary_highlights(run: DailyIntelligenceRun):
    results = [*run.repository_results, *run.paper_results, *run.domain_results]

    def score(result) -> tuple[int, int, str]:
        action = ACTION_RANK.get(result.decision.action, 3)
        magnitude = 0
        if hasattr(result, "star_delta"):
            magnitude = getattr(result, "star_delta", 0)
        elif hasattr(result, "priority_score"):
            magnitude = getattr(result, "priority_score", 0)
        elif hasattr(result, "relationships"):
            magnitude = len(getattr(result, "relationships", ())) * 10
        return (action, -magnitude, result.entity.canonical_name)

    actionable = [result for result in results if result.decision.action in {"Prototype", "Implement", "Read"}]
    ranked = sorted(actionable or results, key=score)
    unique = []
    seen = set()
    for result in ranked:
        identity = _summary_identity(result)
        if identity in seen:
            continue
        unique.append(result)
        seen.add(identity)
    return unique


def _summary_sentence(result) -> str:
    if hasattr(result, "star_delta"):
        release = _observation_text(result.observations, "latest_release")
        release_text = f" 最新 release {release}" if release else ""
        return (
            f"{result.entity.canonical_name}{release_text}，GitHub momentum {result.momentum}，"
            f"stars {result.star_delta:+d}。"
        )
    if hasattr(result, "priority_score"):
        return (
            f"{result.entity.canonical_name} 在 {result.signal_title} 中達到 impact {result.priority_score}，"
            f"{_first_sentence(result.entity.summary)}。"
        )
    summary = _normalize_summary_fragment(_remove_leading_title(result.entity.summary, result.entity.canonical_name))
    action_label = "原型驗證" if result.decision.action == "Prototype" else "閱讀"
    return f"{result.entity.canonical_name} 值得{action_label}；重點是：{_first_sentence(summary)}。"


def _summary_identity(result) -> str:
    signal_id = str(result.decision.signal_id)
    if signal_id.startswith("domain:"):
        return f"domain:{result.entity.canonical_name.casefold()}"
    if signal_id.startswith("paper:"):
        return f"paper:{result.entity.canonical_name.casefold()}"
    return f"{signal_id.split(':', 1)[0]}:{result.entity.canonical_name.casefold()}"


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "目前缺少摘要"
    for separator in (". ", "。", "\n"):
        if separator in cleaned:
            return cleaned.split(separator, 1)[0].strip(" .。")
    return _trim_at_word_boundary(cleaned, 180)


def _remove_leading_title(text: str, title: str) -> str:
    cleaned = " ".join(text.split())
    normalized_title = " ".join(title.split())
    if cleaned.casefold().startswith(normalized_title.casefold()):
        return cleaned[len(normalized_title) :].lstrip(" :-—,，。")
    short_title = normalized_title.split(":", 1)[0].strip()
    if short_title and cleaned.casefold().startswith(short_title.casefold()):
        return cleaned[len(short_title) :].lstrip(" :-—,，。")
    return cleaned


def _normalize_summary_fragment(text: str) -> str:
    cleaned = text.strip()
    lowered = cleaned.casefold()
    for prefix in ("is ", "are "):
        if lowered.startswith(prefix):
            return cleaned[len(prefix) :].lstrip()
    return cleaned


def _trim_at_word_boundary(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    trimmed = text[: limit + 1].rsplit(" ", 1)[0].strip(" ,，;；")
    if not trimmed:
        trimmed = text[:limit].strip(" ,，;；")
    return f"{trimmed}…"


def _daily_score(run: DailyIntelligenceRun) -> int:
    domain_score = max((result.priority_score for result in run.domain_results), default=0)
    if not run.repository_results:
        return min(domain_score, 100)
    if domain_score:
        return min(max(domain_score, _repo_daily_score(run)), 100)
    return _repo_daily_score(run)


def _repo_daily_score(run: DailyIntelligenceRun) -> int:
    if not run.repository_results:
        return 0
    max_delta = max(result.star_delta for result in run.repository_results)
    if max_delta >= 1000:
        return 85
    if max_delta >= 500:
        return 75
    if max_delta >= 100:
        return 65
    return 45


def _publish_obsidian(
    *,
    run: DailyIntelligenceRun,
    run_date: str,
    executive_summary: str,
    store: MemoryStore,
    obsidian_client: ObsidianClient | None,
    publish_obsidian: bool,
) -> DeliveryStatus:
    if not publish_obsidian:
        return DeliveryStatus(channel="obsidian", status="dry-run", detail="Obsidian publishing not requested.")
    if obsidian_client is None:
        return DeliveryStatus(channel="obsidian", status="skipped", detail="Missing Obsidian client.")

    try:
        repository = SQLiteRepository.from_memory_store(store)
        model = ObsidianReadModelBuilder(repository).build()
        publish_result = ObsidianPublisher(obsidian_client.vault_path).publish(model, ObsidianRenderer())
        if publish_result.broken_wikilinks:
            return DeliveryStatus(
                channel="obsidian",
                status="failed",
                detail=f"Broken WikiLinks: {len(publish_result.broken_wikilinks)}",
            )
        brief_file = next(
            (
                path
                for path in publish_result.written
                if path.relative_to(obsidian_client.vault_path).as_posix().startswith("01 Briefs/Daily/")
            ),
            obsidian_client.vault_path,
        )
        return DeliveryStatus(channel="obsidian", status="published", detail=str(brief_file))
    except Exception as exc:
        return failed_delivery("obsidian", exc)


def _process_daily_proposals(
    *,
    store: MemoryStore,
    run: DailyIntelligenceRun,
    run_date: str,
    executive_summary: str,
) -> ProposalMetrics:
    proposal_store = SQLiteProposalStore.from_memory_store(store)
    trust_service = ProposalTrustService(store=store, proposals=proposal_store)
    try:
        result = CanonicalInsightEngine(trust_service).process_daily_run(
            run,
            run_date=run_date,
            executive_summary=executive_summary,
        )
        return trust_service.record_metrics(
            run_date=run_date,
            stage="daily",
            results=result.proposal_results,
        )
    except Exception as exc:
        _log.warning("Daily proposal processing failed: %s", exc)
        metrics = ProposalMetrics(
            run_date=run_date,
            stage="daily",
            proposals_created=0,
            proposals_accepted=0,
            proposals_rejected=0,
            proposals_needing_review=0,
            canonical_records_created=0,
            canonical_records_updated=0,
            insight_count=0,
        )
        proposal_store.record_metrics(metrics)
        return metrics
