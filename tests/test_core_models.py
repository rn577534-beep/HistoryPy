import pytest

from historypy import EvidenceLink, HistoricalDate, HistoricalEvent, SourceRecord


def test_exact_date_display():
    value = HistoricalDate(
        earliest="1947-08-14", latest="1947-08-14",
        precision="day", calendar="gregorian",
    )
    assert value.display() == "1947-08-14 (gregorian)"


def test_date_range_overlap():
    first = HistoricalDate(earliest="1900-01-01", latest="1910-12-31")
    second = HistoricalDate(earliest="1910-01-01", latest="1920-12-31")
    third = HistoricalDate(earliest="1921-01-01", latest="1922-01-01")
    assert first.overlaps(second)
    assert not first.overlaps(third)


def test_rejects_reversed_date_range():
    with pytest.raises(ValueError, match="earliest"):
        HistoricalDate(earliest="1910-01-01", latest="1900-01-01")


def test_requires_date_information():
    with pytest.raises(ValueError, match="Provide"):
        HistoricalDate()


def test_original_historical_date_expression():
    value = HistoricalDate(
        precision="unknown", calendar="Hijri", original_expression="Ramadan, 2 AH"
    )
    assert "Ramadan, 2 AH" in value.display()


def test_source_record():
    source = SourceRecord(
        id="source-001", title="Example archival catalogue",
        source_type="archival", accessed_on="2026-11-24",
    )
    assert source.source_type == "archival"


def test_evidence_link_preserves_contradiction():
    link = EvidenceLink(
        claim_id="claim-001", source_id="source-001", relation="contradicts",
        locator="folio 12",
    )
    assert link.relation == "contradicts"


def test_historical_event():
    event = HistoricalEvent(
        id="event-001", title="Example event",
        date=HistoricalDate(earliest="2000-01-01", latest="2000-01-01"),
        source_ids=("source-001",),
    )
    assert event.source_ids == ("source-001",)


def test_rejects_duplicate_source_ids():
    with pytest.raises(ValueError, match="duplicates"):
        HistoricalEvent(
            id="event-002", title="Example event",
            date=HistoricalDate(original_expression="unknown"),
            source_ids=("source-001", "source-001"),
        )
