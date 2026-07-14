# Quickstart

Supported version: **Python 3.11**.

## Windows PowerShell

```powershell
python -m venv hub_env
.\hub_env\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\hub_env\Scripts\intelligence-hub.exe seed-demo
.\hub_env\Scripts\intelligence-hub.exe serve --seed-demo
```

## Linux/macOS

```bash
python3.11 -m venv hub_env
source hub_env/bin/activate
python -m pip install -e .
cp .env.example .env
intelligence-hub seed-demo
intelligence-hub serve --seed-demo
```

Open the Dashboard at <http://127.0.0.1:8000/>, OpenAPI at <http://127.0.0.1:8000/docs>, and the generated Vault at `data/demo/obsidian_vault/`.

## Compatibility

`scripts/intelligence_hub.py` calls the same platform CLI implementation. Legacy `python -m hermes` commands remain available for existing automation, but Hermes is not the platform runtime owner.
