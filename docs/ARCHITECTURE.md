# Architecture

## Release Candidate Surface

Intelligence Hub now exposes a local-first release-candidate surface:

- `core.platform_runtime.PlatformRuntime` is the platform-neutral composition root.
- `core.repository.Repository` / `SQLiteRepository` provide canonical read access over SQLite.
- `core.proposal_store`, `core.proposal_gate`, and `core.proposal_service` implement the proposal trust layer.
- `core.canonical_knowledge` and `core.insight_engine` provide canonical Event/Insight persistence and deterministic insight generation.
- `core.api.create_app()` exposes the FastAPI API and serves the static dashboard in `dashboard/`.
- `scripts/intelligence_hub.py` is the platform-neutral local CLI for demo seed, daily fixture runs, API/dashboard serving, status, proposal review, Obsidian export, and safe demo reset.

Hermes remains an optional research-agent integration and compatibility layer. Platform modules must not import `hermes`.

## Public Data Flow

```text
fixtures/live sources
→ deterministic normalization
→ proposal store
→ proposal gate
→ canonical SQLite repository
→ insight engine / decision policy
→ FastAPI dashboard + Obsidian workspace + compatibility publishers
```

Intelligence Hub is the product and platform.

The Platform Runtime is the core execution layer. It owns collection, processing, orchestration, canonical persistence, intelligence generation, decision support, delivery, scheduling, and observability.

Hermes is an optional agent integration. It may provide autonomous research, reflection, personalized memory, skill accumulation, and tool-driven investigation, but it does not own platform execution or canonical state.

Markdown/Obsidian remains the primary zero-secret demo surface. Notion is an optional production review workspace when credentials are configured. Telegram is an optional notification channel. These delivery paths are owned by the Platform Runtime and must work without Hermes installed or configured.

## Runtime Architecture

```text
Sources
  GitHub repositories
  arXiv / Papers with Code / Hugging Face Papers
  Domain RSS watchlists
  Local fixtures for tests and dry-runs

    |
    v

Collection
  fetch, parse, retry, and validate source-specific payloads

    |
    v

Processing
  normalize, dedupe, classify, summarize, extract entities,
  extract relationships, extract events, and prepare intelligence inputs

    |
    +-----------------------------+
    |                             |
    v                             v

Raw Document / Source Snapshot    Proposal Store
Repository                        model-generated or agent-generated
deterministic collector output    entity, relationship, event, insight,
                                  synthesis, or research proposals

    |                             |
    |                             v
    |                           Proposal Gate
    |                           schema validation
    |                           evidence validation
    |                           confidence check
    |                           conflict detection
    |                             |
    |                  +----------+----------+
    |                  |                     |
    v                  v                     v

Canonical Repository     Accepted Proposal     Rejected Proposal
SQLiteRepository by      canonical persistence rejection reason retained;
default local mode       through repository     no canonical write

    |
    v

World Model
  Entity, Observation, Relationship, Decision,
  BriefRecord, RunRecord, Event, Insight

    |
    v

Intelligence and Decision Support
  daily, weekly, monthly, dashboard, Radar, decision review
  DecisionPolicy: RuleBased, ModelAssisted, or Hybrid

    |
    v

Delivery and Observability
  Obsidian, Notion, Telegram, dashboard read models,
  scheduler, readiness checks, run ledger, outbox, health
```

The deterministic source path and the proposal path are deliberately separate. Raw source snapshots and normalized documents can be persisted directly. Model-generated or agent-generated entities, relationships, events, insights, and synthesis outputs must pass through the Proposal Gate before they can affect the canonical world model.

Milestone 3 implements the first trust layer: typed `Proposal` payloads, `SQLiteProposalStore`, composable `ProposalGate` validators, and `ProposalTrustService` for accepted canonical persistence. Rejected proposals retain rejection reasons and needs-review proposals remain auditable.

Hermes remains an optional proposal producer. A Hermes research agent may submit proposals through this seam, but it must not write canonical records directly.

## Platform Boundary

`PlatformRuntime` is the platform-neutral facade and composition root for settings, SQLite memory, synthesis policy, agent registry, optional publishers, model routing, memory status, and fixture daily dispatch. The current code still has compatibility names such as `HermesRuntime` and `python -m hermes`. Those are public entrypoints and remain supported during migration.

`HermesRuntime` is now a legacy compatibility name over `PlatformRuntime`. It remains available for existing callers and tests, but platform-neutral code should import `core.platform_runtime.PlatformRuntime`. The compatibility layer is intentionally temporary while public entrypoints and downstream automation continue to use the older name.

The target runtime boundary is Platform Runtime:

```text
Platform Runtime
  AgentRegistry
    ai_intelligence compatibility agent
  IntelligenceEngine
  DecisionPolicy
  SynthesisPolicy
  Repository
  BriefRenderer / BriefPublisher / BriefDeliveryCoordinator
```

