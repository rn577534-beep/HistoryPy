import pytest

from historypy import (
    EvidenceLink, HistoricalClaim, HistoricalDate, HistoricalEvent, SourceRecord
)


def test_exact_date_display():
    value = HistoricalDate(
        earliest="1947-08-14", latest="1947-08-14",
        precision="day", calendar="gregorian",
    )
    assert value.display() == "1947-08-14 (gregorian)"


def test_date_range_overlap():
    first = HistoricalDate(
        earliest="1900-01-01", latest="1910-12-31", calendar="gregorian"
    )
    second = HistoricalDate(
        earliest="1910-01-01", latest="1920-12-31", calendar="gregorian"
    )
    third = HistoricalDate(
        earliest="1921-01-01", latest="1922-01-01", calendar="gregorian"
    )
    assert first.overlaps(second) is True
    assert first.overlaps(third) is False


def test_bce_years_use_astronomical_numbering():
    one_bce = HistoricalDate(
        earliest_year=0, latest_year=0, precision="year", calendar="proleptic_gregorian"
    )
    forty_four_bce = HistoricalDate(
        earliest_year=-43, latest_year=-43, precision="year",
        calendar="proleptic_gregorian",
    )
    assert one_bce.display() == "1 BCE (proleptic_gregorian)"
    assert forty_four_bce.display() == "44 BCE (proleptic_gregorian)"


def test_bce_and_ce_interval_comparison():
    bce = HistoricalDate(
        earliest_year=-100, latest_year=0, calendar="proleptic_gregorian"
    )
    ce = HistoricalDate(
        earliest_year=1, latest_year=100, calendar="proleptic_gregorian"
    )
    assert bce.overlaps(ce) is False


def test_unknown_or_incompatible_dates_are_not_guessed():
    unknown = HistoricalDate(original_expression="early medieval period")
    known = HistoricalDate(earliest_year=900, latest_year=950)
    different_calendar = HistoricalDate(
        earliest_year=900, latest_year=950, calendar="Hijri"
    )
    assert unknown.overlaps(known) is None
    assert known.overlaps(different_calendar) is None


def test_rejects_mixed_date_bound_formats():
    with pytest.raises(ValueError, match="not both"):
        HistoricalDate(earliest="1900-01-01", earliest_year=1900)


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


def test_claim_is_a_first_class_record():
    claim = HistoricalClaim(
        id="claim-001", statement="An illustrative research proposition"
    )
    assert claim.statement.startswith("An illustrative")


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
