# Hermes Intelligence OS PRD

## 1. Product Summary

Hermes Intelligence OS is a personal decision system that turns external technology signals into long-term judgment.

It is not a news reader, summary bot, Notion template, Telegram bot, or generic agent demo. Hermes collects signals, remembers what it has seen before, tracks how entities evolve, makes decisions, publishes a small daily intelligence surface to Markdown/Obsidian by default, and can optionally publish to Notion and notify through Telegram in production.

The product goal is:

> Spend 5 minutes per day to understand 95% of the highest-value changes in the technology world.

The initial domain is AI Intelligence. The long-term product can expand into Finance Intelligence, Cybersecurity Intelligence, Apple Intelligence, NVIDIA Intelligence, Startup Intelligence, and other domains, all flowing into one Executive Dashboard. The implementation should treat these domains as first-class signal streams that share the same memory and decision contract, even before each domain has a dedicated live connector.

## 2. Product Principles

### 2.1 Decision Over Summary

Hermes must not dump information. Every meaningful output must make a decision.

Allowed decision actions:

- Ignore
- Watch
- Read
- Prototype
- Implement
- Review later

Each decision must explain:

- why this matters now
- what changed compared with prior memory
- what it connects to
- what the user should do
- how confident the platform is

### 2.2 Memory Over Repetition

Hermes must remember yesterday.

If Hermes saw `OpenHands` yesterday and sees it again today, it should not treat it as a new item. It should update the existing entity with new observations such as:

- star delta
- release activity
- issue or PR movement
- contributor changes
- discussion spikes
- related papers or companies
- momentum over 1 day, 7 days, and 30 days

### 2.3 Evolution Over Snapshot

Hermes should prefer trajectory over daily novelty.

Daily outputs explain what changed today. Radar pages explain how technologies, companies, repositories, and papers evolve over time.

### 2.4 Radar Over Feed

Hermes should maintain durable Radar entities such as:

- technologies: MCP, AI agents, VLM, RAG, inference optimization
- companies: Anthropic, OpenAI, NVIDIA, Apple, Google, Meta
- repositories: OpenHands, vLLM, llama.cpp, LangGraph
- papers: important papers and their related follow-up work

A Radar entity should become more useful over months and years.

### 2.5 Five-Year Value

Core architecture should be useful for at least five years.

Temporary scripts are acceptable, but the core product must preserve:

- history
- entity identity
- observations
- decisions
- relationships
- trend evolution
- publishing records

### 2.6 Cloud-First Model Quality

Hermes should use cloud models for production intelligence quality. Local models may remain as fallback, smoke-test support, or offline experiments, but the main decision workflow should not depend on local model search or synthesis quality.

To control cost, Hermes should use tiered model routing:

- fast tier: classification, deduplication, short summaries, formatting, notification copy
- pro tier: decisions, research synthesis, weekly/monthly trend judgment, executive dashboard, decision review

Correctness and usefulness are valued over extreme token savings. The main goal is high-quality decision intelligence. While token savings are achieved by using the right model tier, the system must not compromise judgment to save tokens. Defenses against token waste must focus on avoiding structural bugs (e.g. infinite loops, repetitive crawling, redundant analysis of the same source) rather than limiting quality.

### 2.7 Progressive Information Contract

To maximize readability across different contexts, Hermes enforces a progressive information disclosure strategy:

- **Telegram Tier (Extreme Simplicity)**: Designed for a 30-second morning read. It contains only the executive brief of the day's core tech events and high-priority action recommendations (max 300 words).
- **Notion/Dashboard Tier (Moderated Simplicity)**: Designed for a 5-minute daily check. It presents structured summaries, clear action rationales, and momentum trends without noise or filler words.
- **Obsidian Tier (Detailed Context)**: Designed for deep local research and KB navigation. It preserves full details, historical observations, relation maps, and bi-directional linking (`[[Entity]]`) while utilizing formatting structures (like headers, properties, code blocks) to keep it clean.

### 2.8 Intelligent Noise Filtering Pipeline

**Status: Deferred — config keys exist, pipeline not wired.**

The following describes the product target. Phase 3 does not implement semantic interest filtering.

For unstructured and high-noise signal sources (e.g., domain RSS feeds, blogs, arXiv papers), Hermes uses a multi-stage noise filtering pipeline:

