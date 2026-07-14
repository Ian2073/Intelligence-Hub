from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectDoc:
    path: Path
    title: str
    content: str

    @property
    def name(self) -> str:
        return self.path.name


def load_markdown_docs(docs_dir: Path) -> list[ProjectDoc]:
    docs_path = docs_dir.resolve()
    if not docs_path.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_path}")
    if not docs_path.is_dir():
        raise NotADirectoryError(f"Docs path is not a directory: {docs_path}")

    docs: list[ProjectDoc] = []
    for path in sorted(docs_path.glob("*.md"), key=lambda item: item.name.lower()):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        docs.append(ProjectDoc(path=path, title=_extract_title(path, content), content=content))

    if not docs:
        raise ValueError(f"No non-empty Markdown docs found in {docs_path}")
    return docs


def load_markdown_file(path: Path) -> ProjectDoc:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Markdown file not found: {resolved}")
    if not resolved.is_file():
        raise IsADirectoryError(f"Markdown path is not a file: {resolved}")
    if resolved.suffix.lower() != ".md":
        raise ValueError(f"Markdown file must use .md extension: {resolved}")

    content = resolved.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Markdown file is empty: {resolved}")
    return ProjectDoc(path=resolved, title=_extract_title(resolved, content), content=content)


def build_docs_context(docs: list[ProjectDoc]) -> str:
    return "\n\n".join(f"--- {doc.name}: {doc.title} ---\n{doc.content}" for doc in docs)


def docs_summary(docs: list[ProjectDoc]) -> str:
    lines = [f"{len(docs)} docs loaded:"]
    lines.extend(f"- {doc.name}: {len(doc.content)} chars" for doc in docs)
    return "\n".join(lines)


def markdown_summary(label: str, docs: list[ProjectDoc]) -> str:
    lines = [f"{len(docs)} {label} loaded:"]
    lines.extend(f"- {doc.name}: {len(doc.content)} chars" for doc in docs)
    return "\n".join(lines)


def _extract_title(path: Path, content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
    return path.stem
