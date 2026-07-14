# ADR 0001: Decision Actions Are Rule-Owned

## Status

Accepted

## Context

Phase 2 improves rationale quality with AI synthesis, but the decision action itself controls ranking, notifications, and follow-up behavior. If the LLM can choose actions directly, identical evidence may drift between `Watch`, `Read`, and `Prototype` across runs.

## Decision

Hermes keeps action selection and action ranking in `DecisionEngine`. AI may generate structured rationale for selected top decisions, but that rationale must pass validation and does not override the action.

## Consequences

- Fixture and scheduled runs remain stable.
- Golden baseline tests can detect unintended action drift.
- AI failures degrade to deterministic rationale without changing the decision posture.
