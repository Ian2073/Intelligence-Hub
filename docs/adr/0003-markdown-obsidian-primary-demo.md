# ADR 0003: Markdown And Obsidian Are The Primary Demo Surface

## Status

Accepted

## Context

Notion remains useful for configured workspaces, but open-source users should be able to see Intelligence Hub output without API keys or workspace provisioning.

## Decision

Markdown/Obsidian is the primary zero-secret demo surface. Notion and Telegram are optional publisher adapters used when credentials are configured.

## Consequences

- `intelligence-hub seed-demo` can run from fixtures and produce readable output locally.
- The core intelligence pipeline cannot depend on Notion database schema.
- Delivery behavior must report skipped optional integrations instead of crashing.
