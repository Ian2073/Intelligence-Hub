from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.api import create_app
from core.release_runtime import DEMO_DATE, export_obsidian, platform_status, reset_demo_data, seed_demo
from scripts.proposals import main as proposals_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Intelligence Hub platform CLI.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path.")
    parser.add_argument("--vault", type=Path, default=None, help="Obsidian vault path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Seed demo data and export Obsidian.")
    demo.add_argument("--date", default=DEMO_DATE)

    seed = subparsers.add_parser("seed-demo", help="Seed repeatable zero-secret demo data.")
    seed.add_argument("--date", default=DEMO_DATE)
    seed.add_argument("--force", action="store_true")

    daily = subparsers.add_parser("daily", help="Run fixture daily path.")
    daily.add_argument("--date", default=DEMO_DATE)

    serve = subparsers.add_parser("serve", help="Serve API and dashboard.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--seed-demo", action="store_true")

    subparsers.add_parser("status", help="Show platform status.")
    subparsers.add_parser("export-obsidian", help="Export Obsidian vault from canonical repository.")
    reset = subparsers.add_parser("reset-demo-data", help="Reset only the managed demo data directory.")
    reset.add_argument("--yes", action="store_true")

    proposals = subparsers.add_parser("proposals", help="List proposals.")
    proposals.add_argument("--status", choices=("pending", "accepted", "rejected", "needs_review"))

    review = subparsers.add_parser("review-proposal", help="Revalidate, accept, or reject a proposal.")
    review.add_argument("proposal_id")
    review.add_argument("--action", choices=("revalidate", "accept", "reject"), required=True)
    review.add_argument("--reason", default="Rejected from platform CLI")

    args = parser.parse_args(argv)
    _configure_db(args.db)

    if args.command in {"demo", "seed-demo", "daily"}:
        result = seed_demo(
            PROJECT_ROOT,
            db_path=args.db,
            vault_path=args.vault,
            run_date=args.date,
            force=getattr(args, "force", False),
        )
        print(f"Demo database: {result.db_path}")
        print(f"Obsidian vault: {result.vault_path}")
        print(
            f"Seeded={result.seeded} proposals={result.proposal_count} insights={result.insight_count} "
            f"events={result.event_count} decisions={result.decision_count} briefs={result.brief_count}"
        )
        return 0
    if args.command == "serve":
        import uvicorn

        app = create_app(project_root=PROJECT_ROOT, db_path=args.db, vault_path=args.vault, auto_seed=args.seed_demo)
        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    if args.command == "status":
        status = platform_status(PROJECT_ROOT, db_path=args.db)
        print("# Intelligence Hub Status")
        for key, value in status.items():
            if key in {"latest_briefs", "proposal_metrics"}:
                continue
            print(f"{key}: {value}")
        metrics = status.get("proposal_metrics")
        if metrics:
            print(f"proposal_metrics: {metrics}")
        return 0
    if args.command == "export-obsidian":
        result = export_obsidian(PROJECT_ROOT, db_path=args.db, vault_path=args.vault)
        print(
            f"Obsidian vault: {result.vault_path} notes={result.notes_written} "
            f"stale={result.stale_count} broken_links={result.broken_link_count}"
        )
        return 0 if result.broken_link_count == 0 else 1
    if args.command == "reset-demo-data":
        path = reset_demo_data(PROJECT_ROOT, yes=args.yes)
        print(f"Reset demo data: {path}")
        return 0
    if args.command == "proposals":
        proposal_args = ["list"]
        if args.status:
            proposal_args.extend(["--status", args.status])
        return proposals_main(proposal_args)
    if args.command == "review-proposal":
        if args.action == "revalidate":
            return proposals_main(["revalidate", args.proposal_id])
        if args.action == "accept":
            return proposals_main(["accept", args.proposal_id])
        return proposals_main(["reject", args.proposal_id, "--reason", args.reason])
    return 2


def _configure_db(db_path: Path | None) -> None:
    if db_path is not None:
        os.environ["INTELLIGENCE_HUB_DB"] = str(db_path)
        os.environ["HERMES_MEMORY_DB"] = str(db_path)


if __name__ == "__main__":
    raise SystemExit(main())
