"""Federated cross-check discovery for a single historical claim.

Provider hits are discovery candidates, not automatically accepted evidence.
A researcher must inspect each result, its underlying document, and its
provenance before linking it to a claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from historypy.core.dataset import HistoricalDataset
from historypy.integrations.aggregation import (
    AggregationReport,
    DuplicateCandidateGroup,
    MetadataConflict,
    SearchProvider,
    compare_metadata,
    find_duplicate_candidates,
    search_all,
)


@dataclass(frozen=True, slots=True)
class CrossVerificationReport:
    claim_id: str
    query: str
    provider_report: AggregationReport
    duplicate_candidates: tuple[DuplicateCandidateGroup, ...]
    metadata_conflicts: tuple[MetadataConflict, ...]
    notes: tuple[str, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.provider_report.records)

    @property
    def successful_provider_count(self) -> int:
        return self.provider_report.successful_provider_count


def cross_verify_claim(
    dataset: HistoricalDataset,
    claim_id: str,
    providers: Sequence[SearchProvider],
    *,
    query: str | None = None,
    limit_per_provider: int = 10,
    max_workers: int | None = None,
) -> CrossVerificationReport:
    """Search multiple catalogs/news sources for a claim without auto-importing.

    The default query is the exact claim statement. Search results are not
    automatically treated as supporting or contradicting evidence. Duplicate
    groups and metadata disagreements are review aids only.
    """
    dataset.require_valid()
    claim = next((item for item in dataset.claims if item.id == claim_id), None)
    if claim is None:
        raise KeyError(f"Unknown claim id: {claim_id}")
    search_query = query if query is not None else claim.statement
    if not isinstance(search_query, str) or not search_query.strip():
        raise ValueError("query cannot be empty")

    result = search_all(
        providers,
        search_query,
        limit_per_provider=limit_per_provider,
        max_workers=max_workers,
    )
    records = result.records
    notes = [
        "Search hits are discovery candidates and are not automatically attached as evidence to the claim.",
        "A result's title, snippet, and metadata do not verify the underlying historical assertion.",
        "Different providers may index the same original source; provider count is not independent corroboration.",
        "Inspect source provenance, full context, date, authorship, and rights before importing a record.",
    ]
    if result.failures:
        notes.append("Some providers failed; an incomplete search must not be treated as absence of evidence.")
    if not records:
        notes.append("No candidates were returned; this does not prove that no relevant sources exist.")
    return CrossVerificationReport(
        claim_id=claim_id,
        query=search_query.strip(),
        provider_report=result,
        duplicate_candidates=find_duplicate_candidates(records),
        metadata_conflicts=compare_metadata(records),
        notes=tuple(notes),
    )


__all__ = ["CrossVerificationReport", "cross_verify_claim"]