1. **Static Deduplication & Rule Filters**: Instantly ignore identical titles, URLs, or non-technical domains to prevent API waste.
2. **Entity & Keyword Triggering**: Prioritize or screen content based on known watchlist entities.
3. **AI Semantic Value Evaluation & Relevance Rating**:
   - 系統允許使用者在配置中以自然語言詳細描述其「目前的研究興趣與關注範疇」（如：`Multimodal pretraining, but no specific language applications`）。
   - Fast-tier AI 會閱讀摘要（Abstract）或內文，並為該訊號與興趣的關聯性給予 **1 至 10 分的語意相關性評分**。
   - 僅有評分高於預設閾值（Threshold，例如 >= 7 分）且代表「95% 高價值變化」的訊號，才會通過篩選並記錄至 SQLite 中，其餘無涉內容則自動過濾，以防止資訊雜訊與資料庫膨脹。

## 3. User Experience

### 3.0 Public Demo vs Production Deployment

The public demo path is Dashboard plus Obsidian and requires no secrets. It uses fixtures, local SQLite memory, generated proposal/insight data, and generated Obsidian output.

The production deployment can add Notion, Telegram, cloud LLM synthesis, live connectors, and scheduling. Both paths share the same `IntelligenceBrief` contract and SQLite memory model.

### 3.1 Daily Experience

Every morning, Hermes runs automatically.

It collects source updates, analyzes them, writes a daily brief to the Notion Executive Dashboard and the local Obsidian Vault, and sends a Telegram notification.

The Telegram message acts as the primary morning reading interface (designed for a quick 30-second browse). It contains:

- A brief title & YYYY-MM-DD timestamp
- An **Executive Brief (核心情報精華)**: A highly condensed summary of the day's critical tech changes (max 300 words).
- **Top decisions and actions**: Action recommendations (e.g., [Prototype]... / [Read]...)
- Links to the Notion Dashboard page and the local Obsidian file.

When the user has time, they open Notion (for the database view dashboard on mobile/web) or Obsidian (for local research, relations mapping, and note-taking) to see the detailed evidence.

### 3.2 Weekly Experience

Hermes produces a weekly report that is published to Notion and Obsidian. It answers:

- which domains accelerated
- which technologies gained or lost momentum
- which companies made meaningful moves
- which repositories had real engineering movement
- which prior decisions should be updated (due decision reviews)

Example trend labels:

- Agent: Up
- MCP: Up
- Reasoning: Stable
- VLM: Down

In Obsidian, the weekly report features an interactive markdown checklist `- [ ]` of "Due Decisions" (revisit dates reached). The user can simply check `[x]` to mark them reviewed, which Hermes reads back during the next synchronization.

### 3.3 Monthly / Quarterly Experience

Hermes produces higher-level trend reports that connect daily signals into durable judgment.

The long-term goal is that by year-end Hermes can produce an annual technology development report grounded in its own memory rather than a one-off LLM summary.

## 4. v1 Scope

v1 must establish the skeleton of Hermes Intelligence OS, not full coverage.

### 4.1 Must Have

- Product identity: Hermes Intelligence OS
- One domain: AI Intelligence (plus multi-domain RSS experiments)
- Local-first runtime (with potential to be wrapped inside standard automation containers or GitHub Actions for serverless runs)
- Durable memory store (SQLite)
- Entity model
- Observation model
- Signal model (AI Relevance Rating 1-10 scores are deferred until semantic filtering is wired)
- Decision model
- Daily brief model
- Technology Radar model
- Company Radar model
- Repository Radar model
- Paper Radar model
- Notion publishing target (Dashboard & Radar Database)
- Obsidian publishing target (Markdown files, Frontmatter properties, Bi-directional links)
- Bi-directional sync engine (Obsidian to SQLite: sync checklist ticks, user notes, trend edits, new entities)
- Telegram notification hook (morning brief format with Executive Brief)
- Natural Language Interest Profiling & Relevance Scorer (1-10 rating pipeline) deferred until post-release semantic filtering work
- **Quality Eval Harness**: A suite for testing agent regression (`eval-regression`) and prompt drift (`eval-drift`) to ensure scoring quality
- Manual run command & Unified CLI wrapper
- Scheduler-ready command boundary
- Honest reporting of which connectors actually ran

### 4.2 First Real Connector

The first real connector should be GitHub because it best validates memory and momentum:

