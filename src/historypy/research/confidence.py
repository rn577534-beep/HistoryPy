"""Conservative, auditable documentation assessment for historical claims.

The report describes the state of recorded evidence and its traceability. It
is not a probability that a claim is true and must not be presented as one.
"""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.citations import audit_evidence_citations
from historypy.research.evidence_analysis import analyze_claim_evidence


@dataclass(frozen=True, slots=True)
class ClaimConfidenceReport:
    claim_id: str
    documentation_score: float | None
    documentation_band: str
    evidence_status: str
    evidence_link_count: int
    distinct_source_count: int
    citation_coverage: float | None
    locator_coverage: float | None
    source_independence_status: str
    supporting_source_ids: tuple[str, ...]
    contradicting_source_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def is_truth_probability(self) -> bool:
        return False


def analyze_claim_confidence(
    dataset: HistoricalDataset,
    claim_id: str,
) -> ClaimConfidenceReport:
    """Summarize evidence documentation; never infer a truth probability.

    The 0-100 documentation score is a simple, transparent average of:
    citation traceability (50%), locator coverage (30%), and capped source
    count coverage (20%). Unknown source independence is surfaced separately
    and does not earn a corroboration bonus. This score measures documentation
    completeness only, not historical accuracy or source reliability.
    """
    analysis = analyze_claim_evidence(dataset, claim_id)
    audit = audit_evidence_citations(dataset, claim_id)
    if not analysis.total_links:
        return ClaimConfidenceReport(
            claim_id=claim_id,
            documentation_score=None,
            documentation_band="not_assessable",
            evidence_status=analysis.assessment_status,
            evidence_link_count=0,
            distinct_source_count=0,
            citation_coverage=None,
            locator_coverage=None,
            source_independence_status=analysis.source_independence.status,
            supporting_source_ids=(),
            contradicting_source_ids=(),
            limitations=(
                "No evidence links are recorded for this claim.",
                "No historical-truth probability is calculated.",
            ),
        )

    citation_coverage = audit.coverage or 0.0
    locator_coverage = analysis.locator_coverage or 0.0
    source_coverage = min(analysis.distinct_source_count, 3) / 3
    score = round(
        100 * (
            0.50 * citation_coverage
            + 0.30 * locator_coverage
            + 0.20 * source_coverage
        ),
        2,
    )
    if analysis.assessment_status == "mixed":
        band = "mixed_evidence"
    elif score >= 80 and analysis.assessment_status == "supported":
        band = "well_documented"
    elif score >= 50:
        band = "partially_documented"
    else:
        band = "weakly_documented"

    limitations = [
        "The documentation score is not a probability that the claim is true.",
        "Source count does not establish source independence.",
        "Recorded support/contradiction labels are researcher-entered metadata.",
        "Source authenticity, context, bias, and interpretation require human review.",
    ]
    if analysis.source_independence.status not in {"known_dependence"}:
        limitations.append(
            "Source independence is unknown or only partly documented; do not treat "
            "multiple records as independent corroboration."
        )
    if analysis.assessment_status == "mixed":
        limitations.append(
            "Both supporting and contradicting evidence are recorded; inspect both sides."
        )
    return ClaimConfidenceReport(
        claim_id=claim_id,
        documentation_score=score,
        documentation_band=band,
        evidence_status=analysis.assessment_status,
        evidence_link_count=analysis.total_links,
        distinct_source_count=analysis.distinct_source_count,
        citation_coverage=audit.coverage,
        locator_coverage=analysis.locator_coverage,
        source_independence_status=analysis.source_independence.status,
        supporting_source_ids=tuple(sorted({
            source_id for source_id in analysis.source_independence.evidence_source_ids
            if any(
                link.claim_id == claim_id and link.source_id == source_id
                and link.relation == "supports"
                for link in dataset.evidence
            )
        })),
        contradicting_source_ids=tuple(sorted({
            source_id for source_id in analysis.source_independence.evidence_source_ids
            if any(
                link.claim_id == claim_id and link.source_id == source_id
                and link.relation == "contradicts"
                for link in dataset.evidence
            )
        })),
        limitations=tuple(limitations),
    )


__all__ = ["ClaimConfidenceReport", "analyze_claim_confidence"]
