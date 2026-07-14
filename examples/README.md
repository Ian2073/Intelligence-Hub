# Hermes Fixture Demo

This directory contains the zero-secret fixture demo entrypoint and a small set of committed sample outputs.

## Samples

`examples/samples/` contains static Markdown examples generated from the fixture-backed demo:

- `samples/DailyBriefs/Daily Brief - 2026-07-10.md`
- `samples/Repositories/openai-openai-agents-python.md`
- `samples/Papers/Tool Learning with Foundation Agents.md`
- `samples/Ecosystem/Agentic security evaluation.md`

These files are committed so GitHub visitors can inspect Hermes output before running the project locally.

## Regenerate Output

Run from the repository root:

```powershell
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```

The demo uses repository fixtures, paper fixtures, domain RSS fixtures, local SQLite memory, and Markdown/Obsidian output. It does not require Notion, Telegram, GitHub, or cloud model credentials.

Generated files under `examples/output/` are runtime artifacts and are ignored by source control. To refresh committed samples, regenerate the demo and copy only representative Markdown files from `examples/output/obsidian/` into `examples/samples/`.
