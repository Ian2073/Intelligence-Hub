# Intelligence Hub

[![CI](https://github.com/Ian2073/Intelligence-Hub/actions/workflows/ci.yml/badge.svg)](https://github.com/Ian2073/Intelligence-Hub/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![授權：MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Ian2073/Intelligence-Hub?include_prereleases)](https://github.com/Ian2073/Intelligence-Hub/releases)

**一個 local-first 決策情報平台，將分散的技術訊號轉成有證據、可追溯、可採取行動的知識與決策。**

當你同時追蹤數十個 GitHub repositories、論文與 RSS 來源時，真正困難的不是收集更多連結，而是判斷發生了什麼變化、有哪些證據、不同來源之間如何連接，以及這項訊號究竟值得 `Watch`、`Read`、`Prototype` 或 `Implement`。

Intelligence Hub 會先保存 evidence。模型、Agent 或 extraction 產生的結果必須先成為 proposal，通過驗證後才能進入 canonical knowledge。

```text
Information → Evidence → Proposal → Validated Knowledge → Insight → Decision → Actionable Brief
```

它不是新聞摘要器、一般 RAG demo，也不是讓 Agent 自行無限迴圈執行的框架。

## 核心差異

- **Proposal Trust Layer**：未驗證的 AI 輸出不得直接污染正式知識。
- **Canonical SQLite Repository**：保存 Entity、Observation、Relationship、Event、Insight、Decision、Brief、Proposal 與執行指標。
- **決策優先**：將訊號轉成明確 action posture，而不是再產生一份無人閱讀的摘要。
- **Obsidian Knowledge Workspace**：使用穩定 identity 與具語意的 WikiLink，不強制依賴 Dataview。
- **Zero-secret demo**：只使用 deterministic fixtures、SQLite 與 FastAPI，不需要任何外部服務。
- **Local-first review surfaces**：提供 Dashboard、API、Proposal Review 與可重建的 Obsidian Vault。

請參閱可重現的 [Proposal Trust Layer walkthrough](docs/proposal-trust-layer.md)。

## 五分鐘快速開始

支援版本：**Python 3.11**。

Windows PowerShell：

```powershell
git clone https://github.com/Ian2073/Intelligence-Hub.git
cd Intelligence-Hub
python -m venv hub_env
.\hub_env\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\hub_env\Scripts\intelligence-hub.exe seed-demo
.\hub_env\Scripts\intelligence-hub.exe serve --seed-demo
```

Linux／macOS：

```bash
git clone https://github.com/Ian2073/Intelligence-Hub.git
cd Intelligence-Hub
python3.11 -m venv hub_env
source hub_env/bin/activate
python -m pip install -e .
cp .env.example .env
intelligence-hub seed-demo
intelligence-hub serve --seed-demo
```

開啟：

- Dashboard：<http://127.0.0.1:8000/>
- OpenAPI：<http://127.0.0.1:8000/docs>
- Obsidian Vault：`data/demo/obsidian_vault/`

Demo 不需要 API key、外部 collector、Notion、Telegram、PostgreSQL 或 Hermes。

## 三十秒情境

1. Fixture collectors 載入互相關聯的 repository、paper、article、company 與 technology 訊號。
2. Deterministic normalization 將原始 evidence 保存到 SQLite。
3. 非確定性的 extraction 與 synthesis 結果先進入 Proposal Store。
4. Schema、evidence、confidence、provenance 與 conflict validators 將 proposal 分成 `accepted`、`rejected` 或 `needs_review`。
5. 只有 accepted proposal 能成為 canonical Entity、Event、Relationship 或 Insight。
6. Decision policy 產生明確行動，Daily Brief 再連回 evidence 與 accepted Insights。

## 正式 CLI

```bash
intelligence-hub --version
intelligence-hub demo
intelligence-hub seed-demo
intelligence-hub serve --seed-demo
intelligence-hub status
intelligence-hub proposals --status rejected
intelligence-hub export-obsidian
```

`scripts/intelligence_hub.py` 保留為相容 wrapper，與正式 CLI 共用同一份實作。

## Dashboard

本機 single-user Dashboard 包含：

- **Overview**：重要 Insights、Decisions、最新 Brief、Events、Proposal 指標與 runtime 狀態。
- **Insights**：Claim、evidence、confidence、相關 Entities／Events、可能行動與 provenance。
- **Knowledge**：Entities、Relationships、Observations、timeline、Sources、Insights 與 Decisions。
- **Proposal Review**：accepted、rejected、needs-review proposal、驗證原因與 review actions。
- **Briefs**：Daily、Weekly 與 Monthly intelligence records。
- **Operations**：runtime runs、collector／delivery 狀態、readiness warning 與 Obsidian export 健康度。

## Obsidian Knowledge Workspace

SQLite 是 system of record；Obsidian 是可由 canonical repository 重新產生的人類可讀 projection：

```text
Canonical Repository
  → ObsidianReadModelBuilder
  → ObsidianRenderer
  → ObsidianPublisher
```

Generated notes 使用 stable canonical ID、防碰撞檔名、semantic WikiLinks、atomic writes、User Notes 保留與 stale-note manifest。

## API

FastAPI 提供 typed、platform-neutral routes，包括：

- `/health`、`/ready`
- `/api/briefs`、`/api/insights`、`/api/entities`、`/api/events`、`/api/decisions`
- `/api/proposals` 與 proposal review actions
- `/api/runtime/runs`、`/api/runtime/status`

透過 API 人工接受 proposal 時，仍不得繞過 schema、evidence 與 provenance 驗證。

## Intelligence Hub 與 Hermes

Intelligence Hub 擁有 canonical persistence、proposal validation、insight generation、decision policy、API、Dashboard、model routing、delivery 與 Obsidian projection。

Hermes 是 optional research-agent integration 與 legacy compatibility layer。它可以透過 trust boundary 提交 proposal，但不擁有、也不能直接寫入 canonical knowledge。

既有 `python -m hermes` 指令仍保留相容性，但不是公開專案的主要入口。

## Configured Mode

Configured mode 可啟用 live GitHub／RSS／paper collectors、model providers、Notion、Telegram 與 optional Hermes integration。外部設定缺失時會清楚降級，不影響 demo mode。

新設定應優先使用 platform-neutral 的 `INTELLIGENCE_HUB_*`；文件中標示的 `HERMES_*` 僅作 legacy compatibility。

## Repository 結構

- `core/`：runtime、repository、proposal gate、insight engine、API、Dashboard services 與 Obsidian projection。
- `connectors/`：外部來源與 delivery adapters。
- `workflows/`：daily、weekly、monthly、dashboard、radar 與 decision-review workflows。
- `dashboard/`：不依賴外部 CDN 的本機 Dashboard assets。
- `data/fixtures/`：deterministic zero-secret demo inputs。
- `tests/`：regression、boundary、repository、trust-layer、projection、CLI 與 release tests。
- `scripts/`：operational 與 legacy compatibility entrypoints，詳見 `scripts/README.md`。
- `docs/`：architecture、configuration、operations、roadmap 與 design rationale。

## 開發驗證

```bash
python -m pip install -e ".[test]"
ruff check .
python -m pytest tests -q
python -m compileall contracts core connectors hermes workflows scripts main.py
python scripts/smoke_test.py
python scripts/acceptance_check.py
python scripts/first_run_check.py
python scripts/pre_publish_audit.py
```

請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Roadmap 邊界

已完成：local SQLite repository、Proposal Trust Layer、canonical Events／Insights、Dashboard／API、Obsidian projection、zero-secret demo、optional configured publishers 與 Hermes compatibility。

尚未完成：PostgreSQL、authentication、multi-user SaaS、Kubernetes、causal graph reasoning、完整 WorldState、多 Agent 辯論或公開可寫的 hosted demo。

詳見 [docs/ROADMAP.md](docs/ROADMAP.md) 與 [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)。

## 安全與隱私

- Demo data 是合成且 fixture-based。
- Secrets 只能放在已忽略的 `.env`，demo mode 完全不需要 secrets。
- SQLite demo paths 與 generated Vault 皆由 Git 忽略。
- Reset 僅能操作受管理的 `data/demo/`，且要求明確確認。
- UI 錯誤頁不會直接傾印完整 proposal payload 或 traceback。

安全問題請參閱 [.github/SECURITY.md](.github/SECURITY.md)。

## License

本專案使用 MIT License，詳見 [LICENSE](LICENSE)。

[English](README.md)
