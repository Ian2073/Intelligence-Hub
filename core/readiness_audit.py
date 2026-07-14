from __future__ import annotations

from dataclasses import dataclass

from core.acceptance import AcceptanceReport
from core.doctor import DoctorReport
from core.operational_status import BRIEF_TYPES, HermesOperationalStatus, LatestBriefStatus
from core.scheduled_task_audit import ScheduledTaskAuditReport


@dataclass(frozen=True)
class ReadinessRequirement:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ReadinessAuditReport:
    as_of: str
    ready: bool
    requirements: tuple[ReadinessRequirement, ...]
    latest_briefs: tuple[LatestBriefStatus, ...]
    next_commands: tuple[str, ...]

    @property
    def failures(self) -> tuple[ReadinessRequirement, ...]:
        return tuple(requirement for requirement in self.requirements if requirement.status == "failed")


def build_readiness_audit(
    *,
    as_of: str,
    operational_status: HermesOperationalStatus,
    acceptance_report: AcceptanceReport | None,
    go_live_report: DoctorReport,
    schedule_failures: tuple[str, ...],
    scheduled_task_report: ScheduledTaskAuditReport | None = None,
) -> ReadinessAuditReport:
    requirements = (
        _memory_requirement(operational_status),
        _latest_briefs_requirement(operational_status),
        _acceptance_requirement(acceptance_report),
        _schedule_requirement(schedule_failures),
        _installed_schedule_requirement(scheduled_task_report),
        _go_live_requirement(go_live_report),
        _pending_notifications_requirement(operational_status),
        _github_credentials_requirement(operational_status),
        _telegram_credentials_requirement(operational_status),
    )
    return ReadinessAuditReport(
        as_of=as_of,
        ready=all(requirement.status != "failed" for requirement in requirements),
        requirements=requirements,
        latest_briefs=operational_status.latest_briefs,
        next_commands=_next_commands(operational_status.next_commands, go_live_report),
    )


