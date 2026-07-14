from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from connectors.github import GitHubClient
from connectors.domain_rss import DomainRssClient
from connectors.notion import NotionClient
from connectors.papers import ArxivClient, PapersWithCodeClient
from connectors.telegram import TelegramClient
from core.config import Settings
from core.model_router import ModelRouter
from core.schedule_plan import build_schedule_plan, validate_production_schedule
from core.watchlist import load_domain_watchlist, load_github_watchlist, load_paper_watchlist


CheckStatus = Literal["ok", "skipped", "failed"]
DoctorProfile = Literal["default", "demo"]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.status != "failed" for check in self.checks)

    @property
    def failures(self) -> tuple[DoctorCheck, ...]:
        return tuple(check for check in self.checks if check.status == "failed")


def run_doctor(
    settings: Settings,
    *,
    live: bool = False,
    profile: DoctorProfile = "default",
    github_client: GitHubClient | None = None,
    paper_client: ArxivClient | None = None,
    papers_with_code_client: PapersWithCodeClient | None = None,
    domain_rss_client: DomainRssClient | None = None,
    notion_client: NotionClient | None = None,
    telegram_client: TelegramClient | None = None,
    model_router: ModelRouter | None = None,
) -> DoctorReport:
    checks: list[DoctorCheck] = []
    github_watchlist = []
    paper_watchlist = []
    domain_watchlist = []

    checks.append(DoctorCheck("profile", "ok", f"doctor profile={profile}"))
    checks.append(_path_exists("project_root", settings.project_root, "project root"))
    if profile != "demo":
        checks.extend(_model_config_checks(settings))
        checks.append(_path_exists("source_file", settings.source_file, "legacy source file"))
        checks.append(_directory_ready("memory_db_parent", settings.memory_db.parent, "memory database parent"))
    checks.append(_directory_ready("fixture_root", settings.fixture_root, "fixture root"))
    checks.append(_synthesis_policy_check(settings))

    try:
        github_watchlist = load_github_watchlist(settings.github_watchlist_file)
        checks.append(
            DoctorCheck(
                "github_watchlist",
                "ok",
                f"{len(github_watchlist)} repository watch item(s) loaded from {settings.github_watchlist_file}",
            )
        )
        checks.extend(_fixture_checks("github_fixture", settings.fixture_root, [item.fixture for item in github_watchlist]))
    except Exception as exc:
        checks.append(DoctorCheck("github_watchlist", "failed", str(exc)))

    try:
        paper_watchlist = load_paper_watchlist(settings.paper_watchlist_file)
        checks.append(
            DoctorCheck(
                "paper_watchlist",
                "ok",
                f"{len(paper_watchlist)} paper watch item(s) loaded from {settings.paper_watchlist_file}",
            )
        )
        checks.extend(_fixture_checks("paper_fixture", settings.fixture_root, [item.fixture for item in paper_watchlist]))
    except Exception as exc:
        checks.append(DoctorCheck("paper_watchlist", "failed", str(exc)))

    try:
        domain_watchlist = load_domain_watchlist(settings.domain_watchlist_file)
        checks.append(
            DoctorCheck(
                "domain_watchlist",
                "ok",
                f"{len(domain_watchlist)} domain signal watch item(s) loaded from {settings.domain_watchlist_file}",
            )
        )
        checks.extend(_fixture_checks("domain_fixture", settings.fixture_root, [item.fixture for item in domain_watchlist]))
        rss_count = sum(1 for item in domain_watchlist if item.rss_url)
        checks.append(DoctorCheck("domain_rss_sources", "ok" if rss_count else "skipped", f"{rss_count} domain RSS source(s) configured."))
    except Exception as exc:
        checks.append(DoctorCheck("domain_watchlist", "failed", str(exc)))

    checks.append(_optional_integration_check("github_token", settings.github_token, "GITHUB_TOKEN", profile))
    checks.append(_optional_integration_check("notion_token", settings.notion_token, "NOTION_TOKEN", profile))
    checks.append(_optional_integration_check("notion_parent_page_id", settings.notion_parent_page_id, "NOTION_PARENT_PAGE_ID", profile))
    checks.append(_optional_integration_check("notion_papers_database_id", settings.notion_papers_database_id, "NOTION_PAPERS_DATABASE_ID", profile))
    checks.append(
        _optional_integration_check(
            "notion_github_repos_database_id",
            settings.notion_github_repos_database_id,
            "NOTION_GITHUB_REPOS_DATABASE_ID",
            profile,
        )
    )
    checks.append(_optional_integration_check("notion_ecosystem_database_id", settings.notion_ecosystem_database_id, "NOTION_ECOSYSTEM_DATABASE_ID", profile))
    checks.append(
        _optional_integration_check(
            "notion_radar_entities_database_id",
            settings.notion_radar_entities_database_id,
            "NOTION_RADAR_ENTITIES_DATABASE_ID",
            profile,
        )
    )
    checks.append(_optional_integration_check("telegram_bot_token", settings.telegram_bot_token, "TELEGRAM_BOT_TOKEN", profile))
    checks.append(_optional_integration_check("telegram_chat_id", settings.telegram_chat_id, "TELEGRAM_CHAT_ID", profile))

    if live:
        checks.append(_check_live_github(settings, github_watchlist, github_client))
        checks.append(_check_live_arxiv(paper_watchlist, paper_client))
        checks.append(_check_live_papers_with_code(paper_watchlist, papers_with_code_client))
        checks.extend(_check_live_domain_rss(domain_watchlist, domain_rss_client))
        checks.append(_check_live_cloud_model(settings, model_router))
        checks.extend(_check_live_notion(settings, notion_client))
        checks.append(_check_live_telegram(settings, telegram_client))
    else:
        checks.append(DoctorCheck("live_checks", "skipped", "Pass --live to verify external APIs."))

    return DoctorReport(tuple(checks))


