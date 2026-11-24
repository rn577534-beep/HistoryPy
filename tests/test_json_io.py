import json

import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
    SourceRecord,
)
from historypy.io import (
    dataset_from_dict,
    dataset_from_json,
    dataset_to_dict,
    dataset_to_json,
    load_dataset,
    save_dataset,
)


def sample_dataset():
    source = SourceRecord(
        id="src-1", title="Sample source", source_type="primary",
        creator="Unknown author", language="en",
    )
    person = HistoricalPerson(
        id="person-1", name="Sample person",
        birth_date=HistoricalDate(
            earliest_year=0, latest_year=0, calendar="proleptic_gregorian"
        ),
        aliases=("Alias",), source_ids=("src-1",),
    )
    place = HistoricalPlace(
        id="place-1", name="Sample place", place_type="city",
        latitude=24.0, longitude=90.0,
    )
    event = HistoricalEvent(
        id="event-1", title="Sample event",
        date=HistoricalDate(
            earliest="1947-08-14", latest="1947-08-14",
            precision="day", calendar="gregorian",
        ),
        place_ids=("place-1",), source_ids=("src-1",),
    )
    claim = HistoricalClaim(
        id="claim-1", statement="A testable sample claim",
        subject_ids=("person-1",), event_ids=("event-1",),
    )
    relationship = HistoricalRelationship(
        id="rel-1", subject_id="person-1", predicate="associated_with",
        object_id="place-1", source_ids=("src-1",), confidence=0.7,
    )
    evidence = EvidenceLink(
        claim_id="claim-1", source_id="src-1", relation="supports",
        locator="page 3",
    )
    return HistoricalDataset(
        sources=(source,), claims=(claim,), events=(event,), people=(person,),
        places=(place,), relationships=(relationship,), evidence=(evidence,),
        metadata={"dataset_name": "test", "language": "en"},
    )


def test_dataset_dict_round_trip():
    original = sample_dataset()
    restored = dataset_from_dict(dataset_to_dict(original))
    assert restored == original
    assert restored.people[0].birth_date.display() == "1 BCE (proleptic_gregorian)"


def test_dataset_json_round_trip_preserves_unicode():
    original = sample_dataset()
    text = dataset_to_json(original)
    assert "Sample person" in text
    assert dataset_from_json(text) == original


def test_dataset_file_round_trip(tmp_path):
    original = sample_dataset()
    target = tmp_path / "history.json"
    save_dataset(original, target)
    assert load_dataset(target) == original


def test_rejects_unsupported_schema_version():
    payload = dataset_to_dict(sample_dataset())
    payload["schema_version"] = 99
    with pytest.raises(ValueError, match="Unsupported"):
        dataset_from_dict(payload)


def test_rejects_unknown_record_fields():
    payload = dataset_to_dict(sample_dataset())
    payload["people"][0]["invented_field"] = "not accepted"
    with pytest.raises(ValueError, match="Unknown HistoricalPerson field"):
        dataset_from_dict(payload)


def test_validated_import_rejects_broken_references():
    payload = dataset_to_dict(sample_dataset())
    payload["events"][0]["source_ids"] = ["missing-source"]
    with pytest.raises(ValueError, match="missing_source"):
        dataset_from_dict(payload)


def test_unvalidated_import_can_be_used_for_repair():
    payload = dataset_to_dict(sample_dataset())
    payload["events"][0]["source_ids"] = ["missing-source"]
    restored = dataset_from_dict(payload, validate=False)
    assert restored.events[0].source_ids == ("missing-source",)
    assert not restored.is_valid()


def test_json_schema_header_is_explicit():
    payload = json.loads(dataset_to_json(HistoricalDataset()))
    assert payload["schema"] == "historypy.dataset"
    assert payload["schema_version"] == 1
