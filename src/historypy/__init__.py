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
    save_dataset,
)

__version__ = "0.1.0"

__all__ = [
    "EvidenceLink", "HistoricalClaim", "HistoricalCivilization", "HistoricalDataset",
    "HistoricalDate", "HistoricalEvent", "HistoricalOrganization", "HistoricalPerson",
    "HistoricalPlace", "HistoricalRelationship", "RelationshipGraph", "SourceRecord",
    "ValidationIssue", "dataset_from_dict", "dataset_from_json", "dataset_to_dict",
    "dataset_to_json", "load_dataset", "save_dataset", "__version__",
]
