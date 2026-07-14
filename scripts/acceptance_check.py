from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.acceptance import render_acceptance_report, run_acceptance_check
from core.config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hermes local end-to-end acceptance check with fixtures.")
    parser.add_argument("--date", default="2026-07-02", help="Fixture acceptance run date in YYYY-MM-DD format.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    report = run_acceptance_check(settings, run_date=args.date)
    print(render_acceptance_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
