# Contributing

## Development Principles

- Keep Intelligence Hub local-first and fixture-testable.
- Prefer platform-neutral names in new public surfaces.
- Preserve Hermes compatibility without making Hermes own canonical persistence.
- Do not commit `.env`, SQLite runtime databases, generated logs, or generated Obsidian vaults.
- Avoid claiming production or live readiness from local tests alone.

## Validation

Before submitting a pull request:

```powershell
.\hub_env\Scripts\python.exe -m pytest tests -q
.\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py seed-demo
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py export-obsidian
```

Also check that Obsidian broken-link diagnostics remain at zero for generated demo vaults.

## Scope Discipline

This project intentionally defers PostgreSQL, authentication, multi-user deployment, causal graphs, full WorldState, and full Hermes proposal-producer migration until later milestones.
