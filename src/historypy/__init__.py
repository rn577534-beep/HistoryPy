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

__version__ = "0.1.0"

__all__ = [
    "EvidenceLink", "HistoricalClaim", "HistoricalCivilization", "HistoricalDataset",
    "HistoricalDate", "HistoricalEvent", "HistoricalOrganization", "HistoricalPerson",
    "HistoricalPlace", "HistoricalRelationship", "RelationshipGraph", "SourceRecord",
    "ValidationIssue", "__version__",
]
