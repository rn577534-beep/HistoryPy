import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    SourceRecord,
    analyze_claim_confidence,
    verify_source_urls,
)
from historypy.research import source_verification


def sample_dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord(
                "s1", "Source One", "primary",
                url="https://example.org/source",
            ),
            SourceRecord(
                "s2", "Source Two", "secondary",
                url="https://example.org/second",
            ),
        ),
        claims=(HistoricalClaim("c1", "A test claim"),),
        evidence=(
            EvidenceLink(
                "c1", "s1", "supports",
                quotation="A precise quoted sentence.", page="10",
            ),
            EvidenceLink(
                "c1", "s2", "contradicts",
                quotation="A different quoted sentence.", locator="section 2",
            ),
        ),
    )


def test_verify_source_urls_deduplicates_by_source(monkeypatch):
    calls = []

    def fake_fetch(source_id, url, quotations, *, timeout, max_bytes):
        calls.append((source_id, url, quotations))
        return source_verification.SourceVerificationResult(
            source_id, url, "reachable", 200, "text/html", "found", url,
        )

    monkeypatch.setattr(source_verification, "_fetch_source", fake_fetch)
    report = verify_source_urls(sample_dataset(), "c1")

    assert len(calls) == 2
    assert report.reachable_count == 2
    assert report.quotation_match_count == 2
    assert report.failed_count == 0


def test_verify_source_urls_reports_missing_url():
    dataset = HistoricalDataset(
        sources=(SourceRecord("s1", "No URL", "primary"),),
        claims=(HistoricalClaim("c1", "A claim"),),
        evidence=(EvidenceLink("c1", "s1", "supports", quotation="quote"),),
    )
    report = verify_source_urls(dataset)
    assert report.results[0].status == "missing_url"


def test_verify_source_urls_rejects_unknown_claim():
    with pytest.raises(KeyError, match="Unknown claim"):
        verify_source_urls(sample_dataset(), "missing")


def test_source_url_validation_rejects_local_hosts():
    with pytest.raises(ValueError, match="Local"):
        source_verification._validate_public_http_url("http://localhost/admin")
    with pytest.raises(ValueError, match="HTTP"):
        source_verification._validate_public_http_url("file:///etc/passwd")


def test_text_extractor_ignores_script_and_style():
    parser = source_verification._TextExtractor()
    parser.feed("<html><body>History <b>record</b><script>secret</script><style>hidden</style></body></html>")
    assert parser.text() == "History record"


def test_claim_documentation_score_is_not_a_truth_probability():
    report = analyze_claim_confidence(sample_dataset(), "c1")
    assert report.documentation_score is not None
    assert 0 <= report.documentation_score <= 100
    assert report.documentation_band == "mixed_evidence"
    assert report.evidence_status == "mixed"
    assert report.is_truth_probability is False
    assert report.source_independence_status == "dependence_unknown"
    assert any("not a probability" in item for item in report.limitations)


def test_claim_documentation_score_not_assessable_without_evidence():
    dataset = HistoricalDataset(
        claims=(HistoricalClaim("c1", "No evidence recorded"),),
    )
    report = analyze_claim_confidence(dataset, "c1")
    assert report.documentation_score is None
    assert report.documentation_band == "not_assessable"
