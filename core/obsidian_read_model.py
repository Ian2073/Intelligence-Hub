from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from core.canonical_knowledge import Event, Insight
from core.memory import BriefRecord, Decision, Entity, EntityRelationship, Observation
from core.proposals import Proposal
from core.repository import Repository


GENERATED_BY = "intelligence_hub.obsidian.v1"


@dataclass(frozen=True)
class ObsidianLink:
    canonical_id: str
    path: str
    title: str
    note_type: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObsidianFact:
    label: str
    text: str
    links: tuple[ObsidianLink, ...] = ()


@dataclass(frozen=True)
class ObsidianSection:
    title: str
    facts: tuple[ObsidianFact, ...]


@dataclass(frozen=True)
class ObsidianNote:
    canonical_id: str
    note_type: str
    path: str
    title: str
    aliases: tuple[str, ...]
    created_at: str
    updated_at: str
    generated_by: str
    source: str
    evidence: tuple[str, ...]
    confidence: str
    related_notes: tuple[ObsidianLink, ...]
    sections: tuple[ObsidianSection, ...]


@dataclass(frozen=True)
class NoteIdentityIndex:
    by_canonical_id: dict[str, ObsidianLink]
    by_path: dict[str, ObsidianLink]
    by_title: dict[str, tuple[ObsidianLink, ...]]

    @classmethod
    def from_notes(cls, notes: tuple[ObsidianNote, ...]) -> "NoteIdentityIndex":
        by_canonical_id: dict[str, ObsidianLink] = {}
        by_path: dict[str, ObsidianLink] = {}
        by_title: dict[str, list[ObsidianLink]] = {}
        for note in notes:
            link = ObsidianLink(
                canonical_id=note.canonical_id,
                path=note.path,
                title=note.title,
                note_type=note.note_type,
                aliases=note.aliases,
            )
            by_canonical_id[note.canonical_id] = link
            by_path[note.path] = link
            by_title.setdefault(note.title.casefold(), []).append(link)
            for alias in note.aliases:
                by_title.setdefault(alias.casefold(), []).append(link)
        return cls(
            by_canonical_id=by_canonical_id,
            by_path=by_path,
            by_title={key: tuple(value) for key, value in by_title.items()},
        )

    def link_for(self, canonical_id: str) -> ObsidianLink | None:
        return self.by_canonical_id.get(canonical_id)


@dataclass(frozen=True)
class ObsidianReadModel:
    notes: tuple[ObsidianNote, ...]
    identity_index: NoteIdentityIndex


class ObsidianReadModelBuilder:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def build(self) -> ObsidianReadModel:
        entities = self.repository.list_entities()
        observations = self.repository.list_observations()
        relationships = self.repository.list_relationships()
        decisions = self.repository.list_decisions()
        briefs = self.repository.list_briefs()
        events = self.repository.list_events()
        insights = self.repository.list_insights()
        proposals = self.repository.list_proposals()

        notes = []
        notes.extend(_base_entity_notes(entities, observations))
        notes.extend(_event_notes(entities, observations))
        notes.extend(_canonical_event_notes(events))
        notes.extend(_insight_notes(insights))
        notes.extend(_decision_notes(decisions))
        notes.extend(_brief_notes(briefs))
        notes.extend(_dashboard_notes(entities, decisions, briefs))
        notes.extend(_proposal_review_notes(proposals))

        index = NoteIdentityIndex.from_notes(tuple(notes))
        hydrated = _hydrate_links(
            tuple(notes),
            index=index,
            entities=entities,
            observations=observations,
            relationships=relationships,
            decisions=decisions,
            briefs=briefs,
            events=events,
            insights=insights,
        )
        return ObsidianReadModel(notes=hydrated, identity_index=NoteIdentityIndex.from_notes(hydrated))


