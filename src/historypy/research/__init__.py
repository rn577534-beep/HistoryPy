"""Research utilities for evidence-aware historical analysis."""

from historypy.research.alias_import import import_wikidata_alias_candidates
from historypy.research.alias_registry import AliasAssertion, AliasMatch, AliasRegistry
from historypy.research.audit_trail import (
    ResearchAction,
    append_research_action,
    content_hash,
    verify_research_audit_trail,
)
from historypy.research.bm25 import BM25SearchHit, BM25SearchIndex
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
from historypy.research.entropy import (
    EntropyReport,
    evidence_relation_entropy,
    shannon_entropy,
    source_type_entropy,
)
from historypy.research.evidence import (
    EvidenceSummary,
    claims_with_conflicting_evidence,
    evidence_for_claim,
    summarize_claim_evidence,
)
from historypy.research.evidence_analysis import (
    CitationCompletenessReport,
    ClaimEvidenceAnalysis,
    analyze_claim_evidence,
    audit_citation_completeness,
)
from historypy.research.geography import (
    PlaceDistance,
    great_circle_distance_km,
    places_within_radius,
)
from historypy.research.hybrid import (
    DecomposedQuery,
    EntityAliasMatch,
    EntityAliasSuggestion,
    EntityAwareSearchIndex,
    HybridSearchHit,
    HybridSearchIndex,
    decompose_research_question,
)
from historypy.research.network_analysis import (
    GraphCentralityReport,
    NodeCentrality,
    analyze_graph_centrality,
)
from historypy.research.pipeline import (
    ResearchPipeline,
    ResearchReport,
    ResearchTask,
    ResearchTaskResult,
    render_research_report,
)
from historypy.research.profile import DatasetProfile, profile_dataset
from historypy.research.probabilistic_evidence import (
    BayesianUpdate,
    DempsterShaferResult,
    bayesian_update,
    combine_dempster_shafer,
)
from historypy.research.provenance import DatasetProvenanceReport, audit_dataset_provenance
from historypy.research.quality import (
    DatasetQualityReport,
    QualityFinding,
    assess_dataset_quality,
)
from historypy.research.query import SearchHit, events_overlapping, search_dataset
from historypy.research.question_planner import (
    EntityMentionCandidate,
    HopEvidenceReview,
    PredicateCandidate,
    QuestionExecutionReport,
    QuestionPathReview,
    QuestionPlan,
    TemporalPathSelection,
    execute_question_plan,
    plan_research_question,
    select_paths_by_temporal_policy,
)
from historypy.research.relationship_paths import (
    RelationshipPath,
    RelationshipPathQuery,
    RelationshipPathSearchReport,
    RelationshipPathStep,
    find_relationship_paths,
)
from historypy.research.report import render_claim_report
from historypy.research.search_index import DatasetSearchIndex
from historypy.research.semantic import SemanticSearchHit, SemanticSearchIndex
from historypy.research.similarity import NameSimilarityScores, compare_names
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
    render_event_source_comparison,
)
from historypy.research.source_dependency_registry import (
    DependencyReviewStatus,
    DependencyType,
    SourceDependencyAssertion,
    SourceDependencyRegistry,
)
from historypy.research.source_independence import (
    ClaimSourceIndependenceReport,
    DatasetSourceIndependenceReport,
    DependencyCluster,
    SourceDependency,
    SourceSetIndependenceReport,
    analyze_claim_source_independence,
    analyze_source_set_independence,
    audit_source_independence,
)
from historypy.research.temporal_sensitivity import (
    TemporalSensitivityReport,
    analyze_temporal_sensitivity,
)
from historypy.research.timeline import TimelineEntry, TimelineResult, timeline_for_dataset
from historypy.research.verification import ClaimAssessment, assess_claim
from historypy.research.visualization import (
    dataset_graph_data,
    export_visualization_json,
    render_visualization_html,
    timeline_visualization_data,
    to_geojson,
    to_graphviz_dot,
)
from historypy.research.weighted_paths import (
    WeightedPathReport,
    WeightedRelationshipPath,
    find_weighted_relationship_paths,
)

