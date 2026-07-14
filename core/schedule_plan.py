from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScheduledTaskSpec:
    name: str
    schedule: str
    time: str
    script: str
    flags: tuple[str, ...]
    extra_args: tuple[str, ...] = ()

    def command(self, project_root: Path) -> str:
        script_path = project_root / self.script
        flag_text = f" {' '.join(self.flags)}" if self.flags else ""
        return f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{script_path}"{flag_text}'


@dataclass(frozen=True)
class SchedulePlan:
    tasks: tuple[ScheduledTaskSpec, ...]


def build_schedule_plan(
    *,
    daily_time: str = "08:00",
    weekly_time: str = "08:15",
    monthly_time: str = "08:30",
    dashboard_time: str = "08:45",
    radar_time: str = "08:50",
    decision_review_time: str = "08:55",
    live_github: bool = False,
    live_papers: bool = False,
    live_papers_with_code: bool = False,
    live_domain_rss: bool = False,
    publish_notion: bool = False,
    send_telegram: bool = False,
    model_synthesis: bool = False,
    include_weekly: bool = False,
    include_monthly: bool = False,
    include_dashboard: bool = False,
    include_radar: bool = False,
    include_decision_review: bool = False,
) -> SchedulePlan:
    live_flags = _flags(
        ("-LiveGitHub", live_github),
        ("-LivePapers", live_papers),
        ("-LivePapersWithCode", live_papers_with_code),
        ("-LiveDomainRss", live_domain_rss),
        ("-PublishNotion", publish_notion),
        ("-SendTelegram", send_telegram),
        ("-ModelSynthesis", model_synthesis),
    )
    publish_flags = _flags(
        ("-PublishNotion", publish_notion),
        ("-SendTelegram", send_telegram),
    )
    synthesis_publish_flags = _flags(
        ("-PublishNotion", publish_notion),
        ("-SendTelegram", send_telegram),
        ("-ModelSynthesis", model_synthesis),
    )

    tasks: list[ScheduledTaskSpec] = [
        ScheduledTaskSpec(
            name="Intelligence Hub Daily",
            schedule="DAILY",
            time=daily_time,
            script="scripts/run_hermes_orchestration.ps1",
            flags=(*live_flags, "-NoDashboard"),
        )
    ]
    if include_weekly:
        tasks.append(
            ScheduledTaskSpec(
                name="Intelligence Hub Weekly",
                schedule="WEEKLY",
                time=weekly_time,
                script="scripts/run_weekly_intelligence.ps1",
                flags=synthesis_publish_flags,
                extra_args=("/D", "MON"),
            )
        )
    if include_monthly:
        tasks.append(
            ScheduledTaskSpec(
                name="Intelligence Hub Monthly",
                schedule="MONTHLY",
                time=monthly_time,
                script="scripts/run_monthly_intelligence.ps1",
                flags=synthesis_publish_flags,
                extra_args=("/D", "1"),
            )
        )
    if include_dashboard:
        tasks.append(
            ScheduledTaskSpec(
                name="Intelligence Hub Dashboard",
                schedule="DAILY",
                time=dashboard_time,
                script="scripts/run_executive_dashboard.ps1",
                flags=synthesis_publish_flags,
            )
        )
    if include_radar:
        tasks.append(
            ScheduledTaskSpec(
                name="Intelligence Hub Radar",
                schedule="DAILY",
                time=radar_time,
                script="scripts/run_radar_snapshot.ps1",
                flags=publish_flags,
            )
        )
    if include_decision_review:
        tasks.append(
            ScheduledTaskSpec(
                name="Intelligence Hub Decision Review",
                schedule="WEEKLY",
                time=decision_review_time,
                script="scripts/run_decision_review.ps1",
                flags=publish_flags,
                extra_args=("/D", "MON"),
            )
        )
    return SchedulePlan(tasks=tuple(tasks))


def validate_production_schedule(plan: SchedulePlan) -> tuple[str, ...]:
    failures: list[str] = []
    by_name = {task.name: task for task in plan.tasks}
    required = (
        "Intelligence Hub Daily",
        "Intelligence Hub Weekly",
        "Intelligence Hub Monthly",
        "Intelligence Hub Dashboard",
        "Intelligence Hub Radar",
        "Intelligence Hub Decision Review",
    )
    for name in required:
        if name not in by_name:
            failures.append(f"Missing task: {name}")

    daily = by_name.get("Intelligence Hub Daily")
    if daily is not None:
        for flag in ("-LiveGitHub", "-LivePapersWithCode", "-LiveDomainRss", "-PublishNotion", "-SendTelegram", "-ModelSynthesis"):
            if flag not in daily.flags:
                failures.append(f"Daily task missing {flag}.")
        if "-NoDashboard" not in daily.flags:
            failures.append("Daily task must include -NoDashboard when dashboard is scheduled separately.")

    for name in ("Intelligence Hub Weekly", "Intelligence Hub Monthly", "Intelligence Hub Dashboard"):
        task = by_name.get(name)
        if task is None:
            continue
        for flag in ("-PublishNotion", "-SendTelegram", "-ModelSynthesis"):
            if flag not in task.flags:
                failures.append(f"{name} missing {flag}.")

    for name in ("Intelligence Hub Radar", "Intelligence Hub Decision Review"):
        task = by_name.get(name)
        if task is None:
            continue
        for flag in ("-PublishNotion", "-SendTelegram"):
            if flag not in task.flags:
                failures.append(f"{name} missing {flag}.")
    return tuple(failures)


def render_schedule_plan(plan: SchedulePlan, *, project_root: Path) -> str:
    lines = ["# Intelligence Hub Schedule Plan", ""]
    for task in plan.tasks:
        lines.append(f"- {task.name}: {task.schedule} at {task.time}")
        lines.append(f"  command: {task.command(project_root)}")
        if task.extra_args:
            lines.append(f"  schtasks extra args: {' '.join(task.extra_args)}")
    return "\n".join(lines)


def _flags(*pairs: tuple[str, bool]) -> tuple[str, ...]:
    return tuple(flag for flag, enabled in pairs if enabled)
