import pytest

from historypy import (
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    SourceRecord,
)
from historypy.research.query import events_overlapping, search_dataset


def test_search_dataset_matches_names_aliases_and_descriptions():
    dataset = HistoricalDataset(
        people=(HistoricalPerson(
            id="p1", name="Ada Example", aliases=("Countess of Example",),
            occupations=("mathematician",),
        ),),
        places=(HistoricalPlace(
            id="place1", name="Example City", description="ancient port",
        ),),
        sources=(SourceRecord(
            id="s1", title="Letters from the coast", source_type="primary",
        ),),
    )
    assert [hit.record_id for hit in search_dataset(dataset, "countess mathematician")] == ["p1"]
    assert [hit.record_id for hit in search_dataset(dataset, "ancient port")] == ["place1"]
    assert [hit.record_id for hit in search_dataset(dataset, "letters", kinds=("source",))] == ["s1"]


def test_search_is_case_insensitive_and_requires_all_terms():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Queen Example"),
        HistoricalPerson(id="p2", name="Example Scholar"),
    ))
    hits = search_dataset(dataset, "QUEEN example")
    assert [(hit.kind, hit.record_id) for hit in hits] == [("person", "p1")]
    assert search_dataset(dataset, "queen missing") == ()


def test_search_empty_query_and_limit():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Person One"),
        HistoricalPerson(id="p2", name="Person Two"),
    ))
    assert search_dataset(dataset, "  ") == ()
    assert search_dataset(dataset, "person", limit=1)[0].record_id == "p1"
    assert search_dataset(dataset, "person", limit=0) == ()
    with pytest.raises(TypeError, match="query"):
        search_dataset(dataset, None)  # type: ignore[arg-type]


def test_search_results_have_stable_order():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="z", name="Example"),
        HistoricalPerson(id="a", name="Example"),
    ))
    assert [hit.record_id for hit in search_dataset(dataset, "example")] == ["a", "z"]


def test_events_overlapping_period_and_calendar_mismatch():
    dataset = HistoricalDataset(events=(
        HistoricalEvent(
            id="inside", title="Inside",
            date=HistoricalDate(earliest_year=100, latest_year=110, calendar="julian"),
        ),
        HistoricalEvent(
            id="outside", title="Outside",
            date=HistoricalDate(earliest_year=200, latest_year=210, calendar="julian"),
        ),
        HistoricalEvent(
            id="unknown", title="Unknown",
            date=HistoricalDate(original_expression="date uncertain"),
        ),
    ))
    period = HistoricalDate(earliest_year=105, latest_year=105, calendar="julian")
    assert [event.id for event in events_overlapping(dataset, period)] == ["inside"]
    assert [event.id for event in events_overlapping(
        dataset, period, include_indeterminate=True
    )] == ["inside", "unknown"]


def test_events_overlapping_requires_historical_date():
    with pytest.raises(TypeError, match="period"):
        events_overlapping(HistoricalDataset(), "1900")  # type: ignore[arg-type]