- stars
- releases
- issues
- pull requests
- contributors
- topics
- repo description
- last pushed date

GitHub also validates the rule that release and contributor movement may matter more than stars.

### 4.3 Second Connector

The second connector should be arXiv or Papers with Code.

The paper workflow must not only summarize papers. It must connect papers to:

- related papers
- related GitHub repositories
- related companies
- related technologies
- related trends

### 4.4 Third Connector: RSS Feed

The third connector is RSS to fetch unstructured news across domains (Finance, Cybersecurity, NVIDIA, Apple, Startup). RSS items are evaluated via the Intelligent Noise Filtering Pipeline (Fast-tier AI) to filter out noise, ensuring only high-value changes enter the database.

### 4.5 Not v1

Do not require these before v1 is useful:

- native dashboard
- vector database
- multi-agent planner
- finance automation
- browser automation
- large-scale crawling
- investment advice
- full Notion workspace auto-provisioning

## 5. Core Concepts

### 5.1 Entity

An Entity is anything Hermes can remember over time.

Entity types:

- Technology
- Company
- Repository
- Paper
- Product
- Person
- Topic
- Source

Required fields:

- id
- type
- canonical name
- aliases
- first seen date
- last seen date
- status
- tags
- summary

### 5.2 Observation

An Observation is a dated fact about an entity.

Examples:

- repo stars changed from 24,000 to 25,500
- repository published a release
- paper appeared on arXiv
- company announced a new agent product
- issue count increased
- contributor count changed

Required fields:

- id
- entity id
- observed date
- source type
- source URL
- metric name
- previous value
- current value
- raw evidence
- confidence

### 5.3 Signal

A Signal is an interpreted observation or group of observations that may deserve user attention.

Required fields:

- id
- title
- source observations
- related entities
- importance
- impact
- momentum
- engineering value
- adoption
- longevity
- novelty
- intelligence score
- confidence
- reasoning

### 5.4 Decision

A Decision is Hermes' recommended action for a signal.

Required fields:

- id
- signal id
- action
- rationale
- expected payoff
- risk
- revisit date
- confidence

Decision review is the mechanism that prevents old recommendations from becoming permanent assumptions. When a decision reaches its revisit date, Hermes must surface it in the weekly report or a standalone decision review and ask whether the action should remain, escalate, or be ignored.

### 5.5 Brief

A Brief is a compressed user-facing output.

Brief types:

- Daily Brief
- Weekly Report
- Monthly Report
- Quarterly Trend Report
- Annual Review

Required fields:

- id
- domain
- period start
- period end
- executive summary
- top signals
- recommended actions
- radar changes
- confidence notes
- Notion page id
- Telegram notification status

### 5.6 Obsidian Document Structure & Boundaries

An Obsidian document is a local Markdown representation of an Entity, Decision, or Brief. It enforces a strict boundary between automated updates and user-owned content to enable bi-directional synchronization without data loss:

1. **YAML Frontmatter (Properties Area)**:
   - Synchronized double-way.
   - Includes canonical fields: `id`, `type`, `aliases`, `tags`, `trend` (e.g. Up/Down/Stable), and `status` (e.g. Watch/Prototype/Reviewed).
   - If the user modifies these properties in Obsidian, Hermes imports them back to SQLite.
2. **Hermes Output Area (Write-Only by System)**:
   - Contains automatically collected data, metrics graphs, release histories, and backlinks.
   - Overwritten/refreshed by Hermes on runs. User edits here are not preserved.
3. **User Notes Area (Read-Only by System)**:
   - Denoted by a specific header: `## 📝 User Notes` (or `## 📝 我的筆記與思維`).
   - The user can write anything under this header.
   - **Hermes only reads from this area (to extract insights for AI context alignment) and NEVER writes to or overwrites it.**


## 6. System Architecture

```text
Sources
  GitHub
  arXiv
  Papers with Code
  RSS
  Company blogs
  Hacker News
  Reddit

    |
    v

Connectors
  fetch raw data
  normalize source records
  preserve evidence

    |
    v

Memory Store
  entities
  observations
  relationships
  prior decisions
  prior briefs

    |
    v

Intelligence Engines
  signal scoring
  relationship mapping
  momentum calculation
  radar updates
  decision generation

    |
    v

Workflows
  AI Daily
  AI Weekly
  GitHub Radar
  Paper Radar
  Company Radar

    |
    v

Publishers
  Notion workspace
  Telegram notification

    |
    v

Executive Dashboard
```

