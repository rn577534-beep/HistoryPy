import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    SourceRecord,
    audit_evidence_citations,
    format_evidence_citation,
)


def make_dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord(
                id="primary",
                title="A Primary Record",
                source_type="primary",
                creator="Archive Office",
                publication_date="1920-01-01",
                publisher="National Archive",
                url="https://example.org/record/1",
                accessed_on="2026-11-27",
            ),
            SourceRecord(
                id="missing",
                title="An Incomplete Record",
                source_type="secondary",
                url="ftp://example.org/file",
            ),
        ),
        claims=(
            HistoricalClaim(id="claim-1", statement="A testable claim."),
            HistoricalClaim(id="claim-2", statement="A second claim."),
        ),
        evidence=(
            EvidenceLink(
                claim_id="claim-1",
                source_id="primary",
                relation="supports",
                quotation="A recorded excerpt.",
                page="14",
            ),
            EvidenceLink(
                claim_id="claim-1",
                source_id="missing",
                relation="contradicts",
            ),
        ),
    )


def test_audit_reports_complete_and_incomplete_citations():
    report = audit_evidence_citations(make_dataset())

    assert report.total_links == 2
    assert report.complete_links == 1
    assert report.coverage == 0.5
    assert not report.is_complete
    assert [(item.evidence_index, item.code) for item in report.findings] == [
        (1, "missing_locator"),
        (1, "missing_quotation"),
        (1, "invalid_source_url"),
    ]


def test_audit_can_be_scoped_to_one_claim():
    report = audit_evidence_citations(make_dataset(), "claim-1")

    assert report.total_links == 2
    assert report.complete_links == 1
    assert all(item.claim_id == "claim-1" for item in report.findings)


def test_audit_rejects_unknown_claim():
    with pytest.raises(KeyError, match="Unknown claim"):
        audit_evidence_citations(make_dataset(), "not-a-claim")


def test_empty_audit_has_no_coverage_and_is_not_complete():
    dataset = HistoricalDataset(
        sources=(),
        claims=(HistoricalClaim(id="claim-1", statement="No evidence yet."),),
        evidence=(),
    )

    report = audit_evidence_citations(dataset, "claim-1")

    assert report.total_links == 0
    assert report.coverage is None
    assert not report.is_complete


def test_citation_formatter_uses_only_recorded_metadata():
    citation = format_evidence_citation(make_dataset(), 0)

    assert "Archive Office" in citation
    assert "*A Primary Record*" in citation
    assert "National Archive 1920-01-01" in citation
    assert "p. 14" in citation
    assert "https://example.org/record/1" in citation
    assert "source ID: primary" in citation


def test_citation_formatter_validates_index():
    with pytest.raises(IndexError):
        format_evidence_citation(make_dataset(), 10)
    with pytest.raises(TypeError):
        format_evidence_citation(make_dataset(), True)
