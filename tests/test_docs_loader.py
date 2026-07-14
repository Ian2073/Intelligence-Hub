from __future__ import annotations

from pathlib import Path

import pytest

from core.docs_loader import (
    build_docs_context,
    docs_summary,
    load_markdown_docs,
    load_markdown_file,
    markdown_summary,
)


def test_load_markdown_docs_reads_non_empty_docs_in_name_order(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "b.md").write_text("# Beta\n\nSecond", encoding="utf-8")
    (docs_dir / "a.md").write_text("# Alpha\n\nFirst", encoding="utf-8")
    (docs_dir / "empty.md").write_text("  ", encoding="utf-8")

    docs = load_markdown_docs(docs_dir)

    assert [doc.name for doc in docs] == ["a.md", "b.md"]
    assert [doc.title for doc in docs] == ["Alpha", "Beta"]
    assert "a.md" in docs_summary(docs)
    assert "2 soul files loaded:" in markdown_summary("soul files", docs)
    assert "--- a.md: Alpha ---" in build_docs_context(docs)


def test_load_markdown_docs_errors_when_no_non_empty_docs(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "empty.md").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="No non-empty Markdown docs"):
        load_markdown_docs(docs_dir)


def test_load_markdown_file_reads_one_prompt(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("# Prompt\n\nDo the thing.", encoding="utf-8")

    prompt = load_markdown_file(prompt_path)

    assert prompt.name == "prompt.md"
    assert prompt.title == "Prompt"
    assert prompt.content == "# Prompt\n\nDo the thing."
