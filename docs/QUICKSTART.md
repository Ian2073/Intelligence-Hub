# Quickstart

## Zero-Secret Demo

Supported Python version: **Python 3.11**. This is the version exercised by CI.

```powershell
python -m venv hub_env
.\hub_env\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py seed-demo
.\hub_env\Scripts\python.exe scripts\intelligence_hub.py serve --seed-demo
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- OpenAPI docs: `http://127.0.0.1:8000/docs`
- Obsidian vault: `data/demo/obsidian_vault/`

## Compatibility Demo

Legacy Hermes entrypoints remain available:

```powershell
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
.\hub_env\Scripts\python.exe -m hermes status
```

Hermes is an optional integration and compatibility layer, not the platform runtime owner.