__all__ = [
    "AliasAssertion",
    "AliasMatch",
    "AliasRegistry",
    "BM25SearchHit",
    "BM25SearchIndex",
    "BayesianUpdate",
    "DempsterShaferResult",
    "CitationCompletenessReport",
    "ClaimAssessment",
    "ClaimEvidenceAnalysis",
    "ClaimSourceIndependenceReport",
    "DatasetProfile",
    "DatasetProvenanceReport",
    "DatasetQualityReport",
    "DatasetSearchIndex",
    "DatasetSourceIndependenceReport",
    "DecomposedQuery",
    "DependencyCluster",
    "DependencyReviewStatus",
    "DependencyType",
    "EntityAliasMatch",
    "EntityAliasSuggestion",
    "EntityAwareSearchIndex",
    "EntityMatchCandidate",
    "EntityMentionCandidate",
    "EntropyReport",
    "EventSourceComparison",
    "EventSourceEntry",
    "EvidenceSummary",
    "GraphCentralityReport",
    "HopEvidenceReview",
    "HybridSearchHit",
    "HybridSearchIndex",
    "MetricComparison",
    "MetricObservation",
    "NameSimilarityScores",
    "NodeCentrality",
    "PlaceDistance",
    "PredicateCandidate",
    "QualityFinding",
    "QuestionExecutionReport",
    "QuestionPathReview",
    "QuestionPlan",
    "RelationshipPath",
    "RelationshipPathQuery",
    "RelationshipPathSearchReport",
    "RelationshipPathStep",
    "ResearchAction",
    "ResearchFacets",
    "ResearchPipeline",
    "ResearchQuery",
    "ResearchReport",
    "ResearchSearchResult",
    "ResearchTask",
    "ResearchTaskResult",
    "SearchHit",
    "SemanticSearchHit",
    "SemanticSearchIndex",
    "SourceDependency",
    "SourceDependencyAssertion",
    "SourceDependencyRegistry",
    "SourceEvidenceExcerpt",
    "SourceMetadataAudit",
    "SourceSetIndependenceReport",
    "TemporalPathSelection",
    "TemporalSensitivityReport",
    "TimelineEntry",
    "TimelineResult",
    "WeightedPathReport",
    "WeightedRelationshipPath",
    "analyze_claim_evidence",
    "bayesian_update",
    "combine_dempster_shafer",
    "analyze_claim_source_independence",
    "analyze_graph_centrality",
    "analyze_source_set_independence",
    "analyze_temporal_sensitivity",
    "append_research_action",
    "assess_claim",
    "assess_dataset_quality",
    "audit_citation_completeness",
    "audit_dataset_provenance",
    "audit_dataset_sources",
    "audit_source_independence",
    "audit_source_record",
    "claims_with_conflicting_evidence",
    "compare_event_sources",
    "compare_metrics",
    "compare_names",
    "content_hash",
    "dataset_graph_data",
    "decompose_research_question",
    "events_overlapping",
    "evidence_for_claim",
    "evidence_relation_entropy",
    "execute_question_plan",
    "execute_research_query",
    "export_visualization_json",
    "find_relationship_paths",
    "find_weighted_relationship_paths",
    "great_circle_distance_km",
    "import_wikidata_alias_candidates",
    "places_within_radius",
    "plan_research_question",
    "profile_dataset",
    "render_claim_report",
    "render_event_source_comparison",
    "render_research_report",
    "render_visualization_html",
    "search_dataset",
    "select_paths_by_temporal_policy",
    "shannon_entropy",
    "source_type_entropy",
    "suggest_entity_matches",
    "summarize_claim_evidence",
    "timeline_for_dataset",
    "timeline_visualization_data",
    "to_geojson",
    "to_graphviz_dot",
    "verify_research_audit_trail",

]
