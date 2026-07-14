from __future__ import annotations

from pathlib import Path

from core.schedule_plan import build_schedule_plan, render_schedule_plan, validate_production_schedule


def test_build_schedule_plan_includes_full_production_tasks_and_flags() -> None:
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

    by_name = {task.name: task for task in plan.tasks}

    assert len(plan.tasks) == 6
    assert by_name["Intelligence Hub Daily"].flags == (
        "-LiveGitHub",
        "-LivePapersWithCode",
        "-LiveDomainRss",
        "-PublishNotion",
        "-SendTelegram",
        "-ModelSynthesis",
        "-NoDashboard",
    )
    assert by_name["Intelligence Hub Weekly"].extra_args == ("/D", "MON")
    assert by_name["Intelligence Hub Monthly"].extra_args == ("/D", "1")
    assert by_name["Intelligence Hub Radar"].flags == ("-PublishNotion", "-SendTelegram")
    assert validate_production_schedule(plan) == ()


def test_validate_production_schedule_reports_missing_coverage() -> None:
    plan = build_schedule_plan()

    failures = validate_production_schedule(plan)

    assert "Missing task: Intelligence Hub Weekly" in failures
    assert "Daily task missing -LiveGitHub." in failures
    assert "Daily task missing -SendTelegram." in failures


def test_render_schedule_plan_uses_absolute_project_scripts() -> None:
    plan = build_schedule_plan(include_dashboard=True)
    project_root = Path("E:/intelligence-hub")

    rendered = render_schedule_plan(plan, project_root=project_root)

    expected_daily_script = str(project_root / "scripts" / "run_hermes_orchestration.ps1")
    assert f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{expected_daily_script}"' in rendered
    assert "Intelligence Hub Dashboard" in rendered