def _base_entity_notes(entities: list[Entity], observations: list[Observation]) -> list[ObsidianNote]:
    observations_by_entity = _group_observations(observations)
    notes: list[ObsidianNote] = []
    for entity in entities:
        note_type = "source" if entity.kind == "paper" else "entity"
        note_id = _entity_note_id(entity)
        notes.append(
            ObsidianNote(
                canonical_id=note_id,
                note_type=note_type,
                path=_entity_path(entity),
                title=entity.canonical_name,
                aliases=_aliases(entity),
                created_at=entity.first_seen,
                updated_at=entity.last_seen,
                generated_by=GENERATED_BY,
                source=_entity_source(entity, observations_by_entity.get(entity.id, ())),
                evidence=tuple(
                    _evidence(observation)
                    for observation in observations_by_entity.get(entity.id, ())[:5]
                    if _evidence(observation)
                ),
                confidence=_latest_confidence(observations_by_entity.get(entity.id, ())),
                related_notes=(),
                sections=(
                    ObsidianSection(
                        title="Summary",
                        facts=(ObsidianFact("Kind", entity.kind), ObsidianFact("Status", entity.status), ObsidianFact("Summary", entity.summary or "No summary recorded.")),
                    ),
                    ObsidianSection(
                        title="Observations",
                        facts=tuple(_observation_fact(item) for item in observations_by_entity.get(entity.id, ())[:12])
                        or (ObsidianFact("", "No observations recorded."),),
                    ),
                    ObsidianSection(title="Related Notes", facts=()),
                ),
            )
        )
    return notes


def _event_notes(entities: list[Entity], observations: list[Observation]) -> list[ObsidianNote]:
    entities_by_id = {entity.id: entity for entity in entities}
    notes: list[ObsidianNote] = []
    for observation in observations:
        if not _has_event_semantics(observation):
            continue
        entity = entities_by_id.get(observation.entity_id)
        if entity is None:
            continue
        title = f"{_event_title(observation.metric_name)}: {entity.canonical_name}"
        notes.append(
            ObsidianNote(
                canonical_id=_observation_note_id(observation),
                note_type="event",
                path=_stable_path("03 Events", "event", f"{observation.metric_name}-{entity.canonical_name}", observation.id),
                title=title,
                aliases=(),
                created_at=observation.observed_at,
                updated_at=observation.observed_at,
                generated_by=GENERATED_BY,
                source=observation.source_url,
                evidence=(_evidence(observation),),
                confidence=observation.confidence,
                related_notes=(),
                sections=(
                    ObsidianSection(
                        title="Event",
                        facts=(
                            ObsidianFact("Entity", entity.canonical_name),
                            ObsidianFact("Metric", observation.metric_name),
                            ObsidianFact("Current", observation.current_value),
                            ObsidianFact("Previous", observation.previous_value),
                            ObsidianFact("Evidence", observation.raw_evidence),
                        ),
                    ),
                ),
            )
        )
    return notes


def _canonical_event_notes(events: list[Event]) -> list[ObsidianNote]:
    notes = []
    for event in events:
        notes.append(
            ObsidianNote(
                canonical_id=event.id,
                note_type="event",
                path=_stable_path("03 Events", "event", event.title, event.id),
                title=event.title,
                aliases=(),
                created_at=event.occurred_at,
                updated_at=event.occurred_at,
                generated_by=GENERATED_BY,
                source="canonical event",
                evidence=event.evidence_refs,
                confidence=event.confidence,
                related_notes=(),
                sections=(
                    ObsidianSection(
                        title="Event",
                        facts=(
                            ObsidianFact("Type", event.event_type),
                            ObsidianFact("Summary", event.summary),
                            ObsidianFact("Occurred at", event.occurred_at),
                            ObsidianFact("Evidence", ", ".join(event.evidence_refs)),
                        ),
                    ),
                    ObsidianSection(title="Related Entities", facts=()),
                ),
            )
        )
    return notes


