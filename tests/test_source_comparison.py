from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
    compare_event_sources,
)


def test_compare_event_sources_preserves_source_quotes_relations_and_locators():
    dataset = HistoricalDataset(
        sources=(
            SourceRecord(
                id="s1", title="Chronicle A", source_type="primary",
                url="https://example.org/a",
            ),
            SourceRecord(
                id="s2", title="Study B", source_type="secondary",
                url="https://example.org/b",
            ),
            SourceRecord(id="s3", title="Event catalogue", source_type="tertiary"),
        ),
        events=(
            HistoricalEvent(
                id="event-1", title="Treaty signing",
                date=HistoricalDate(earliest_year=1200, latest_year=1200, calendar="gregorian"),
                source_ids=("s3", "s1"),
            ),
        ),
        claims=(
            HistoricalClaim(
                id="claim-1", statement="The treaty was signed in spring.",
                event_ids=("event-1",),
            ),
        ),
        evidence=(
            EvidenceLink(
                claim_id="claim-1", source_id="s1", relation="supports",
                quotation="The treaty was concluded in the spring.",
                page="12", paragraph="3",
            ),
            EvidenceLink(
                claim_id="claim-1", source_id="s2", relation="contradicts",
                quotation="The treaty was concluded in late autumn.",
                locator="chapter 4, paragraph 8",
            ),
        ),
    )

    report = compare_event_sources(dataset, "event-1")

    assert report.event_title == "Treaty signing"
    assert [source.source_id for source in report.sources] == ["s3", "s1", "s2"]
    assert report.sources[0].directly_linked_to_event is True
    assert report.sources[0].evidence == ()
    assert report.sources[1].evidence[0].quotation.startswith("The treaty")
    assert report.sources[1].evidence[0].page == "12"
    assert report.sources[2].evidence[0].relation == "contradicts"
    assert report.evidence_count == 2
    assert report.evidence_missing_locators == 0
    assert report.has_recorded_support_contradiction is True


def test_compare_event_sources_counts_missing_locator_and_rejects_unknown_event():
    dataset = HistoricalDataset(
        sources=(SourceRecord(id="s1", title="Source", source_type="primary"),),
        events=(
            HistoricalEvent(
                id="event-1", title="Event",
                date=HistoricalDate(original_expression="date unknown"),
            ),
        ),
        claims=(
            HistoricalClaim(id="c1", statement="Claim", event_ids=("event-1",)),
        ),
        evidence=(
            EvidenceLink(claim_id="c1", source_id="s1", relation="mentions"),
        ),
    )

    report = compare_event_sources(dataset, "event-1")
    assert report.evidence_missing_locators == 1
    assert report.has_recorded_support_contradiction is False

    try:
        compare_event_sources(dataset, "missing")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Unknown event id must raise KeyError")