`IntelligenceBrief` is the canonical output contract for intelligence surfaces. Signals inside a brief carry action, confidence, rationale, and the PRD decision fields: why now, what changed, connects to, and what to do.

Decision support is exposed through a `DecisionPolicy` abstraction. v1 keeps rule-based action selection as the default implementation, but the architecture allows `RuleBasedDecisionPolicy`, `ModelAssistedDecisionPolicy`, and `HybridDecisionPolicy` without changing pipeline callers.

`SynthesisPolicy` provides `off`, `hybrid`, and `full` modes with a per-run pro-tier call limit. When the limit is exceeded or generation fails, the Platform Runtime falls back to deterministic output and records metadata.

`MemoryEngine` currently wraps the SQLite `MemoryStore` with schema versioning, synthesis metadata persistence, indexes for high-frequency queries, DB size, and table row stats. `Repository` and `SQLiteRepository` now provide the platform-neutral canonical read seam over the existing store.

`AgentRegistry` currently registers `ai_intelligence`; orchestrator code can dispatch through the registry while existing script entrypoints remain compatible. Research agents are separate from model providers and decision policies.

## Integration Types

Agent integrations:

- `HermesResearchAgent`
- future custom research agents

Model providers:

- OpenAI-compatible providers
- Claude
- Ollama

Decision policies:

- `RuleBasedDecisionPolicy`
- `ModelAssistedDecisionPolicy`
- `HybridDecisionPolicy`

These three extension categories must not be collapsed into a single optional integration layer. Agents can investigate and propose. Model providers generate text or structured outputs. Decision policies choose or rank actions under a defined policy.

## Source and Connector Responsibilities

Connectors own external IO and source-specific parsing:

- GitHub repository snapshots, authenticated checks, and repository metadata.
- Paper feeds from arXiv and Papers with Code, including the Hugging Face Papers redirect fallback.
- Domain RSS watchlists for Finance, Cybersecurity, Apple, NVIDIA, and Startup intelligence.
- Notion, Obsidian, Telegram, cloud model, Ollama, and retry adapters.

Pipelines should consume normalized connector output rather than embedding source-specific parsing logic.

## Pipeline Responsibilities

Daily Intelligence collects source signals, writes deterministic source observations, evaluates proposals where needed, ranks decisions, publishes structured Notion records, and produces notification payloads.

Weekly and Monthly Intelligence aggregate canonical repository state over time, summarize changes, and surface stale or due decisions.

Executive Dashboard reads accumulated repository state to provide a compact operating view: top actions, deduplicated priorities, and operational health.

Radar Snapshot turns accumulated entities, observations, relationships, and decisions into a durable long-term radar surface.

Decision Review revisits persisted decisions so earlier Watch, Read, Prototype, Ignore, or Implement calls do not become permanent assumptions.

All of these paths must run without Hermes installed or configured.

## Repository and World Model

SQLite is the default local repository mode. It is not legacy-only. It supports the zero-secret demo, local development, and environments where no external service should be required.

The repository abstraction is incremental:

- `Repository` protocol for the canonical reads currently needed by projection and reporting.
- `SQLiteRepository` as the default local implementation, wrapping or evolving the current `MemoryStore`.
- `PostgreSQLRepository` as a later production or Docker profile implementation.

Both implementations should eventually pass the same repository contract tests. Milestone 2 introduces the protocol and SQLite implementation without moving all writes away from `MemoryStore`; PostgreSQL is deferred to a later API/Docker phase or a dedicated Phase 2B.

The world model should evolve from the current schema rather than duplicate it:

- Existing: `Entity`, `Observation`, `Relationship`, `Decision`, `BriefRecord`, `RunRecord`.
- Additive: `Event`, `Insight`.
- Deferred: `Document`.
- Evaluated later: `WorldState`, preferably as a temporal projection over observations unless a separate model proves necessary.

Each canonical record should preserve source, evidence, confidence, validity window where applicable, generator identity, and model version where applicable.

## Synthesis and Decision Layer

Deterministic summaries remain the default for fixture runs, CI, and dry-runs so local execution does not spend tokens unexpectedly.

When `-ModelSynthesis` / `--model-synthesis` is enabled, daily, weekly, monthly, and dashboard pipelines can use the configured pro model tier for final executive synthesis. The model path must keep deterministic fallback behavior so scheduled runs continue if the model call fails.

Model-generated synthesis is a proposal source. Accepted synthesis can be persisted canonically only after validation. Rejected synthesis should retain a rejection reason outside the canonical world model.

Decision rationales expose the PRD-facing contract: why now, what changed, what it connects to, what to do, and confidence. This area remains a high-value improvement target because the product promise is decision intelligence, not collection volume.

## Model Routing

Model routing belongs to Intelligence Hub. It is available to the Platform Runtime regardless of whether Hermes is installed.