def _insight_notes(insights: list[Insight]) -> list[ObsidianNote]:
    notes = []
    for insight in insights:
        notes.append(
            ObsidianNote(
                canonical_id=insight.id,
                note_type="insight",
                path=_stable_path("02 Insights", "insight", insight.claim, insight.id),
                title=insight.claim,
                aliases=(),
                created_at=insight.generated_at,
                updated_at=insight.generated_at,
                generated_by=GENERATED_BY,
                source="canonical insight",
                evidence=insight.evidence_refs,
                confidence=insight.confidence,
                related_notes=(),
                sections=(
                    ObsidianSection("Claim", (ObsidianFact("", insight.claim),)),
                    ObsidianSection("Why It Matters", (ObsidianFact("", insight.why_it_matters),)),
                    ObsidianSection("Evidence", tuple(ObsidianFact("", ref) for ref in insight.evidence_refs)),
                    ObsidianSection("Related Entities", facts=()),
                    ObsidianSection("Related Events", facts=()),
                    ObsidianSection(
                        "Possible Actions",
                        tuple(ObsidianFact("", action) for action in insight.possible_actions)
                        or (ObsidianFact("", "Watch"),),
                    ),
                    ObsidianSection("Confidence", (ObsidianFact("", insight.confidence),)),
                    ObsidianSection(
                        "Provenance",
                        (
                            ObsidianFact("Proposed by", str(insight.provenance.get("proposed_by", ""))),
                            ObsidianFact("Model", str(insight.provenance.get("model_name", ""))),
                            ObsidianFact("Proposal", insight.proposal_id),
                        ),
                    ),
                ),
            )
        )
    return notes


def _decision_notes(decisions: list[Decision]) -> list[ObsidianNote]:
    notes = []
    for decision in decisions:
        title = f"{decision.action}: {_decision_subject(decision)}"
        notes.append(
            ObsidianNote(
                canonical_id=_decision_note_id(decision),
                note_type="decision",
                path=_stable_path("06 Decisions", "decision", title, decision.id),
                title=title,
                aliases=(decision.signal_id,),
                created_at=decision.revisit_date,
                updated_at=decision.revisit_date,
                generated_by=GENERATED_BY,
                source=decision.signal_id,
                evidence=(decision.rationale,),
                confidence=decision.confidence,
                related_notes=(),
                sections=(
                    ObsidianSection(
                        title="Decision",
                        facts=(
                            ObsidianFact("Action", decision.action),
                            ObsidianFact("Signal", decision.signal_id),
                            ObsidianFact("Rationale", decision.rationale),
                            ObsidianFact("Expected payoff", decision.expected_payoff),
                            ObsidianFact("Risk", decision.risk),
                            ObsidianFact("Revisit date", decision.revisit_date),
                        ),
                    ),
                    ObsidianSection(title="Based On", facts=()),
                ),
            )
        )
    return notes


def _brief_notes(briefs: list[BriefRecord]) -> list[ObsidianNote]:
    notes = []
    for brief in briefs:
        folder = f"01 Briefs/{brief.brief_type.title()}"
        notes.append(
            ObsidianNote(
                canonical_id=_brief_note_id(brief),
                note_type="brief",
                path=_stable_path(str(folder), "brief", f"{brief.brief_type}-{brief.period_end}", brief.id),
                title=_platform_neutral_title(brief.title),
                aliases=(f"{brief.brief_type.title()} Brief {brief.period_end}",),
                created_at=brief.period_start,
                updated_at=brief.period_end,
                generated_by=GENERATED_BY,
                source=brief.notion_url,
                evidence=brief.top_actions,
                confidence="medium",
                related_notes=(),
                sections=(
                    ObsidianSection(
                        title="Executive Summary",
                        facts=(ObsidianFact("", brief.executive_summary),),
                    ),
                    ObsidianSection(
                        title="Top Actions",
                        facts=tuple(ObsidianFact("", action) for action in brief.top_actions)
                        or (ObsidianFact("", "No top actions recorded."),),
                    ),
                    ObsidianSection(title="Contained Notes", facts=()),
                ),
            )
        )
    return notes


