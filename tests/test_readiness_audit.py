from __future__ import annotations

from core.acceptance import AcceptanceReport, AcceptanceStage
from core.doctor import DoctorCheck, DoctorReport
from core.operational_status import CredentialGap, LatestBriefStatus, OperationalStatus
from core.readiness_audit import build_readiness_audit, render_readiness_audit
from core.scheduled_task_audit import ScheduledTaskAuditItem, ScheduledTaskAuditReport


def test_readiness_audit_reports_ready_when_all_requirements_pass() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(),
        acceptance_report=_acceptance_report(ok=True),
        go_live_report=DoctorReport((DoctorCheck("go_live", "ok", "ready"),)),
        schedule_failures=(),
    )
    rendered = render_readiness_audit(report)

    assert report.ready is True
    assert report.failures == ()
    assert any(requirement.name == "Installed schedule" and requirement.status == "skipped" for requirement in report.requirements)
    assert "| Go-live gate | OK | Required production configuration passed. |" in rendered
    assert "Result: ready" in rendered
    assert "https://notion.local/daily" in rendered


def test_readiness_audit_blocks_on_credentials_and_go_live_failures() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(
            credential_gaps=(
                CredentialGap("GITHUB_TOKEN", ("GH_TOKEN",)),
                CredentialGap("TELEGRAM_BOT_TOKEN", ("TELEGRAM_TOKEN", "TG_BOT_TOKEN")),
                CredentialGap("TELEGRAM_CHAT_ID", ("TG_CHAT_ID",)),
            )
        ),
        acceptance_report=_acceptance_report(ok=True),
        go_live_report=DoctorReport(
            (
                DoctorCheck("go_live_github_token", "failed", "GITHUB_TOKEN is required for go-live."),
                DoctorCheck("go_live_telegram_bot_token", "failed", "TELEGRAM_BOT_TOKEN is required for go-live."),
                DoctorCheck("go_live_telegram_chat_id", "failed", "TELEGRAM_CHAT_ID is required for go-live."),
            )
        ),
        schedule_failures=(),
    )
    rendered = render_readiness_audit(report)

    assert report.ready is False
    assert [failure.name for failure in report.failures] == [
        "Go-live gate",
        "GitHub credentials",
        "Telegram credentials",
    ]
    assert "Result: not ready" in rendered
    assert "- GitHub credentials: GITHUB_TOKEN is missing." in rendered
    assert "- Telegram credentials: Missing TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID." in rendered


def test_readiness_audit_adds_next_step_for_unsplit_model_tiers() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(),
        acceptance_report=_acceptance_report(ok=True),
        go_live_report=DoctorReport(
            (
                DoctorCheck(
                    "go_live_model_tier_split",
                    "failed",
                    "HERMES_FAST_MODEL and HERMES_PRO_MODEL must be different.",
                ),
            )
        ),
        schedule_failures=(),
    )

    assert report.next_commands[0] == (
        "Set distinct HERMES_FAST_MODEL and HERMES_PRO_MODEL values in .env, "
        "then rerun scripts\\go_live_check.py"
    )


def test_readiness_audit_can_require_installed_scheduled_tasks() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(),
        acceptance_report=_acceptance_report(ok=True),
        go_live_report=DoctorReport((DoctorCheck("go_live", "ok", "ready"),)),
        schedule_failures=(),
        scheduled_task_report=ScheduledTaskAuditReport(
            (
                ScheduledTaskAuditItem(
                    "Intelligence Hub Daily",
                    "ok",
                    "Installed task matches expected command, schedule, and start time.",
                ),
            )
        ),
    )

    assert report.ready is True
    assert any(
        requirement.name == "Installed schedule" and requirement.status == "ok"
        for requirement in report.requirements
    )


def test_readiness_audit_blocks_on_installed_scheduled_task_failures() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(),
        acceptance_report=_acceptance_report(ok=True),
        go_live_report=DoctorReport((DoctorCheck("go_live", "ok", "ready"),)),
        schedule_failures=(),
        scheduled_task_report=ScheduledTaskAuditReport(
            (
                ScheduledTaskAuditItem("Intelligence Hub Daily", "failed", "Task is not installed."),
            )
        ),
    )
    rendered = render_readiness_audit(report)

    assert report.ready is False
    assert [failure.name for failure in report.failures] == ["Installed schedule"]
    assert "Installed schedule | FAILED" in rendered
    assert "First issue: Task is not installed." in rendered


def test_readiness_audit_blocks_on_missing_runtime_surface_and_acceptance_skip() -> None:
    report = build_readiness_audit(
        as_of="2026-07-03",
        operational_status=_operational_status(
            latest_briefs=_briefs("daily"),
            entity_count=0,
            observation_count=0,
            decision_count=0,
            pending_notification_count=2,
        ),
        acceptance_report=None,
        go_live_report=DoctorReport((DoctorCheck("go_live", "ok", "ready"),)),
        schedule_failures=("Missing task: Intelligence Hub Weekly",),
    )
    rendered = render_readiness_audit(report)

    assert report.ready is False
    assert [failure.name for failure in report.failures] == [
        "Runtime memory",
        "Notion surfaces",
        "Local acceptance",
        "Production schedule",
        "Telegram outbox",
    ]
    assert "missing: weekly, monthly, dashboard, radar, decision_review" in rendered
    assert "Acceptance check was skipped." in rendered
    assert "2 pending notification(s) must be flushed." in rendered


def _acceptance_report(*, ok: bool) -> AcceptanceReport:
    stages = (
        AcceptanceStage("daily", "published", "sent"),
        AcceptanceStage("weekly", "published", "sent"),
        AcceptanceStage("monthly", "published", "sent"),
        AcceptanceStage("dashboard", "published", "sent"),
        AcceptanceStage("radar", "published", "sent"),
        AcceptanceStage("decision_review", "published", "sent"),
    )
    failures = () if ok else ("daily Notion status is dry-run, expected published.",)
    return AcceptanceReport(
        ok=ok,
        stages=stages,
        entity_count=12,
        observation_count=30,
        decision_count=10,
        brief_count=6,
        run_count=6,
        failures=failures,
    )


def _operational_status(
    *,
    credential_gaps: tuple[CredentialGap, ...] = (),
    latest_briefs: tuple[LatestBriefStatus, ...] | None = None,
    entity_count: int = 12,
    observation_count: int = 30,
    decision_count: int = 10,
    pending_notification_count: int = 0,
) -> OperationalStatus:
    return OperationalStatus(
        go_live_ready=not credential_gaps,
        credential_gaps=credential_gaps,
        latest_briefs=latest_briefs if latest_briefs is not None else _briefs(),
        entity_count=entity_count,
        observation_count=observation_count,
        decision_count=decision_count,
        pending_notification_count=pending_notification_count,
        next_commands=("python scripts/go_live_check.py",),
    )


def _briefs(*brief_types: str) -> tuple[LatestBriefStatus, ...]:
    selected = brief_types or ("daily", "weekly", "monthly", "dashboard", "radar", "decision_review")
    return tuple(
        LatestBriefStatus(
            brief_type=brief_type,
            title=f"Hermes {brief_type}",
            period_start="2026-07-03",
            period_end="2026-07-03",
            notion_status="published",
            notion_url=f"https://notion.local/{brief_type}",
            telegram_status="sent",
            telegram_detail="sent",
            source="run",
        )
        for brief_type in selected
    )
