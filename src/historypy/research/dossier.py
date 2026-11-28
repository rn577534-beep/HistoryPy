"""Stepwise, evidence-traceable historical dossier assembly.

This module organizes researcher-curated records into a readable structure. It
does not discover facts, invent causal links, or decide historical truth.
"""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset, ValidationIssue
from historypy.core.entities import (
    HistoricalCivilization,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
)
from historypy.core.models import EvidenceLink, HistoricalClaim, HistoricalEvent, SourceRecord
from historypy.research.evidence import EvidenceSummary, summarize_claim_evidence
from historypy.research.quality import DatasetQualityReport, assess_dataset_quality
from historypy.research.timeline import TimelineResult, timeline_for_dataset
from historypy.research.source_independence import (
    ClaimSourceIndependenceReport,
    analyze_claim_source_independence,
)
from historypy.research.verification import ClaimAssessment, assess_claim


@dataclass(frozen=True, slots=True)
class ClaimReview:
    """A claim, its recorded evidence links, and a non-truth assessment."""

    claim: HistoricalClaim
    assessment: ClaimAssessment
    evidence: tuple[EvidenceLink, ...]
    summary: EvidenceSummary
    sources: tuple[SourceRecord, ...]
    independence: ClaimSourceIndependenceReport


@dataclass(frozen=True, slots=True)
class EventChapter:
    """One chronological chapter, linked only to explicitly related records."""

    event: HistoricalEvent
    claims: tuple[ClaimReview, ...]
    people: tuple[HistoricalPerson, ...]
    places: tuple[HistoricalPlace, ...]
    organizations: tuple[HistoricalOrganization, ...]
    civilizations: tuple[HistoricalCivilization, ...]
    sources: tuple[SourceRecord, ...]


@dataclass(frozen=True, slots=True)
class HistoricalDossier:
    """Structured output of the stepwise history-organizing engine."""

    title: str
    scope_note: str
    timeline: TimelineResult
    chapters: tuple[EventChapter, ...]
    unassigned_claims: tuple[ClaimReview, ...]
    quality: DatasetQualityReport
    validation_issues: tuple[ValidationIssue, ...]
    people: tuple[HistoricalPerson, ...]
    places: tuple[HistoricalPlace, ...]
    organizations: tuple[HistoricalOrganization, ...]
    civilizations: tuple[HistoricalCivilization, ...]
    sources: tuple[SourceRecord, ...]
    research_gaps: tuple[str, ...]


def _claim_review(dataset: HistoricalDataset, claim: HistoricalClaim) -> ClaimReview:
    links = tuple(link for link in dataset.evidence if link.claim_id == claim.id)
    source_by_id = {source.id: source for source in dataset.sources}
    linked_sources = tuple(
        source_by_id[source_id]
        for source_id in dict.fromkeys(link.source_id for link in links)
        if source_id in source_by_id
    )
    return ClaimReview(
        claim=claim,
        assessment=assess_claim(dataset, claim.id),
        evidence=links,
        summary=summarize_claim_evidence(dataset, claim.id),
        sources=linked_sources,
        independence=analyze_claim_source_independence(dataset, claim.id),
    )