def _dashboard_notes(entities: list[Entity], decisions: list[Decision], briefs: list[BriefRecord]) -> list[ObsidianNote]:
    updated_at = max([*(entity.last_seen for entity in entities), *(brief.period_end for brief in briefs), "1970-01-01"])
    dashboard_specs = (
        ("system:dashboard:home", "00 Dashboard/Home.md", "Home", "Knowledge Workspace"),
        ("system:dashboard:today", "00 Dashboard/Today.md", "Today", "Latest generated notes"),
        ("system:dashboard:technology-radar", "00 Dashboard/Technology Radar.md", "Technology Radar", "Technology and repository map"),
        ("system:dashboard:recent-decisions", "00 Dashboard/Recent Decisions.md", "Recent Decisions", "Recent decision records"),
    )
    return [
        ObsidianNote(
            canonical_id=canonical_id,
            note_type="dashboard",
            path=path,
            title=title,
            aliases=(),
            created_at=updated_at,
            updated_at=updated_at,
            generated_by=GENERATED_BY,
            source="canonical repository",
            evidence=(),
            confidence="medium",
            related_notes=(),
            sections=(ObsidianSection(title=section, facts=()),),
        )
        for canonical_id, path, title, section in dashboard_specs
    ]


def _proposal_review_notes(proposals: list[Proposal]) -> list[ObsidianNote]:
    updated_at = max((proposal.created_at for proposal in proposals), default="1970-01-01")
    return [
        _proposal_review_note(
            canonical_id="system:rejected-proposals",
            path="90 System/Rejected Proposals.md",
            title="Rejected Proposals",
            proposals=tuple(proposal for proposal in proposals if proposal.validation_status == "rejected"),
            updated_at=updated_at,
        ),
        _proposal_review_note(
            canonical_id="system:needs-review",
            path="90 System/Needs Review.md",
            title="Needs Review",
            proposals=tuple(proposal for proposal in proposals if proposal.validation_status == "needs_review"),
            updated_at=updated_at,
        ),
    ]


def _proposal_review_note(
    *,
    canonical_id: str,
    path: str,
    title: str,
    proposals: tuple[Proposal, ...],
    updated_at: str,
) -> ObsidianNote:
    facts = tuple(
        ObsidianFact(
            proposal.proposal_type,
            f"{proposal.id}: {proposal.validation_status}; reasons={'; '.join(proposal.rejection_reasons)}",
        )
        for proposal in proposals
    ) or (ObsidianFact("", "No proposals in this state."),)
    return ObsidianNote(
        canonical_id=canonical_id,
        note_type="system",
        path=path,
        title=title,
        aliases=(),
        created_at=updated_at,
        updated_at=updated_at,
        generated_by=GENERATED_BY,
        source="proposal store",
        evidence=(),
        confidence="medium",
        related_notes=(),
        sections=(ObsidianSection(title, facts),),
    )


