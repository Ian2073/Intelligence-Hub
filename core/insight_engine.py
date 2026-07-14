from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.proposal_service import ProposalProcessResult, ProposalTrustService
from core.proposals import EventProposalPayload, InsightProposalPayload, Proposal, SynthesisProposalPayload


@dataclass(frozen=True)
class InsightEngineResult:
    proposal_results: tuple[ProposalProcessResult, ...]

    @property
    def accepted_insight_ids(self) -> tuple[str, ...]:
        return tuple(
            item.canonical_id
            for item in self.proposal_results
            if item.canonical_id.startswith("insight:")
        )


class CanonicalInsightEngine:
    def __init__(self, trust_service: ProposalTrustService) -> None:
        self.trust_service = trust_service

    def process_daily_run(self, run, *, run_date: str, executive_summary: str = "") -> InsightEngineResult:
        proposals = [
            *self._event_proposals(run, run_date=run_date),
            *self._insight_proposals(run, run_date=run_date),
        ]
        if executive_summary:
            proposals.append(self._synthesis_proposal(run, run_date=run_date, executive_summary=executive_summary))
        results = tuple(self.trust_service.submit(proposal) for proposal in proposals)
        return InsightEngineResult(results)

    def _event_proposals(self, run, *, run_date: str) -> list[Proposal]:
        proposals: list[Proposal] = []
        for result in _all_signal_results(run):
            for observation in getattr(result, "observations", ()):
                if not _has_event_semantics(observation):
                    continue
                entity = result.entity
                evidence_refs = (f"observation:{observation.id}",)
                proposals.append(
                    Proposal.create(
                        proposal_type="event",
                        payload=EventProposalPayload(
                            event_type=observation.metric_name,
                            title=f"{_event_title(observation.metric_name)}: {entity.canonical_name}",
                            summary=f"{entity.canonical_name}: {observation.previous_value} -> {observation.current_value}",
                            entity_refs=(f"entity:{entity.id}",),
                            evidence_refs=evidence_refs,
                            occurred_at=observation.observed_at,
                        ),
                        evidence_refs=evidence_refs,
                        confidence=observation.confidence,
                        proposed_by="intelligence_hub.event_extractor",
                        model_provider="deterministic",
                        model_name="canonical_event_extractor",
                        model_version="v1",
                        created_at=f"{run_date}T00:00:00+00:00",
                    )
                )
        return proposals

    def _insight_proposals(self, run, *, run_date: str) -> list[Proposal]:
        proposals: list[Proposal] = []
        for insight in getattr(run, "cross_signal_insights", ()):
            matching_results = _matching_results(run, insight.subject)
            evidence_refs = _evidence_refs(matching_results)
            related_entity_refs = tuple(
                dict.fromkeys(f"entity:{result.entity.id}" for result in matching_results)
            )
            if not evidence_refs:
                continue
            proposals.append(
                Proposal.create(
                    proposal_type="insight",
                    payload=InsightProposalPayload(
                        claim=insight.title,
                        summary=_what_changed(insight, matching_results),
                        why_it_matters=insight.rationale,
                        evidence_refs=evidence_refs,
                        related_entity_refs=related_entity_refs,
                        possible_actions=_possible_actions(matching_results),
                        confidence=insight.confidence,
                        generated_at=run_date,
                    ),
                    evidence_refs=evidence_refs,
                    confidence=insight.confidence,
                    proposed_by="intelligence_hub.insight_engine",
                    model_provider="deterministic",
                    model_name="canonical_insight_engine",
                    model_version="v1",
                    created_at=f"{run_date}T00:00:00+00:00",
                )
            )
        return proposals

    def _synthesis_proposal(self, run, *, run_date: str, executive_summary: str) -> Proposal:
        evidence_refs = tuple(
            dict.fromkeys(
                f"decision:{result.decision.id}"
                for result in _all_signal_results(run)
                if getattr(result, "decision", None) is not None
            )
        )
        return Proposal.create(
            proposal_type="synthesis",
            payload=SynthesisProposalPayload(
                subject_type="brief",
                subject_id=run_date,
                content=executive_summary,
                summary=executive_summary[:240],
            ),
            evidence_refs=evidence_refs or ("daily-run:empty",),
            confidence="medium",
            proposed_by="intelligence_hub.daily_pipeline",
            model_provider="deterministic",
            model_name="daily_synthesis",
            model_version="v1",
            created_at=f"{run_date}T00:00:00+00:00",
        )


def _all_signal_results(run) -> tuple:
    return tuple((*run.repository_results, *run.paper_results, *run.domain_results))


def _matching_results(run, subject: str) -> tuple:
    normalized = _normalize(subject)
    matches = []
    for result in _all_signal_results(run):
        text = " ".join(
            (
                result.entity.canonical_name,
                " ".join(getattr(result.entity, "tags", ())),
                " ".join(getattr(result.entity, "aliases", ())),
                getattr(result, "signal_title", ""),
                " ".join(getattr(rel, "evidence", "") for rel in getattr(result, "relationships", ())),
            )
        )
        if normalized and normalized in _normalize(text):
            matches.append(result)
    if len({ _source(result) for result in matches }) >= 2:
        return tuple(matches)
    return tuple(_all_signal_results(run)[:3])


def _evidence_refs(results: Iterable) -> tuple[str, ...]:
    refs = []
    for result in results:
        for observation in getattr(result, "observations", ())[:3]:
            refs.append(f"observation:{observation.id}")
        for relationship in getattr(result, "relationships", ())[:3]:
            refs.append(f"relationship:{relationship.id}")
        decision = getattr(result, "decision", None)
        if decision:
            refs.append(f"decision:{decision.id}")
    return tuple(dict.fromkeys(refs))


def _possible_actions(results: Iterable) -> tuple[str, ...]:
    actions = []
    for result in results:
        decision = getattr(result, "decision", None)
        if decision:
            actions.append(decision.action)
    return tuple(dict.fromkeys(actions)) or ("Watch",)


def _what_changed(insight, results: Iterable) -> str:
    entities = ", ".join(result.entity.canonical_name for result in tuple(results)[:4])
    return f"{insight.subject} appears across {', '.join(insight.sources)} signals: {entities}."


def _source(result) -> str:
    signal_id = getattr(getattr(result, "decision", None), "signal_id", "")
    return signal_id.split(":", 1)[0] if ":" in signal_id else signal_id


def _has_event_semantics(observation) -> bool:
    if observation.metric_name not in {"latest_release", "latest_pull_request", "latest_issue", "published"}:
        return False
    return bool(observation.current_value) and observation.current_value != observation.previous_value


def _event_title(metric_name: str) -> str:
    return {
        "latest_release": "Release observed",
        "latest_pull_request": "Pull request activity observed",
        "latest_issue": "Issue activity observed",
        "published": "Publication observed",
    }.get(metric_name, "Event observed")


def _normalize(value: str) -> str:
    return value.casefold().replace("-", " ").replace("_", " ")
