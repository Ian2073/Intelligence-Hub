from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.obsidian_read_model import ObsidianReadModel
from core.obsidian_renderer import ObsidianRenderer, find_wikilinks


USER_START = "<!-- intelligence_hub:user:start -->"
USER_END = "<!-- intelligence_hub:user:end -->"
LEGACY_USER_MARKER = "## ?? User Notes"


@dataclass(frozen=True)
class PublishResult:
    written: tuple[Path, ...]
    stale: tuple[Path, ...]
    broken_wikilinks: tuple[tuple[str, str], ...]


class ObsidianPublisher:
    def __init__(self, vault_path: str | Path) -> None:
        self.vault_path = Path(vault_path).resolve()

    def publish(self, model: ObsidianReadModel, renderer: ObsidianRenderer | None = None) -> PublishResult:
        renderer = renderer or ObsidianRenderer()
        self.vault_path.mkdir(parents=True, exist_ok=True)
        expected_paths = {note.path for note in model.notes}
        stale = self._stale_paths(expected_paths)
        written: list[Path] = []
        for note in model.notes:
            output_path = self.vault_path / Path(note.path)
            existing_user_section = _extract_user_section(output_path)
            content = renderer.render(note, existing_user_section=existing_user_section)
            self._atomic_write(output_path, content)
            written.append(output_path)
        manifest = self._write_stale_manifest(stale)
        written.append(manifest)
        broken = diagnose_vault_wikilinks(self.vault_path)
        return PublishResult(written=tuple(written), stale=tuple(stale), broken_wikilinks=tuple(broken))

    def _stale_paths(self, expected_paths: set[str]) -> tuple[Path, ...]:
        stale: list[Path] = []
        for path in self.vault_path.rglob("*.md"):
            relative = path.relative_to(self.vault_path).as_posix()
            if relative == "90 System/Stale Notes.md":
                continue
            text = path.read_text(encoding="utf-8")
            if "generated_by: \"intelligence_hub.obsidian.v1\"" in text and relative not in expected_paths:
                stale.append(path)
        return tuple(sorted(stale))

    def _write_stale_manifest(self, stale: tuple[Path, ...]) -> Path:
        manifest = self.vault_path / "90 System" / "Stale Notes.md"
        lines = [
            "---",
            'canonical_id: "system:stale-notes"',
            'note_type: "system"',
            'title: "Stale Notes"',
            'generated_by: "intelligence_hub.obsidian.v1"',
            "---",
            "# Stale Notes",
            "",
            "These generated notes were not present in the latest projection. They are not deleted automatically.",
            "",
        ]
        if stale:
            for path in stale:
                lines.append(f"- {path.relative_to(self.vault_path).as_posix()}")
        else:
            lines.append("- No stale generated notes detected.")
        lines.append("")
        self._atomic_write(manifest, "\n".join(lines))
        return manifest

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            Path(tmp_name).replace(path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise


def diagnose_vault_wikilinks(vault_path: str | Path) -> list[tuple[str, str]]:
    root = Path(vault_path)
    markdown_files = sorted(root.rglob("*.md"))
    by_relative = {path.relative_to(root).with_suffix("").as_posix() for path in markdown_files}
    by_relative_with_suffix = {path.relative_to(root).as_posix() for path in markdown_files}
    by_stem = {path.stem for path in markdown_files}
    broken: list[tuple[str, str]] = []
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for link in find_wikilinks(text):
            target = link.split("|", 1)[0].split("#", 1)[0]
            if target not in by_relative and target not in by_relative_with_suffix and target not in by_stem:
                broken.append((path.relative_to(root).as_posix(), link))
    return broken


def _extract_user_section(path: Path) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    if USER_START in content and USER_END in content:
        return content.split(USER_START, 1)[1].split(USER_END, 1)[0].replace("## User Notes", "", 1).strip()
    if LEGACY_USER_MARKER in content:
        return content.split(LEGACY_USER_MARKER, 1)[1].strip()
    match = re.search(r"^##\s+User Notes\s*$", content, flags=re.MULTILINE)
    if match:
        return content[match.end() :].strip()
    return ""
