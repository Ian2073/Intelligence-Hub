# Demo

The release-candidate demo is deterministic and zero-secret.

## What It Seeds

- GitHub repositories from `data/fixtures/github/`
- papers/articles from `data/fixtures/papers/`
- domain signals from `data/fixtures/domains/`
- canonical entities, observations, relationships, events, insights, decisions, briefs, proposals, and runtime metrics
- one rejected proposal and one needs-review proposal for review-surface demonstration
- an Obsidian vault with broken-link diagnostics equal to zero

## Commands

```powershell
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py demo
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py proposals --status needs_review
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py review-proposal <proposal-id> --action revalidate
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py export-obsidian
```

Repeated `seed-demo` runs are idempotent for the managed demo database. To remove generated demo state:

```powershell
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py reset-demo-data --yes
```

The reset command is intentionally limited to `data/demo/`.
