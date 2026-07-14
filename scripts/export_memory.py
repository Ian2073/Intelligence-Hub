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
from core.memory_export import export_memory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Intelligence Hub runtime memory to JSONL and Markdown.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="Export date in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", help="Output directory. Defaults to exports/memory-<as-of>.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "exports" / f"memory-{args.as_of}"
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    store = MemoryStore(settings.memory_db)
    try:
        result = export_memory(store, output_dir=output_dir, as_of=args.as_of)
    finally:
        store.close()

    print(f"Intelligence Hub memory exported: {result.output_dir}")
    print(f"Entities: {result.entity_count}")
    print(f"Observations: {result.observation_count}")
    print(f"Relationships: {result.relationship_count}")
    print(f"Decisions: {result.decision_count}")
    print(f"Briefs: {result.brief_count}")
    print(f"Runs: {result.run_count}")
    print(f"Notification outbox: {result.notification_outbox_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
