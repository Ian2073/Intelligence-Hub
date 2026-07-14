from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.schedule_plan import build_schedule_plan
from core.scheduled_task_audit import audit_scheduled_tasks, parse_schtasks_csv, render_scheduled_task_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit installed Intelligence Hub Windows scheduled tasks.")
    parser.add_argument("--from-csv", help="Read schtasks CSV output from a file instead of calling schtasks.exe.")
    parser.add_argument("--minimal", action="store_true", help="Audit only the default daily dry-run task.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    plan = (
        build_schedule_plan()
        if args.minimal
        else build_schedule_plan(
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
    )
    try:
        csv_text = Path(args.from_csv).read_text(encoding="utf-8-sig") if args.from_csv else _query_schtasks()
    except OSError as exc:
        print("# Intelligence Hub Scheduled Task Audit")
        print("")
        print("Result: failed")
        print("")
        print(f"Could not read scheduled task data: {exc}")
        return 1
    except RuntimeError as exc:
        print("# Intelligence Hub Scheduled Task Audit")
        print("")
        print("Result: failed")
        print("")
        print(f"Could not query Windows Task Scheduler: {exc}")
        return 1
    report = audit_scheduled_tasks(plan, parse_schtasks_csv(csv_text), project_root=PROJECT_ROOT)
    print(render_scheduled_task_audit(report))
    return 0 if report.ok else 1


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
