import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    SourceRecord,
)
from historypy.research import (
    claims_with_conflicting_evidence,
    evidence_for_claim,
    summarize_claim_evidence,
)


def evidence_dataset():
    sources = (
        SourceRecord(id="s1", title="Source one", source_type="primary"),
        SourceRecord(id="s2", title="Source two", source_type="secondary"),
        SourceRecord(id="s3", title="Source three", source_type="archival"),
    )
    claims = (
        HistoricalClaim(id="c1", statement="A claim with conflicting evidence"),
        HistoricalClaim(id="c2", statement="A claim with supporting evidence only"),
    )
    links = (
        EvidenceLink(claim_id="c1", source_id="s1", relation="supports"),
        EvidenceLink(claim_id="c1", source_id="s2", relation="contradicts"),
        EvidenceLink(claim_id="c1", source_id="s3", relation="contextualizes"),
        EvidenceLink(claim_id="c1", source_id="s1", relation="mentions"),
        EvidenceLink(claim_id="c2", source_id="s1", relation="supports"),
    )
    return HistoricalDataset(sources=sources, claims=claims, evidence=links)


def test_evidence_summary_keeps_support_and_contradiction_separate():
    summary = summarize_claim_evidence(evidence_dataset(), "c1")
    assert summary.supporting_source_ids == ("s1",)
    assert summary.contradicting_source_ids == ("s2",)
    assert summary.contextualizing_source_ids == ("s3",)
    assert summary.mentioning_source_ids == ("s1",)
    assert summary.has_conflicting_evidence
    assert summary.distinct_source_count == 3
    assert summary.link_count == 4


def test_claims_with_conflicting_evidence_only_returns_conflicts():
    summaries = claims_with_conflicting_evidence(evidence_dataset())
    assert [item.claim_id for item in summaries] == ["c1"]


def test_evidence_lookup_requires_a_known_claim():
    with pytest.raises(KeyError, match="Unknown claim"):
        evidence_for_claim(evidence_dataset(), "missing")
