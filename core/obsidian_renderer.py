from __future__ import annotations

import re

from core.obsidian_read_model import ObsidianFact, ObsidianLink, ObsidianNote


class ObsidianRenderer:
    def render(self, note: ObsidianNote, *, existing_user_section: str = "") -> str:
        return "\n".join(
            (
                self._frontmatter(note),
                "",
                "<!-- intelligence_hub:generated:start -->",
                f"# {note.title}",
                "",
                self._body(note),
                "<!-- intelligence_hub:generated:end -->",
                "",
                "<!-- intelligence_hub:user:start -->",
                "## User Notes",
                "",
                existing_user_section.strip(),
                "<!-- intelligence_hub:user:end -->",
                "",
            )
        )

    def _frontmatter(self, note: ObsidianNote) -> str:
        fields: list[tuple[str, object]] = [
            ("canonical_id", note.canonical_id),
            ("note_type", note.note_type),
            ("title", note.title),
            ("aliases", note.aliases),
            ("created_at", note.created_at),
            ("updated_at", note.updated_at),
            ("generated_by", note.generated_by),
            ("source", note.source),
            ("evidence", note.evidence),
            ("confidence", note.confidence),
            ("related_notes", tuple(link.path for link in note.related_notes)),
        ]
        lines = ["---"]
        for key, value in fields:
            lines.extend(_yaml_field(key, value))
        lines.append("---")
        return "\n".join(lines)

    def _body(self, note: ObsidianNote) -> str:
        lines: list[str] = []
        for section in note.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            for fact in section.facts:
                lines.extend(_fact_lines(fact))
            lines.append("")
        return "\n".join(lines).rstrip()


def wikilink(link: ObsidianLink) -> str:
    target = link.path[:-3] if link.path.endswith(".md") else link.path
    return f"[[{target}|{link.title}]]"


def find_wikilinks(markdown: str) -> list[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", markdown)


def diagnose_broken_wikilinks(rendered: dict[str, str]) -> list[tuple[str, str]]:
    paths = {path.rsplit(".", 1)[0] if path.endswith(".md") else path for path in rendered}
    paths.update(rendered)
    broken: list[tuple[str, str]] = []
    for source_path, markdown in rendered.items():
        for link in find_wikilinks(markdown):
            target = link.split("|", 1)[0].split("#", 1)[0]
            if target not in paths and f"{target}.md" not in rendered:
                broken.append((source_path, link))
    return broken


def _fact_lines(fact: ObsidianFact) -> list[str]:
    suffix = ""
    if fact.links:
        suffix = " " + " ".join(wikilink(link) for link in fact.links)
    text = _escape_body_text(fact.text)
    if fact.label:
        return [f"- **{fact.label}:** {text}{suffix}"]
    return [f"- {text}{suffix}"]


def _yaml_field(key: str, value: object) -> list[str]:
    if isinstance(value, tuple):
        if not value:
            return [f"{key}: []"]
        return [f"{key}:"] + [f"  - {_yaml_scalar(item)}" for item in value]
    return [f"{key}: {_yaml_scalar(value)}"]


def _yaml_scalar(value: object) -> str:
    text = str(value)
    if text == "":
        return '""'
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _escape_body_text(value: str) -> str:
    return " ".join(value.split()) if value else ""
