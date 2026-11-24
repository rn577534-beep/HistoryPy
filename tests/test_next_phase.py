from dataclasses import replace

import pytest

from historypy import (
    HistoricalClaim, HistoricalDataset, HistoricalEvent, HistoricalDate,
    HistoricalPerson, SourceRecord,
)
from historypy.research.audit_trail import append_research_action, verify_research_audit_trail
from historypy.research.comparison import MetricObservation, compare_metrics
from historypy.research.quality import assess_dataset_quality
from historypy.research.search_index import DatasetSearchIndex
from historypy.research.profile import profile_dataset


def test_hash_linked_audit_trail_and_tamper_detection():
    entries = append_research_action(
        (), action_id="a1", timestamp="2026-01-01T00:00:00+00:00",
        actor="researcher", operation="create", target_type="claim",
        target_id="c1", rationale="Initial record", after={"statement": "A"},
    )
    entries = append_research_action(
        entries, action_id="a2", timestamp="2026-01-02T00:00:00+00:00",
        actor="researcher", operation="revise", target_type="claim",
        target_id="c1", rationale="New source", before={"statement": "A"},
        after={"statement": "B"},
    )
    assert verify_research_audit_trail(entries) == (True, ())
    changed = (entries[0], replace(entries[1], rationale="tampered"))
    assert verify_research_audit_trail(changed)[0] is False


def test_comparison_preserves_unknown_and_units():
    result = compare_metrics((
        MetricObservation("empire-a", "population", 10, "million", ("s1",)),
        MetricObservation("empire-b", "population", None, "million"),
        MetricObservation("empire-c", "population", 15, "million"),
        MetricObservation("empire-a", "area", 20, "km2"),
    ))
    population = next(item for item in result if item.metric == "population")
    assert population.unknown_entity_ids == ("empire-b",)
    assert population.spread == 5
    assert len(result) == 2


def test_comparison_rejects_duplicate_and_nonfinite_values():
    with pytest.raises(ValueError, match="Duplicate"):
        compare_metrics((
            MetricObservation("x", "m", 1, "u"),
            MetricObservation("x", "m", 2, "u"),
        ))
    with pytest.raises(ValueError, match="finite"):
        MetricObservation("x", "m", float("nan"), "u")


def test_quality_report_flags_claim_without_evidence_and_validation():
    dataset = HistoricalDataset(
        claims=(HistoricalClaim("c1", "A claim"),),
        events=(HistoricalEvent(
            "e1", "An event", HistoricalDate(earliest_year=1, calendar="julian")
        ),),
    )
    codes = {item.code for item in assess_dataset_quality(dataset).findings}
    assert "claim_without_evidence" in codes
    assert "event_without_source" in codes


def test_search_index_matches_lexical_query_and_kind_filter():
    dataset = HistoricalDataset(people=(
        HistoricalPerson("p1", "Ada Example", occupations=("mathematician",)),
        HistoricalPerson("p2", "Example Scholar"),
    ))
    index = DatasetSearchIndex.build(dataset)
    assert [hit.record_id for hit in index.search("ada mathematician")] == ["p1"]
    assert index.search("example", kinds=("place",)) == ()
    assert [hit.record_id for hit in index.search("mathemat")] == ["p1"]


def test_profile_counts_missing_data_without_scoring_truth():
    dataset = HistoricalDataset(
        people=(HistoricalPerson("p1", "Person"),),
        claims=(HistoricalClaim("c1", "A claim"),),
    )
    profile = profile_dataset(dataset)
    assert dict(profile.record_counts)["people"] == 1
    assert profile.claims_without_evidence == 1
    assert profile.places_without_coordinates == 0
