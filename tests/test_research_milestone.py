import pytest

from historypy import (
    EvidenceLink,
    HarvardArtMuseumsSearch,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalKnowledgeGraph,
    HistoricalPerson,
    HistoricalPlace,
    SmithsonianSearch,
    SourceRecord,
    SQLiteDatasetStore,
    assess_claim,
    render_claim_report,
    temporal_graph,
)
from historypy.integrations import collection_apis


def sample_dataset():
    source = SourceRecord(
        id="s1", title="Archive catalogue", source_type="archival",
        url="https://example.org/source",
    )
    person = HistoricalPerson(id="p1", name="Research subject", source_ids=("s1",))
    place = HistoricalPlace(id="pl1", name="Example place", source_ids=("s1",))
    event = HistoricalEvent(
        id="e1", title="Recorded event",
        date=HistoricalDate(
            earliest_year=1947, latest_year=1947, precision="year", calendar="gregorian"
        ),
        place_ids=("pl1",), source_ids=("s1",),
    )
    claim = HistoricalClaim(
        id="c1", statement="The event occurred at the example place.",
        subject_ids=("p1",), event_ids=("e1",),
    )
    evidence = EvidenceLink("c1", "s1", "supports", locator="catalogue entry 1")
    return HistoricalDataset(
        sources=(source,), claims=(claim,), events=(event,), people=(person,),
        places=(place,), evidence=(evidence,),
    )


def test_knowledge_graph_projects_entities_claims_sources_and_evidence():
    graph = HistoricalKnowledgeGraph.from_dataset(sample_dataset())
    assert graph.node("p1").kind == "person"
    assert graph.node("c1").kind == "claim"
    assert graph.neighbors("c1", predicate="supports")[0].id == "s1"
    assert graph.neighbors("e1", predicate="occurred_at")[0].id == "pl1"


def test_temporal_graph_filters_events_and_keeps_provenance():
    dataset = sample_dataset()
    period = HistoricalDate(
        earliest_year=1940, latest_year=1950, calendar="gregorian"
    )
    graph = temporal_graph(dataset, period)
    assert {node.id for node in graph.nodes} == {"e1", "pl1", "s1"}
    assert graph.neighbors("e1", predicate="documented_by")[0].id == "s1"


def test_temporal_graph_excludes_incomparable_dates_by_default():
    dataset = HistoricalDataset(events=(
        HistoricalEvent(
            id="e2", title="Undated-calendar event",
            date=HistoricalDate(original_expression="circa ancient era"),
        ),
    ))
    period = HistoricalDate(earliest_year=1, latest_year=10, calendar="gregorian")
    assert temporal_graph(dataset, period).nodes == ()
    assert temporal_graph(dataset, period, include_indeterminate=True).node("e2")


def test_claim_assessment_reports_mixed_evidence_without_truth_claim():
    dataset = sample_dataset()
    contradictory = EvidenceLink("c1", "s1", "contradicts", locator="alternate note")
    dataset = HistoricalDataset(
        sources=dataset.sources, claims=dataset.claims, events=dataset.events,
        people=dataset.people, places=dataset.places,
        evidence=dataset.evidence + (contradictory,),
    )
    assessment = assess_claim(dataset, "c1")
    assert assessment.status == "mixed"
    assert "not proof" in assessment.explanation


def test_claim_report_contains_sources_and_limitations():
    report = render_claim_report(sample_dataset(), "c1")
    assert "# Research note:" in report
    assert "Archive catalogue" in report
    assert "does not assess" in report


def test_sqlite_store_round_trips_and_deletes(tmp_path):
    store = SQLiteDatasetStore(tmp_path / "history.sqlite")
    dataset = sample_dataset()
    store.save("bengal-research", dataset)
    assert store.names() == ("bengal-research",)
    assert store.load("bengal-research") == dataset
    assert store.delete("bengal-research")
    assert store.names() == ()
    with pytest.raises(KeyError):
        store.load("bengal-research")


def test_collection_adapters_require_api_keys(monkeypatch):
    monkeypatch.delenv("SMITHSONIAN_API_KEY", raising=False)
    monkeypatch.delenv("HARVARD_ART_MUSEUMS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SMITHSONIAN_API_KEY"):
        SmithsonianSearch()
    with pytest.raises(ValueError, match="HARVARD_ART_MUSEUMS_API_KEY"):
        HarvardArtMuseumsSearch()


def test_smithsonian_adapter_normalizes_item_metadata(monkeypatch):
    monkeypatch.setattr(collection_apis, "_request_json", lambda url, headers=None: {
        "response": {"rows": [{
            "id": "edanmdm:test_1",
            "content": {
                "descriptiveNonRepeating": {
                    "record_ID": "test_1", "record_link": "https://si.edu/object/1"
                },
                "freetext": {"title": [{"content": "Bronze object"}]},
            },
        }]}
    })
    record = SmithsonianSearch("test-key").search("bronze")[0]
    assert record.provider == "Smithsonian Open Access"
    assert record.title == "Bronze object"


def test_harvard_adapter_normalizes_object_metadata(monkeypatch):
    monkeypatch.setattr(collection_apis, "_request_json", lambda url, headers=None: {
        "records": [{
            "objectid": 123, "title": "Ancient vessel", "dated": "5th century BCE",
            "url": "https://harvardartmuseums.org/collections/object/123",
            "people": [{"name": "Unknown maker"}],
        }]
    })
    record = HarvardArtMuseumsSearch("test-key").search("vessel")[0]
    assert record.external_id == "123"
    assert record.creator == "Unknown maker"
    assert record.date == "5th century BCE"


def test_sqlite_store_rejects_empty_name(tmp_path):
    store = SQLiteDatasetStore(tmp_path / "empty.sqlite")
    with pytest.raises(ValueError, match="name"):
        store.save(" ", sample_dataset())