def run_go_live_check(
    settings: Settings,
    *,
    live: bool = False,
    github_client: GitHubClient | None = None,
    paper_client: ArxivClient | None = None,
    papers_with_code_client: PapersWithCodeClient | None = None,
    domain_rss_client: DomainRssClient | None = None,
    notion_client: NotionClient | None = None,
    telegram_client: TelegramClient | None = None,
    model_router: ModelRouter | None = None,
) -> DoctorReport:
    report = run_doctor(
        settings,
        live=live,
        github_client=github_client,
        paper_client=paper_client,
        papers_with_code_client=papers_with_code_client,
        domain_rss_client=domain_rss_client,
        notion_client=notion_client,
        telegram_client=telegram_client,
        model_router=model_router,
    )
    checks = list(report.checks)
    checks.extend(_production_config_checks(settings))
    checks.extend(_production_schedule_checks())
    if live:
        checks.extend(_production_live_checks(report))
    return DoctorReport(tuple(checks))


def _path_exists(name: str, path: Path, label: str) -> DoctorCheck:
    if path.exists():
        return DoctorCheck(name, "ok", f"{label} exists: {path}")
    return DoctorCheck(name, "failed", f"{label} is missing: {path}")


def _directory_ready(name: str, path: Path, label: str) -> DoctorCheck:
    if path.exists() and path.is_dir():
        return DoctorCheck(name, "ok", f"{label} exists: {path}")
    return DoctorCheck(name, "failed", f"{label} directory is missing: {path}")


def _fixture_checks(name: str, root: Path, fixtures: list[str]) -> tuple[DoctorCheck, ...]:
    checks = []
    for fixture in fixtures:
        if not fixture:
            continue
        path = root / fixture
        status: CheckStatus = "ok" if path.exists() else "failed"
        detail = f"fixture exists: {path}" if status == "ok" else f"fixture is missing: {path}"
        checks.append(DoctorCheck(name, status, detail))
    if not checks:
        return (DoctorCheck(name, "skipped", f"No fixture entries declared under {root}."),)
    return tuple(checks)


