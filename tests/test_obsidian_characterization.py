from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from connectors.notion import (
    NotionBriefRecord,
    NotionEcosystemRecord,
    NotionGitHubRepoRecord,
    NotionPaperRecord,
)
from connectors.obsidian import ObsidianClient


@dataclass(frozen=True)
class MockEntity:
    canonical_name: str


@dataclass(frozen=True)
class MockResult:
    entity: MockEntity


def _markdown_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _headings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [match.group(2).strip() for match in re.finditer(r"^(#{2,3})\s+(.+)$", text, re.MULTILINE)]


def _wikilinks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def _broken_wikilinks(root: Path) -> list[tuple[str, str]]:
    markdown_files = _markdown_files(root)
    by_vault_relative_stem = {
        path.relative_to(root).with_suffix("").as_posix(): path for path in markdown_files
    }
    by_basename_stem = {path.stem: path for path in markdown_files}
    broken: list[tuple[str, str]] = []
    for path in markdown_files:
        for link in _wikilinks(path):
            target = link.split("|", 1)[0].split("#", 1)[0]
            if target not in by_vault_relative_stem and target not in by_basename_stem:
                broken.append((path.relative_to(root).as_posix(), link))
    return broken


def _repo_record(name: str, *, stars: int = 150, summary: str = "Repository summary") -> NotionGitHubRepoRecord:
    owner = name.split("/", 1)[0] if "/" in name else "owner"
    return NotionGitHubRepoRecord(
        name=name,
        url=f"https://github.com/{name}",
        owner=owner,
        stars=stars,
        category="AI Agent",
        summary=summary,
        why_it_matters="Why now: current exporter stores rationale as body text.",
        engineering_value="high",
        adoption_potential="medium",
        recommended_action="Prototype",
    )


def _paper_record(title: str, *, summary: str = "Paper summary") -> NotionPaperRecord:
    return NotionPaperRecord(
        title=title,
        authors="A. Researcher",
        url=f"https://example.com/{ObsidianClient.sanitize_filename(title)}",
        published_date="2026-07-10",
        summary=summary,
        why_it_matters="Paper rationale",
        technology_area=("AI agents",),
        intelligence_score=80,
        recommended_action="Read",
        confidence="medium",
    )


def _ecosystem_record(name: str) -> NotionEcosystemRecord:
    return NotionEcosystemRecord(
        name=name,
        type="Technology Signal",
        company_or_maintainer="Fixture Maintainer",
        category=("AI", "Infrastructure"),
        summary=f"{name} summary",
        why_it_matters="Fixture evidence for legacy exporter characterization.",
        impact="high",
        momentum="rising",
    )


@pytest.fixture
def legacy_demo_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "legacy-obsidian-vault"
    client = ObsidianClient(vault)

    repository_names = (
        "openai/openai-agents-python",
        "owner/repo-01",
        "owner/repo-02",
        "owner/repo-03",
        "owner/repo-04",
        "owner/repo-05",
        "owner/repo-06",
        "owner/repo-07",
        "owner/repo-08",
        "owner/repo-09",
        "owner/repo-10",
        "owner/repo-11",
    )
    paper_titles = (
        "Tool Learning with Foundation Agents",
        "Deterministic Paper 02",
        "Deterministic Paper 03",
        "Deterministic Paper 04",
        "Deterministic Paper 05",
        "Deterministic Paper 06",
    )
    ecosystem_names = (
        "Agentic security evaluation",
        "Deterministic Ecosystem 02",
        "Deterministic Ecosystem 03",
        "Deterministic Ecosystem 04",
        "Deterministic Ecosystem 05",
    )

    for name in repository_names:
        client.upsert_repository(_repo_record(name))
    for title in paper_titles:
        client.upsert_paper(_paper_record(title))
    for name in ecosystem_names:
        client.upsert_ecosystem(_ecosystem_record(name))

    linked_repositories = repository_names[:5]
    linked_papers = paper_titles[:4]
    linked_ecosystem = ecosystem_names[:4]
    body = "\n".join(
        (
            "## GitHub Repositories",
            *(f"- [{name}](https://github.com/{name})" for name in linked_repositories),
            "## Research Papers",
            *(
                f"- [{title}](https://example.com/papers/{index})"
                for index, title in enumerate(linked_papers, 1)
            ),
            "## Domain Signals",
            *(f"- {name}" for name in linked_ecosystem),
            "## Top Decisions",
            "- Prototype the strongest converging signal.",
        )
    )
    client.create_daily_brief(
        "2026-07-10",
        NotionBriefRecord(
            title="Platform Runtime Daily Intelligence - 2026-07-10",
            date="2026-07-10",
            executive_summary="Deterministic characterization fixture.",
            recommended_actions=("Prototype",),
            intelligence_score=82,
            confidence="high",
            status="Published",
            tags=("AI Intelligence",),
            body=body,
        ),
        repository_results=tuple(MockResult(MockEntity(name)) for name in linked_repositories),
        paper_results=tuple(MockResult(MockEntity(title)) for title in linked_papers),
        domain_results=tuple(MockResult(MockEntity(name)) for name in linked_ecosystem),
    )

    return vault


