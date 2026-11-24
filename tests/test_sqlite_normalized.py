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