def render_readiness_audit(report: ReadinessAuditReport) -> str:
    lines = ["# Hermes Readiness Audit", ""]
    lines.append(f"As of: {report.as_of}")
    lines.append(f"Result: {'ready' if report.ready else 'not ready'}")
    lines.append("")
    lines.append("## Requirements")
    lines.append("| Requirement | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for requirement in report.requirements:
        lines.append(
            f"| {requirement.name} | {requirement.status.upper()} | {_table_escape(requirement.detail)} |"
        )

    lines.append("")
    lines.append("## Latest Notion Surfaces")
    if not report.latest_briefs:
        lines.append("- No latest briefs recorded.")
    else:
        for brief in report.latest_briefs:
            url = brief.notion_url or "(no Notion URL)"
            lines.append(
                f"- {brief.brief_type}: {brief.title} ({brief.period_start} to {brief.period_end}) "
                f"Notion={brief.notion_status} Telegram={brief.telegram_status} URL={url}"
            )

    lines.append("")
    lines.append("## Blocking Items")
    if not report.failures:
        lines.append("- None.")
    else:
        lines.extend(f"- {failure.name}: {failure.detail}" for failure in report.failures)

    lines.append("")
    lines.append("## Next Commands")
    for command in report.next_commands:
        lines.append(f"- `{command}`")
    return "\n".join(lines)


def _memory_requirement(status: HermesOperationalStatus) -> ReadinessRequirement:
    missing = []
    if status.entity_count <= 0:
        missing.append("entities")
    if status.observation_count <= 0:
        missing.append("observations")
    if status.decision_count <= 0:
        missing.append("decisions")
    if missing:
        return ReadinessRequirement("Runtime memory", "failed", f"Missing persisted {', '.join(missing)}.")
    return ReadinessRequirement(
        "Runtime memory",
        "ok",
        f"{status.entity_count} entities, {status.observation_count} observations, {status.decision_count} decisions.",
    )


def _latest_briefs_requirement(status: HermesOperationalStatus) -> ReadinessRequirement:
    by_type = {brief.brief_type: brief for brief in status.latest_briefs}
    missing = [brief_type for brief_type in BRIEF_TYPES if brief_type not in by_type]
    unpublished = [
        f"{brief.brief_type}={brief.notion_status}"
        for brief in status.latest_briefs
        if brief.notion_status != "published"
    ]
    if missing or unpublished:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unpublished:
            details.append(f"not published: {', '.join(unpublished)}")
        return ReadinessRequirement("Notion surfaces", "failed", "; ".join(details))
    return ReadinessRequirement("Notion surfaces", "ok", f"{len(BRIEF_TYPES)} latest surfaces are published.")


def _acceptance_requirement(report: AcceptanceReport | None) -> ReadinessRequirement:
    if report is None:
        return ReadinessRequirement("Local acceptance", "failed", "Acceptance check was skipped.")
    if not report.ok:
        return ReadinessRequirement("Local acceptance", "failed", f"{len(report.failures)} acceptance failure(s).")
    return ReadinessRequirement(
        "Local acceptance",
        "ok",
        f"{len(report.stages)} stages passed with {report.brief_count} briefs and {report.run_count} runs.",
    )


def _schedule_requirement(failures: tuple[str, ...]) -> ReadinessRequirement:
    if failures:
        return ReadinessRequirement("Production schedule", "failed", "; ".join(failures))
    return ReadinessRequirement("Production schedule", "ok", "Full production schedule plan validates.")


def _installed_schedule_requirement(report: ScheduledTaskAuditReport | None) -> ReadinessRequirement:
    if report is None:
        return ReadinessRequirement(
            "Installed schedule",
            "skipped",
            "Installed Windows scheduled task audit was not requested.",
        )
    if not report.ok:
        names = ", ".join(item.name for item in report.failures)
        first_detail = report.failures[0].detail if report.failures else "No detail."
        return ReadinessRequirement(
            "Installed schedule",
            "failed",
            f"{len(report.failures)} installed task issue(s): {names}. First issue: {first_detail}",
        )
    return ReadinessRequirement(
        "Installed schedule",
        "ok",
        f"{len(report.items)} installed scheduled task(s) match the production plan.",
    )


def _go_live_requirement(report: DoctorReport) -> ReadinessRequirement:
    if not report.ok:
        names = ", ".join(check.name for check in report.failures)
        return ReadinessRequirement("Go-live gate", "failed", f"{len(report.failures)} failed check(s): {names}.")
    return ReadinessRequirement("Go-live gate", "ok", "Required production configuration passed.")


def _pending_notifications_requirement(status: HermesOperationalStatus) -> ReadinessRequirement:
    if status.pending_notification_count:
        return ReadinessRequirement(
            "Telegram outbox",
            "failed",
            f"{status.pending_notification_count} pending notification(s) must be flushed.",
        )
    return ReadinessRequirement("Telegram outbox", "ok", "No pending notifications.")


def _github_credentials_requirement(status: HermesOperationalStatus) -> ReadinessRequirement:
    if any(gap.name == "GITHUB_TOKEN" for gap in status.credential_gaps):
        return ReadinessRequirement("GitHub credentials", "failed", "GITHUB_TOKEN is missing.")
    return ReadinessRequirement("GitHub credentials", "ok", "GitHub token is configured.")


def _telegram_credentials_requirement(status: HermesOperationalStatus) -> ReadinessRequirement:
    missing = [gap.name for gap in status.credential_gaps if gap.name.startswith("TELEGRAM_")]
    if missing:
        return ReadinessRequirement("Telegram credentials", "failed", f"Missing {', '.join(missing)}.")
    return ReadinessRequirement("Telegram credentials", "ok", "Telegram bot token and chat id are configured.")


def _table_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _next_commands(base_commands: tuple[str, ...], go_live_report: DoctorReport) -> tuple[str, ...]:
    commands = list(base_commands)
    failure_names = {check.name for check in go_live_report.failures}
    if "go_live_model_tier_split" in failure_names:
        commands.insert(
            0,
            "Set distinct HERMES_FAST_MODEL and HERMES_PRO_MODEL values in .env, then rerun scripts\\go_live_check.py",
        )
    return tuple(dict.fromkeys(commands))
