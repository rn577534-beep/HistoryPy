"""Structured evidence coverage analysis without credibility or truth scoring."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.evidence import summarize_claim_evidence


@dataclass(frozen=True, slots=True)
class CitationCompletenessReport:
    """Dataset-wide locator, quotation, and URL coverage; not a truth score."""

    total_evidence_links: int
    links_with_locator: int
    links_with_quotation: int
    links_with_source_url: int
    links_with_locator_quotation_and_url: int
    missing_locator_indices: tuple[int, ...]
    missing_quotation_indices: tuple[int, ...]
    missing_source_url_indices: tuple[int, ...]

    @property
    def complete_citation_coverage(self) -> float | None:
        if not self.total_evidence_links:
            return None
        return self.links_with_locator_quotation_and_url / self.total_evidence_links


def audit_citation_completeness(
    dataset: HistoricalDataset,
) -> CitationCompletenessReport:
    """Audit whether each evidence link has a locator, quotation, and source URL.

    Evidence indices refer to their zero-based position in dataset.evidence.
    Completeness is a traceability measure, not an assessment of source quality.
    """
    sources = {source.id: source for source in dataset.sources}
    missing_locator = []
    missing_quotation = []
    missing_url = []
    with_locator = with_quotation = with_url = complete = 0
    for index, link in enumerate(dataset.evidence):
        has_locator = any((
            link.locator, link.page, link.paragraph, link.archive_shelfmark,
            link.url_fragment, link.transcription_line, link.timecode,
        ))
        has_quotation = bool(link.quotation and link.quotation.strip())
        source = sources.get(link.source_id)
        has_url = bool(source and source.url and source.url.strip())
        with_locator += int(has_locator)
        with_quotation += int(has_quotation)
        with_url += int(has_url)
        complete += int(has_locator and has_quotation and has_url)
        if not has_locator:
            missing_locator.append(index)
        if not has_quotation:
            missing_quotation.append(index)
        if not has_url:
            missing_url.append(index)
    return CitationCompletenessReport(
        total_evidence_links=len(dataset.evidence),
        links_with_locator=with_locator,
        links_with_quotation=with_quotation,
        links_with_source_url=with_url,
        links_with_locator_quotation_and_url=complete,
        missing_locator_indices=tuple(missing_locator),
        missing_quotation_indices=tuple(missing_quotation),
        missing_source_url_indices=tuple(missing_url),
    )


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