The current model router supports:

- `fast`: cheaper model tier for classification, cleanup, extraction, and short copy.
- `pro`: stronger model tier for research briefs, synthesis, dashboards, and decision-heavy work.
- `ollama`: local fallback for offline experiments and development.

The cloud adapter is OpenAI-compatible and uses `/v1/chat/completions`. Current compatibility configuration uses `HERMES_CLOUD_BASE_URL`, `HERMES_CLOUD_API_KEY`, `HERMES_FAST_MODEL`, and `HERMES_PRO_MODEL`. Future platform-neutral aliases can be added without removing the existing public environment variables.

Production go-live requires fast and pro model values to be distinct so the Platform Runtime can control cost and quality deliberately.

## Publishers and Delivery Boundaries

Publishers present and persist outputs. They should not hide failed delivery.

Notion supports plain page publishing and structured databases for briefs, papers, GitHub repositories, ecosystem records, decisions, Radar snapshots, and durable Radar entities.

Markdown/Obsidian is the primary zero-secret demo and local review surface.

Telegram sends only when requested and when the primary Notion publish status is `published`. If Telegram cannot send after a successful Notion publish, the Platform Runtime records the notification in the outbox for later flush.

The delivery contract separates `BriefRenderer`, `BriefPublisher`, and `BriefDeliveryCoordinator`. Markdown/Obsidian is the zero-secret default demo surface; Notion and Telegram remain optional adapters.

Obsidian Knowledge Workspace v1 uses a repository-driven projection:

```text
Canonical Repository
  -> ObsidianReadModelBuilder
  -> ObsidianRenderer
  -> ObsidianPublisher
  -> Obsidian Vault
```

The read model builds immutable note graph records from canonical entities, observations, relationships, decisions, and briefs. The renderer owns frontmatter, generated sections, and semantic WikiLinks. The publisher owns vault paths, atomic writes, stale-note manifest generation, and preservation of user-owned note sections.

Daily Obsidian publishing now uses this projection and includes accepted canonical Insight notes under `02 Insights/`, plus proposal review surfaces under `90 System/Rejected Proposals.md` and `90 System/Needs Review.md`. Existing `connectors.obsidian.ObsidianClient` remains as a compatibility facade for callers and characterization tests, but it is no longer the primary daily knowledge-workspace implementation. Weekly, monthly, dashboard, Radar, and decision-review publishers still keep their existing behavior until they are migrated through the same reusable seam.

## Automation Layer

The production operating shape is Windows Task Scheduler plus repository scripts:

- daily ordered orchestration
- optional weekly report
- optional monthly report
- optional Executive Dashboard
- optional Radar Snapshot
- optional weekly Decision Review
- schedule plan validation before touching Task Scheduler
- installed task audit after installation
- go-live and readiness checks for credentials, model routing, Notion, Telegram, and live source access

Automation must be observable through the Platform Runtime run ledger and readiness reports. A documented command is not enough.

## Docs and Knowledge Boundary

`docs/` is maintained by humans and Codex. It defines product intent, architecture, roadmap, agent specs, Notion workspace design, and operations.

`hermes/soul/` is optional agent context. It is not a canonical world model and should not be treated as platform state.

`prompts/` contains workflow prompt contracts.

`knowledge/` contains durable thinking framework and product knowledge intended for agent-readable context. Runtime uses a scoped knowledge loader that only accepts declared keys such as `identity`, `decision_framework`, and `signal_compression`, with a character limit. `docs/` is not loaded as runtime prompt context by default.

## Phase 0 Boundary Rules

Forbidden dependencies:

- `core` imports `hermes`
- `connectors` imports `hermes`
- `workflows` imports `hermes`
- platform-neutral modules import `hermes`

Allowed dependencies:

- `hermes` imports platform modules for compatibility entrypoints
- optional integrations import platform interfaces

## Remaining Architecture Gaps

- The local Dashboard is implemented for the release candidate; a hosted multi-user web product is not implemented.
- PostgreSQL repository implementation is not implemented yet.
- `DecisionPolicy` is not extracted yet; current decision behavior remains rule-based through `DecisionEngine`.
- Obsidian Knowledge Workspace v1 is repository-driven for daily output, but weekly, monthly, dashboard, Radar, and decision-review Obsidian surfaces have not all been migrated yet.
- Proposal Store and Proposal Gate v1 are implemented, but full Hermes proposal producer migration is deferred.
- Finance, Cybersecurity, Apple, NVIDIA, and Startup domains still use RSS/fixtures rather than specialized live APIs.
- Research agents beyond the existing `ai_intelligence` compatibility registration are future work.
- Cross-signal analysis is useful but still shallow compared with semantic entity linking over repository state.
- Telegram-linked Notion delivery in a full scheduled live run still needs end-to-end verification.