def _configured(name: str, value: str | None, env_name: str) -> DoctorCheck:
    if value:
        return DoctorCheck(name, "ok", f"{env_name} is configured.")
    return DoctorCheck(name, "skipped", f"{env_name} is not configured.")


def _optional_integration_check(name: str, value: str | None, env_name: str, profile: DoctorProfile) -> DoctorCheck:
    if profile == "demo":
        return DoctorCheck(name, "skipped", f"{env_name} is optional for the demo profile.")
    return _configured(name, value, env_name)


def _required_configured(name: str, value: str | None, env_name: str) -> DoctorCheck:
    if value and "not-configured" not in value:
        return DoctorCheck(name, "ok", f"{env_name} is configured for go-live.")
    return DoctorCheck(name, "failed", f"{env_name} is required for go-live.")


def _production_config_checks(settings: Settings) -> tuple[DoctorCheck, ...]:
    checks = []
    if settings.model_provider in {"cloud", "openai-compatible"}:
        checks.append(DoctorCheck("go_live_model_provider", "ok", f"HERMES_MODEL_PROVIDER={settings.model_provider}"))
    else:
        checks.append(
            DoctorCheck(
                "go_live_model_provider",
                "failed",
                "HERMES_MODEL_PROVIDER must be cloud or openai-compatible for production go-live.",
            )
        )
    checks.extend(
        (
            _required_configured("go_live_cloud_api_key", settings.cloud_api_key, "HERMES_CLOUD_API_KEY"),
            _required_configured("go_live_fast_model", settings.cloud_fast_model, "HERMES_FAST_MODEL"),
            _required_configured("go_live_pro_model", settings.cloud_pro_model, "HERMES_PRO_MODEL"),
            _model_tier_split_check(settings),
            _required_configured("go_live_github_token", settings.github_token, "GITHUB_TOKEN"),
            _required_configured("go_live_notion_token", settings.notion_token, "NOTION_TOKEN"),
            _required_configured("go_live_notion_parent_page_id", settings.notion_parent_page_id, "NOTION_PARENT_PAGE_ID"),
            _required_configured(
                "go_live_notion_daily_briefs_database_id",
                settings.notion_daily_briefs_database_id,
                "NOTION_DAILY_BRIEFS_DATABASE_ID",
            ),
            _required_configured("go_live_notion_papers_database_id", settings.notion_papers_database_id, "NOTION_PAPERS_DATABASE_ID"),
            _required_configured(
                "go_live_notion_github_repos_database_id",
                settings.notion_github_repos_database_id,
                "NOTION_GITHUB_REPOS_DATABASE_ID",
            ),
            _required_configured(
                "go_live_notion_ecosystem_database_id",
                settings.notion_ecosystem_database_id,
                "NOTION_ECOSYSTEM_DATABASE_ID",
            ),
            _required_configured("go_live_notion_decisions_database_id", settings.notion_decisions_database_id, "NOTION_DECISIONS_DATABASE_ID"),
            _required_configured(
                "go_live_notion_radar_snapshots_database_id",
                settings.notion_radar_snapshots_database_id,
                "NOTION_RADAR_SNAPSHOTS_DATABASE_ID",
            ),
            _required_configured(
                "go_live_notion_radar_entities_database_id",
                settings.notion_radar_entities_database_id,
                "NOTION_RADAR_ENTITIES_DATABASE_ID",
            ),
            _required_configured("go_live_telegram_bot_token", settings.telegram_bot_token, "TELEGRAM_BOT_TOKEN"),
            _required_configured("go_live_telegram_chat_id", settings.telegram_chat_id, "TELEGRAM_CHAT_ID"),
        )
    )
    return tuple(checks)


