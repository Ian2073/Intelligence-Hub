from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

from connectors.retry import retry_on_transient


class NotionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublishedPage:
    id: str
    url: str | None


@dataclass(frozen=True)
class NotionBriefRecord:
    title: str
    date: str
    executive_summary: str
    recommended_actions: tuple[str, ...]
    intelligence_score: int
    confidence: str
    status: str
    tags: tuple[str, ...]
    body: str


@dataclass(frozen=True)
class NotionDecisionRecord:
    title: str
    action: str
    rationale: str
    expected_payoff: str
    risk: str
    revisit_date: str
    confidence: str
    signal_id: str
    status: str


@dataclass(frozen=True)
class NotionRadarSnapshotRecord:
    title: str
    as_of: str
    executive_summary: str
    entity_count: int
    top_actions: tuple[str, ...]
    status: str
    body: str


@dataclass(frozen=True)
class NotionRadarEntityRecord:
    name: str
    type: str
    status: str
    last_seen: str
    summary: str
    tags: tuple[str, ...]
    observation_count: int
    relationship_count: int
    recent_metrics: tuple[str, ...]


@dataclass(frozen=True)
class NotionPaperRecord:
    title: str
    authors: str
    url: str
    published_date: str
    summary: str
    why_it_matters: str
    technology_area: tuple[str, ...]
    intelligence_score: int
    recommended_action: str
    confidence: str


@dataclass(frozen=True)
class NotionGitHubRepoRecord:
    name: str
    url: str
    owner: str
    stars: int
    category: str
    summary: str
    why_it_matters: str
    engineering_value: str
    adoption_potential: str
    recommended_action: str


@dataclass(frozen=True)
class NotionEcosystemRecord:
    name: str
    type: str
    company_or_maintainer: str
    category: tuple[str, ...]
    summary: str
    why_it_matters: str
    impact: str
    momentum: str


@dataclass(frozen=True)
class NotionDatabaseSpec:
    key: str
    title: str
    properties: dict


