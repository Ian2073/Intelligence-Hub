from __future__ import annotations

from dataclasses import dataclass

from connectors.notion import NotionClient, NotionDatabaseSpec, PublishedPage, notion_workspace_database_specs


@dataclass(frozen=True)
class ProvisionedDatabase:
    key: str
    title: str
    status: str
    id: str
    url: str


def provision_notion_workspace(
    *,
    notion_client: NotionClient | None,
    apply: bool = False,
    existing_database_ids: dict[str, str] | None = None,
    specs: tuple[NotionDatabaseSpec, ...] | None = None,
) -> tuple[ProvisionedDatabase, ...]:
    database_specs = specs or notion_workspace_database_specs()
    existing_ids = existing_database_ids or {}
    if not apply:
        return tuple(
            ProvisionedDatabase(
                key=spec.key,
                title=spec.title,
                status="dry-run",
                id="",
                url="",
            )
            for spec in database_specs
        )
    if notion_client is None:
        return tuple(
            ProvisionedDatabase(
                key=spec.key,
                title=spec.title,
                status="skipped",
                id="",
                url="Missing Notion client.",
            )
            for spec in database_specs
        )

    results = []
    for spec in database_specs:
        existing_id = existing_ids.get(spec.key, "").strip()
        if existing_id:
            results.append(
                ProvisionedDatabase(
                    key=spec.key,
                    title=spec.title,
                    status="existing",
                    id=existing_id,
                    url="",
                )
            )
            continue
        page: PublishedPage = notion_client.create_database(spec)
        results.append(
            ProvisionedDatabase(
                key=spec.key,
                title=spec.title,
                status="created",
                id=page.id,
                url=page.url or "",
            )
        )
    return tuple(results)
