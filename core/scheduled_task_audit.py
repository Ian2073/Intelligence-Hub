from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path

from core.schedule_plan import SchedulePlan, ScheduledTaskSpec


@dataclass(frozen=True)
class InstalledScheduledTask:
    name: str
    task_to_run: str
    schedule_type: str
    start_time: str


@dataclass(frozen=True)
class ScheduledTaskAuditItem:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ScheduledTaskAuditReport:
    items: tuple[ScheduledTaskAuditItem, ...]

    @property
    def ok(self) -> bool:
        return all(item.status == "ok" for item in self.items)

    @property
    def failures(self) -> tuple[ScheduledTaskAuditItem, ...]:
        return tuple(item for item in self.items if item.status == "failed")


def parse_schtasks_csv(text: str) -> tuple[InstalledScheduledTask, ...]:
    if not text.strip():
        return ()
    reader = csv.DictReader(StringIO(text))
    tasks: list[InstalledScheduledTask] = []
    for row in reader:
        name = _task_name(row.get("TaskName", ""))
        if not name:
            continue
        tasks.append(
            InstalledScheduledTask(
                name=name,
                task_to_run=(row.get("Task To Run") or "").strip(),
                schedule_type=(row.get("Schedule Type") or row.get("Schedule") or "").strip(),
                start_time=(row.get("Start Time") or "").strip(),
            )
        )
    return tuple(tasks)


def audit_scheduled_tasks(
    plan: SchedulePlan,
    installed_tasks: tuple[InstalledScheduledTask, ...],
    *,
    project_root: Path,
) -> ScheduledTaskAuditReport:
    installed_by_name = {task.name: task for task in installed_tasks}
    items: list[ScheduledTaskAuditItem] = []
    for expected in plan.tasks:
        actual = installed_by_name.get(expected.name)
        if actual is None:
            items.append(ScheduledTaskAuditItem(expected.name, "failed", "Task is not installed."))
            continue
        failures = _task_failures(expected, actual, project_root=project_root)
        if failures:
            items.append(ScheduledTaskAuditItem(expected.name, "failed", "; ".join(failures)))
        else:
            items.append(ScheduledTaskAuditItem(expected.name, "ok", "Installed task matches expected command, schedule, and start time."))
    return ScheduledTaskAuditReport(tuple(items))


def render_scheduled_task_audit(report: ScheduledTaskAuditReport) -> str:
    lines = ["# Intelligence Hub Scheduled Task Audit", ""]
    lines.append(f"Result: {'passed' if report.ok else 'failed'}")
    lines.append("")
    lines.append("## Tasks")
    for item in report.items:
        lines.append(f"- {item.name}: {item.status.upper()} - {item.detail}")
    lines.append("")
    lines.append("## Failures")
    if report.failures:
        lines.extend(f"- {item.name}: {item.detail}" for item in report.failures)
    else:
        lines.append("- None.")
    return "\n".join(lines)


def _task_failures(expected: ScheduledTaskSpec, actual: InstalledScheduledTask, *, project_root: Path) -> list[str]:
    failures: list[str] = []
    expected_command = expected.command(project_root)
    if _normalize_command(expected_command) != _normalize_command(actual.task_to_run):
        failures.append(f"command mismatch; expected {expected_command!r}, got {actual.task_to_run!r}")
    expected_schedule = expected.schedule.casefold()
    actual_schedule = actual.schedule_type.casefold()
    if expected_schedule and expected_schedule not in actual_schedule:
        failures.append(f"schedule mismatch; expected {expected.schedule}, got {actual.schedule_type or '(empty)'}")
    expected_time = _normalize_time(expected.time)
    actual_time = _normalize_time(actual.start_time)
    if expected_time and actual_time and expected_time != actual_time:
        failures.append(f"start time mismatch; expected {expected.time}, got {actual.start_time}")
    elif expected_time and not actual_time:
        failures.append(f"start time missing; expected {expected.time}")
    return failures


def _task_name(value: str) -> str:
    return value.strip().lstrip("\\/")


def _normalize_command(value: str) -> str:
    normalized = value.replace('\\"', '"').replace("`\"", '"')
    normalized = normalized.replace('"', '')
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.casefold()


def _normalize_time(value: str) -> str | None:
    clean = value.strip()
    if not clean:
        return None
    # Handle Chinese locale AM/PM prefixes from schtasks (e.g. '上午 08:00:00', '下午 02:30:00')
    if clean.startswith("\u4e0a\u5348"):  # 上午
        clean = clean.replace("\u4e0a\u5348", "", 1).strip()
    elif clean.startswith("\u4e0b\u5348"):  # 下午
        clean = clean.replace("\u4e0b\u5348", "", 1).strip()
        # Convert PM hours: parse then add 12 if needed
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                t = datetime.strptime(clean, fmt)
                if t.hour < 12:
                    t = t.replace(hour=t.hour + 12)
                return t.strftime("%H:%M")
            except ValueError:
                continue
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(clean, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None
