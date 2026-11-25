from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)
from historypy.research.source_comparison import render_event_source_comparison


def test_synthetic_event_comparison_preserves_two_distinct_accounts_and_locators():
    dataset = HistoricalDataset(
        sources=(
            SourceRecord(
                "archive-a", "Synthetic archive account A", "archival",
                creator="Archive A", url="https://example.org/archive-a",
            ),
            SourceRecord(
                "chronicle-b", "Synthetic chronicle account B", "primary",
                creator="Chronicle B", url="https://example.org/chronicle-b",
            ),
        ),
        events=(HistoricalEvent(
            "event-1", "Synthetic port agreement",
            HistoricalDate(earliest_year=1200, latest_year=1200, calendar="gregorian"),
            source_ids=("archive-a", "chronicle-b"),
        ),),
        claims=(HistoricalClaim(
            "claim-1", "The agreement imposed a harbor toll.",
            event_ids=("event-1",),
        ),),
        evidence=(
            EvidenceLink(
                "claim-1", "archive-a", "supports",
                quotation="A toll shall be collected at the harbor gate.",
                page="12", archive_shelfmark="SYN/A/12",
                interpretation_note="Synthetic teaching fixture; not a real quotation.",
            ),
            EvidenceLink(
                "claim-1", "chronicle-b", "contradicts",
                quotation="No harbor toll was agreed by the council.",
                paragraph="7", url_fragment="section-7",
                interpretation_note="Synthetic teaching fixture; not a real quotation.",
            ),
        ),
    )
    report = render_event_source_comparison(dataset, "event-1")
    assert "Synthetic archive account A" in report
    assert "Synthetic chronicle account B" in report
    assert "SYN/A/12" in report
    assert "paragraph: 7" in report
    assert "supports" in report and "contradicts" in report
    assert "do not establish source independence" in report
