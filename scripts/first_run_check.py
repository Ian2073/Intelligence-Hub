from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_DATE = "2026-07-10"

SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".pytest_tmp",
    "__pycache__",
    "hub_env",
    "logs",
    "exports",
}
SKIP_PREFIXES = (
    ("examples", "output"),
    ("data", "obsidian_vault"),
    ("data", "demo"),
)
SKIP_FILE_NAMES = {
    ".env",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the zero-secret first-run demo path in a clean temp tree.")
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary project copy for debugging.",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    parts = relative.parts
    if path.name in SKIP_FILE_NAMES:
        return True
    if any(part in SKIP_DIRS for part in parts):
        return True
    if any(parts[: len(prefix)] == prefix for prefix in SKIP_PREFIXES):
        return True
    lower_name = path.name.lower()
    return lower_name.endswith((".pyc", ".pyo", ".sqlite", ".sqlite-shm", ".sqlite-wal", ".db"))


def copy_clean_project(destination: Path) -> None:
    for source in PROJECT_ROOT.rglob("*"):
        if should_ignore(source):
            continue
        target = destination / source.relative_to(PROJECT_ROOT)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def first_markdown_file(output_dir: Path) -> Path | None:
    candidates = sorted((output_dir / "01 Briefs" / "Daily").glob("*.md"))
    if not candidates:
        candidates = sorted((output_dir / "DailyBriefs").glob("*.md"))
    return candidates[0] if candidates else None


def run_check(temp_root: Path) -> int:
    project_copy = temp_root / "intelligence-hub"
    output_dir = temp_root / "obsidian"
    copy_clean_project(project_copy)

    env_example = project_copy / ".env.example"
    if not env_example.exists():
        print("First-run check failed: .env.example is missing.")
        return 1
    shutil.copy2(env_example, project_copy / ".env")

    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("HERMES_", "NOTION_", "TELEGRAM_", "TG_", "DEEPSEEK_")) or key in {"GITHUB_TOKEN", "GH_TOKEN"}:
            env.pop(key, None)
    env["PYTHONPATH"] = str(project_copy)

    command = [
        sys.executable,
        "-m",
        "hermes",
        "demo",
        "--date",
        RUN_DATE,
        "--output",
        str(output_dir),
    ]
    result = subprocess.run(command, cwd=project_copy, env=env, text=True, capture_output=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"First-run check failed: demo exited with {result.returncode}.")
        return result.returncode

    brief = first_markdown_file(output_dir)
    if brief is None:
        print(f"First-run check failed: no Daily Brief markdown found under {output_dir}.")
        return 1
    if brief.stat().st_size == 0:
        print(f"First-run check failed: Daily Brief markdown is empty: {brief}.")
        return 1

    print(f"First-run check passed: {brief}")
    return 0


def main() -> int:
    args = parse_args()
    temp_dir = Path(tempfile.mkdtemp(prefix="hermes-first-run-"))
    try:
        return run_check(temp_dir)
    finally:
        if args.keep_temp:
            print(f"Kept temp directory: {temp_dir}")
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
