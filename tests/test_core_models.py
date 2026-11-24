import pytest

from historypy import EvidenceLink, HistoricalClaim, HistoricalDate, HistoricalEvent, SourceRecord
from historypy.chronology import find_overlapping_events, sort_events

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

def test_timeline_sorts_bce_before_ce_and_unknown_last():
    bce = HistoricalEvent(
        id="bce", title="BCE event",
        date=HistoricalDate(
            earliest_year=-43, latest_year=-43, calendar="proleptic_gregorian"
        ),
    )
    ce = HistoricalEvent(
        id="ce", title="CE event",
        date=HistoricalDate(
            earliest="0001-01-01", latest="0001-01-01",
            calendar="proleptic_gregorian",
        ),
    )
    unknown = HistoricalEvent(
        id="unknown", title="Undated event",
        date=HistoricalDate(original_expression="date unknown"),
    )
    assert [event.id for event in sort_events([unknown, ce, bce])] == [
        "bce", "ce", "unknown"
    ]

def test_find_overlapping_events_omits_unknown_dates():
    first = HistoricalEvent(
        id="a", title="A", date=HistoricalDate(
            earliest_year=100, latest_year=200, calendar="proleptic_gregorian"
        )
    )
    second = HistoricalEvent(
        id="b", title="B", date=HistoricalDate(
            earliest_year=150, latest_year=250, calendar="proleptic_gregorian"
        )
    )
    unknown = HistoricalEvent(
        id="c", title="C", date=HistoricalDate(original_expression="uncertain")
    )
    pairs = find_overlapping_events([first, second, unknown])
    assert [(a.id, b.id) for a, b in pairs] == [("a", "b")]

def test_unspecified_calendar_overlap_is_unknown():
    first = HistoricalDate(earliest_year=100, latest_year=200)
    second = HistoricalDate(earliest_year=150, latest_year=250)
    assert first.overlaps(second) is None

def test_timeline_rejects_mixed_calendars():
    gregorian = HistoricalEvent(
        id="g", title="Gregorian", date=HistoricalDate(
            earliest="1900-01-01", latest="1900-01-01", calendar="gregorian"
        )
    )
    hijri = HistoricalEvent(
        id="h", title="Hijri", date=HistoricalDate(
            earliest_year=1300, latest_year=1300, calendar="Hijri"
        )
    )
    with pytest.raises(ValueError, match="one explicit calendar"):
        sort_events([gregorian, hijri])

def test_astronomical_year_bounds_must_be_integers():
    with pytest.raises(TypeError, match="earliest_year"):
        HistoricalDate(earliest_year="44 BCE")

def test_iso_dates_require_canonical_format():
    with pytest.raises(ValueError, match="canonical"):
        HistoricalDate(earliest="19470814")
