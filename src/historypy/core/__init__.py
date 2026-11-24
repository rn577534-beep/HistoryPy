"""Core data structures shared across HistoryPy modules."""

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

__all__ = [
    "EvidenceLink",
    "HistoricalCivilization",
    "HistoricalClaim",
    "HistoricalDataset",
    "HistoricalDate",
    "HistoricalEvent",
    "HistoricalOrganization",
    "HistoricalPerson",
    "HistoricalPlace",
    "HistoricalRelationship",
    "SourceRecord",
    "ValidationIssue",
]
