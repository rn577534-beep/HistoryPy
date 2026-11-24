from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)
from historypy.io.sqlite_normalized import NormalizedSQLiteStore


def make_dataset() -> HistoricalDataset:
    source = SourceRecord("s1", "Archive Chronicle", "archival")
    claim = HistoricalClaim("c1", "A documented proposition")
    event = HistoricalEvent(
        "e1", "A major historical event",
        HistoricalDate(earliest_year=1200, latest_year=1201, precision="year",
                       calendar="gregorian"),
        summary="An event described in the archive",
        source_ids=("s1",),
    )
    evidence = EvidenceLink("c1", "s1", "supports", page="12")
    return HistoricalDataset(sources=(source,), claims=(claim,), events=(event,),
                             evidence=(evidence,), metadata={"project": "demo"})


def test_normalized_store_round_trip_and_names(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    dataset = make_dataset()
    store.save("sample", dataset)
    assert store.names() == ("sample",)
    assert store.load("sample") == dataset
    assert store.count_records("sample") == 4
    assert store.count_records("sample", kind="events") == 1


def test_normalized_store_search_and_pagination(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    dataset = HistoricalDataset(events=tuple(
        HistoricalEvent(f"e{i}", f"Archive event {i}",
                        HistoricalDate(earliest_year=1000 + i, latest_year=1000 + i,
                                       precision="year", calendar="gregorian"))
        for i in range(8)
    ))
    store.save("timeline", dataset)
    if store._fts5_available:
        phrase_hits = store.search_records(
            "timeline", "Archive event", kind="events", limit=20
        )
        assert store._fts5_available
        assert len(phrase_hits) == 8
    first = store.search_records("timeline", "archive", kind="events", limit=3)
    second = store.search_records("timeline", "archive", kind="events", limit=3, offset=3)
    assert [row.record_id for row in first] == ["e0", "e1", "e2"]
    assert [row.record_id for row in second] == ["e3", "e4", "e5"]


def test_normalized_store_source_usage_includes_evidence(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    store.save("sample", make_dataset())
    usage = store.source_usage("sample")
    assert len(usage) == 1
    assert usage[0].source_id == "s1"
    assert usage[0].record_links == 1
    assert usage[0].evidence_links == 1
    assert usage[0].total_links == 2


def test_normalized_store_replace_is_atomic_and_delete_cascades(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    store.save("sample", make_dataset())
    store.save("sample", HistoricalDataset())
    assert store.count_records("sample") == 0
    assert store.load("sample") == HistoricalDataset()
    assert store.delete("sample")
    assert store.names() == ()


def test_normalized_store_validates_inputs(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    store.save("empty", HistoricalDataset())
    import pytest
    with pytest.raises(ValueError):
        store.search_records("empty", "   ")
    with pytest.raises(ValueError):
        store.search_records("empty", "x", limit=0)
    with pytest.raises(KeyError):
        store.load("missing")
    with pytest.raises(KeyError):
        store.search_records("missing", "x")


def test_normalized_store_reports_unused_sources(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    dataset = HistoricalDataset(sources=(
        SourceRecord("used", "Used source", "archival"),
        SourceRecord("unused", "Unused source", "other"),
    ), events=(HistoricalEvent(
        "e1", "Linked event",
        HistoricalDate(earliest_year=100, latest_year=100, precision="year",
                       calendar="gregorian"),
        source_ids=("used",),
    ),))
    store.save("sources", dataset)
    usage = store.source_usage("sources")
    assert [(item.source_id, item.total_links) for item in usage] == [
        ("unused", 0), ("used", 1)
    ]


def test_normalized_store_year_range_handles_bce_and_calendar(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    dataset = HistoricalDataset(events=(
        HistoricalEvent(
            "bce", "BCE record",
            HistoricalDate(earliest_year=-500, latest_year=-400,
                           precision="century", calendar="julian"),
        ),
        HistoricalEvent(
            "ce", "CE record",
            HistoricalDate(earliest_year=100, latest_year=150,
                           precision="century", calendar="gregorian"),
        ),
        HistoricalEvent(
            "open", "Open ended record",
            HistoricalDate(earliest_year=0, precision="unknown", calendar="julian"),
        ),
        HistoricalEvent(
            "undated", "Undated record",
            HistoricalDate(original_expression="date unknown", calendar="unspecified"),
        ),
    ))
    store.save("chronology", dataset)
    bce = store.query_year_range("chronology", -450, -425, kind="events")
    assert [item.record_id for item in bce] == ["bce"]
    julian = store.query_year_range(
        "chronology", -10, 10, kind="events", calendar="julian"
    )
    assert [item.record_id for item in julian] == ["open"]
    assert store.query_year_range(
        "chronology", -10, 10, calendar="gregorian"
    ) == ()
    with_undated = store.query_year_range(
        "chronology", -10, 10, include_undated=True
    )
    assert {item.record_id for item in with_undated} == {"open", "undated"}


def test_normalized_store_search_fallback_and_fts_cleanup(tmp_path):
    store = NormalizedSQLiteStore(tmp_path / "history.db")
    store.save("sample", make_dataset())
    store._fts5_available = False
    fallback = store.search_records("sample", "documented proposition")
    assert [item.record_id for item in fallback] == ["c1"]
    store._fts5_available = True
    assert store.delete("sample")
    with store._connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM hp06_records_fts WHERE dataset_name = 'sample'"
        ).fetchone()[0] == 0
