from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".pytest_tmp",
    "__pycache__",
    "hub_env",
    "logs",
    "exports",
}
SKIP_PATH_PREFIXES = (
    ("examples", "output"),
)
SKIP_FILE_NAMES = {
    ".env",
}
SKIP_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
}

PLACEHOLDER_VALUES = {
    "changeme",
    "change-me",
    "example",
    "example-token",
    "placeholder",
    "replace-me",
    "replace_with_real_value",
    "todo",
    "your-token-here",
    "your_api_key_here",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line_number: int
    label: str
    excerpt: str


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("Notion token", re.compile(r"\bsecret_[A-Za-z0-9]{20,}\b")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)

ENV_SECRET_RE = re.compile(
    r"^\s*(?:export\s+)?[A-Z][A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE_KEY)=['\"]?([^'\"\s#]+)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan tracked Intelligence Hub release files for likely secrets.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every file selected for scanning.",
    )
    return parser.parse_args()


def from_git_index() -> list[Path] | None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    paths = []
    for raw_path in result.stdout.splitlines():
        path = PROJECT_ROOT / raw_path
        if path.is_file() and not should_skip(path):
            paths.append(path)
    return sorted(set(paths))


def from_directory_walk() -> list[Path]:
    paths: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file() and not should_skip(path):
            paths.append(path)
    return sorted(paths)


def should_skip(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    parts = relative.parts
    if path.name in SKIP_FILE_NAMES:
        return True
    if any(part in SKIP_DIRS for part in parts):
        return True
    if any(parts[: len(prefix)] == prefix for prefix in SKIP_PATH_PREFIXES):
        return True
    lower_name = path.name.lower()
    return any(lower_name.endswith(suffix) for suffix in SKIP_SUFFIXES)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("'\"").lower()
    if not normalized:
        return True
    if normalized in PLACEHOLDER_VALUES:
        return True
    return normalized.startswith("<") and normalized.endswith(">")


def redact(line: str) -> str:
    return line.strip()[:120]


def scan_file(path: Path) -> list[Finding]:
    text = read_text(path)
    if text is None:
        return []

    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        env_match = ENV_SECRET_RE.search(line)
        if env_match and not is_placeholder(env_match.group(1)):
            findings.append(
                Finding(
                    path=path,
                    line_number=line_number,
                    label="secret-like environment assignment",
                    excerpt=redact(line),
                )
            )
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        path=path,
                        line_number=line_number,
                        label=label,
                        excerpt=redact(line),
                    )
                )
    return findings


def main() -> int:
    args = parse_args()
    files = from_git_index()
    source = "git index"
    if files is None:
        files = from_directory_walk()
        source = "directory walk"

    if args.verbose:
        for path in files:
            print(path.relative_to(PROJECT_ROOT).as_posix())

    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path))

    if findings:
        print(f"Pre-publish audit failed: {len(findings)} likely secret(s) found.")
        for finding in findings:
            relative = finding.path.relative_to(PROJECT_ROOT).as_posix()
            print(f"- {relative}:{finding.line_number}: {finding.label}: {finding.excerpt}")
        return 1

    print(f"Pre-publish audit passed: scanned {len(files)} publishable file(s) via {source}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
