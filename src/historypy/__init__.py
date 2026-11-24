"""HistoryPy: evidence-aware tools for historical research."""

from historypy.core.dataset import HistoricalDataset, ValidationIssue
from historypy.core.entities import (
    HistoricalCivilization,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
)
from historypy.core.models import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)
from historypy.graph import RelationshipGraph
from historypy.io import (
    dataset_from_dict,
    dataset_from_json,
    dataset_to_dict,
    dataset_to_json,
    load_dataset,
    load_dataset_csv_bundle,
    save_dataset,
    save_dataset_csv_bundle,
)
from historypy.research import (
    DatasetProfile,
    DatasetQualityReport,
    DatasetSearchIndex,
    EntityMatchCandidate,
    EvidenceSummary,
    MetricComparison,
    MetricObservation,
    PlaceDistance,
    QualityFinding,
    ResearchAction,
    SearchHit,
    SourceMetadataAudit,
    append_research_action,
    assess_dataset_quality,
    audit_dataset_sources,
    audit_source_record,
    claims_with_conflicting_evidence,
    compare_metrics,
    content_hash,
    events_overlapping,
    evidence_for_claim,
    great_circle_distance_km,
    places_within_radius,
    profile_dataset,
    search_dataset,
    suggest_entity_matches,
    summarize_claim_evidence,
    verify_research_audit_trail,
)

__version__ = "0.2.0"

__all__ = [
    "DatasetProfile", "DatasetQualityReport", "DatasetSearchIndex",
    "EntityMatchCandidate", "EvidenceLink", "EvidenceSummary",
    "HistoricalCivilization", "HistoricalClaim", "HistoricalDataset",
    "HistoricalDate", "HistoricalEvent", "HistoricalOrganization",
    "HistoricalPerson", "HistoricalPlace", "HistoricalRelationship",
    "MetricComparison", "MetricObservation", "PlaceDistance", "QualityFinding",
    "RelationshipGraph", "ResearchAction", "SearchHit", "SourceMetadataAudit",
    "SourceRecord", "ValidationIssue", "__version__", "append_research_action",
    "assess_dataset_quality", "audit_dataset_sources", "audit_source_record",
    "claims_with_conflicting_evidence", "compare_metrics", "content_hash",
    "dataset_from_dict", "dataset_from_json", "dataset_to_dict", "dataset_to_json",
    "events_overlapping", "evidence_for_claim", "great_circle_distance_km",
    "load_dataset", "load_dataset_csv_bundle", "places_within_radius",
    "profile_dataset", "save_dataset", "save_dataset_csv_bundle",
    "search_dataset", "suggest_entity_matches", "summarize_claim_evidence",
    "verify_research_audit_trail",
]
