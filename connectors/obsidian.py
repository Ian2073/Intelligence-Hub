from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from connectors.notion import (
        NotionBriefRecord,
        NotionGitHubRepoRecord,
        NotionPaperRecord,
        NotionEcosystemRecord,
    )


class ObsidianClient:
    def __init__(self, vault_path: str | Path) -> None:
        self.vault_path = Path(vault_path).resolve()
        
        # 定義子資料夾
        self.dirs = {
            "briefs": self.vault_path / "DailyBriefs",
            "repos": self.vault_path / "Repositories",
            "papers": self.vault_path / "Papers",
            "ecosystem": self.vault_path / "Ecosystem",
        }
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """確保所有 Obsidian 子資料夾均存在。"""
        for directory in self.dirs.values():
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """過濾檔名中的非法字元，使其符合 Windows 檔案系統與 Obsidian 要求。"""
        # 取代 Windows 檔名非法字元 \ / : * ? " < > | 以及 Obsidian 特殊字元 # ^ [ ]
        # 我們將它們統一替換為底線 _
        sanitized = re.sub(r'[\\/:*?"<>|#^[\]]', "_", name)
        # 移除前後空白
        return sanitized.strip()

    @staticmethod
    def _preserved_user_notes(existing: Path) -> str:
        if not existing.exists():
            return ""
        marker = "## 📝 User Notes"
        content = existing.read_text(encoding="utf-8")
        if marker not in content:
            return ""
        return content.split(marker, 1)[1].strip()

    @staticmethod
    def _user_notes_section(existing: Path) -> str:
        notes = ObsidianClient._preserved_user_notes(existing)
        if notes:
            return f"## 📝 User Notes\n{notes}\n"
        return "## 📝 User Notes\n\n"

    @staticmethod
    def _trend_from_action(action: str) -> str:
        if action in {"Prototype", "Implement", "Read"}:
            return "Up"
        if action == "Ignore":
            return "Down"
        return "Stable"

    @staticmethod
    def _format_labeled_text(text: str, *, quote: bool = False) -> str:
        segments = _split_labeled_segments(text)
        if not segments:
            return _format_plain_text(text, quote=quote)
        prefix = "> " if quote else ""
        return "\n".join(f"{prefix}- **{label}:** {value}" for label, value in segments)

    @staticmethod
    def _format_detail_text(text: str) -> str:
        return ObsidianClient._format_labeled_text(text, quote=False)

    @staticmethod
    def _format_daily_body(body: str) -> str:
        lines = []
        previous_plain_quote = False
        for line in body.splitlines():
            if not line.startswith("> ") or line.startswith("> [!"):
                lines.append(line)
                previous_plain_quote = False
                continue
            quoted = line[2:].strip()
            if not quoted:
                lines.append(line)
                previous_plain_quote = False
                continue
            if quoted.startswith("**") and quoted.endswith("**"):
                lines.append(line)
                previous_plain_quote = False
                continue
            if quoted.startswith("- "):
                lines.append(line)
                previous_plain_quote = False
                continue
            if _split_labeled_segments(quoted):
                lines.append(ObsidianClient._format_labeled_text(quoted, quote=True))
                previous_plain_quote = False
                continue
            if previous_plain_quote:
                lines.append(">")
            lines.append(_format_plain_text(quoted, quote=True))
            previous_plain_quote = True
        return "\n".join(lines)

    def upsert_repository(self, record: NotionGitHubRepoRecord) -> Path:
        """寫入或更新 GitHub Repository 資訊到 Repositories 目錄。"""
        # 使用 owner-repo 格式作為檔名以避免名稱重複
        filename_base = record.name.replace("/", "-")
        filename = f"{self.sanitize_filename(filename_base)}.md"
        file_path = self.dirs["repos"] / filename
        user_notes = self._user_notes_section(file_path)

        content = f"""---
type: github-repo
name: {record.name}
url: {record.url}
owner: {record.owner}
stars: {record.stars}
trend: {self._trend_from_action(record.recommended_action)}
momentum: {record.adoption_potential}
first_seen:
last_seen:
category: {record.category}
engineering_value: {record.engineering_value}
adoption_potential: {record.adoption_potential}
recommended_action: {record.recommended_action}
---
# {record.name}

## 摘要
{record.summary}

## 為什麼這重要 (Why it matters)
{self._format_detail_text(record.why_it_matters)}

## 歷史觀察
- Stars: {record.stars}
- Recommended action: {record.recommended_action}

## 相關連結
- [GitHub Repository]({record.url})

{user_notes}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def upsert_paper(self, record: NotionPaperRecord) -> Path:
        """寫入或更新學術論文資訊到 Papers 目錄。"""
        filename = f"{self.sanitize_filename(record.title)}.md"
        file_path = self.dirs["papers"] / filename
        user_notes = self._user_notes_section(file_path)

        content = f"""---
type: paper
title: {record.title}
authors: {record.authors}
url: {record.url}
published_date: {record.published_date}
trend: {self._trend_from_action(record.recommended_action)}
momentum: {record.confidence}
first_seen:
last_seen: {record.published_date}
technology_area: {list(record.technology_area)}
intelligence_score: {record.intelligence_score}
recommended_action: {record.recommended_action}
confidence: {record.confidence}
---
# {record.title}

## 摘要
{record.summary}

## 為什麼這重要 (Why it matters)
{self._format_detail_text(record.why_it_matters)}

## 歷史觀察
- Intelligence score: {record.intelligence_score}
- Confidence: {record.confidence}

## 相關連結
- [Paper]({record.url})