def _model_tier_split_check(settings: Settings) -> DoctorCheck:
    fast = settings.cloud_fast_model.strip()
    pro = settings.cloud_pro_model.strip()
    if settings.model_provider not in {"cloud", "openai-compatible"}:
        return DoctorCheck(
            "go_live_model_tier_split",
            "skipped",
            "Fast/pro split is only required for cloud production providers.",
        )
    if not fast or not pro or fast.endswith("not-configured") or pro.endswith("not-configured"):
        return DoctorCheck(
            "go_live_model_tier_split",
            "skipped",
            "Fast/pro split check waits until HERMES_FAST_MODEL and HERMES_PRO_MODEL are configured.",
        )
    if fast.casefold() == pro.casefold():
        return DoctorCheck(
            "go_live_model_tier_split",
            "failed",
            "HERMES_FAST_MODEL and HERMES_PRO_MODEL must be different for production token control.",
        )
    return DoctorCheck(
        "go_live_model_tier_split",
        "ok",
        "HERMES_FAST_MODEL and HERMES_PRO_MODEL are split for production token control.",
    )


def _production_schedule_checks() -> tuple[DoctorCheck, ...]:
    plan = build_schedule_plan(
        live_github=True,
        live_papers_with_code=True,
        live_domain_rss=True,
        publish_notion=True,
        send_telegram=True,
        model_synthesis=True,
        include_weekly=True,
        include_monthly=True,
        include_dashboard=True,
        include_radar=True,
        include_decision_review=True,
    )
    failures = validate_production_schedule(plan)
    if failures:
        return (
            DoctorCheck(
                "go_live_schedule_plan",
                "failed",
                "; ".join(failures),
            ),
        )
    return (
        DoctorCheck(
            "go_live_schedule_plan",
            "ok",
            f"{len(plan.tasks)} production scheduled task(s) validated.",
        ),
    )


def _production_live_checks(report: DoctorReport) -> tuple[DoctorCheck, ...]:
    required_live_names = {
        "live_github",
        "live_arxiv",
        "live_papers_with_code",
        "live_domain_rss",
        "live_cloud_model",
        "live_notion_parent",
        "live_notion_briefs_database",
        "live_notion_papers_database",
        "live_notion_github_repos_database",
        "live_notion_ecosystem_database",
        "live_notion_decisions_database",
        "live_notion_radar_database",
        "live_notion_radar_entities_database",
        "live_telegram",
    }
    checks = []
    for check in report.checks:
        if check.name not in required_live_names or check.status != "skipped":
            continue
        checks.append(
            DoctorCheck(
                f"go_live_{check.name}",
                "failed",
                f"{check.name} must be ok for live go-live verification; current status is skipped: {check.detail}",
            )
        )
    return tuple(checks)


def _model_config_checks(settings: Settings) -> tuple[DoctorCheck, ...]:
    checks = [
        DoctorCheck("model_provider", "ok", f"HERMES_MODEL_PROVIDER={settings.model_provider}"),
    ]
    if settings.model_provider == "ollama":
        checks.append(DoctorCheck("ollama_model", "ok", f"OLLAMA_MODEL={settings.ollama_model}"))
        return tuple(checks)
    if settings.model_provider in {"cloud", "openai-compatible"}:
        checks.append(_configured("cloud_api_key", settings.cloud_api_key, "HERMES_CLOUD_API_KEY"))
        checks.append(DoctorCheck("cloud_base_url", "ok", f"HERMES_CLOUD_BASE_URL={settings.cloud_base_url}"))
        checks.append(DoctorCheck("cloud_fast_model", "ok", f"HERMES_FAST_MODEL={settings.cloud_fast_model}"))
        checks.append(DoctorCheck("cloud_pro_model", "ok", f"HERMES_PRO_MODEL={settings.cloud_pro_model}"))
        return tuple(checks)
    checks.append(DoctorCheck("model_provider_supported", "failed", f"Unsupported model provider: {settings.model_provider}"))
    return tuple(checks)


