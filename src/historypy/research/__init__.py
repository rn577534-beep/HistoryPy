"""Research utilities for evidence-aware historical analysis."""

from historypy.research.entity_resolution import (
    EntityMatchCandidate,
    suggest_entity_matches,
)
from historypy.research.evidence import (
    EvidenceSummary,
    claims_with_conflicting_evidence,
    evidence_for_claim,
    summarize_claim_evidence,
)
from historypy.research.geography import (
    PlaceDistance,
    great_circle_distance_km,
    places_within_radius,
)
from historypy.research.query import SearchHit, events_overlapping, search_dataset
from historypy.research.source_audit import (
    SourceMetadataAudit,
    audit_dataset_sources,
    audit_source_record,
)

__all__ = [
    "EntityMatchCandidate",
    "EvidenceSummary",
    "PlaceDistance",
    "SearchHit",
    "SourceMetadataAudit",
    "audit_dataset_sources",
    "audit_source_record",
    "claims_with_conflicting_evidence",
    "events_overlapping",
    "evidence_for_claim",
    "great_circle_distance_km",
    "places_within_radius",
    "search_dataset",
    "suggest_entity_matches",
    "summarize_claim_evidence",
]
