# Product Definition

Intelligence Hub is a local-first decision intelligence platform for converting fragmented information into validated knowledge, evidence-backed insights, and explicit actions.

## Product Boundary

Intelligence Hub owns:

- source normalization and evidence retention
- canonical SQLite persistence
- Proposal Store and Proposal Gate
- Event and Insight generation
- rule-owned decision policy
- API and local Dashboard
- delivery adapters and Obsidian projection

Hermes is an optional research-agent integration and legacy compatibility layer. It may investigate and submit proposals, but it does not own platform runtime or canonical knowledge.

## What Intelligence Hub Is

- a traceable evidence-to-decision pipeline
- a canonical repository for durable intelligence records
- a trust boundary for model and agent output
- a decision-support system
- a rebuildable human-readable knowledge workspace

## What It Is Not

- a generic chatbot or RAG demo
- a news feed or link dump
- an autonomous agent allowed to write facts without validation
- a hosted multi-user SaaS
- a complete fact-checking or causal-reasoning system

## Primary Experience

The user starts the zero-secret demo, opens the Dashboard, and can trace:

```text
Source evidence → Proposal → Validation → Canonical Insight → Decision → Brief
```

The same canonical repository can regenerate the Obsidian Knowledge Workspace. Notion and Telegram remain optional configured-mode publishers.

## Core Output

An actionable brief explains:

- what changed
- why it matters
- what evidence supports it
- what it connects to
- what action may follow
- confidence and provenance

## Local-First Release Candidate

The release candidate is designed for one local user:

- Python 3.11
- SQLite
- deterministic fixtures
- FastAPI and a dependency-free Dashboard
- generated Obsidian Vault
- no required secrets or external services

PostgreSQL, authentication, multi-user hosting, Kubernetes, causal graphs, and public writable hosting remain outside the current product boundary.
