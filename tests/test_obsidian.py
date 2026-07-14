from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

from connectors.obsidian import ObsidianClient
from connectors.notion import (
    NotionBriefRecord,
    NotionGitHubRepoRecord,
    NotionPaperRecord,
    NotionEcosystemRecord,
)


@dataclass
class MockEntity:
    canonical_name: str


@dataclass
class MockResult:
    entity: MockEntity


def test_sanitize_filename(tmp_path: Path) -> None:
    client = ObsidianClient(tmp_path / "mock_vault")
    # 測試非法字元是否被正確替換
    assert client.sanitize_filename("owner/repo") == "owner_repo"
    assert client.sanitize_filename("hello:world?*") == "hello_world__"
    assert client.sanitize_filename("  spaces_around  ") == "spaces_around"
    assert client.sanitize_filename("test#^[]") == "test____"


def test_directory_creation(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    ObsidianClient(vault)

    assert (vault / "DailyBriefs").is_dir()
    assert (vault / "Repositories").is_dir()
    assert (vault / "Papers").is_dir()
    assert (vault / "Ecosystem").is_dir()


def test_upsert_repository(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)
    
    record = NotionGitHubRepoRecord(
        name="owner/my-cool-repo",
        url="https://github.com/owner/my-cool-repo",
        owner="owner",
        stars=150,
        category="AI Agent",
        summary="A summary of the repo",
        why_it_matters="It makes code better",
        engineering_value="high",
        adoption_potential="medium",
        recommended_action="Prototype",
    )
    
    file_path = client.upsert_repository(record)
    assert file_path.name == "owner-my-cool-repo.md"
    assert file_path.exists()
    
    content = file_path.read_text(encoding="utf-8")
    assert "type: github-repo" in content
    assert "name: owner/my-cool-repo" in content
    assert "trend: Up" in content
    assert "A summary of the repo" in content
    assert "It makes code better" in content
    assert "## 📝 User Notes" in content


def test_upsert_repository_formats_labeled_rationale(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)

    record = NotionGitHubRepoRecord(
        name="owner/my-cool-repo",
        url="https://github.com/owner/my-cool-repo",
        owner="owner",
        stars=150,
        category="AI Agent",
        summary="A summary of the repo",
        why_it_matters=(
            "Why now: release activity increased. "
            "What changed: star delta moved. "
            "Connects to: agents, tools. "
            "What to do: Read the release. "
            "Confidence: medium."
        ),
        engineering_value="high",
        adoption_potential="medium",
        recommended_action="Prototype",
    )

    content = client.upsert_repository(record).read_text(encoding="utf-8")

    assert "- **Why now:** release activity increased." in content
    assert "- **What changed:** star delta moved." in content
    assert "- **Connects to:** agents, tools." in content
    assert "- **What to do:** Read the release." in content
    assert "- **Confidence:** medium." in content
    assert "Why now: release activity increased. What changed:" not in content


def test_upsert_paper(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)
    
    record = NotionPaperRecord(
        title="Attention Is All You Need",
        authors="Vaswani et al.",
        url="https://arxiv.org/abs/1706.03762",
        published_date="2017-06-12",
        summary="Transformer architecture paper",
        why_it_matters="Revolutionized NLP",
        technology_area=("Transformer", "Deep Learning"),
        intelligence_score=95,
        recommended_action="Implement",
        confidence="high",
    )
    
    file_path = client.upsert_paper(record)
    assert file_path.name == "Attention Is All You Need.md"
    assert file_path.exists()
    
    content = file_path.read_text(encoding="utf-8")
    assert "type: paper" in content
    assert " Vaswani et al." in content
    assert "Revolutionized NLP" in content


def test_upsert_ecosystem(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)
    
    record = NotionEcosystemRecord(
        name="OpenAI o3",
        type="Company Product",
        company_or_maintainer="OpenAI",
        category=("AI", "LLM"),
        summary="New reasoning model series",
        why_it_matters="Provides deep thinking loops",
        impact="high",
        momentum="rising",
    )
    
    file_path = client.upsert_ecosystem(record)
    assert file_path.name == "OpenAI o3.md"
    assert file_path.exists()
    
    content = file_path.read_text(encoding="utf-8")
    assert "type: ecosystem-signal" in content
    assert "OpenAI o3" in content
    assert "Company Product" in content


def test_convert_to_wikilinks(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)
    
    body = """
## Repositories
- [owner/repo](https://github.com/owner/repo) is awesome.
- [google/gemma-2](https://github.com/google/gemma-2) is a model.

## Papers
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) has been widely cited.

## Signals
| Topic | Domain |
| --- | --- |
| OpenAI o3 release | OpenAI |
"""
    
    repos = [
        MockResult(MockEntity("owner/repo")),
        MockResult(MockEntity("google/gemma-2")),
    ]
    papers = [
        MockResult(MockEntity("Attention Is All You Need")),
    ]
    ecosystems = [
        MockResult(MockEntity("OpenAI")),
    ]
    
    converted = client.convert_to_wikilinks(body, repos, papers, ecosystems)
    
    # 檢查 Repo 連結轉換
    assert "[[Repositories/owner-repo|owner/repo]]" in converted
    assert "[[Repositories/google-gemma-2|google/gemma-2]]" in converted
    assert "[owner/repo](" not in converted
    
    # 檢查 Paper 連結轉換
    assert "[[Papers/Attention Is All You Need|Attention Is All You Need]]" in converted
    
    # 檢查 Ecosystem 表格轉換
    assert "| [[Ecosystem/OpenAI|OpenAI]] |" in converted


def test_create_daily_brief(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)
    
    brief_record = NotionBriefRecord(
        title="Intelligence Hub Daily Brief - 2026-07-04",
        date="2026-07-04",
        executive_summary="Summary of the day's events.",
        recommended_actions=("Prototype", "Read"),
        intelligence_score=75,
        confidence="medium",
        status="Published",
        tags=("AI Intelligence", "GitHub Radar"),
        body="- [owner/repo](https://github.com/owner/repo) was updated.",
    )
    
    repos = [MockResult(MockEntity("owner/repo"))]
    
    file_path = client.create_daily_brief(
        "2026-07-04",
        brief_record,
        repository_results=repos,
    )
    
    assert file_path.name == "Daily Brief - 2026-07-04.md"
    assert file_path.exists()
    
    content = file_path.read_text(encoding="utf-8")
    assert "type: daily-brief" in content
    assert "intelligence_score: 75" in content
    # 內文中的連結應該要被轉換
    assert "[[Repositories/owner-repo|owner/repo]]" in content
    assert "## 🔗 Notion" in content
    assert "## 📝 User Notes" in content


def test_create_daily_brief_formats_blockquote_rationale_and_summary(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)

    brief_record = NotionBriefRecord(
        title="Intelligence Hub Daily Brief - 2026-07-04",
        date="2026-07-04",
        executive_summary="Summary.",
        recommended_actions=("Prototype",),
        intelligence_score=75,
        confidence="medium",
        status="Published",
        tags=("AI Intelligence",),
        body=(
            "> [!summary]\n"
            "> **Executive Summary**\n"
            "> First sentence is long enough to split. Second sentence should become its own quoted line.\n"
            "\n"
            "## Repositories\n"
            "> Why now: release activity increased. What changed: star delta moved. "
            "Connects to: agents, tools. What to do: Read the release. Confidence: medium.\n"
        ),
    )

    content = client.create_daily_brief("2026-07-04", brief_record).read_text(encoding="utf-8")

    assert "> First sentence is long enough to split.\n>\n> Second sentence should become its own quoted line." in content
    assert "> Second sentence should become its own quoted line." in content
    assert "> - **Why now:** release activity increased." in content
    assert "> - **What changed:** star delta moved." in content
    assert "> - **Connects to:** agents, tools." in content
    assert "> - **What to do:** Read the release." in content
    assert "> - **Confidence:** medium." in content
    assert "> Why now: release activity increased. What changed:" not in content


def test_upsert_repository_preserves_user_notes(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian_vault"
    client = ObsidianClient(vault)

    record = NotionGitHubRepoRecord(
        name="owner/my-cool-repo",
        url="https://github.com/owner/my-cool-repo",
        owner="owner",
        stars=150,
        category="AI Agent",
        summary="A summary of the repo",
        why_it_matters="It makes code better",
        engineering_value="high",
        adoption_potential="medium",
        recommended_action="Prototype",
    )

    file_path = client.upsert_repository(record)
    file_path.write_text(file_path.read_text(encoding="utf-8") + "\nPersonal note.\n", encoding="utf-8")

    updated = NotionGitHubRepoRecord(
        name=record.name,
        url=record.url,
        owner=record.owner,
        stars=200,
        category=record.category,
        summary="Updated summary",
        why_it_matters=record.why_it_matters,
        engineering_value=record.engineering_value,
        adoption_potential=record.adoption_potential,
        recommended_action=record.recommended_action,
    )
    client.upsert_repository(updated)

    content = file_path.read_text(encoding="utf-8")
    assert "Updated summary" in content
    assert "Personal note." in content