def test_generated_daily_demo_current_folder_structure_and_note_types(
    legacy_demo_vault: Path,
) -> None:
    assert legacy_demo_vault.is_dir()

    folders = {path.name for path in legacy_demo_vault.iterdir() if path.is_dir()}
    assert folders == {"DailyBriefs", "Repositories", "Papers", "Ecosystem"}

    files_by_folder = {
        folder.name: sorted(path.name for path in folder.glob("*.md"))
        for folder in sorted(path for path in legacy_demo_vault.iterdir() if path.is_dir())
    }
    assert len(files_by_folder["DailyBriefs"]) == 1
    assert len(files_by_folder["Repositories"]) == 12
    assert len(files_by_folder["Papers"]) == 6
    assert len(files_by_folder["Ecosystem"]) == 5

    types = {
        path.relative_to(legacy_demo_vault).as_posix(): _frontmatter(path).get("type")
        for path in _markdown_files(legacy_demo_vault)
    }
    assert set(types.values()) == {"daily-brief", "github-repo", "paper", "ecosystem-signal"}


def test_current_frontmatter_keys_by_note_type_are_characterized(legacy_demo_vault: Path) -> None:
    examples = {
        "daily": legacy_demo_vault / "DailyBriefs" / "Daily Brief - 2026-07-10.md",
        "repository": legacy_demo_vault / "Repositories" / "openai-openai-agents-python.md",
        "paper": legacy_demo_vault / "Papers" / "Tool Learning with Foundation Agents.md",
        "ecosystem": legacy_demo_vault / "Ecosystem" / "Agentic security evaluation.md",
    }

    assert set(_frontmatter(examples["daily"])) == {
        "type",
        "date",
        "intelligence_score",
        "confidence",
        "recommended_actions",
        "tags",
    }
    assert set(_frontmatter(examples["repository"])) == {
        "type",
        "name",
        "url",
        "owner",
        "stars",
        "trend",
        "momentum",
        "first_seen",
        "last_seen",
        "category",
        "engineering_value",
        "adoption_potential",
        "recommended_action",
    }
    assert set(_frontmatter(examples["paper"])) == {
        "type",
        "title",
        "authors",
        "url",
        "published_date",
        "trend",
        "momentum",
        "first_seen",
        "last_seen",
        "technology_area",
        "intelligence_score",
        "recommended_action",
        "confidence",
    }
    assert set(_frontmatter(examples["ecosystem"])) == {
        "type",
        "name",
        "signal_type",
        "company_or_maintainer",
        "category",
        "impact",
        "momentum",
        "trend",
        "first_seen",
        "last_seen",
    }


