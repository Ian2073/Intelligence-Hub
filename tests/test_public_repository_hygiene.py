from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def test_removed_internal_and_duplicate_documents_are_not_referenced() -> None:
    removed = (
        "docs/AGENTS.md",
        "docs/CONTRIBUTING.md",
        "docs/PRD.md",
        "docs/VISION.md",
        "docs/implementation_plan.md",
        "docs/superpowers/plans/2026-07-03-readiness-audit.md",
        "docs/superpowers/plans/2026-07-09-intelligence-effectiveness-hardening.md",
        "knowledge/mental_models.md",
        "knowledge/thinking.md",
    )
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _tracked_files()
        if path.suffix.lower() in {".md", ".py", ".toml", ".yml", ".yaml"}
    )

    for relative in removed:
        assert not (PROJECT_ROOT / relative).exists()
        assert relative not in tracked_text


def test_public_surfaces_do_not_use_retired_product_names() -> None:
    banned = ("Hermes Intelligence Platform", "Hermes Daily Intelligence", "Hermes Intelligence OS PRD")
    public_files = []
    for path in _tracked_files():
        relative = path.relative_to(PROJECT_ROOT)
        if relative.parts[0] in {"docs", "examples", "dashboard", "scripts"} or path.name.startswith("README"):
            public_files.append(path)

    for path in public_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in banned:
            assert phrase not in text, f"{phrase!r} remains in {path.relative_to(PROJECT_ROOT)}"


def test_tracked_markdown_and_image_links_resolve_locally() -> None:
    broken: list[str] = []
    for markdown in (path for path in _tracked_files() if path.suffix.lower() == ".md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("#", "mailto:")):
                continue
            relative_target = unquote(parsed.path)
            if not relative_target:
                continue
            resolved = (markdown.parent / relative_target).resolve()
            if not resolved.exists():
                broken.append(f"{markdown.relative_to(PROJECT_ROOT)} -> {target}")

    assert broken == []


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = [PROJECT_ROOT / line for line in result.stdout.splitlines() if line]
    return [path for path in paths if path.exists()]
