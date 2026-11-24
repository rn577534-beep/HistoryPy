"""Reproducible Markdown research reports with explicit evidence and uncertainty."""

from __future__ import annotations

from historypy.core.dataset import HistoricalDataset
from historypy.research.evidence import summarize_claim_evidence
from historypy.research.verification import assess_claim


def render_claim_report(dataset: HistoricalDataset, claim_id: str) -> str:
    """Render a source-linked report for one claim without inventing conclusions."""
    dataset.require_valid()
    claim = next((item for item in dataset.claims if item.id == claim_id), None)
    if claim is None:
        raise KeyError(f"Unknown claim id: {claim_id}")
    assessment = assess_claim(dataset, claim_id)
    summary = summarize_claim_evidence(dataset, claim_id)
    sources = {source.id: source for source in dataset.sources}
    lines = [
        f"# Research note: {claim.statement}", "",
        f"- Claim ID: `{claim.id}`",
        f"- Evidence assessment: **{assessment.status}**",
        f"- Evidence links: {summary.link_count}",
        f"- Distinct linked sources: {summary.distinct_source_count}", "",
        "## Assessment", "", assessment.explanation,
        "This classification reflects recorded evidence-link labels only. It does not assess",
        "source reliability, independence, authenticity, or historical truth.", "",
        "## Supporting evidence", "",
    ]
    for source_id in assessment.supporting_source_ids:
        source = sources[source_id]
        lines.append(f"- **{source.title}** (`{source.id}`; {source.source_type})")
        if source.url:
            lines.append(f"  - URL: {source.url}")
    if not assessment.supporting_source_ids:
        lines.append("- No supporting evidence links are recorded.")
    lines.extend(["", "## Contradicting evidence", ""])
    for source_id in assessment.contradicting_source_ids:
        source = sources[source_id]
        lines.append(f"- **{source.title}** (`{source.id}`; {source.source_type})")
        if source.url:
            lines.append(f"  - URL: {source.url}")
    if not assessment.contradicting_source_ids:
        lines.append("- No contradicting evidence links are recorded.")
    lines.extend(["", "## Other linked sources", ""])
    other_ids = tuple(dict.fromkeys(
        assessment.contextualizing_source_ids + assessment.mentioning_source_ids
    ))
    for source_id in other_ids:
        source = sources[source_id]
        lines.append(f"- {source.title} (`{source.id}`)")
    if not other_ids:
        lines.append("- None recorded.")
    lines.extend(["", "## Recorded quotations and citation locators", ""])
    claim_links = tuple(link for link in dataset.evidence if link.claim_id == claim_id)
    for link in claim_links:
        source = sources[link.source_id]
        lines.append(f"- **{source.title}** ({link.relation}; source ID: `{source.id}`)")
        if link.quotation:
            lines.append(f"  - Quotation: {link.quotation}")
        locator_parts = [
            f"locator: {link.locator}" if link.locator else None,
            f"page: {link.page}" if link.page else None,
            f"paragraph: {link.paragraph}" if link.paragraph else None,
            f"archive shelfmark: {link.archive_shelfmark}" if link.archive_shelfmark else None,
            f"URL fragment: {link.url_fragment}" if link.url_fragment else None,
            f"transcription line: {link.transcription_line}" if link.transcription_line else None,
            f"timecode: {link.timecode}" if link.timecode else None,
        ]
        recorded_locators = [part for part in locator_parts if part]
        lines.append(
            f"  - Citation location: {'; '.join(recorded_locators)}"
            if recorded_locators else "  - Citation location: not recorded"
        )
        if source.url:
            lines.append(f"  - Source URL: {source.url}")
        if link.interpretation_note:
            lines.append(f"  - Researcher note: {link.interpretation_note}")
    if not claim_links:
        lines.append("- No evidence links are recorded for this claim.")
    lines.extend(["", "## Scope and interpretation", "",
                  claim.scope_note or "No scope note supplied.",
                  "", claim.interpretation_note or "No interpretation note supplied.",
                  "", "## Research limitations", "",
                  "- Evidence links are researcher-entered metadata.",
                  "- Repeated accounts may not be independent sources.",
                  "- Missing evidence links do not prove a claim false.",
                  "- Review the cited source and its exact locator before relying on it.", ""])
    return "\n".join(lines)