def test_current_main_body_sections_by_note_type_are_characterized(
    legacy_demo_vault: Path,
) -> None:
    daily_headings = _headings(legacy_demo_vault / "DailyBriefs" / "Daily Brief - 2026-07-10.md")
    assert any("GitHub Repositories" in heading for heading in daily_headings)
    assert any("Research Papers" in heading for heading in daily_headings)
    assert any("Domain Signals" in heading for heading in daily_headings)
    assert any("Top Decisions" in heading for heading in daily_headings)
    assert any("Notion" in heading for heading in daily_headings)
    assert any("User Notes" in heading for heading in daily_headings)

    for note_path in (
        legacy_demo_vault / "Repositories" / "openai-openai-agents-python.md",
        legacy_demo_vault / "Papers" / "Tool Learning with Foundation Agents.md",
        legacy_demo_vault / "Ecosystem" / "Agentic security evaluation.md",
    ):
        headings = _headings(note_path)
        assert headings == [
            "摘要",
            "為什麼這重要 (Why it matters)",
            "歷史觀察",
            "相關連結",
            "📝 User Notes",
        ]


def test_current_filename_sanitization_preserves_case_but_collides_on_punctuation() -> None:
    assert ObsidianClient.sanitize_filename("owner/repo") == "owner_repo"
    assert ObsidianClient.sanitize_filename("hello:world?*") == "hello_world__"
    assert ObsidianClient.sanitize_filename("  spaces_around  ") == "spaces_around"
    assert ObsidianClient.sanitize_filename("test#^[]") == "test____"

    assert ObsidianClient.sanitize_filename("Case Sensitive") == "Case Sensitive"
    assert ObsidianClient.sanitize_filename("case sensitive") == "case sensitive"

    # Characterizes a known identity risk: distinct titles can map to the same filename.
    assert ObsidianClient.sanitize_filename("A/B") == "A_B"
    assert ObsidianClient.sanitize_filename("A:B") == "A_B"


def test_current_markdown_link_conversion_to_wikilinks_is_regex_based(tmp_path: Path) -> None:
    client = ObsidianClient(tmp_path / "vault")
    body = "\n".join(
        [
            "- [owner/repo](https://github.com/owner/repo) is linked.",
            "- [Paper Title](https://example.com/paper) is linked.",
            "| Topic | Domain |",
            "| --- | --- |",
            "| Signal | OpenAI |",
            "OpenAI appears again as plain text.",
        ]
    )

    converted = client.convert_to_wikilinks(
        body,
        repository_results=(MockResult(MockEntity("owner/repo")),),
        paper_results=(MockResult(MockEntity("Paper Title")),),
        domain_results=(MockResult(MockEntity("OpenAI")),),
    )

    assert "[[Repositories/owner-repo|owner/repo]]" in converted
    assert "[[Papers/Paper Title|Paper Title]]" in converted
    assert "| Signal | [[Ecosystem/OpenAI|OpenAI]] |" in converted
    assert "[[Ecosystem/OpenAI|OpenAI]] appears again as plain text." in converted


def test_legacy_obsidian_client_entity_notes_have_no_outbound_wikilinks(
    legacy_demo_vault: Path,
) -> None:
    diagnostics: dict[str, int] = {}
    for folder in ("Repositories", "Papers", "Ecosystem"):
        total = sum(len(_wikilinks(path)) for path in (legacy_demo_vault / folder).glob("*.md"))
        diagnostics[folder] = total

    # Legacy ObsidianClient characterization only; the repository-driven projection has semantic links.
    assert diagnostics == {"Repositories": 0, "Papers": 0, "Ecosystem": 0}


def test_current_user_notes_section_is_preserved_on_rewrite(tmp_path: Path) -> None:
    client = ObsidianClient(tmp_path / "vault")
    file_path = client.upsert_repository(_repo_record("owner/repo", summary="Initial summary"))
    file_path.write_text(
        file_path.read_text(encoding="utf-8") + "\nManual operator note.\n",
        encoding="utf-8",
    )

    updated_path = client.upsert_repository(_repo_record("owner/repo", stars=250, summary="Updated summary"))

    assert updated_path == file_path
    content = updated_path.read_text(encoding="utf-8")
    assert "Updated summary" in content
    assert "Manual operator note." in content


