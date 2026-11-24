"""Structured evidence coverage analysis without credibility or truth scoring."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.evidence import summarize_claim_evidence


@dataclass(frozen=True, slots=True)
class ClaimEvidenceAnalysis:
    """Auditable evidence coverage for one claim; counts are not quality scores."""

    claim_id: str
    relation_counts: tuple[tuple[str, int], ...]
    source_type_counts: tuple[tuple[str, int], ...]
    distinct_source_count: int
    links_missing_locators: int
    total_links: int
    assessment_status: str

    @property
    def locator_coverage(self) -> float | None:
        """Fraction of links with a structured or free-form locator; None if empty."""
        if not self.total_links:
            return None
        return (self.total_links - self.links_missing_locators) / self.total_links


def analyze_claim_evidence(
    dataset: HistoricalDataset, claim_id: str
) -> ClaimEvidenceAnalysis:
    """Report recorded evidence relations, source types, and locator completeness.

    Source type is descriptive metadata only. This function does not infer
    independence, authenticity, reliability, or historical truth.
    """
    summary = summarize_claim_evidence(dataset, claim_id)
    links = tuple(link for link in dataset.evidence if link.claim_id == claim_id)
    relation_counts = Counter(link.relation for link in links)
    sources = {source.id: source for source in dataset.sources}
    source_types = Counter(
        sources[link.source_id].source_type
        for link in links
        if link.source_id in sources
    )
    missing_locators = sum(
        not any((
            link.locator, link.page, link.paragraph, link.archive_shelfmark,
            link.url_fragment, link.transcription_line, link.timecode,
        ))
        for link in links
    )
    if summary.supporting_source_ids and summary.contradicting_source_ids:
        status = "mixed"
    elif summary.supporting_source_ids:
        status = "supported"
    elif summary.contradicting_source_ids:
        status = "contradicted"
    else:
        status = "insufficient"
    return ClaimEvidenceAnalysis(
        claim_id=claim_id,
        relation_counts=tuple(sorted(relation_counts.items())),
        source_type_counts=tuple(sorted(source_types.items())),
        distinct_source_count=summary.distinct_source_count,
        links_missing_locators=missing_locators,
        total_links=len(links),
        assessment_status=status,
    )