def _hydrate_links(
    notes: tuple[ObsidianNote, ...],
    *,
    index: NoteIdentityIndex,
    entities: list[Entity],
    observations: list[Observation],
    relationships: list[EntityRelationship],
    decisions: list[Decision],
    briefs: list[BriefRecord],
    events: list[Event],
    insights: list[Insight],
) -> tuple[ObsidianNote, ...]:
    entities_by_id = {entity.id: entity for entity in entities}
    observations_by_entity = _group_observations(observations)
    relations_by_source: dict[str, list[EntityRelationship]] = {}
    for relationship in relationships:
        relations_by_source.setdefault(relationship.source_entity_id, []).append(relationship)
    decision_links = {_decision_note_id(decision): index.link_for(_decision_note_id(decision)) for decision in decisions}
    decision_targets = {
        _decision_note_id(decision): _decision_target_links(decision, entities, index)
        for decision in decisions
    }
    decisions_by_subject = {
        _decision_note_id(decision): _decision_target_links(decision, entities, index)
        for decision in decisions
    }

    hydrated: list[ObsidianNote] = []
    for note in notes:
        related: list[ObsidianLink] = []
        sections = list(note.sections)
        if note.note_type in {"entity", "source"}:
            entity = _entity_for_note(note, entities)
            if entity is not None:
                relation_links = []
                for relationship in relations_by_source.get(entity.id, ()):
                    target = entities_by_id.get(relationship.target_entity_id)
                    link = index.link_for(_entity_note_id(target)) if target else None
                    if link:
                        relation_links.append(
                            ObsidianFact(relationship.relation_type, relationship.evidence, links=(link,))
                        )
                        related.append(link)
                event_links = tuple(
                    link
                    for observation in observations_by_entity.get(entity.id, ())
                    if (link := index.link_for(_observation_note_id(observation))) is not None
                )
                canonical_event_links = tuple(
                    link
                    for event in events
                    if note.canonical_id in event.entity_refs
                    if (link := index.link_for(event.id)) is not None
                )
                decision_facts = []
                for decision in decisions:
                    targets = decisions_by_subject.get(_decision_note_id(decision), ())
                    if any(target.canonical_id == note.canonical_id for target in targets):
                        link = decision_links.get(_decision_note_id(decision))
                        if link:
                            decision_facts.append(ObsidianFact(decision.action, decision.rationale, links=(link,)))
                            related.append(link)
                related.extend((*event_links, *canonical_event_links))
                sections = _replace_section(
                    tuple(sections),
                    "Related Notes",
                    tuple(
                        relation_links
                        + [ObsidianFact("Event", "Status-change event.", (link,)) for link in event_links]
                        + [ObsidianFact("Event", "Canonical event.", (link,)) for link in canonical_event_links]
                        + decision_facts
                    )
                    or (ObsidianFact("", "No explicit canonical relationships recorded."),),
                )
        elif note.note_type == "event":
            observation = _observation_for_note(note, observations)
            if observation:
                entity = entities_by_id.get(observation.entity_id)
                link = index.link_for(_entity_note_id(entity)) if entity else None
                if link:
                    related.append(link)
                    sections = _append_fact(tuple(sections), "Event", ObsidianFact("Involves", entity.canonical_name, (link,)))
            event = _canonical_event_for_note(note, events)
            if event:
                entity_links = tuple(
                    link
                    for ref in event.entity_refs
                    if (link := index.link_for(ref)) is not None
                )
                related.extend(entity_links)
                sections = _replace_section(
                    tuple(sections),
                    "Related Entities",
                    tuple(ObsidianFact("Entity", link.title, (link,)) for link in entity_links)
                    or (ObsidianFact("", "No related entities resolved."),),
                )
        elif note.note_type == "decision":
            decision = _decision_for_note(note, decisions)
            if decision:
                target_links = decision_targets.get(_decision_note_id(decision), ())
                insight_links = _decision_insight_links(decision, insights, index)
                target_links = (*target_links, *insight_links)
                related.extend(target_links)
                sections = _replace_section(
                    tuple(sections),
                    "Based On",
                    tuple(ObsidianFact("Evidence", decision.signal_id, (link,)) for link in target_links)
                    or (ObsidianFact("", "No canonical target resolved from signal_id."),),
                )
        elif note.note_type == "brief":
            brief = _brief_for_note(note, briefs)
            if brief:
                contained = []
                for insight in insights:
                    if brief.period_start <= insight.generated_at <= brief.period_end:
                        insight_link = index.link_for(insight.id)
                        if insight_link:
                            contained.append(ObsidianFact("Insight", insight.summary, (insight_link,)))
                            related.append(insight_link)
                for decision in decisions:
                    if _decision_date(decision) and brief.period_start <= _decision_date(decision) <= brief.period_end:
                        decision_link = index.link_for(_decision_note_id(decision))
                        if decision_link:
                            contained.append(ObsidianFact("Decision", decision.action, (decision_link,)))
                            related.append(decision_link)
                        for target in decision_targets.get(_decision_note_id(decision), ()):
                            contained.append(ObsidianFact("Evidence", target.title, (target,)))
                            related.append(target)
                sections = _replace_section(
                    tuple(sections),
                    "Contained Notes",
                    tuple(contained) or (ObsidianFact("", "No canonical decisions resolved for this brief period."),),
                )
        elif note.note_type == "dashboard":
            sections, related = _dashboard_sections(note, index, entities, decisions, briefs)
        elif note.note_type == "insight":
            insight = _insight_for_note(note, insights)
            if insight:
                entity_links = tuple(
                    link
                    for ref in insight.related_entity_refs
                    if (link := index.link_for(ref)) is not None
                )
                event_links = tuple(
                    link
                    for ref in insight.related_event_refs
                    if (link := index.link_for(ref)) is not None
                )
                related.extend((*entity_links, *event_links))
                sections = _replace_section(
                    tuple(sections),
                    "Related Entities",
                    tuple(ObsidianFact("Entity", link.title, (link,)) for link in entity_links)
                    or (ObsidianFact("", "No related entities resolved."),),
                )
                sections = _replace_section(
                    tuple(sections),
                    "Related Events",
                    tuple(ObsidianFact("Event", link.title, (link,)) for link in event_links)
                    or (ObsidianFact("", "No related events resolved."),),
                )
        hydrated.append(
            ObsidianNote(
                canonical_id=note.canonical_id,
                note_type=note.note_type,
                path=note.path,
                title=note.title,
                aliases=note.aliases,
                created_at=note.created_at,
                updated_at=note.updated_at,
                generated_by=note.generated_by,
                source=note.source,
                evidence=note.evidence,
                confidence=note.confidence,
                related_notes=_unique_links((*note.related_notes, *related)),
                sections=tuple(sections),
            )
        )
    return tuple(hydrated)