def test_legacy_obsidian_client_collision_behavior_overwrites_existing_note(tmp_path: Path) -> None:
    # Legacy ObsidianClient characterization only; the repository-driven projection uses stable IDs.
    client = ObsidianClient(tmp_path / "vault")

    first_path = client.upsert_paper(_paper_record("Same Title", summary="First version"))
    second_path = client.upsert_paper(_paper_record("Same Title", summary="Second version"))

    assert second_path == first_path
    assert "Second version" in second_path.read_text(encoding="utf-8")
    assert "First version" not in second_path.read_text(encoding="utf-8")

    slash_path = client.upsert_paper(_paper_record("A/B", summary="Slash title"))
    colon_path = client.upsert_paper(_paper_record("A:B", summary="Colon title"))

    assert slash_path == colon_path
    assert colon_path.name == "A_B.md"
    collision_content = colon_path.read_text(encoding="utf-8")
    assert "Colon title" in collision_content
    assert "Slash title" not in collision_content


def test_current_exporter_output_does_not_include_obsidian_starter_files(legacy_demo_vault: Path) -> None:
    starter_phrases = ("歡迎", "建立連接", "Welcome", "Start here", "Create links")
    diagnostics = [
        path.relative_to(legacy_demo_vault).as_posix()
        for path in _markdown_files(legacy_demo_vault)
        if any(phrase in path.stem or phrase in path.read_text(encoding="utf-8") for phrase in starter_phrases)
    ]

    assert diagnostics == []


def test_current_demo_output_wikilinks_resolve_with_diagnostics(legacy_demo_vault: Path) -> None:
    broken = _broken_wikilinks(legacy_demo_vault)

    assert broken == [], f"Broken WikiLinks: {broken!r}"


def test_current_daily_brief_contains_wikilinks_while_legacy_entity_notes_do_not(
    legacy_demo_vault: Path,
) -> None:
    daily_links = _wikilinks(legacy_demo_vault / "DailyBriefs" / "Daily Brief - 2026-07-10.md")
    entity_note_links = [
        (path.relative_to(legacy_demo_vault).as_posix(), _wikilinks(path))
        for folder in ("Repositories", "Papers", "Ecosystem")
        for path in (legacy_demo_vault / folder).glob("*.md")
    ]

    assert len(daily_links) == 13
    assert all(links == [] for _, links in entity_note_links)


def test_current_daily_brief_creation_frontmatter_and_sections(tmp_path: Path) -> None:
    client = ObsidianClient(tmp_path / "vault")
    record = NotionBriefRecord(
        title="Platform Runtime Daily Intelligence - 2026-07-10",
        date="2026-07-10",
        executive_summary="Summary",
        recommended_actions=("Read",),
        intelligence_score=75,
        confidence="medium",
        status="Published",
        tags=("AI Intelligence",),
        body="- [owner/repo](https://github.com/owner/repo) was updated.",
    )

    path = client.create_daily_brief(
        "2026-07-10",
        record,
        repository_results=(MockResult(MockEntity("owner/repo")),),
    )

    assert path.relative_to(tmp_path / "vault").as_posix() == "DailyBriefs/Daily Brief - 2026-07-10.md"
    assert set(_frontmatter(path)) == {
        "type",
        "date",
        "intelligence_score",
        "confidence",
        "recommended_actions",
        "tags",
    }
    content = path.read_text(encoding="utf-8")
    assert "[[Repositories/owner-repo|owner/repo]]" in content
    assert "## 🔗 Notion" in content
    assert "## 📝 User Notes" in content


def test_current_ecosystem_note_shape_from_public_writer(tmp_path: Path) -> None:
    client = ObsidianClient(tmp_path / "vault")
    path = client.upsert_ecosystem(
        NotionEcosystemRecord(
            name="OpenAI o3",
            type="Company Product",
            company_or_maintainer="OpenAI",
            category=("AI", "LLM"),
            summary="New reasoning model series",
            why_it_matters="Provides deep thinking loops",
            impact="high",
            momentum="rising",
        )
    )

    assert path.relative_to(tmp_path / "vault").as_posix() == "Ecosystem/OpenAI o3.md"
    assert _frontmatter(path)["type"] == "ecosystem-signal"
    assert _wikilinks(path) == []
