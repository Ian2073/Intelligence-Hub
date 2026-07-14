from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings
from core.memory import MemoryStore
from core.operational_status import build_operational_status, render_operational_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legacy Hermes entrypoint for Intelligence Hub operational status.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Only consider briefs at or before this date.")
    parser.add_argument("--include-future", action="store_true", help="Include briefs dated after --as-of.")
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
        status = build_operational_status(settings, store, as_of=args.as_of, include_future=args.include_future)
    finally:
        store.close()
    print(render_operational_status(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
