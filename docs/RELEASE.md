# Release Checklist

Use this checklist for the first public push and `v0.1.0` release.

## Local Verification

1. Run the pre-publish audit:

   ```powershell
   python scripts/pre_publish_audit.py
   ```

2. Run the CI-equivalent local checks:

   ```powershell
   .\hub_env\Scripts\python.exe -m pytest tests -q
   .\hub_env\Scripts\python.exe -m compileall contracts core connectors hermes workflows scripts main.py
   .\hub_env\Scripts\python.exe scripts\smoke_test.py
   .\hub_env\Scripts\python.exe scripts\acceptance_check.py
   .\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
   .\hub_env\Scripts\python.exe scripts\first_run_check.py
   ```

3. Confirm committed samples and preview assets exist:

   - `examples/samples/`
   - `docs/assets/daily-brief-preview.png`

## GitHub Repository Metadata

- Description: `Local-first decision intelligence: turn GitHub, papers, and RSS into actionable briefs with memory.`
- Topics: `decision-intelligence`, `local-first`, `obsidian`, `github-radar`, `arxiv`, `sqlite`, `python`, `intelligence-platform`
- Website: leave blank or point to repository docs
- Social preview: `docs/assets/daily-brief-preview.png`

## Publish

1. Confirm `git status` is clean except ignored local runtime files.
2. Push the repository.
3. Wait for GitHub Actions to pass on Windows and Linux.
4. Create GitHub Release `v0.1.0`.
5. Tag the completed release commit:

   ```powershell
   git tag v0.1.0
   git push origin v0.1.0
   ```

## Post-publish Smoke

Clone into a fresh directory and run:

```powershell
python -m venv hub_env
.\hub_env\Scripts\python.exe -m pip install -r requirements.txt
.\hub_env\Scripts\python.exe -m hermes demo --date 2026-07-10 --output examples/output/obsidian
```
