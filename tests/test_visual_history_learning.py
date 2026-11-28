"""Tests for seven-part visual history learning data."""

# ruff: noqa: I001 - preserve readable public imports

import pytest

from historypy import (
    EvidenceLink, HistoricalClaim, HistoricalDataset, HistoricalDate,
    HistoricalEvent, HistoricalPerson, HistoricalPlace, HistoricalRelationship,
    SourceRecord, learning_experience_data,
)


def year(value, calendar="gregorian"):
    return HistoricalDate(
        earliest_year=value, latest_year=value, precision="year", calendar=calendar
    )


def dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("src1", "Primary archive", "archival", url="https://example.org/archive"),
            SourceRecord("src2", "Regional chronicle", "secondary"),
        ),
        claims=(HistoricalClaim(
            "claim1", "The event affected the region.",
            event_ids=("event1",), scope_note="A claim to investigate.",
        ),),
        events=(
            HistoricalEvent(
                "event1", "Main event", year(1200), summary="A documented event.",
                place_ids=("place1",), source_ids=("src1",),
            ),
            HistoricalEvent(
                "event2", "Contemporary event elsewhere", year(1200),
                summary="A different event in another region.", place_ids=("place2",),
                source_ids=("src2",),
            ),
            HistoricalEvent("event3", "Later event", year(1300), place_ids=("place2",)),
        ),
        people=(HistoricalPerson("person1", "Recorded participant"),),
        places=(
            HistoricalPlace("place1", "Place One", latitude=23.7, longitude=90.4),
            HistoricalPlace("place2", "Place Two"),
        ),
        relationships=(HistoricalRelationship(
            "rel1", "person1", "participated_in", "event1"
        ),),
        evidence=(
            EvidenceLink("claim1", "src1", "supports", locator="folio 4"),
            EvidenceLink("claim1", "src2", "contradicts", locator="chapter 2"),
        ),
    )


def test_learning_data_contains_seven_parts_and_grounded_elsewhere_matches():
    data = learning_experience_data(dataset(), "event1")
    assert data["title"] == "Main event"
    assert len(data["mystery"]["prompts"]) == 4
    assert data["map"]["places"][0]["coordinates_available"] is True
    assert any(item["selected"] for item in data["timeline"]["entries"])
    assert [item["id"] for item in data["elsewhere"]["events"]] == ["event2"]
    assert data["storyboard"][1]["content"] == "A documented event."
    assert {item["relation"] for item in data["evidence"]["items"]} == {
        "supports", "contradicts"
    }
    assert data["assessment"]["available"] is False


def test_elsewhere_excludes_different_calendars_and_non_overlapping_dates():
    original = dataset()
    changed = HistoricalDataset(
        sources=original.sources, claims=original.claims,
        events=(
            original.events[0],
            HistoricalEvent(
                "julian", "Julian calendar event", year(1200, "julian"),
                place_ids=("place2",),
            ),
            original.events[2],
        ),
        people=original.people, places=original.places,
        relationships=original.relationships, evidence=original.evidence,
    )
    data = learning_experience_data(changed, "event1")
    assert data["elsewhere"]["events"] == []


def test_unknown_event_is_rejected():
    with pytest.raises(KeyError, match="Unknown event"):
        learning_experience_data(dataset(), "missing")
