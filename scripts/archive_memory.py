from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive old时序 data from memory SQLite db.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        help="Number of days of data to keep in SQLite memory. Default is 90.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be archived and deleted without changing the database.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    db_path = Path(settings.memory_db)
    if not db_path.exists():
        print(f"Memory database does not exist: {db_path}")
        return 0

    cutoff_date = (date.today() - timedelta(days=args.retention_days)).isoformat()
    print(f"Retention days: {args.retention_days} days. Cutoff date: {cutoff_date}")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    try:
        # 1. Fetch observations to archive
        cursor.execute(
            "SELECT * FROM observations WHERE observed_at < ?", (cutoff_date,)
        )
        obs_rows = [dict(row) for row in cursor.fetchall()]

        # 2. Fetch decisions to archive (where revisit_date is before cutoff)
        cursor.execute(
            "SELECT * FROM decisions WHERE revisit_date < ?", (cutoff_date,)
        )
        dec_rows = [dict(row) for row in cursor.fetchall()]

        total_obs = len(obs_rows)
        total_dec = len(dec_rows)

        if total_obs == 0 and total_dec == 0:
            print("No old observations or decisions to archive.")
            return 0

        print(f"Found {total_obs} observations and {total_dec} decisions to archive.")

        if args.dry_run:
            print("[Dry-run] Database was not modified.")
            return 0

        # Create export directory
        export_dir = PROJECT_ROOT / "exports" / f"archive-{date.today().isoformat()}"
        export_dir.mkdir(parents=True, exist_ok=True)

        if total_obs > 0:
            obs_file = export_dir / "observations_archive.jsonl"
            with open(obs_file, "w", encoding="utf-8") as f:
                for row in obs_rows:
                    f.write(json.dumps(row) + "\n")
            print(f"Archived observations to: {obs_file}")

        if total_dec > 0:
            dec_file = export_dir / "decisions_archive.jsonl"
            with open(dec_file, "w", encoding="utf-8") as f:
                for row in dec_rows:
                    f.write(json.dumps(row) + "\n")
            print(f"Archived decisions to: {dec_file}")

        # Delete archived records from database
        if total_obs > 0:
            cursor.execute(
                "DELETE FROM observations WHERE observed_at < ?", (cutoff_date,)
            )
            print(f"Deleted {total_obs} observations from SQLite.")

        if total_dec > 0:
            cursor.execute(
                "DELETE FROM decisions WHERE revisit_date < ?", (cutoff_date,)
            )
            print(f"Deleted {total_dec} decisions from SQLite.")

        connection.commit()
        # Run VACUUM to reclaim space
        cursor.execute("VACUUM")
        print("Database optimization (VACUUM) complete.")

    except Exception as exc:
        connection.rollback()
        print(f"Error occurred during archival: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
