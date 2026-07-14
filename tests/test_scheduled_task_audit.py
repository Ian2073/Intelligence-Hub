from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from core.schedule_plan import build_schedule_plan
from core.scheduled_task_audit import audit_scheduled_tasks, parse_schtasks_csv, render_scheduled_task_audit


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_parse_schtasks_csv_and_audit_matching_production_plan() -> None:
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
    installed = parse_schtasks_csv(_csv_for_plan(plan))

    report = audit_scheduled_tasks(plan, installed, project_root=PROJECT_ROOT)
    rendered = render_scheduled_task_audit(report)

    assert report.ok is True
    assert report.failures == ()
    assert "Result: passed" in rendered
    assert "Hermes Intelligence OS Radar: OK" in rendered


def test_audit_scheduled_tasks_reports_missing_command_and_time_mismatch() -> None:
    plan = build_schedule_plan(
        live_github=True,
        live_papers_with_code=True,
        live_domain_rss=True,
        publish_notion=True,
        send_telegram=True,
        model_synthesis=True,
        include_weekly=True,
        include_radar=True,
    )
    csv_text = "\n".join(
        (
            '"TaskName","Task To Run","Schedule Type","Start Time"',
            (
                '"\\Hermes Intelligence OS Daily",'
                f'"{_task_command("run_hermes_orchestration.ps1", "-NoDashboard")}",'
                '"Daily","08:00"'
            ),
            (
                '"\\Hermes Intelligence OS Radar",'
                f'"{_task_command("run_radar_snapshot.ps1", "-PublishNotion -SendTelegram")}",'
                '"Daily","09:10"'
            ),
        )
    )

    report = audit_scheduled_tasks(plan, parse_schtasks_csv(csv_text), project_root=PROJECT_ROOT)
    failures = {item.name: item.detail for item in report.failures}

    assert report.ok is False
    assert "command mismatch" in failures["Hermes Intelligence OS Daily"]
    assert failures["Hermes Intelligence OS Weekly"] == "Task is not installed."
    assert "start time mismatch" in failures["Hermes Intelligence OS Radar"]


def test_audit_scheduled_tasks_cli_accepts_csv_fixture(tmp_path) -> None:
    plan = build_schedule_plan()
    csv_file = tmp_path / "schtasks.csv"
    csv_file.write_text(_csv_for_plan(plan), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_scheduled_tasks.py",
            "--minimal",
            "--from-csv",
            str(csv_file),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Result: passed" in result.stdout


def test_audit_scheduled_tasks_cli_reports_missing_csv_without_traceback(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_scheduled_tasks.py",
            "--from-csv",
            str(tmp_path / "missing.csv"),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Result: failed" in result.stdout
    assert "Could not read scheduled task data" in result.stdout
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def _csv_for_plan(plan) -> str:
    lines = ['"TaskName","Task To Run","Schedule Type","Start Time"']
    for task in plan.tasks:
        command = task.command(PROJECT_ROOT).replace('"', '""')
        lines.append(f'"\\{task.name}","{command}","{task.schedule.title()}","{task.time}"')
    return "\n".join(lines)


def _task_command(script_name: str, flags: str) -> str:
    script = PROJECT_ROOT / "scripts" / script_name
    return f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""{script}"" {flags}'
