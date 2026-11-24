import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPlace,
    SourceRecord,
)
from historypy.io.csv_bundle import load_dataset_csv_bundle, save_dataset_csv_bundle


def sample_dataset():
    source = SourceRecord(
        id="s1", title="Primary record", source_type="archival",
        archive_reference="Archive A, box 2",
    )
    place = HistoricalPlace(
        id="p1", name="ঢাকা", latitude=23.7, longitude=90.4,
        aliases=("Dacca",),
    )
    event = HistoricalEvent(
        id="e1", title="An event",
        date=HistoricalDate(earliest_year=1947, latest_year=1947, calendar="gregorian"),
        place_ids=("p1",), source_ids=("s1",), tags=("politics",),
    )
    claim = HistoricalClaim(id="c1", statement="A claim", event_ids=("e1",))
    evidence = EvidenceLink(
        claim_id="c1", source_id="s1", relation="supports",
        locator="folio 3", page="3r",
    )
    return HistoricalDataset(
        sources=(source,), places=(place,), events=(event,),
        claims=(claim,), evidence=(evidence,), metadata={"project": "test"},
    )


def test_csv_bundle_round_trip_preserves_all_records(tmp_path):
    dataset = sample_dataset()
    save_dataset_csv_bundle(dataset, tmp_path / "bundle")
    restored = load_dataset_csv_bundle(tmp_path / "bundle")
    assert restored == dataset


def test_csv_bundle_rejects_invalid_json_cell(tmp_path):
    directory = tmp_path / "bundle"
    save_dataset_csv_bundle(sample_dataset(), directory)
    (directory / "sources.csv").write_text(
        "id,title,source_type\ns1,not-json,archival\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Invalid JSON cell"):
        load_dataset_csv_bundle(directory)