## 7. Deep Module Interfaces

Hermes should use a small number of deep module interfaces.

### 7.1 Connector Interface

The connector interface should hide source-specific details.

```text
fetch(window) -> list[SourceRecord]
```

Each adapter handles authentication, pagination, rate limits, and source-specific fields internally.

### 7.2 Memory Interface

The memory interface should hide storage details and handle bi-directional synchronization.

```text
upsert_entity(entity)
record_observation(observation)
find_entity(type, canonical_name, aliases)
get_entity_history(entity_id, window)
link_entities(source_entity_id, target_entity_id, relation_type)
sync_from_obsidian(vault_path) -> SyncReport
```

v1 can use SQLite. JSONL is acceptable only for temporary experiments. The `sync_from_obsidian` method parses frontmatter properties, checked lists, and custom note sections, and safely writes them back into the memory database.

### 7.3 Intelligence Interface

The intelligence interface should turn observations into signals and decisions.

```text
analyze(observations, memory_context) -> IntelligenceRun
```

The caller should not need to know scoring internals, prompt structure, or relationship heuristics.

### 7.5 Model Router Interface

The model router should hide provider details and expose task or tier selection.

```text
generate(prompt, tier=fast|pro) -> text
```

The default production provider should be cloud / OpenAI-compatible. Ollama remains a fallback provider, not the primary quality path.

### 7.4 Publisher Interface

The publisher interface should hide Notion, Obsidian, and Telegram details.

```text
publish_brief(brief) -> PublishedBrief
publish_obsidian(brief_or_entity) -> ObsidianPublishResult
notify(notification) -> NotificationResult
```

## 8. Notion Workspace

Notion is the v1 presentation and archive layer. It is not the runtime control plane.

Required Notion surfaces:

- Executive Dashboard
- AI Intelligence Daily Briefs
- Technology Radar
- Company Radar
- Repository Radar
- Paper Radar
- Decisions

Each daily brief should link to relevant Radar records.

Notion should store:

- final briefs
- entities
- decisions
- scores
- confidence
- user annotations

Notion should not store:

- API keys
- scheduler configuration
- raw logs
- prompt control
- model routing config

## 9. Telegram Notification

Telegram is the primary quick morning reading interface, delivering key intelligence summaries directly to the user's phone.

Daily notification format:

```text
🤖 Hermes Daily Intelligence (YYYY-MM-DD)

💡 【核心情報精華】
• [Bullet summarizing core technology/ecosystem movement]
• [Bullet summarizing core paper/repository breakthrough]

🎯 【最優決策與行動】
1. [Decision/Action] Signal Title & Link
2. [Decision/Action] Signal Title & Link

🔗 Notion: <dashboard link>
📂 Obsidian: <local folder path/link>
```

Telegram should only send after Notion and Obsidian publishing stages finish, unless the publishing failure itself is what needs notification.

## 10. Success Metrics

### 10.1 Product Metrics

- User can understand the day's important AI changes in 5 minutes.
- Daily brief contains fewer than 7 top-level signals.
- Every signal has a decision.
- Every repeated entity links to prior memory.
- Weekly report uses daily memory, not a fresh summary.
- Notion page links are created reliably.
- Telegram notification includes the correct Notion/Obsidian links.
- Telegram morning brief text length remains strictly under **300 words** to avoid scrolling fatigue.
- Notion dashboard uses structured toggle blocks or brief columns to keep layouts visually clean and compact.

### 10.2 Engineering Metrics

- A manual run can complete without hidden manual source collection.
- The same repository seen twice updates the same entity.
- Star delta and release activity can be computed from stored observations.
- Tests cover entity upsert, observation recording, momentum calculation, and brief publishing payloads.
- Runtime clearly reports which connectors ran and which did not.
- **Obsidian Linking Rate**: Over **90%** of known entities referenced in daily/weekly briefs automatically receive correct double-brackets `[[Entity]]` links.
- **Bi-directional Sync Accuracy & Safety**: Checked todo items, manual entities, and trend ratings changed in Obsidian must be 100% synchronized back to SQLite, with **zero risk** of overwriting or deleting anything in user notes area.

## 11. Milestones

