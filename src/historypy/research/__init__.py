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
from historypy.research.engine import (
    ResearchFacets,
    ResearchQuery,
    ResearchSearchResult,
    execute_research_query,
)
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
from historypy.research.evidence_analysis import (
    ClaimEvidenceAnalysis,
    analyze_claim_evidence,
)
from historypy.research.geography import (
    PlaceDistance,
    great_circle_distance_km,
    places_within_radius,
)
from historypy.research.pipeline import (
    ResearchPipeline,
    ResearchReport,
    ResearchTask,
    ResearchTaskResult,
    render_research_report,
)
from historypy.research.profile import DatasetProfile, profile_dataset
from historypy.research.provenance import DatasetProvenanceReport, audit_dataset_provenance
from historypy.research.quality import (
    DatasetQualityReport,
    QualityFinding,
    assess_dataset_quality,
)
from historypy.research.query import SearchHit, events_overlapping, search_dataset
from historypy.research.report import render_claim_report
from historypy.research.search_index import DatasetSearchIndex
from historypy.research.semantic import SemanticSearchHit, SemanticSearchIndex
from historypy.research.source_audit import (
    SourceMetadataAudit,
    audit_dataset_sources,
    audit_source_record,
)
from historypy.research.source_comparison import (
    EventSourceComparison,
    EventSourceEntry,
    SourceEvidenceExcerpt,
    compare_event_sources,
)
from historypy.research.timeline import TimelineEntry, TimelineResult, timeline_for_dataset
from historypy.research.verification import ClaimAssessment, assess_claim

__all__ = [
    "analyze_claim_evidence",
    "append_research_action",
    "assess_claim",
    "assess_dataset_quality",
    "audit_dataset_provenance",
    "audit_dataset_sources",
    "audit_source_record",
    "ClaimAssessment",
    "ClaimEvidenceAnalysis",
    "claims_with_conflicting_evidence",
    "compare_event_sources",
    "compare_metrics",
    "content_hash",
    "DatasetProfile",
    "DatasetProvenanceReport",
    "DatasetQualityReport",
    "DatasetSearchIndex",
    "EntityMatchCandidate",
    "events_overlapping",
    "EventSourceComparison",
    "EventSourceEntry",
    "evidence_for_claim",
    "EvidenceSummary",
    "execute_research_query",
    "great_circle_distance_km",
    "MetricComparison",
    "MetricObservation",
    "PlaceDistance",
    "places_within_radius",
    "profile_dataset",
    "QualityFinding",
    "render_claim_report",
    "render_research_report",
    "ResearchAction",
    "ResearchFacets",
    "ResearchPipeline",
    "ResearchQuery",
    "ResearchReport",
    "ResearchSearchResult",
    "ResearchTask",
    "ResearchTaskResult",
    "search_dataset",
    "SearchHit",
    "SemanticSearchHit",
    "SemanticSearchIndex",
    "SourceEvidenceExcerpt",
    "SourceMetadataAudit",
    "suggest_entity_matches",
    "summarize_claim_evidence",
    "timeline_for_dataset",
    "TimelineEntry",
    "TimelineResult",
    "verify_research_audit_trail",
]