def _dashboard_sections(
    note: ObsidianNote,
    index: NoteIdentityIndex,
    entities: list[Entity],
    decisions: list[Decision],
    briefs: list[BriefRecord],
) -> tuple[tuple[ObsidianSection, ...], list[ObsidianLink]]:
    links: list[ObsidianLink] = []
    if note.canonical_id == "system:dashboard:home":
        facts = []
        for dashboard_id in ("system:dashboard:today", "system:dashboard:technology-radar", "system:dashboard:recent-decisions"):
            link = index.link_for(dashboard_id)
            if link:
                facts.append(ObsidianFact("", link.title, (link,)))
                links.append(link)
        return (ObsidianSection("Knowledge Workspace", tuple(facts)),), links
    if note.canonical_id == "system:dashboard:today":
        recent_briefs = sorted(briefs, key=lambda item: item.period_end, reverse=True)[:5]
        facts = []
        for brief in recent_briefs:
            link = index.link_for(_brief_note_id(brief))
            if link:
                facts.append(ObsidianFact("Brief", brief.period_end, (link,)))
                links.append(link)
        return (ObsidianSection("Latest Briefs", tuple(facts) or (ObsidianFact("", "No briefs recorded."),)),), links
    if note.canonical_id == "system:dashboard:technology-radar":
        facts = []
        for entity in sorted(entities, key=lambda item: (item.kind, item.canonical_name.casefold())):
            if entity.kind not in {"repository", "technology", "company", "product", "topic"}:
                continue
            link = index.link_for(_entity_note_id(entity))
            if link:
                facts.append(ObsidianFact(entity.kind, entity.canonical_name, (link,)))
                links.append(link)
        return (ObsidianSection("Domain Index", tuple(facts) or (ObsidianFact("", "No radar entities recorded."),)),), links
    facts = []
    for decision in sorted(decisions, key=lambda item: item.revisit_date, reverse=True)[:12]:
        link = index.link_for(_decision_note_id(decision))
        if link:
            facts.append(ObsidianFact(decision.action, _decision_subject(decision), (link,)))
            links.append(link)
    return (ObsidianSection("Recent Decisions", tuple(facts) or (ObsidianFact("", "No decisions recorded."),)),), links


