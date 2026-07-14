# Intelligence Hub Demo Evidence

The canonical demo output is generated from repository fixtures instead of committed as a partial or stale Vault.

Run:

```bash
intelligence-hub seed-demo
intelligence-hub serve --seed-demo
```

Then inspect:

- Dashboard: <http://127.0.0.1:8000/>
- Proposal lifecycle: [`docs/proposal-trust-layer.md`](../docs/proposal-trust-layer.md)
- Generated Obsidian Workspace: `data/demo/obsidian_vault/`
- Public Dashboard screenshots: [`docs/assets/`](../docs/assets/)

Generated SQLite databases and Vault files are intentionally ignored. This prevents a developer workspace snapshot from becoming a public fixture dependency.