{user_notes}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def upsert_ecosystem(self, record: NotionEcosystemRecord) -> Path:
        """寫入或更新生態系訊號資訊到 Ecosystem 目錄。"""
        filename = f"{self.sanitize_filename(record.name)}.md"
        file_path = self.dirs["ecosystem"] / filename
        user_notes = self._user_notes_section(file_path)

        content = f"""---
type: ecosystem-signal
name: {record.name}
signal_type: {record.type}
company_or_maintainer: {record.company_or_maintainer}
category: {list(record.category)}
impact: {record.impact}
momentum: {record.momentum}
trend: {self._trend_from_action(record.impact)}
first_seen:
last_seen:
---
# {record.name}

## 摘要
{record.summary}

## 為什麼這重要 (Why it matters)
{self._format_detail_text(record.why_it_matters)}

## 歷史觀察
- Impact: {record.impact}
- Momentum: {record.momentum}

## 相關連結

{user_notes}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def convert_to_wikilinks(
        self,
        body: str,
        repository_results: list | tuple,
        paper_results: list | tuple,
        domain_results: list | tuple,
    ) -> str:
        """將 Markdown 內文中的 Repo、Paper 與 Ecosystem 參照轉換為 Obsidian 的雙向連結。"""
        converted_body = body

        # 1. 轉換 Repositories: 將 `[owner/repo](url)` 替換成 `[[Repositories/owner-repo|owner/repo]]`
        for r in repository_results:
            canonical_name = r.entity.canonical_name
            filename_base = canonical_name.replace("/", "-")
            sanitized = self.sanitize_filename(filename_base)
            escaped_name = re.escape(canonical_name)
            
            # 搜尋 Markdown 連結如 `[owner/repo](...)`
            pattern = rf"\[{escaped_name}\]\([^\)]+\)"
            converted_body = re.sub(
                pattern,
                f"[[Repositories/{sanitized}|{canonical_name}]]",
                converted_body,
            )

        # 2. 轉換 Papers: 將 `[paper_title](url)` 替換成 `[[Papers/sanitized_title|paper_title]]`
        for p in paper_results:
            canonical_name = p.entity.canonical_name
            sanitized = self.sanitize_filename(canonical_name)
            escaped_name = re.escape(canonical_name)
            
            # 搜尋 Markdown 連結如 `[title](...)`
            pattern = rf"\[{escaped_name}\]\([^\)]+\)"
            converted_body = re.sub(
                pattern,
                f"[[Papers/{sanitized}|{canonical_name}]]",
                converted_body,
            )

        # 3. 轉換 Domain Signals: 表格中有 `| {signal_title} | {canonical_name} |`
        # 我們將表格中的 `{canonical_name}` 加上雙向連結
        for d in domain_results:
            canonical_name = d.entity.canonical_name
            sanitized = self.sanitize_filename(canonical_name)
            escaped_name = re.escape(canonical_name)
            
            # 搜尋 `| name |` 並取代成 `| [[Ecosystem/sanitized|name]] |`
            pattern = rf"\|\s*({escaped_name})\s*\|"
            converted_body = re.sub(
                pattern,
                rf"| [[Ecosystem/{sanitized}|\1]] |",
                converted_body,
            )
            converted_body = re.sub(
                rf"(?<![\w/\|-]){escaped_name}(?![\w/\]|-])",
                f"[[Ecosystem/{sanitized}|{canonical_name}]]",
                converted_body,
            )

        return converted_body

    def create_daily_brief(
        self,
        date_str: str,
        record: NotionBriefRecord,
        repository_results: list | tuple = (),
        paper_results: list | tuple = (),
        domain_results: list | tuple = (),
    ) -> Path:
        """寫入 Daily Brief 到 DailyBriefs 目錄，並將內文轉換成 Wikilinks。"""
        filename = f"Daily Brief - {date_str}.md"
        file_path = self.dirs["briefs"] / filename
        user_notes = self._user_notes_section(file_path)

        # 轉換內文的連結為 Obsidian 雙向連結
        converted_body = self.convert_to_wikilinks(
            record.body,
            repository_results,
            paper_results,
            domain_results,
        )
        converted_body = self._format_daily_body(converted_body)

        content = f"""---
type: daily-brief
date: {record.date}
intelligence_score: {record.intelligence_score}
confidence: {record.confidence}
recommended_actions: {list(record.recommended_actions)}
tags: {list(record.tags)}
---
# {record.title}

{converted_body}

## 🔗 Notion
{getattr(record, "notion_url", "") or "Notion URL will be added after publishing."}

{user_notes}
"""
        file_path.write_text(content, encoding="utf-8")
        return file_path


_RATIONALE_LABELS = (
    "Why now",
    "What changed",
    "Evidence",
    "Memory",
    "Connects to",
    "Implementation signal",
    "What to do",
    "Confidence",
)

_RATIONALE_PATTERN = re.compile(
    rf"({'|'.join(re.escape(label) for label in _RATIONALE_LABELS)}):"
)


def _split_labeled_segments(text: str) -> list[tuple[str, str]]:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return []
    matches = list(_RATIONALE_PATTERN.finditer(cleaned))
    if not matches or matches[0].start() != 0:
        return []

    segments: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        label = match.group(1)
        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        value = cleaned[value_start:value_end].strip()
        if value:
            segments.append((label, value))
    return segments


def _format_plain_text(text: str, *, quote: bool) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return "> " if quote else ""
    prefix = "> " if quote else ""
    separator = "\n>\n" if quote else "\n"
    return separator.join(f"{prefix}{sentence}" for sentence in _split_sentences(cleaned))


def _split_sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[。.!?])\s+", text) if part.strip()]
    if len(sentences) <= 1:
        return [text]
    return sentences
