"""Compact, transparent structural profile of a HistoryPy dataset."""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    record_counts: tuple[tuple[str, int], ...]
    geocoded_places: int
    places_without_coordinates: int
    events_with_sources: int
    events_without_sources: int
    claims_with_evidence: int
    claims_without_evidence: int
    validation_issue_count: int


def profile_dataset(dataset: HistoricalDataset) -> DatasetProfile:
    """Count records and selected coverage indicators; counts are not quality scores."""
    evidence_claims = {item.claim_id for item in dataset.evidence}
    return DatasetProfile(
        record_counts=tuple((name, len(getattr(dataset, name))) for name in (
            "sources", "claims", "events", "people", "places",
            "civilizations", "organizations", "relationships", "evidence",
        )),
        geocoded_places=sum(
            place.latitude is not None and place.longitude is not None
            for place in dataset.places
        ),
        places_without_coordinates=sum(
            place.latitude is None for place in dataset.places
        ),
        events_with_sources=sum(bool(event.source_ids) for event in dataset.events),
        events_without_sources=sum(not event.source_ids for event in dataset.events),
        claims_with_evidence=sum(claim.id in evidence_claims for claim in dataset.claims),
        claims_without_evidence=sum(claim.id not in evidence_claims for claim in dataset.claims),
        validation_issue_count=len(dataset.validate()),
    )
