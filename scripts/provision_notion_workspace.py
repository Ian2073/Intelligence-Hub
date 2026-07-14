from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.notion import NotionClient, build_database_payload, notion_workspace_database_specs
from core.config import load_settings
from core.env_file import update_env_values
from core.notion_provisioning import provision_notion_workspace


ENV_BY_DATABASE_KEY = {
    "briefs": "NOTION_DAILY_BRIEFS_DATABASE_ID",
    "papers": "NOTION_PAPERS_DATABASE_ID",
    "github_repos": "NOTION_GITHUB_REPOS_DATABASE_ID",
    "ecosystem": "NOTION_ECOSYSTEM_DATABASE_ID",
    "decisions": "NOTION_DECISIONS_DATABASE_ID",
    "radar_snapshots": "NOTION_RADAR_SNAPSHOTS_DATABASE_ID",
    "radar_entities": "NOTION_RADAR_ENTITIES_DATABASE_ID",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision Intelligence Hub Notion workspace databases.")
    parser.add_argument("--apply", action="store_true", help="Create databases in Notion. Default is dry-run.")
    parser.add_argument("--update-env", action="store_true", help="Write created database ids back to .env. Requires --apply.")
    parser.add_argument("--print-payloads", action="store_true", help="Print database creation payloads.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    args = parse_args()
    settings = load_settings(PROJECT_ROOT)
    specs = notion_workspace_database_specs()

    if args.print_payloads:
        parent_page_id = settings.notion_parent_page_id or "NOTION_PARENT_PAGE_ID"
        for spec in specs:
            print(f"--- {spec.key}: {spec.title} ---")
            print(json.dumps(build_database_payload(parent_page_id, spec), ensure_ascii=False, indent=2))

    notion_client = None
    if args.apply:
        if not settings.notion_token or not settings.notion_parent_page_id:
            print("Notion provisioning skipped: NOTION_TOKEN and NOTION_PARENT_PAGE_ID are required for --apply.")
        else:
            notion_client = NotionClient(
                token=settings.notion_token,
                parent_page_id=settings.notion_parent_page_id,
            )

    results = provision_notion_workspace(
        notion_client=notion_client,
        apply=args.apply,
        existing_database_ids=_existing_database_ids(settings),
        specs=specs,
    )
    env_updates = {}
    for result in results:
        suffix = f" id={result.id}" if result.id else ""
        url = f" url={result.url}" if result.url else ""
        env_name = ENV_BY_DATABASE_KEY.get(result.key, "")
        env_hint = f" env={env_name}" if env_name else ""
        print(f"{result.status}: {result.key} - {result.title}{suffix}{url}{env_hint}")
        if result.id and env_name:
            print(f"{env_name}={result.id}")
            env_updates[env_name] = result.id
    if args.update_env:
        if not args.apply:
            print("--update-env skipped: --apply is required before .env can be updated.")
        elif env_updates:
            update_env_values(PROJECT_ROOT / ".env", env_updates)
            print(f"Updated .env with {len(env_updates)} Notion database id(s).")
        else:
            print("--update-env skipped: no created Notion database ids were returned.")
    return 0


def _existing_database_ids(settings) -> dict[str, str]:
    values = {
        "briefs": settings.notion_daily_briefs_database_id,
        "papers": settings.notion_papers_database_id,
        "github_repos": settings.notion_github_repos_database_id,
        "ecosystem": settings.notion_ecosystem_database_id,
        "decisions": settings.notion_decisions_database_id,
        "radar_snapshots": settings.notion_radar_snapshots_database_id,
        "radar_entities": settings.notion_radar_entities_database_id,
    }
    return {key: value for key, value in values.items() if value}


if __name__ == "__main__":
    raise SystemExit(main())