class NotionClient:
    def __init__(self, token: str, parent_page_id: str, timeout: float = 30.0) -> None:
        self.token = token
        self.parent_page_id = parent_page_id
        self.timeout = timeout

    def create_page(self, title: str, body: str) -> PublishedPage:
        payload = {
            "parent": {"page_id": self.parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title[:2000],
                            }
                        }
                    ]
                }
            },
            "children": _paragraph_blocks(body),
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        try:
            response = retry_on_transient(
                lambda: httpx.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                ),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        page_id = str(data.get("id", "")).strip()
        if not page_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=page_id, url=data.get("url"))

    def create_brief_record(self, database_id: str, record: NotionBriefRecord) -> PublishedPage:
        payload = build_brief_database_payload(database_id, record)
        return self._post_page(payload)

    def create_decision_record(self, database_id: str, record: NotionDecisionRecord) -> PublishedPage:
        payload = build_decision_database_payload(database_id, record)
        return self._post_page(payload)

    def upsert_decision_record(self, database_id: str, record: NotionDecisionRecord) -> PublishedPage:
        existing = self.find_database_page_by_rich_text(database_id, "Signal ID", record.signal_id)
        if existing is None:
            return self.create_decision_record(database_id, record)
        return self.update_decision_record(existing.id, record)

    def update_decision_record(self, page_id: str, record: NotionDecisionRecord) -> PublishedPage:
        payload = build_decision_update_payload(record)
        data = self._patch_json(f"https://api.notion.com/v1/pages/{page_id}", payload)
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def create_radar_snapshot_record(self, database_id: str, record: NotionRadarSnapshotRecord) -> PublishedPage:
        payload = build_radar_snapshot_database_payload(database_id, record)
        return self._post_page(payload)

    def create_radar_entity_record(self, database_id: str, record: NotionRadarEntityRecord) -> PublishedPage:
        payload = build_radar_entity_database_payload(database_id, record)
        return self._post_page(payload)

    def upsert_radar_entity_record(self, database_id: str, record: NotionRadarEntityRecord) -> PublishedPage:
        existing = self.find_database_page_by_title(database_id, "Name", record.name)
        if existing is None:
            return self.create_radar_entity_record(database_id, record)
        return self.update_radar_entity_record(existing.id, record)

    def update_radar_entity_record(self, page_id: str, record: NotionRadarEntityRecord) -> PublishedPage:
        payload = build_radar_entity_update_payload(record)
        data = self._patch_json(f"https://api.notion.com/v1/pages/{page_id}", payload)
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def create_paper_record(self, database_id: str, record: NotionPaperRecord) -> PublishedPage:
        payload = build_paper_database_payload(database_id, record)
        return self._post_page(payload)

    def upsert_paper_record(self, database_id: str, record: NotionPaperRecord) -> PublishedPage:
        existing = self.find_database_page_by_url(database_id, "URL", record.url)
        if existing is None:
            return self.create_paper_record(database_id, record)
        return self.update_paper_record(existing.id, record)

    def update_paper_record(self, page_id: str, record: NotionPaperRecord) -> PublishedPage:
        payload = build_paper_update_payload(record)
        data = self._patch_json(f"https://api.notion.com/v1/pages/{page_id}", payload)
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def create_github_repo_record(self, database_id: str, record: NotionGitHubRepoRecord) -> PublishedPage:
        payload = build_github_repo_database_payload(database_id, record)
        return self._post_page(payload)

    def upsert_github_repo_record(self, database_id: str, record: NotionGitHubRepoRecord) -> PublishedPage:
        existing = self.find_database_page_by_title(database_id, "Name", record.name)
        if existing is None:
            return self.create_github_repo_record(database_id, record)
        return self.update_github_repo_record(existing.id, record)

    def update_github_repo_record(self, page_id: str, record: NotionGitHubRepoRecord) -> PublishedPage:
        payload = build_github_repo_update_payload(record)
        data = self._patch_json(f"https://api.notion.com/v1/pages/{page_id}", payload)
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def create_ecosystem_record(self, database_id: str, record: NotionEcosystemRecord) -> PublishedPage:
        payload = build_ecosystem_database_payload(database_id, record)
        return self._post_page(payload)

    def upsert_ecosystem_record(self, database_id: str, record: NotionEcosystemRecord) -> PublishedPage:
        existing = self.find_database_page_by_title(database_id, "Name", record.name)
        if existing is None:
            return self.create_ecosystem_record(database_id, record)
        return self.update_ecosystem_record(existing.id, record)

    def update_ecosystem_record(self, page_id: str, record: NotionEcosystemRecord) -> PublishedPage:
        payload = build_ecosystem_update_payload(record)
        data = self._patch_json(f"https://api.notion.com/v1/pages/{page_id}", payload)
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def _post_page(self, payload: dict) -> PublishedPage:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        try:
            response = retry_on_transient(
                lambda: httpx.post(
                    "https://api.notion.com/v1/pages",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                ),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        page_id = str(data.get("id", "")).strip()
        if not page_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=page_id, url=data.get("url"))

    def create_database(self, spec: NotionDatabaseSpec) -> PublishedPage:
        payload = build_database_payload(self.parent_page_id, spec)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        try:
            response = retry_on_transient(
                lambda: httpx.post(
                    "https://api.notion.com/v1/databases",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                ),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        database_id = str(data.get("id", "")).strip()
        if not database_id:
            raise NotionError("Notion did not return a database id.")
        return PublishedPage(id=database_id, url=data.get("url"))

    def retrieve_page(self, page_id: str | None = None) -> PublishedPage:
        data = self._get_json(f"https://api.notion.com/v1/pages/{page_id or self.parent_page_id}")
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a page id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def retrieve_database(self, database_id: str) -> PublishedPage:
        data = self._get_json(f"https://api.notion.com/v1/databases/{database_id}")
        resolved_id = str(data.get("id", "")).strip()
        if not resolved_id:
            raise NotionError("Notion did not return a database id.")
        return PublishedPage(id=resolved_id, url=data.get("url"))

    def find_database_page_by_title(self, database_id: str, property_name: str, title: str) -> PublishedPage | None:
        payload = build_database_title_query_payload(property_name, title)
        data = self._post_json(f"https://api.notion.com/v1/databases/{database_id}/query", payload)
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            return None
        page_id = str(first.get("id", "")).strip()
        if not page_id:
            return None
        return PublishedPage(id=page_id, url=first.get("url"))

    def find_database_page_by_rich_text(self, database_id: str, property_name: str, text: str) -> PublishedPage | None:
        payload = build_database_rich_text_query_payload(property_name, text)
        data = self._post_json(f"https://api.notion.com/v1/databases/{database_id}/query", payload)
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            return None
        page_id = str(first.get("id", "")).strip()
        if not page_id:
            return None
        return PublishedPage(id=page_id, url=first.get("url"))

    def find_database_page_by_url(self, database_id: str, property_name: str, url: str) -> PublishedPage | None:
        payload = build_database_url_query_payload(property_name, url)
        data = self._post_json(f"https://api.notion.com/v1/databases/{database_id}/query", payload)
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            return None
        page_id = str(first.get("id", "")).strip()
        if not page_id:
            return None
        return PublishedPage(id=page_id, url=first.get("url"))

    def _get_json(self, url: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
        }
        try:
            response = retry_on_transient(
                lambda: httpx.get(url, headers=headers, timeout=self.timeout),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise NotionError("Notion returned a non-object payload.")
        return data

    def _post_json(self, url: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        try:
            response = retry_on_transient(
                lambda: httpx.post(url, headers=headers, json=payload, timeout=self.timeout),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise NotionError("Notion returned a non-object payload.")
        return data

    def _patch_json(self, url: str, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        try:
            response = retry_on_transient(
                lambda: httpx.patch(url, headers=headers, json=payload, timeout=self.timeout),
                operation_name="Notion API",
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NotionError(
                f"Notion returned HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except Exception as exc:
            raise NotionError(f"Notion request failed: {exc}") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise NotionError("Notion returned a non-object payload.")
        return data


def build_brief_database_payload(database_id: str, record: NotionBriefRecord) -> dict:
    return {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": record.title[:2000]}}]},
            "Date": {"date": {"start": record.date}},
            "Executive Summary": {"rich_text": [{"text": {"content": record.executive_summary[:2000]}}]},
            "Recommended Actions": {
                "multi_select": [{"name": action} for action in record.recommended_actions]
            },
            "Intelligence Score": {"number": record.intelligence_score},
            "Confidence": {"select": {"name": record.confidence}},
            "Status": {"select": {"name": record.status}},
            "Tags": {"multi_select": [{"name": tag} for tag in record.tags]},
        },
        "children": _rich_body_blocks(record.body),
    }


def build_decision_database_payload(database_id: str, record: NotionDecisionRecord) -> dict:
    return {
        "parent": {"database_id": database_id},
        "properties": build_decision_properties(record),
    }


def build_decision_update_payload(record: NotionDecisionRecord) -> dict:
    return {"properties": build_decision_properties(record)}


def build_decision_properties(record: NotionDecisionRecord) -> dict:
    return {
        "Name": {"title": [{"text": {"content": record.title[:2000]}}]},
        "Action": {"select": {"name": record.action}},
        "Rationale": {"rich_text": [{"text": {"content": record.rationale[:2000]}}]},
        "Expected Payoff": {"rich_text": [{"text": {"content": record.expected_payoff[:2000]}}]},
        "Risk": {"rich_text": [{"text": {"content": record.risk[:2000]}}]},
        "Revisit Date": {"date": {"start": record.revisit_date}},
        "Confidence": {"select": {"name": record.confidence}},
        "Signal ID": {"rich_text": [{"text": {"content": record.signal_id[:2000]}}]},
        "Status": {"select": {"name": record.status}},
    }


def build_radar_snapshot_database_payload(database_id: str, record: NotionRadarSnapshotRecord) -> dict:
    return {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": record.title[:2000]}}]},
            "As Of": {"date": {"start": record.as_of}},
            "Executive Summary": {"rich_text": [{"text": {"content": record.executive_summary[:2000]}}]},
            "Entity Count": {"number": record.entity_count},
            "Top Actions": {"multi_select": [{"name": action} for action in record.top_actions]},
            "Status": {"select": {"name": record.status}},
        },
        "children": _rich_body_blocks(record.body),
    }


def build_radar_entity_database_payload(database_id: str, record: NotionRadarEntityRecord) -> dict:
    body = "\n".join(
        (
            record.summary,
            "",
            "Recent metrics:",
            *(f"- {metric}" for metric in record.recent_metrics),
        )
    )
    return {
        "parent": {"database_id": database_id},
        "properties": build_radar_entity_properties(record),
        "children": _paragraph_blocks(body),
    }


def build_radar_entity_update_payload(record: NotionRadarEntityRecord) -> dict:
    return {"properties": build_radar_entity_properties(record)}


def build_radar_entity_properties(record: NotionRadarEntityRecord) -> dict:
    return {
        "Name": {"title": [{"text": {"content": record.name[:2000]}}]},
        "Type": {"select": {"name": record.type}},
        "Status": {"select": {"name": record.status}},
        "Last Seen": {"date": {"start": record.last_seen}},
        "Summary": {"rich_text": [{"text": {"content": record.summary[:2000]}}]},
        "Tags": {"multi_select": [{"name": tag} for tag in record.tags]},
        "Observation Count": {"number": record.observation_count},
        "Relationship Count": {"number": record.relationship_count},
    }


def build_database_title_query_payload(property_name: str, title: str) -> dict:
    return {
        "filter": {
            "property": property_name,
            "title": {
                "equals": title[:2000],
            },
        },
        "page_size": 1,
    }


def build_database_rich_text_query_payload(property_name: str, text: str) -> dict:
    return {
        "filter": {
            "property": property_name,
            "rich_text": {
                "equals": text[:2000],
            },
        },
        "page_size": 1,
    }


def build_database_url_query_payload(property_name: str, url: str) -> dict:
    return {
        "filter": {
            "property": property_name,
            "url": {
                "equals": url[:2000],
            },
        },
        "page_size": 1,
    }


def build_paper_database_payload(database_id: str, record: NotionPaperRecord) -> dict:
    body = _paper_body(record)
    return {
        "parent": {"database_id": database_id},
        "properties": build_paper_properties(record),
        "children": _rich_body_blocks(body),
    }


def build_paper_update_payload(record: NotionPaperRecord) -> dict:
    return {"properties": build_paper_properties(record)}


def build_paper_properties(record: NotionPaperRecord) -> dict:
    return {
        "Title": {"title": [{"text": {"content": record.title[:2000]}}]},
        "Authors": {"rich_text": [{"text": {"content": record.authors[:2000]}}]},
        "URL": {"url": record.url},
        "Published Date": {"date": {"start": record.published_date}},
        "Summary": {"rich_text": [{"text": {"content": record.summary[:2000]}}]},
        "Why It Matters": {"rich_text": [{"text": {"content": record.why_it_matters[:2000]}}]},
        "Technology Area": {"multi_select": [{"name": area} for area in record.technology_area]},
        "Intelligence Score": {"number": record.intelligence_score},
        "Recommended Action": {"select": {"name": record.recommended_action}},
        "Confidence": {"select": {"name": record.confidence}},
    }


def build_github_repo_database_payload(database_id: str, record: NotionGitHubRepoRecord) -> dict:
    body = _github_repo_body(record)
    return {
        "parent": {"database_id": database_id},
        "properties": build_github_repo_properties(record),
        "children": _rich_body_blocks(body),
    }


def build_github_repo_update_payload(record: NotionGitHubRepoRecord) -> dict:
    return {"properties": build_github_repo_properties(record)}


def build_github_repo_properties(record: NotionGitHubRepoRecord) -> dict:
    return {
        "Name": {"title": [{"text": {"content": record.name[:2000]}}]},
        "URL": {"url": record.url},
        "Owner": {"rich_text": [{"text": {"content": record.owner[:2000]}}]},
        "Stars": {"number": record.stars},
        "Category": {"select": {"name": record.category}},
        "Summary": {"rich_text": [{"text": {"content": record.summary[:2000]}}]},
        "Why It Matters": {"rich_text": [{"text": {"content": record.why_it_matters[:2000]}}]},
        "Engineering Value": {"select": {"name": record.engineering_value}},
        "Adoption Potential": {"select": {"name": record.adoption_potential}},
        "Recommended Action": {"select": {"name": record.recommended_action}},
    }


def build_ecosystem_database_payload(database_id: str, record: NotionEcosystemRecord) -> dict:
    body = _ecosystem_body(record)
    return {
        "parent": {"database_id": database_id},
        "properties": build_ecosystem_properties(record),
        "children": _rich_body_blocks(body),
    }


def build_ecosystem_update_payload(record: NotionEcosystemRecord) -> dict:
    return {"properties": build_ecosystem_properties(record)}


def build_ecosystem_properties(record: NotionEcosystemRecord) -> dict:
    return {
        "Name": {"title": [{"text": {"content": record.name[:2000]}}]},
        "Type": {"select": {"name": record.type}},
        "Company or Maintainer": {"rich_text": [{"text": {"content": record.company_or_maintainer[:2000]}}]},
        "Category": {"multi_select": [{"name": category} for category in record.category]},
        "Summary": {"rich_text": [{"text": {"content": record.summary[:2000]}}]},
        "Why It Matters": {"rich_text": [{"text": {"content": record.why_it_matters[:2000]}}]},
        "Impact": {"select": {"name": record.impact}},
        "Momentum": {"select": {"name": record.momentum}},
    }


def notion_workspace_database_specs() -> tuple[NotionDatabaseSpec, ...]:
    return (
        NotionDatabaseSpec(
            key="briefs",
            title="AI Intelligence Briefs",
            properties={
                "Name": {"title": {}},
                "Date": {"date": {}},
                "Executive Summary": {"rich_text": {}},
                "Recommended Actions": {"multi_select": {"options": _select_options("Ignore", "Watch", "Read", "Prototype", "Implement", "Review later")}},
                "Intelligence Score": {"number": {"format": "number"}},
                "Confidence": {"select": {"options": _select_options("low", "medium", "high")}},
                "Status": {"select": {"options": _select_options("Draft", "Published", "Failed")}},
                "Tags": {"multi_select": {}},
            },
        ),
        NotionDatabaseSpec(
            key="papers",
            title="Papers",
            properties={
                "Title": {"title": {}},
                "Authors": {"rich_text": {}},
                "URL": {"url": {}},
                "Published Date": {"date": {}},
                "Summary": {"rich_text": {}},
                "Why It Matters": {"rich_text": {}},
                "Technology Area": {"multi_select": {}},
                "Intelligence Score": {"number": {"format": "number"}},
                "Recommended Action": {"select": {"options": _select_options("Ignore", "Watch", "Read", "Prototype", "Implement", "Review later")}},
                "Confidence": {"select": {"options": _select_options("low", "medium", "high")}},
            },
        ),
        NotionDatabaseSpec(
            key="github_repos",
            title="GitHub Repos",
            properties={
                "Name": {"title": {}},
                "URL": {"url": {}},
                "Owner": {"rich_text": {}},
                "Stars": {"number": {"format": "number"}},
                "Category": {"select": {"options": _select_options("AI Agent", "Inference", "RAG", "Developer Tool", "Infrastructure")}},
                "Summary": {"rich_text": {}},
                "Why It Matters": {"rich_text": {}},
                "Engineering Value": {"select": {"options": _select_options("low", "medium", "high")}},
                "Adoption Potential": {"select": {"options": _select_options("low", "medium", "high")}},
                "Recommended Action": {"select": {"options": _select_options("Ignore", "Watch", "Read", "Prototype", "Implement", "Review later")}},
            },
        ),
        NotionDatabaseSpec(
            key="ecosystem",
            title="AI Ecosystem",
            properties={
                "Name": {"title": {}},
                "Type": {"select": {"options": _select_options("Technology", "Company", "Product", "Trend", "Concept")}},
                "Company or Maintainer": {"rich_text": {}},
                "Category": {"multi_select": {}},
                "Summary": {"rich_text": {}},
                "Why It Matters": {"rich_text": {}},
                "Impact": {"select": {"options": _select_options("low", "medium", "high")}},
                "Momentum": {"select": {"options": _select_options("flat", "watch", "active", "rising", "surging")}},
            },
        ),
        NotionDatabaseSpec(
            key="decisions",
            title="Decisions",
            properties={
                "Name": {"title": {}},
                "Action": {"select": {"options": _select_options("Ignore", "Watch", "Read", "Prototype", "Implement", "Review later")}},
                "Rationale": {"rich_text": {}},
                "Expected Payoff": {"rich_text": {}},
                "Risk": {"rich_text": {}},
                "Revisit Date": {"date": {}},
                "Confidence": {"select": {"options": _select_options("low", "medium", "high")}},
                "Signal ID": {"rich_text": {}},
                "Status": {"select": {"options": _select_options("Open", "Reviewed", "Closed")}},
            },
        ),
        NotionDatabaseSpec(
            key="radar_snapshots",
            title="Radar Snapshots",
            properties={
                "Name": {"title": {}},
                "As Of": {"date": {}},
                "Executive Summary": {"rich_text": {}},
                "Entity Count": {"number": {"format": "number"}},
                "Top Actions": {"multi_select": {"options": _select_options("Ignore", "Watch", "Read", "Prototype", "Implement", "Review later")}},
                "Status": {"select": {"options": _select_options("Draft", "Published", "Failed")}},
            },
        ),
        NotionDatabaseSpec(
            key="radar_entities",
            title="Radar Entities",
            properties={
                "Name": {"title": {}},
                "Type": {"select": {"options": _select_options("Technology", "Company", "Repository", "Paper", "Product", "Person", "Topic", "Source", "Trend", "Concept")}},
                "Status": {"select": {"options": _select_options("new", "active", "watch", "growing", "declining", "archived")}},
                "Last Seen": {"date": {}},
                "Summary": {"rich_text": {}},
                "Tags": {"multi_select": {}},
                "Observation Count": {"number": {"format": "number"}},
                "Relationship Count": {"number": {"format": "number"}},
            },
        ),
    )


def build_database_payload(parent_page_id: str, spec: NotionDatabaseSpec) -> dict:
    return {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": spec.title}}],
        "properties": spec.properties,
    }


def _select_options(*names: str) -> list[dict]:
    return [{"name": name} for name in names]


def _paragraph_blocks(body: str) -> list[dict]:
    blocks: list[dict] = []
    for chunk in _chunks(body.strip() or "(empty)", 1800):
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": chunk},
                        }
                    ]
                },
            }
        )
    return blocks


