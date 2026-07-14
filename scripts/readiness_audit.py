from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.acceptance import run_acceptance_check
from core.config import load_settings
from core.doctor import run_go_live_check
from core.memory import MemoryStore
from core.operational_status import build_operational_status
from core.readiness_audit import build_readiness_audit, render_readiness_audit
from core.schedule_plan import build_schedule_plan, validate_production_schedule
from core.scheduled_task_audit import (
    ScheduledTaskAuditItem,
    ScheduledTaskAuditReport,
    audit_scheduled_tasks,
    parse_schtasks_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Hermes Intelligence OS final readiness audit.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Only consider runtime briefs at or before this date.")
    parser.add_argument("--include-future", action="store_true", help="Include runtime briefs dated after --as-of.")
    parser.add_argument("--live", action="store_true", help="Include read-only live API checks in the go-live gate.")
    parser.add_argument("--skip-acceptance", action="store_true", help="Skip the local fixture acceptance loop.")
    parser.add_argument("--check-scheduled-tasks", action="store_true", help="Audit installed Windows scheduled tasks.")
    parser.add_argument("--scheduled-tasks-from-csv", help="Read schtasks CSV output from a file for scheduled task audit.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)

    store = MemoryStore(settings.memory_db)
    try:
        operational_status = build_operational_status(
            settings,
            store,
            as_of=args.as_of,
            include_future=args.include_future,
        )
    finally:
        store.close()

    acceptance_report = None if args.skip_acceptance else run_acceptance_check(settings, run_date=args.as_of)
    go_live_report = run_go_live_check(settings, live=args.live)
    schedule_plan = build_schedule_plan(
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
    schedule_failures = validate_production_schedule(schedule_plan)
    scheduled_task_report = None
    if args.check_scheduled_tasks or args.scheduled_tasks_from_csv:
        scheduled_task_report = _scheduled_task_report(schedule_plan, from_csv=args.scheduled_tasks_from_csv)
    report = build_readiness_audit(
        as_of=args.as_of,
        operational_status=operational_status,
        acceptance_report=acceptance_report,
        go_live_report=go_live_report,
        schedule_failures=schedule_failures,
        scheduled_task_report=scheduled_task_report,
    )
    print(render_readiness_audit(report))
    return 0 if report.ready else 1


def _scheduled_task_report(schedule_plan, *, from_csv: str | None) -> ScheduledTaskAuditReport:
    try:
        csv_text = Path(from_csv).read_text(encoding="utf-8-sig") if from_csv else _query_schtasks()
    except OSError as exc:
        return ScheduledTaskAuditReport((ScheduledTaskAuditItem("Windows Task Scheduler", "failed", f"Could not read scheduled task data: {exc}"),))
    except RuntimeError as exc:
        return ScheduledTaskAuditReport((ScheduledTaskAuditItem("Windows Task Scheduler", "failed", f"Could not query Windows Task Scheduler: {exc}"),))
    return audit_scheduled_tasks(schedule_plan, parse_schtasks_csv(csv_text), project_root=PROJECT_ROOT)


def _query_schtasks() -> str:
    result = subprocess.run(
        ["schtasks.exe", "/Query", "/FO", "CSV", "/V"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = _decode_output(result.stderr).strip() or _decode_output(result.stdout).strip() or "schtasks.exe query failed."
        raise RuntimeError(detail)
    return _decode_output(result.stdout)


def _decode_output(data: bytes) -> str:
    for enc in ("utf-8", "cp950", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
