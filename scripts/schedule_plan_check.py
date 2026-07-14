from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.schedule_plan import build_schedule_plan, render_schedule_plan, validate_production_schedule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview and validate the Intelligence Hub Windows scheduled task plan.")
    parser.add_argument("--validate-production", action="store_true", help="Require full production schedule coverage.")
    parser.add_argument("--minimal", action="store_true", help="Preview only the default daily dry-run task.")
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
    print(render_schedule_plan(plan, project_root=PROJECT_ROOT))
    if not args.validate_production:
        return 0
    failures = validate_production_schedule(plan)
    if not failures:
        print("")
        print("Intelligence Hub production schedule plan passed.")
        return 0
    print("")
    print(f"Intelligence Hub production schedule plan failed with {len(failures)} issue(s):")
    for failure in failures:
        print(f"- {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