def _chunks(text: str, size: int) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]


def _parse_markdown_text(text: str) -> list[dict]:
    pattern = re.compile(r"(\*\*.*?\*\*)")
    parts = pattern.split(text)
    rich_text = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            rich_text.append({
                "type": "text",
                "text": {"content": part[2:-2][:2000]},
                "annotations": {"bold": True}
            })
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": part[:2000]}
            })
    if not rich_text:
        rich_text.append({"type": "text", "text": {"content": "(empty)"}})
    return rich_text


def _rich_body_blocks(body: str) -> list[dict]:
    blocks: list[dict] = []
    lines = body.strip().split("\n")

    has_headings = any(line.strip().startswith("## ") or line.strip().startswith("### ") for line in lines)
    if has_headings:
        # Add Table of Contents
        blocks.append({
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {}
        })

        blocks.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        line_strip = line.strip()

        # 1. Handle Markdown Table
        if line_strip.startswith("|") and line_strip.endswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 1:
                header_cols = [col.strip() for col in table_lines[0].split("|")[1:-1]]
                table_width = len(header_cols)

                children = []
                children.append({
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [_parse_markdown_text(col) for col in header_cols]
                    }
                })

                start_row = 1
                if len(table_lines) > 1 and all(c in "-:| " for c in table_lines[1].replace("|", "")):
                    start_row = 2

                for row_line in table_lines[start_row:]:
                    row_cols = [col.strip() for col in row_line.split("|")[1:-1]]
                    if len(row_cols) < table_width:
                        row_cols.extend([""] * (table_width - len(row_cols)))
                    else:
                        row_cols = row_cols[:table_width]

                    children.append({
                        "object": "block",
                        "type": "table_row",
                        "table_row": {
                            "cells": [_parse_markdown_text(col) for col in row_cols]
                        }
                    })

                blocks.append({
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": table_width,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": children
                    }
                })
            continue

        # 2. Handle Markdown Callout blockquote
        if line_strip.startswith("> "):
            callout_lines = []
            callout_icon = "💡"
            callout_color = "gray_background"

            inner = line_strip[2:].strip()
            directive = inner.split("]", 1)[0].casefold() + "]" if inner.startswith("[!") and "]" in inner else ""
            if directive == "[!note]":
                callout_icon = "💡"
                callout_color = "blue_background"
                content = inner[7:].strip()
                if content:
                    callout_lines.append(content)
            elif directive == "[!summary]":
                callout_icon = "🧭"
                callout_color = "blue_background"
                content = inner[10:].strip()
                if content:
                    callout_lines.append(content)
            elif directive == "[!important]":
                callout_icon = "🎯"
                callout_color = "orange_background"
                content = inner[12:].strip()
                if content:
                    callout_lines.append(content)
            elif directive == "[!warning]":
                callout_icon = "⚠️"
                callout_color = "yellow_background"
                content = inner[10:].strip()
                if content:
                    callout_lines.append(content)
            elif directive == "[!tip]":
                callout_icon = "💡"
                callout_color = "green_background"
                content = inner[6:].strip()
                if content:
                    callout_lines.append(content)
            else:
                callout_lines.append(inner)

            i += 1
            while i < n and lines[i].strip().startswith("> "):
                inner_line = lines[i].strip()[2:].strip()
                callout_lines.append(inner_line)
                i += 1

            text_content = "\n".join(callout_lines)
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": _parse_markdown_text(text_content),
                    "icon": {"emoji": callout_icon},
                    "color": callout_color
                }
            })
            continue

        if not line_strip:
            i += 1
            continue

        if line_strip.startswith("## "):
            content = line_strip[3:].strip()
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                }
            })
        elif line_strip.startswith("### "):
            content = line_strip[4:].strip()
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                }
            })
        elif line_strip in ("---", "***"):
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        elif line_strip.startswith("- Rationale:"):
            content = line_strip.removeprefix("- Rationale:").strip()
            blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": "Decision rationale"}}],
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": _parse_markdown_text(content)},
                        }
                    ],
                },
            })
        elif line_strip.startswith("- "):
            content = line_strip[2:].strip()
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": _parse_markdown_text(content)
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": _parse_markdown_text(line_strip)
                }
            })
        i += 1

    return blocks[:100]


