"""Research utilities for evidence-aware historical analysis."""

from historypy.research.audit_trail import (
    ResearchAction,
    append_research_action,
    content_hash,
    verify_research_audit_trail,
)
from historypy.research.comparison import (
    MetricComparison,
    MetricObservation,
    compare_metrics,
)
from historypy.research.entity_resolution import EntityMatchCandidate, suggest_entity_matches
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
from historypy.research.profile import DatasetProfile, profile_dataset
from historypy.research.quality import DatasetQualityReport, QualityFinding, assess_dataset_quality
from historypy.research.query import SearchHit, events_overlapping, search_dataset
from historypy.research.search_index import DatasetSearchIndex
from historypy.research.source_audit import (
    SourceMetadataAudit,
    audit_dataset_sources,
    audit_source_record,
)

__all__ = [
    "DatasetProfile", "DatasetQualityReport", "DatasetSearchIndex",
    "EntityMatchCandidate", "EvidenceSummary", "MetricComparison",
    "MetricObservation", "PlaceDistance", "QualityFinding", "ResearchAction",
    "SearchHit", "SourceMetadataAudit", "append_research_action",
    "assess_dataset_quality", "audit_dataset_sources", "audit_source_record",
    "claims_with_conflicting_evidence", "compare_metrics", "content_hash",
    "events_overlapping", "evidence_for_claim", "great_circle_distance_km",
    "places_within_radius", "profile_dataset", "search_dataset",
    "suggest_entity_matches", "summarize_claim_evidence",
    "verify_research_audit_trail",
]
