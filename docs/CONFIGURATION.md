# Configuration

Intelligence Hub supports two runtime modes.

## Zero-Secret Demo Mode

Demo mode requires no API keys and no external services.

```powershell
Copy-Item .env.example .env
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py seed-demo
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py serve --seed-demo
```

Default demo paths:

- SQLite: `data/demo/intelligence_hub_demo.sqlite`
- Obsidian vault: `data/demo/obsidian_vault/`
- fixtures: `data/fixtures/`

## Configured Mode

Configured mode can enable live collectors, model providers, Notion, Telegram, and optional Hermes integration. Missing external settings should degrade clearly instead of crashing the zero-secret path.

## Preferred Platform Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `INTELLIGENCE_HUB_DB` | `data/demo/intelligence_hub_demo.sqlite` in demo scripts | SQLite repository path |
| `INTELLIGENCE_HUB_FIXTURE_ROOT` | `data/fixtures` | fixture root |
| `INTELLIGENCE_HUB_GITHUB_WATCHLIST_FILE` | `data/watchlists/github_repos.json` | GitHub watchlist |
| `INTELLIGENCE_HUB_PAPER_WATCHLIST_FILE` | `data/watchlists/papers.json` | paper watchlist |
| `INTELLIGENCE_HUB_DOMAIN_WATCHLIST_FILE` | `data/watchlists/domain_signals.json` | domain watchlist |
| `INTELLIGENCE_HUB_SYNTHESIS_MODE` | `hybrid` | `off`, `hybrid`, or `full` |
| `INTELLIGENCE_HUB_OBSIDIAN_ENABLED` | empty/false | non-demo Obsidian publishing |
| `INTELLIGENCE_HUB_OBSIDIAN_VAULT_PATH` | empty | non-demo vault path |

## Compatibility Variables

Legacy entrypoints still support existing names:

- `HERMES_MEMORY_DB`
- `HERMES_FIXTURE_ROOT`
- `HERMES_GITHUB_WATCHLIST_FILE`
- `HERMES_PAPER_WATCHLIST_FILE`
- `HERMES_DOMAIN_WATCHLIST_FILE`
- `HERMES_SYNTHESIS_MODE`
- `OBSIDIAN_ENABLED`
- `OBSIDIAN_VAULT_PATH`

Prefer `INTELLIGENCE_HUB_*` for new platform usage. Keep `HERMES_*` for compatibility scripts and legacy automation.

## Optional Integrations

| Integration | Variables |
| --- | --- |
| Cloud model provider | `INTELLIGENCE_HUB_CLOUD_API_KEY`, `INTELLIGENCE_HUB_FAST_MODEL`, `INTELLIGENCE_HUB_PRO_MODEL` or legacy `HERMES_*` aliases |
| GitHub live fetching | `GITHUB_TOKEN` or `GH_TOKEN` |
| Notion publishing | `NOTION_TOKEN`, `NOTION_PARENT_PAGE_ID`, `NOTION_*_DATABASE_ID` |
| Telegram notification | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Ollama local model | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |

Do not commit `.env`, SQLite databases, logs, or generated Obsidian vaults.