def _synthesis_policy_check(settings: Settings) -> DoctorCheck:
    if settings.synthesis_mode not in {"off", "hybrid", "full"}:
        return DoctorCheck(
            "synthesis_policy",
            "failed",
            f"HERMES_SYNTHESIS_MODE must be off, hybrid, or full; got {settings.synthesis_mode!r}.",
        )
    if settings.pro_call_limit < 0:
        return DoctorCheck("synthesis_policy", "failed", "HERMES_PRO_CALL_LIMIT must be >= 0.")
    return DoctorCheck(
        "synthesis_policy",
        "ok",
        f"mode={settings.synthesis_mode}; pro_call_limit={settings.pro_call_limit}.",
    )


def _check_live_github(settings: Settings, watchlist: list, client: GitHubClient | None) -> DoctorCheck:
    if not watchlist:
        return DoctorCheck("live_github", "skipped", "GitHub watchlist is empty.")
    target = watchlist[0]
    client = client or GitHubClient(token=settings.github_token)
    try:
        snapshot = client.fetch_repository(target.owner, target.name, "doctor")
    except Exception as exc:
        return DoctorCheck("live_github", "failed", str(exc))
    mode = "authenticated" if settings.github_token else "unauthenticated"
    return DoctorCheck("live_github", "ok", f"Fetched {snapshot.full_name} from GitHub ({mode}).")


def _check_live_arxiv(watchlist: list, client: ArxivClient | None) -> DoctorCheck:
    target = next((item for item in watchlist if item.query), None)
    if target is None:
        return DoctorCheck("live_arxiv", "skipped", "No arXiv query found in paper watchlist.")
    client = client or ArxivClient()
    try:
        papers = client.search(target.query, "doctor", max_results=1)
    except Exception as exc:
        return DoctorCheck("live_arxiv", "failed", str(exc))
    return DoctorCheck("live_arxiv", "ok", f"arXiv returned {len(papers)} paper(s) for {target.query!r}.")


def _check_live_papers_with_code(watchlist: list, client: PapersWithCodeClient | None) -> DoctorCheck:
    target = next((item for item in watchlist if item.query), None)
    if target is None:
        return DoctorCheck("live_papers_with_code", "skipped", "No paper query found in paper watchlist.")
    client = client or PapersWithCodeClient()
    try:
        papers = client.search(target.query, "doctor", max_results=1)
    except Exception as exc:
        return DoctorCheck("live_papers_with_code", "failed", str(exc))
    return DoctorCheck(
        "live_papers_with_code",
        "ok",
        f"Papers with Code returned {len(papers)} paper(s) for {target.query!r}.",
    )


def _check_live_domain_rss(watchlist: list, client: DomainRssClient | None) -> tuple[DoctorCheck, ...]:
    rss_items = [item for item in watchlist if item.rss_url]
    if not rss_items:
        return (DoctorCheck("live_domain_rss", "skipped", "No domain RSS sources configured."),)
    client = client or DomainRssClient()
    checks = []
    for item in rss_items:
        try:
            snapshots = client.fetch(item, "doctor")
            checks.append(
                DoctorCheck(
                    "live_domain_rss",
                    "ok",
                    f"{item.domain}/{item.name}: RSS returned {len(snapshots)} signal(s).",
                )
            )
        except Exception as exc:
            checks.append(
                DoctorCheck(
                    "live_domain_rss",
                    "failed",
                    f"{item.domain}/{item.name}: {exc}",
                )
            )
    return tuple(checks)


def _check_live_cloud_model(settings: Settings, router: ModelRouter | None) -> DoctorCheck:
    if settings.model_provider not in {"cloud", "openai-compatible"}:
        return DoctorCheck("live_cloud_model", "skipped", "Cloud model provider is not selected.")
    if not settings.cloud_api_key:
        return DoctorCheck("live_cloud_model", "skipped", "HERMES_CLOUD_API_KEY is missing.")
    router = router or ModelRouter(settings)
    try:
        text = router.generate("Return exactly: ok", tier="fast")
    except Exception as exc:
        return DoctorCheck("live_cloud_model", "failed", str(exc))
    if "ok" not in text.casefold():
        return DoctorCheck("live_cloud_model", "failed", f"Unexpected cloud model response: {text[:100]}")
    return DoctorCheck("live_cloud_model", "ok", f"Fast cloud model responded with {text[:30]!r}.")


