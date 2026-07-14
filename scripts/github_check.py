from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connectors.github import GitHubClient
from core.config import load_settings
from core.watchlist import load_github_watchlist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Intelligence Hub GitHub token setup.")
    return parser.parse_args()


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_stdout()
    parse_args()
    settings = load_settings(PROJECT_ROOT)
    if not settings.github_token:
        print("GitHub check failed: missing GITHUB_TOKEN.")
        print("Alias accepted: GH_TOKEN.")
        return 1

    client = GitHubClient(token=settings.github_token)
    try:
        user = client.get_authenticated_user()
    except Exception as exc:
        print(f"GitHub token identity check failed: {exc}")
        return 1

    print(f"GitHub token identity ok: {user.login}.")

    try:
        watchlist = load_github_watchlist(settings.github_watchlist_file)
    except Exception as exc:
        print(f"GitHub watchlist check failed: {exc}")
        return 1

    if not watchlist:
        print(f"No GitHub watchlist items found at {settings.github_watchlist_file}.")
        return 0

    item = watchlist[0]
    try:
        snapshot = client.fetch_repository(item.owner, item.name, observed_at="github-check")
    except Exception as exc:
        print(f"GitHub watchlist fetch failed for {item.owner}/{item.name}: {exc}")
        return 1

    print(f"GitHub watchlist fetch ok: {snapshot.full_name} ({snapshot.stars} stars).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
