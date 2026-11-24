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
    lines.extend(["", "## Scope and interpretation", "",
                  claim.scope_note or "No scope note supplied.",
                  "", claim.interpretation_note or "No interpretation note supplied.",
                  "", "## Research limitations", "",
                  "- Evidence links are researcher-entered metadata.",
                  "- Repeated accounts may not be independent sources.",
                  "- Missing evidence links do not prove a claim false.",
                  "- Review the cited source and its exact locator before relying on it.", ""])
    return "\n".join(lines)