def _check_live_notion(settings: Settings, client: NotionClient | None) -> tuple[DoctorCheck, ...]:
    if not settings.notion_token or not settings.notion_parent_page_id:
        return (DoctorCheck("live_notion_parent", "skipped", "NOTION_TOKEN or NOTION_PARENT_PAGE_ID is missing."),)
    client = client or NotionClient(token=settings.notion_token, parent_page_id=settings.notion_parent_page_id)
    checks = []
    try:
        page = client.retrieve_page()
        checks.append(DoctorCheck("live_notion_parent", "ok", f"Retrieved Notion parent page {page.id}."))
    except Exception as exc:
        checks.append(DoctorCheck("live_notion_parent", "failed", str(exc)))

    if not settings.notion_daily_briefs_database_id:
        checks.append(
            DoctorCheck("live_notion_briefs_database", "skipped", "NOTION_DAILY_BRIEFS_DATABASE_ID is missing.")
        )
    else:
        checks.append(_retrieve_notion_database(client, settings.notion_daily_briefs_database_id, "live_notion_briefs_database"))
    if settings.notion_decisions_database_id:
        checks.append(_retrieve_notion_database(client, settings.notion_decisions_database_id, "live_notion_decisions_database"))
    else:
        checks.append(DoctorCheck("live_notion_decisions_database", "skipped", "NOTION_DECISIONS_DATABASE_ID is missing."))
    if settings.notion_papers_database_id:
        checks.append(_retrieve_notion_database(client, settings.notion_papers_database_id, "live_notion_papers_database"))
    else:
        checks.append(DoctorCheck("live_notion_papers_database", "skipped", "NOTION_PAPERS_DATABASE_ID is missing."))
    if settings.notion_github_repos_database_id:
        checks.append(
            _retrieve_notion_database(client, settings.notion_github_repos_database_id, "live_notion_github_repos_database")
        )
    else:
        checks.append(DoctorCheck("live_notion_github_repos_database", "skipped", "NOTION_GITHUB_REPOS_DATABASE_ID is missing."))
    if settings.notion_ecosystem_database_id:
        checks.append(_retrieve_notion_database(client, settings.notion_ecosystem_database_id, "live_notion_ecosystem_database"))
    else:
        checks.append(DoctorCheck("live_notion_ecosystem_database", "skipped", "NOTION_ECOSYSTEM_DATABASE_ID is missing."))
    if settings.notion_radar_snapshots_database_id:
        checks.append(
            _retrieve_notion_database(client, settings.notion_radar_snapshots_database_id, "live_notion_radar_database")
        )
    else:
        checks.append(DoctorCheck("live_notion_radar_database", "skipped", "NOTION_RADAR_SNAPSHOTS_DATABASE_ID is missing."))
    if settings.notion_radar_entities_database_id:
        checks.append(
            _retrieve_notion_database(client, settings.notion_radar_entities_database_id, "live_notion_radar_entities_database")
        )
    else:
        checks.append(DoctorCheck("live_notion_radar_entities_database", "skipped", "NOTION_RADAR_ENTITIES_DATABASE_ID is missing."))
    return tuple(checks)


def _retrieve_notion_database(client: NotionClient, database_id: str, check_name: str) -> DoctorCheck:
    try:
        database = client.retrieve_database(database_id)
        return DoctorCheck(check_name, "ok", f"Retrieved Notion database {database.id}.")
    except Exception as exc:
        return DoctorCheck(check_name, "failed", str(exc))


def _check_live_telegram(settings: Settings, client: TelegramClient | None) -> DoctorCheck:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return DoctorCheck("live_telegram", "skipped", "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
    client = client or TelegramClient(bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
    try:
        bot = client.get_me()
    except Exception as exc:
        return DoctorCheck("live_telegram", "failed", str(exc))
    username = f"@{bot.username}" if bot.username else str(bot.id)
    return DoctorCheck("live_telegram", "ok", f"Authenticated Telegram bot {username}.")