def build_historical_dossier(
    dataset: HistoricalDataset,
    *,
    title: str = "Historical dossier",
    scope_note: str = "",
    include_indeterminate_dates: bool = True,
) -> HistoricalDossier:
    """Organize a dataset into chronological chapters, evidence, entities and gaps.

    Event-to-claim links are taken only from HistoricalClaim.event_ids. Person,
    place, organization and civilization links are taken only from the event's
    place_ids and explicit relationship/entity references. No relationship is
    inferred from name co-occurrence or date overlap.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title cannot be empty")
    if not isinstance(scope_note, str):
        raise TypeError("scope_note must be a string")
    if not isinstance(include_indeterminate_dates, bool):
        raise TypeError("include_indeterminate_dates must be bool")

    issues = tuple(dataset.validate())
    if issues:
        # Preserve findings in the report instead of silently discarding records.
        validation_issues = issues
    else:
        validation_issues = ()

    timeline = timeline_for_dataset(
        dataset,
        kinds=("event",),
        include_indeterminate=include_indeterminate_dates,
    )
    event_by_id = {event.id: event for event in dataset.events}
    people_by_id = {person.id: person for person in dataset.people}
    places_by_id = {place.id: place for place in dataset.places}
    sources_by_id = {source.id: source for source in dataset.sources}
    reviews = {claim.id: _claim_review(dataset, claim) for claim in dataset.claims}

    chapters: list[EventChapter] = []
    assigned_claim_ids: set[str] = set()
    for entry in timeline.entries:
        if entry.kind != "event" or entry.record_id not in event_by_id:
            continue
        event = event_by_id[entry.record_id]
        event_claims = tuple(
            reviews[claim.id] for claim in dataset.claims
            if event.id in claim.event_ids
        )
        assigned_claim_ids.update(item.claim.id for item in event_claims)
        event_places = tuple(
            places_by_id[item_id] for item_id in event.place_ids
            if item_id in places_by_id
        )
        place_ids = {item.id for item in event_places}
        event_organizations = tuple(
            item for item in dataset.organizations
            if place_ids.intersection(item.place_ids)
        )
        event_civilizations = tuple(
            item for item in dataset.civilizations
            if place_ids.intersection(item.region_place_ids)
        )
        source_ids = list(event.source_ids)
        for review in event_claims:
            source_ids.extend(source.id for source in review.sources)
        chapter_sources = tuple(
            sources_by_id[source_id]
            for source_id in dict.fromkeys(source_ids)
            if source_id in sources_by_id
        )
        chapters.append(EventChapter(
            event=event,
            claims=event_claims,
            people=tuple(
                people_by_id[item_id] for item_id in dict.fromkeys(
                    person_id
                    for relationship in dataset.relationships
                    if relationship.subject_id == event.id or relationship.object_id == event.id
                    for person_id in (relationship.subject_id, relationship.object_id)
                ) if item_id in people_by_id
            ),
            places=event_places,
            organizations=event_organizations,
            civilizations=event_civilizations,
            sources=chapter_sources,
        ))

    unassigned = tuple(
        reviews[claim.id] for claim in dataset.claims
        if claim.id not in assigned_claim_ids
    )
    quality = assess_dataset_quality(dataset)
    gaps: list[str] = []
    if not dataset.events:
        gaps.append("No event records are present; add dated or explicitly undated events.")
    if not dataset.sources:
        gaps.append("No source catalogue records are present.")
    if not dataset.claims:
        gaps.append("No explicit historical claims are present.")
    if timeline.undated_count:
        gaps.append(f"{timeline.undated_count} event(s) have no computable date bounds.")
    if validation_issues:
        gaps.append(f"{len(validation_issues)} structural validation issue(s) need review.")
    for review in reviews.values():
        if review.assessment.status in {"mixed", "insufficient"}:
            gaps.append(
                f"Claim {review.claim.id!r} has {review.assessment.status} recorded "
                "support/contradiction links; human source review is needed."
            )
        if review.summary.distinct_source_count == 0:
            gaps.append(f"Claim {review.claim.id!r} has no linked evidence sources.")
    if any(item.severity == "warning" for item in quality.findings):
        gaps.append("Dataset quality warnings remain; inspect the quality findings.")
    return HistoricalDossier(
        title=title.strip(),
        scope_note=scope_note,
        timeline=timeline,
        chapters=tuple(chapters),
        unassigned_claims=unassigned,
        quality=quality,
        validation_issues=validation_issues,
        people=tuple(dataset.people),
        places=tuple(dataset.places),
        organizations=tuple(dataset.organizations),
        civilizations=tuple(dataset.civilizations),
        sources=tuple(dataset.sources),
        research_gaps=tuple(dict.fromkeys(gaps)),
    )


def _source_label(source: SourceRecord) -> str:
    creator = f", {source.creator}" if source.creator else ""
    url = f" — {source.url}" if source.url else ""
    return f"{source.title}{creator} [`{source.id}`]{url}"


def render_historical_dossier(dossier: HistoricalDossier) -> str:
    """Render a readable Markdown dossier with evidence traceability."""
    if not isinstance(dossier, HistoricalDossier):
        raise TypeError("dossier must be a HistoricalDossier")
    lines = [f"# {dossier.title}", ""]
    if dossier.scope_note:
        lines.extend((dossier.scope_note, ""))
    lines.extend((
        ("> Research organization, not an automated verdict on historical truth. "
         "Claims and causal links are not inferred."),
        "",
        "## 1. Chronological narrative",
        "",
    ))
    if not dossier.chapters:
        lines.append("- No event chapters are available.")
    for index, chapter in enumerate(dossier.chapters, 1):
        event = chapter.event
        lines.extend((f"### {index}. {event.title}", "", f"**Date:** {event.date.display()}", ""))
        date_notes = []
        if event.date.precision != "unknown":
            date_notes.append(f"precision: {event.date.precision}")
        if event.date.circa:
            date_notes.append("approximate date")
        if event.date.original_expression:
            date_notes.append(f"source wording: {event.date.original_expression}")
        if date_notes:
            lines.append("**Date uncertainty:** " + "; ".join(date_notes) + ".")
            lines.append("")
        if event.summary:
            lines.extend((event.summary, ""))
        if chapter.places:
            lines.extend((
                "**Recorded places:** " + ", ".join(item.name for item in chapter.places), ""
            ))
        if chapter.people:
            lines.extend((
                "**Explicitly linked people:** " + ", ".join(item.name for item in chapter.people), ""
            ))
        if chapter.organizations:
            lines.extend((
                "**Organizations associated through recorded place links:** "
                + ", ".join(item.name for item in chapter.organizations), ""
            ))
        if chapter.civilizations:
            lines.extend((
                "**Civilizations associated through recorded place links:** "
                + ", ".join(item.name for item in chapter.civilizations), ""
            ))
        if chapter.claims:
            lines.extend(("**Claims and evidence review:**", ""))
            for review in chapter.claims:
                lines.append(
                    f"- **{review.claim.statement}** — recorded status: "
                    f"`{review.assessment.status}`."
                )
                for link in review.evidence:
                    source = next(
                        (item for item in review.sources if item.id == link.source_id), None
                    )
                    source_text = _source_label(source) if source else f"source `{link.source_id}`"
                    locator = link.locator or link.page or link.paragraph or link.archive_shelfmark
                    locator_text = f"; locator: {locator}" if locator else "; locator missing"
                    quote_text = f'; excerpt: “{link.quotation}”' if link.quotation else ""
                    lines.append(
                        f"  - {link.relation}: {source_text}{locator_text}{quote_text}"
                    )
                support_count = sum(link.relation == "supports" for link in review.evidence)
                contradiction_count = sum(
                    link.relation == "contradicts" for link in review.evidence
                )
                contextual_count = sum(
                    link.relation == "contextualizes" for link in review.evidence
                )
                mention_count = sum(link.relation == "mentions" for link in review.evidence)
                lines.append(
                    f"  - Evidence balance: {support_count} supporting, "
                    f"{contradiction_count} contradicting, {contextual_count} contextualizing, "
                    f"{mention_count} mentioning."
                )
                independence = review.independence
                lines.append(
                    f"  - Source independence: `{independence.status}`; "
                    f"{len(independence.dependent_clusters)} known dependency cluster(s); "
                    f"{len(independence.unknown_source_ids)} source(s) with unknown independence."
                )
                for cluster in independence.dependent_clusters:
                    lines.append(
                        "    - Dependent evidence sources: "
                        + ", ".join(cluster.evidence_source_ids)
                        + (
                            "; intermediate sources: " + ", ".join(cluster.bridge_source_ids)
                            if cluster.bridge_source_ids else ""
                        )
                    )
                if independence.unknown_source_ids:
                    lines.append(
                        "    - Independence not established for: "
                        + ", ".join(independence.unknown_source_ids)
                    )
        else:
            lines.append("**Claims:** No claim is explicitly linked to this event.")
        if chapter.sources:
            lines.extend(("", "**Event/source records:**"))
            lines.extend(f"- {_source_label(source)}" for source in chapter.sources)
        lines.append("")

    lines.extend(("## 2. Claims not assigned to an event", ""))
    if dossier.unassigned_claims:
        for review in dossier.unassigned_claims:
            lines.append(
                f"- **{review.claim.statement}** — `{review.assessment.status}`; "
                f"{review.summary.distinct_source_count} linked source(s)."
            )
    else:
        lines.append("- None.")
    lines.extend(("", "## 3. People and historical actors", ""))
    lines.extend(
        f"- **{item.name}** — {item.description or 'No description recorded.'} "
        f"(sources: {', '.join(item.source_ids) or 'not linked'})"
        for item in dossier.people
    ) if dossier.people else lines.append("- No people records.")
    lines.extend(("", "## 4. Places and geography", ""))
    lines.extend(
        f"- **{item.name}** ({item.place_type}) — {item.description or 'No description recorded.'}"
        for item in dossier.places
    ) if dossier.places else lines.append("- No place records.")
    lines.extend(("", "## 5. Organizations and civilizations", ""))
    for item in dossier.organizations:
        lines.append(f"- **{item.name}** ({item.organization_type})")
    for item in dossier.civilizations:
        lines.append(f"- **{item.name}** (civilization record)")
    if not dossier.organizations and not dossier.civilizations:
        lines.append("- No organization or civilization records.")
    lines.extend(("", "## 6. Source catalogue", ""))
    if dossier.sources:
        lines.extend(f"- {_source_label(source)} ({source.source_type})" for source in dossier.sources)
    else:
        lines.append("- No sources recorded.")
    lines.extend(("", "## 7. Research gaps and validation", ""))
    if dossier.research_gaps:
        lines.extend(f"- {gap}" for gap in dossier.research_gaps)
    else:
        lines.append("- No automatic gap flags. This does not mean the research is complete.")
    if dossier.validation_issues:
        lines.extend(("", "**Structural validation issues:**"))
        lines.extend(
            f"- `{issue.code}`: {issue.message}" for issue in dossier.validation_issues
        )
    if dossier.quality.findings:
        lines.extend(("", "**Dataset quality findings:**"))
        lines.extend(
            f"- [{finding.severity}] `{finding.code}`: {finding.message}"
            for finding in dossier.quality.findings
        )
    lines.extend((
        "",
        "## 8. Interpretation protocol",
        "",
        "1. Verify each source against the original document or artefact.",
        "2. Review supporting and contradicting evidence separately.",
        "3. Check source genealogy before treating accounts as independent.",
        "4. Keep uncertain dates and competing interpretations visible.",
        "5. Add causal explanations only when a researcher records and cites the argument.",
    ))
    return "\n".join(lines)


__all__ = [
    "ClaimReview",
    "EventChapter",
    "HistoricalDossier",
    "build_historical_dossier",
    "render_historical_dossier",
]
