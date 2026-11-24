"""Evidence retrieval and conflict summaries without automated truth scoring."""

from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import EvidenceLink


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    """A transparent count and source list for one claim's evidence links."""

    claim_id: str
    supporting_source_ids: tuple[str, ...]
    contradicting_source_ids: tuple[str, ...]
    contextualizing_source_ids: tuple[str, ...]
    mentioning_source_ids: tuple[str, ...]
    link_count: int

    @property
    def has_conflicting_evidence(self) -> bool:
        """Whether at least one source is linked as supporting and one as contradicting."""
        return bool(self.supporting_source_ids and self.contradicting_source_ids)

    @property
    def distinct_source_count(self) -> int:
        """Count unique sources across all evidence relationships."""
        return len(set(
            self.supporting_source_ids
            + self.contradicting_source_ids
            + self.contextualizing_source_ids
            + self.mentioning_source_ids
        ))


def evidence_for_claim(
    dataset: HistoricalDataset, claim_id: str
) -> tuple[EvidenceLink, ...]:
    """Return all evidence links for a known claim, preserving dataset order."""
    if not any(claim.id == claim_id for claim in dataset.claims):
        raise KeyError(f"Unknown claim id: {claim_id}")
    return tuple(link for link in dataset.evidence if link.claim_id == claim_id)


def summarize_claim_evidence(
    dataset: HistoricalDataset, claim_id: str
) -> EvidenceSummary:
    """Summarize source relationships without ranking truth or source quality."""
    links = evidence_for_claim(dataset, claim_id)

    def unique_sources(relation: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            link.source_id for link in links if link.relation == relation
        ))

    return EvidenceSummary(
        claim_id=claim_id,
        supporting_source_ids=unique_sources("supports"),
        contradicting_source_ids=unique_sources("contradicts"),
        contextualizing_source_ids=unique_sources("contextualizes"),
        mentioning_source_ids=unique_sources("mentions"),
        link_count=len(links),
    )


def claims_with_conflicting_evidence(
    dataset: HistoricalDataset,
) -> tuple[EvidenceSummary, ...]:
    """Return summaries for claims with both supporting and contradicting links."""
    summaries = (
        summarize_claim_evidence(dataset, claim.id) for claim in dataset.claims
    )
    return tuple(item for item in summaries if item.has_conflicting_evidence)