def _github_repo_body(record: NotionGitHubRepoRecord) -> str:
    lines = [
        f"## {record.name}",
        "",
        record.summary or "(No description)",
        "",
        "---",
        "",
        "### Why It Matters",
        "",
        record.why_it_matters or "(No rationale)",
        "",
        "### Metrics",
        "",
        f"- ⭐ **Stars**: {record.stars:,}" if record.stars is not None else "- ⭐ **Stars**: 0",
        f"- 🏷️ **Category**: {record.category}",
        f"- 🔧 **Engineering Value**: {record.engineering_value}",
        f"- 📈 **Adoption Potential**: {record.adoption_potential}",
        f"- 🎯 **Recommended Action**: {record.recommended_action}",
    ]
    if record.url:
        lines.extend(["", f"🔗 [GitHub Repository]({record.url})"])
    return "\n".join(lines)


def _paper_body(record: NotionPaperRecord) -> str:
    lines = [
        f"## {record.title}",
        "",
        "### Summary",
        "",
        record.summary or "(No summary)",
        "",
        "---",
        "",
        "### Why It Matters",
        "",
        record.why_it_matters or "(No rationale)",
        "",
        "### Details",
        "",
        f"- 📊 **Intelligence Score**: {record.intelligence_score}/100",
        f"- 🎯 **Recommended Action**: {record.recommended_action}",
        f"- 🔒 **Confidence**: {record.confidence}",
    ]
    if record.authors:
        lines.append(f"- 👥 **Authors**: {record.authors}")
    if record.technology_area:
        lines.append(f"- 🏷️ **Technology Area**: {', '.join(record.technology_area)}")
    if record.url:
        lines.extend(["", f"🔗 [Paper Link]({record.url})"])
    return "\n".join(lines)


def _ecosystem_body(record: NotionEcosystemRecord) -> str:
    lines = [
        f"## {record.name}",
        "",
        record.summary or "(No summary)",
        "",
        "---",
        "",
        "### Why It Matters",
        "",
        record.why_it_matters or "(No rationale)",
        "",
        "### Metrics",
        "",
        f"- 📊 **Impact**: {record.impact}",
        f"- 📈 **Momentum**: {record.momentum}",
        f"- 🏷️ **Type**: {record.type}",
    ]
    if record.company_or_maintainer:
        lines.append(f"- 🏢 **Company/Maintainer**: {record.company_or_maintainer}")
    if record.category:
        lines.append(f"- 📂 **Category**: {', '.join(record.category)}")
    return "\n".join(lines)
