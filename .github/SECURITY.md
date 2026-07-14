# Security Policy

## Reporting A Vulnerability

Please report vulnerabilities through GitHub Security Advisories when available. If advisories are unavailable, open a private maintainer contact channel before posting exploit details publicly.

Do not include live API keys, `.env` files, SQLite memory databases, or production logs in public issues.

## Secrets

Hermes must not commit:

- `.env`
- API keys or tokens
- Notion integration tokens
- Telegram bot tokens
- production SQLite memory
- logs or generated exports that may contain private context

Run before publishing:

```powershell
python scripts/pre_publish_audit.py
```

## Out Of Scope

The project cannot recover or rotate secrets leaked by a user in their own fork, logs, screenshots, or local machine. Rotate leaked credentials with the provider directly.
