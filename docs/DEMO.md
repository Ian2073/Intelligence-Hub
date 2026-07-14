# Zero-Secret Demo

The release demo uses deterministic, connected fixture data and requires no API key or external service.

## What It Seeds

- GitHub repository fixtures from `data/fixtures/github/`
- papers and articles from `data/fixtures/papers/`
- domain signals from `data/fixtures/domains/`
- canonical entities, observations, relationships, events, insights, decisions, briefs, and runtime metrics
- accepted, rejected, and needs-review proposals
- an Obsidian Vault with stable IDs and zero broken WikiLinks

## Commands

```bash
intelligence-hub demo
intelligence-hub proposals --status needs_review
intelligence-hub proposals --status rejected
intelligence-hub export-obsidian
```

Run `intelligence-hub seed-demo` twice to verify idempotency. The second run reports `Seeded=False` and does not duplicate canonical records.

Proposal IDs are deterministic but should be read from the current CLI or Dashboard instead of copied from documentation:

```bash
intelligence-hub review-proposal <proposal-id> --action revalidate
```

To remove generated demo state:

```bash
intelligence-hub reset-demo-data --yes
```

Reset is restricted to the managed `data/demo/` directory.