def _entity_path(entity: Entity) -> str:
    if entity.kind == "paper":
        return _stable_path("05 Sources/Papers", "source", entity.canonical_name, entity.id)
    if entity.kind == "repository":
        return _stable_path("04 Entities/Repositories", "entity", entity.canonical_name, entity.id)
    folder = {
        "company": "Companies",
        "technology": "Technologies",
        "product": "Products",
        "topic": "Topics",
    }.get(entity.kind, "Other")
    return _stable_path(f"04 Entities/{folder}", "entity", entity.canonical_name, entity.id)


def _stable_path(folder: str, prefix: str, title: str, stable_id: str) -> str:
    return f"{folder}/{prefix}--{_short_id(stable_id)}.md"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\s.-]+", "-", value, flags=re.UNICODE)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-.").casefold()
    return cleaned[:72].strip("-")


def _short_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def _entity_note_id(entity: Entity | None) -> str:
    if entity is None:
        return ""
    return f"entity:{entity.id}" if entity.kind != "paper" else f"source:{entity.id}"


def _observation_note_id(observation: Observation) -> str:
    return f"event:{observation.id}"


def _insight_note_id(insight: Insight) -> str:
    return insight.id


def _decision_note_id(decision: Decision) -> str:
    return f"decision:{decision.id}"


def _brief_note_id(brief: BriefRecord) -> str:
    return f"brief:{brief.id}"


def _aliases(entity: Entity) -> tuple[str, ...]:
    aliases = []
    for alias in entity.aliases:
        if alias == entity.canonical_name or alias.startswith(("http://", "https://")):
            continue
        aliases.append(alias)
    return tuple(dict.fromkeys(aliases))


def _entity_source(entity: Entity, observations: tuple[Observation, ...]) -> str:
    for observation in reversed(observations):
        if observation.source_url:
            return observation.source_url
    if entity.kind == "repository":
        for alias in entity.aliases:
            if alias.startswith(("http://", "https://")):
                return alias
    return ""


def _evidence(observation: Observation) -> str:
    if observation.source_url:
        return f"{observation.raw_evidence} Source: {observation.source_url}"
    return observation.raw_evidence


def _latest_confidence(observations: tuple[Observation, ...]) -> str:
    if not observations:
        return "medium"
    return observations[-1].confidence


def _observation_fact(observation: Observation) -> ObsidianFact:
    text = f"{observation.metric_name}: {observation.previous_value} -> {observation.current_value}"
    return ObsidianFact(observation.observed_at, text)


def _has_event_semantics(observation: Observation) -> bool:
    if observation.metric_name not in {"latest_release", "latest_pull_request", "latest_issue", "published"}:
        return False
    if not observation.current_value:
        return False
    return observation.current_value != observation.previous_value


def _event_title(metric_name: str) -> str:
    return {
        "latest_release": "Release observed",
        "latest_pull_request": "Pull request activity observed",
        "latest_issue": "Issue activity observed",
        "published": "Publication observed",
    }.get(metric_name, "Event observed")


def _group_observations(observations: list[Observation]) -> dict[str, tuple[Observation, ...]]:
    grouped: dict[str, list[Observation]] = {}
    for observation in observations:
        grouped.setdefault(observation.entity_id, []).append(observation)
    return {key: tuple(sorted(value, key=lambda item: (item.observed_at, item.id))) for key, value in grouped.items()}


def _replace_section(
    sections: tuple[ObsidianSection, ...],
    title: str,
    facts: tuple[ObsidianFact, ...],
) -> tuple[ObsidianSection, ...]:
    replaced = []
    found = False
    for section in sections:
        if section.title == title:
            replaced.append(ObsidianSection(title, facts))
            found = True
        else:
            replaced.append(section)
    if not found:
        replaced.append(ObsidianSection(title, facts))
    return tuple(replaced)


