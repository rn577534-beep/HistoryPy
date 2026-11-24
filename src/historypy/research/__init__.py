"""Research utilities for evidence-aware historical analysis."""

from historypy.research.evidence import (
    EvidenceSummary,
    claims_with_conflicting_evidence,
    evidence_for_claim,
    summarize_claim_evidence,
)
from historypy.research.entity_resolution import EntityMatchCandidate, suggest_entity_matches
from historypy.research.query import SearchHit, events_overlapping, search_dataset

__all__ = [
    "EntityMatchCandidate",
    "EvidenceSummary",
    "SearchHit",
    "claims_with_conflicting_evidence",
    "events_overlapping",
    "evidence_for_claim",
    "search_dataset",
    "summarize_claim_evidence",
    "suggest_entity_matches",
]
