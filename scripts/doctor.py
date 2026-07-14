from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from core.doctor import DoctorCheck, run_doctor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Intelligence Hub readiness.")
    parser.add_argument("--live", action="store_true", help="Verify external APIs, not only local readiness.")
    parser.add_argument("--profile", choices=("default", "demo"), default="default", help="Select readiness profile.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    report = run_doctor(settings, live=args.live, profile=args.profile)
    for check in report.checks:
        print(_format_check(check))
    if report.ok:
        print("Intelligence Hub doctor completed without failed checks.")
        return 0
    print(f"Intelligence Hub doctor found {len(report.failures)} failed check(s).")
    return 1


def _format_check(check: DoctorCheck) -> str:
    return f"[{check.status.upper()}] {check.name}: {check.detail}"


if __name__ == "__main__":
    raise SystemExit(main())
