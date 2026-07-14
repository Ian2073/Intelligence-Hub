# ADR 0002: No Vector Database In Phase 2

## Status

Accepted

## Context

The Phase 2 goal is to establish a clearer platform boundary: canonical briefs, decision rules, synthesis policy, memory metadata, agents, and pluggable delivery. Adding embeddings or a vector database would expand runtime dependencies and migration risk before the core contracts are proven.

## Decision

Phase 2 keeps SQLite as the only required memory store. Semantic entity linking remains an extension point in `IntelligenceEngine`, but vector search is out of scope.

## Consequences

- Zero-secret fixture demo and CI stay lightweight.
- Existing production memory remains compatible.
- Future semantic search can be added behind the Memory/Intelligence Engine boundary.
