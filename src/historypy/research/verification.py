"""Transparent claim-evidence assessment; never an automated truth detector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from historypy.core.dataset import HistoricalDataset
from historypy.research.evidence import summarize_claim_evidence

AssessmentStatus = Literal["supported", "contradicted", "mixed", "insufficient"]


@dataclass(frozen=True, slots=True)
class ClaimAssessment:
    claim_id: str
    status: AssessmentStatus
    supporting_source_ids: tuple[str, ...]
    contradicting_source_ids: tuple[str, ...]
    contextualizing_source_ids: tuple[str, ...]
    mentioning_source_ids: tuple[str, ...]
    explanation: str


def assess_claim(dataset: HistoricalDataset, claim_id: str) -> ClaimAssessment:
    """Classify only the recorded direction of evidence links, not source quality."""
    summary = summarize_claim_evidence(dataset, claim_id)
    support = summary.supporting_source_ids
    contradict = summary.contradicting_source_ids
    if support and contradict:
        status: AssessmentStatus = "mixed"
        explanation = "Recorded links are mixed; this classification is not proof either way."
    elif support:
        status = "supported"
        explanation = "At least one source is linked as supporting; this is not proof."
    elif contradict:
        status = "contradicted"
        explanation = "At least one source is linked as contradicting; this is not disproof."
    else:
        status = "insufficient"
        explanation = "No supporting or contradicting evidence links are recorded."
    return ClaimAssessment(
        claim_id, status, support, contradict, summary.contextualizing_source_ids,
        summary.mentioning_source_ids, explanation,
    )