### Milestone 1: Product Skeleton

Deliverables:

- this PRD
- updated architecture docs
- data model spec
- module interface spec
- local command plan

Outcome:

Hermes has a stable product target and implementation skeleton.

### Milestone 2: Memory Store

Deliverables:

- SQLite-backed memory store
- Entity table
- Observation table
- Relationship table
- Decision table
- tests for repeated entity updates

Outcome:

Hermes can remember yesterday.

### Milestone 3: GitHub Radar

Deliverables:

- GitHub connector
- Repository entity upsert
- star delta observations
- release observations
- issue and PR observations
- contributor activity observations
- repository momentum scoring

Outcome:

Hermes can track repository evolution instead of re-summarizing repositories.

### Milestone 4: Daily AI Brief

Deliverables:

- signal scoring
- decision generation
- Notion daily brief publishing
- Telegram link notification

Outcome:

Hermes can produce a useful daily intelligence loop.

### Milestone 5: Paper Radar

Deliverables:

- paper connector
- paper entity memory
- related repository/company/technology links
- paper-to-trend mapping

Outcome:

Hermes can connect research to engineering and ecosystem movement.

### Milestone 6: Weekly Report

Deliverables:

- weekly aggregation workflow
- technology momentum report
- company momentum report
- decision review

Outcome:

Hermes starts producing trend judgment rather than daily-only briefs.

### Milestone 7: Decision Review Loop

Deliverables:

- standalone due-decision review workflow
- weekly integration for decisions reaching revisit date
- decision review publishing to Notion
- decision review Telegram notification

Outcome:

Hermes remembers its own prior calls and forces old judgments back into the decision loop.

### Milestone 8: Obsidian & Bi-directional Sync

Deliverables:

- Obsidian Markdown publisher for daily/weekly briefs, radars, and decisions
- Bi-directional sync parser to read back checklist ticks, trend rating changes, and manual entities
- Tests validating the read/write boundaries (ensuring user custom notes are never overwritten)
- PowerShell runner and CLI wrapper for manual/automated double-way synchronization

Outcome:

User can read, update, and co-evolve technology trends and decisions directly within their local Obsidian Vault.

### Milestone 9: Quality Eval & Relevance Scoring

Deliverables:

- Natural Language profile interface matching observations against user interests (1-10 scoring module)
- Regression test runner (`eval-regression`) and drift detector (`eval-drift`) using historical signal samples
- SQLite schema updates for storing raw LLM scores and grading histories

Outcome:

Hermes achieves consistent judgment quality and relevance filtering, and developers can programmatically evaluate the impact of prompt modifications on daily decisions.

## 12. Open Product Decisions

### 12.1 Resolved Decisions in v1

The following decisions have been resolved and implemented in v1:

- **Memory Source of Truth**: SQLite database serves as the active memory store, with JSONL and Markdown exports acting as backups.
- **Notion Database Provisioning**: Automated by Hermes via setup CLI rather than manual creation.
- **Telegram Bot Scope**: A single unified Hermes Telegram bot is used for all domains and alerts.
- **AI Scoring Strategy**: Model-first (Pro tier) analysis with prompt-based and deterministic rule heuristics validation.
- **Orchestration Execution**: Unified, ordered process running all connectors and domains in sequence with parallel fetchers.
- **Notion & Obsidian Coexistence**: Dual-publishing model. Notion serves as the mobile/cloud executive dashboard, while Obsidian serves as the local-first detailed knowledge vault and bi-directional control plane.
- **Synchronization Timing**: Hybrid synchronization (automatic scan before daily run, manual CLI runner for on-demand sync).
- **Obsidian Read/Write Boundary**: Enforced partition (YAML properties double-sync, Hermes output area write-only, User Notes section read-only by system).

### 12.2 Current Open Decisions

- Whether to integrate automatic Git commit and push routines within the Obsidian Sync workflow to back up the local vault automatically.
- How to store and link binary assets (e.g., project logos, paper figures, PDF attachments) inside the Obsidian `/assets` folder when ingested from arXiv or GitHub.

## 13. Non-Negotiable Product Rule

Hermes must never optimize for complete information.

Hermes optimizes for judgment:

- fewer signals
- better decisions
- durable memory
- clear uncertainty
- actionability
- long-term evolution

If an output makes the user read more without helping them decide better, it has failed.
