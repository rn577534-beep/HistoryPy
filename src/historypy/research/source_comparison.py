"""Side-by-side source evidence views for a historical event.

The comparison preserves researcher-entered claims, relations, quotations, and
locators. It does not infer source independence, reconcile contradictions, or
decide which account is historically correct.
"""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class SourceEvidenceExcerpt:
    """One source's recorded evidence for a claim associated with an event."""

    claim_id: str
    claim_statement: str
    relation: str
    quotation: str | None
    interpretation_note: str | None
    locator: str | None
    page: str | None
    paragraph: str | None
    archive_shelfmark: str | None
    url_fragment: str | None
    transcription_line: str | None
    timecode: str | None

    @property
    def has_locator(self) -> bool:
        """Whether any structured or free-form citation location is recorded."""
        return any((
            self.locator, self.page, self.paragraph, self.archive_shelfmark,
            self.url_fragment, self.transcription_line, self.timecode,
        ))


@dataclass(frozen=True, slots=True)
class EventSourceEntry:
    """A source attached directly to an event or through an event-linked claim."""

    source_id: str
    title: str
    source_type: str
    url: str | None
    directly_linked_to_event: bool
    evidence: tuple[SourceEvidenceExcerpt, ...]


@dataclass(frozen=True, slots=True)
class EventSourceComparison:
    """Traceable source-by-source evidence for one event."""

    event_id: str
    event_title: str
    sources: tuple[EventSourceEntry, ...]

    @property
    def evidence_count(self) -> int:
        return sum(len(source.evidence) for source in self.sources)

    @property
    def evidence_missing_locators(self) -> int:
        return sum(
            not excerpt.has_locator
            for source in self.sources
            for excerpt in source.evidence
        )

    @property
    def has_recorded_support_contradiction(self) -> bool:
        """True only when both relation labels were explicitly recorded."""
        relations = {
            excerpt.relation
            for source in self.sources
            for excerpt in source.evidence
        }
        return "supports" in relations and "contradicts" in relations


def compare_event_sources(
    dataset: HistoricalDataset, event_id: str
) -> EventSourceComparison:
    """Group all recorded sources and evidence excerpts for a historical event.

    Direct event source references are included even when no quotation or claim
    evidence has been entered. Evidence is included through claims whose
    event_ids contain the requested event. Ordering follows dataset order.
    """
    dataset.require_valid()
    event = next((item for item in dataset.events if item.id == event_id), None)
    if event is None:
        raise KeyError(f"Unknown event id: {event_id}")

    linked_claims = tuple(
        claim for claim in dataset.claims if event_id in claim.event_ids
    )
    claim_by_id = {claim.id: claim for claim in linked_claims}
    source_by_id = {source.id: source for source in dataset.sources}
    evidence_by_source: dict[str, list[SourceEvidenceExcerpt]] = {}
    for link in dataset.evidence:
        claim = claim_by_id.get(link.claim_id)
        if claim is None:
            continue
        evidence_by_source.setdefault(link.source_id, []).append(
            SourceEvidenceExcerpt(
                claim_id=claim.id,
                claim_statement=claim.statement,
                relation=link.relation,
                quotation=link.quotation,
                interpretation_note=link.interpretation_note,
                locator=link.locator,
                page=link.page,
                paragraph=link.paragraph,
                archive_shelfmark=link.archive_shelfmark,
                url_fragment=link.url_fragment,
                transcription_line=link.transcription_line,
                timecode=link.timecode,
            )
        )

    direct_ids = set(event.source_ids)
    ordered_source_ids = list(event.source_ids)
    for link in dataset.evidence:
        if link.claim_id in claim_by_id and link.source_id not in ordered_source_ids:
            ordered_source_ids.append(link.source_id)

    entries = tuple(
        EventSourceEntry(
            source_id=source_id,
            title=source_by_id[source_id].title,
            source_type=source_by_id[source_id].source_type,
            url=source_by_id[source_id].url,
            directly_linked_to_event=source_id in direct_ids,
            evidence=tuple(evidence_by_source.get(source_id, ())),
        )
        for source_id in ordered_source_ids
    )
    return EventSourceComparison(event.id, event.title, entries)



def render_event_source_comparison(
    dataset: HistoricalDataset, event_id: str
) -> str:
    """Render a side-by-side Markdown report with recorded citations."""
    comparison = compare_event_sources(dataset, event_id)
    lines = [
        f"# Source comparison: {comparison.event_title}",
        "",
        (
            "This report presents recorded evidence side by side. It does not "
            "rank source credibility or decide historical truth."
        ),
        "",
    ]
    for source in comparison.sources:
        lines.append(f"## {source.title}")
        lines.append(f"- Source ID: {source.source_id}")
        lines.append(f"- Source type: {source.source_type}")
        lines.append(
            "- Directly linked to event: "
            + ("yes" if source.directly_linked_to_event else "no; linked through claim evidence")
        )
        if source.url:
            lines.append(f"- Source URL: {source.url}")
        if not source.evidence:
            lines.extend(["- No claim quotation or evidence link is recorded.", ""])
            continue
        lines.append("")
        for excerpt in source.evidence:
            lines.append(f"### Claim: {excerpt.claim_statement}")
            lines.append(f"- Recorded relation: {excerpt.relation}")
            if excerpt.quotation:
                lines.append(f"- Quotation: {excerpt.quotation}")
            locator_parts = [
                f"locator: {excerpt.locator}" if excerpt.locator else None,
                f"page: {excerpt.page}" if excerpt.page else None,
                f"paragraph: {excerpt.paragraph}" if excerpt.paragraph else None,
                f"archive shelfmark: {excerpt.archive_shelfmark}"
                if excerpt.archive_shelfmark else None,
                f"URL fragment: {excerpt.url_fragment}"
                if excerpt.url_fragment else None,
                f"transcription line: {excerpt.transcription_line}"
                if excerpt.transcription_line else None,
                f"timecode: {excerpt.timecode}" if excerpt.timecode else None,
            ]
            recorded = [part for part in locator_parts if part]
            lines.append(
                "- Citation location: " + "; ".join(recorded)
                if recorded else "- Citation location: not recorded"
            )
            if excerpt.interpretation_note:
                lines.append(f"- Researcher note: {excerpt.interpretation_note}")
            lines.append("")
    lines.extend([
        "## Audit summary",
        f"- Evidence links: {comparison.evidence_count}",
        (
            f"- Evidence links missing a citation location: "
            f"{comparison.evidence_missing_locators}"
        ),
        (
            f"- Recorded supporting and contradicting labels both present: "
            f"{'yes' if comparison.has_recorded_support_contradiction else 'no'}"
        ),
        "",
        (
            "These relation labels and excerpts are researcher-entered records. "
            "They do not establish source independence or prove a claim."
        ),
    ])
    return "\n".join(lines)