def _append_fact(
    sections: tuple[ObsidianSection, ...],
    title: str,
    fact: ObsidianFact,
) -> tuple[ObsidianSection, ...]:
    return tuple(
        ObsidianSection(section.title, (*section.facts, fact)) if section.title == title else section
        for section in sections
    )


def _unique_links(links: tuple[ObsidianLink, ...]) -> tuple[ObsidianLink, ...]:
    by_id: dict[str, ObsidianLink] = {}
    for link in links:
        by_id.setdefault(link.canonical_id, link)
    return tuple(by_id.values())


def _decision_subject(decision: Decision) -> str:
    signal_id = decision.signal_id
    if ":" not in signal_id:
        return signal_id
    parts = signal_id.split(":")
    if parts[0] == "domain" and len(parts) >= 4:
        return ":".join(parts[2:-1]) or signal_id
    if parts[0] in {"github-repo", "paper", "repo"} and len(parts) >= 2:
        return ":".join(parts[1:-1]) if _looks_like_date(parts[-1]) else ":".join(parts[1:])
    return signal_id


def _platform_neutral_title(title: str) -> str:
    return title.replace("Hermes Daily Intelligence", "Daily Intelligence").replace(
        "Hermes Executive Dashboard", "Executive Dashboard"
    )


def _decision_date(decision: Decision) -> str | None:
    last = decision.signal_id.rsplit(":", 1)[-1]
    return last if _looks_like_date(last) else None


def _looks_like_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value))


def _decision_target_links(decision: Decision, entities: list[Entity], index: NoteIdentityIndex) -> tuple[ObsidianLink, ...]:
    targets: list[ObsidianLink] = []
    subject = _decision_subject(decision)
    kinds: tuple[str, ...]
    if decision.signal_id.startswith(("github-repo:", "repo:")):
        kinds = ("repository",)
    elif decision.signal_id.startswith("paper:"):
        kinds = ("paper",)
    elif decision.signal_id.startswith("domain:"):
        kinds = ("company", "technology", "product", "topic", "repository", "paper")
    else:
        kinds = tuple({entity.kind for entity in entities})
    for entity in entities:
        names = (entity.canonical_name, *entity.aliases)
        if entity.kind in kinds and any(subject.casefold() == name.casefold() for name in names):
            link = index.link_for(_entity_note_id(entity))
            if link:
                targets.append(link)
    return tuple(targets)


def _decision_insight_links(decision: Decision, insights: list[Insight], index: NoteIdentityIndex) -> tuple[ObsidianLink, ...]:
    subject = _decision_subject(decision).casefold()
    links = []
    for insight in insights:
        text = " ".join((insight.claim, insight.summary, " ".join(insight.related_entity_refs))).casefold()
        if subject and subject in text:
            link = index.link_for(insight.id)
            if link:
                links.append(link)
    return tuple(links)


def _entity_for_note(note: ObsidianNote, entities: list[Entity]) -> Entity | None:
    for entity in entities:
        if _entity_note_id(entity) == note.canonical_id:
            return entity
    return None


def _observation_for_note(note: ObsidianNote, observations: list[Observation]) -> Observation | None:
    for observation in observations:
        if _observation_note_id(observation) == note.canonical_id:
            return observation
    return None


def _decision_for_note(note: ObsidianNote, decisions: list[Decision]) -> Decision | None:
    for decision in decisions:
        if _decision_note_id(decision) == note.canonical_id:
            return decision
    return None


def _brief_for_note(note: ObsidianNote, briefs: list[BriefRecord]) -> BriefRecord | None:
    for brief in briefs:
        if _brief_note_id(brief) == note.canonical_id:
            return brief
    return None


def _insight_for_note(note: ObsidianNote, insights: list[Insight]) -> Insight | None:
    for insight in insights:
        if _insight_note_id(insight) == note.canonical_id:
            return insight
    return None


def _canonical_event_for_note(note: ObsidianNote, events: list[Event]) -> Event | None:
    for event in events:
        if event.id == note.canonical_id:
            return event
    return None
