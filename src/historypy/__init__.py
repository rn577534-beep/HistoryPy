"""HistoryPy: evidence-aware tools for historical research."""

from historypy.core.dataset import HistoricalDataset, ValidationIssue
from historypy.core.entities import (
    HistoricalCivilization, HistoricalOrganization, HistoricalPerson,
    HistoricalPlace, HistoricalRelationship,
)
from historypy.core.models import (
    EvidenceLink, HistoricalClaim, HistoricalDate, HistoricalEvent, SourceRecord,
)
from historypy.graph import RelationshipGraph
from historypy.io import (
    dataset_from_dict, dataset_from_json, dataset_to_dict, dataset_to_json,
    load_dataset, save_dataset,
)
from historypy.research import (
    EvidenceSummary, SearchHit, claims_with_conflicting_evidence,
    events_overlapping, evidence_for_claim, search_dataset,
    summarize_claim_evidence,
)

__version__ = "0.1.0"

__all__ = [
    "EvidenceLink", "EvidenceSummary", "HistoricalClaim", "HistoricalCivilization",
    "HistoricalDataset", "HistoricalDate", "HistoricalEvent", "HistoricalOrganization",
    "HistoricalPerson", "HistoricalPlace", "HistoricalRelationship", "RelationshipGraph",
    "SearchHit", "SourceRecord", "ValidationIssue", "claims_with_conflicting_evidence",
    "dataset_from_dict", "dataset_from_json", "dataset_to_dict", "dataset_to_json",
    "events_overlapping", "evidence_for_claim", "load_dataset", "save_dataset",
    "search_dataset", "summarize_claim_evidence", "__version__",
]
