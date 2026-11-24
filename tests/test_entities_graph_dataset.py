import pytest

from historypy import (
    EvidenceLink,
    HistoricalCivilization,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
    RelationshipGraph,
    SourceRecord,
)


def test_person_and_place_records():
    person = HistoricalPerson(
        id="person-1", name="Example historical person",
        aliases=("Alternate name",), occupations=("writer",),
    )
    place = HistoricalPlace(
        id="place-1", name="Example place", place_type="city",
        latitude=24.0, longitude=90.0,
    )
    assert person.name == "Example historical person"
    assert place.latitude == 24.0


def test_place_requires_coordinate_pair_and_valid_ranges():
    with pytest.raises(ValueError, match="supplied together"):
        HistoricalPlace(id="p1", name="Place", latitude=20.0)
    with pytest.raises(ValueError, match="latitude"):
        HistoricalPlace(id="p1", name="Place", latitude=91.0, longitude=0.0)


def test_civilization_and_organization_records():
    civilization = HistoricalCivilization(
        id="civilization-1", name="Example civilization",
        languages=("Example language",),
    )
    organization = HistoricalOrganization(
        id="organization-1", name="Example dynasty",
        organization_type="dynasty",
    )
    assert civilization.name == "Example civilization"
    assert organization.organization_type == "dynasty"


def test_relationship_validates_confidence_and_self_parent():
    with pytest.raises(ValueError, match="confidence"):
        HistoricalRelationship(
            id="r1", subject_id="a", predicate="related_to", object_id="b",
            confidence=1.5,
        )
    with pytest.raises(ValueError, match="own parent"):
        HistoricalOrganization(
            id="o1", name="Org", parent_organization_ids=("o1",)
        )


def test_dataset_validates_cross_references():
    source = SourceRecord(
        id="source-1", title="Example source", source_type="primary"
    )
    person = HistoricalPerson(id="person-1", name="Person", source_ids=("source-1",))
    place = HistoricalPlace(id="place-1", name="Place", place_type="city")
    event = HistoricalEvent(
        id="event-1", title="Event",
        date=HistoricalDate(original_expression="date uncertain"),
        place_ids=("place-1",), source_ids=("source-1",),
    )
    claim = HistoricalClaim(
        id="claim-1", statement="A sample proposition",
        subject_ids=("person-1",), event_ids=("event-1",),
    )
    link = EvidenceLink(
        claim_id="claim-1", source_id="source-1", relation="supports"
    )
    relationship = HistoricalRelationship(
        id="relationship-1", subject_id="person-1",
        predicate="associated_with", object_id="place-1",
        source_ids=("source-1",),
    )
    dataset = HistoricalDataset(
        sources=(source,), people=(person,), places=(place,), events=(event,),
        claims=(claim,), evidence=(link,), relationships=(relationship,),
    )
    assert dataset.is_valid()
    dataset.require_valid()


def test_dataset_reports_missing_references_without_dropping_records():
    dataset = HistoricalDataset(
        events=(HistoricalEvent(
            id="event-1", title="Event",
            date=HistoricalDate(original_expression="unknown"),
            source_ids=("missing-source",), place_ids=("missing-place",),
        ),)
    )
    codes = {issue.code for issue in dataset.validate()}
    assert {"missing_source", "missing_place"} <= codes
    assert len(dataset.events) == 1


def test_dataset_reports_unknown_relationship_endpoints():
    dataset = HistoricalDataset(
        relationships=(HistoricalRelationship(
            id="r1", subject_id="missing-a", predicate="related_to",
            object_id="missing-b",
        ),)
    )
    issues = dataset.validate()
    assert sum(issue.code == "missing_relationship_endpoint" for issue in issues) == 2


def test_relationship_graph_neighbors_and_predicate_filter():
    edges = (
        HistoricalRelationship(
            id="r1", subject_id="a", predicate="member_of", object_id="b"
        ),
        HistoricalRelationship(
            id="r2", subject_id="a", predicate="located_in", object_id="c"
        ),
    )
    graph = RelationshipGraph(("a", "b", "c"), edges)
    assert graph.neighbors("a") == ("b", "c")
    assert graph.neighbors("a", predicate="member_of") == ("b",)
    assert graph.neighbors("b", direction="incoming") == ("a",)


def test_relationship_graph_shortest_path_and_components():
    edges = (
        HistoricalRelationship(
            id="r1", subject_id="a", predicate="connected_to", object_id="b"
        ),
        HistoricalRelationship(
            id="r2", subject_id="b", predicate="connected_to", object_id="c"
        ),
    )
    graph = RelationshipGraph(("a", "b", "c", "isolated"), edges)
    assert graph.shortest_path("a", "c") == ("a", "b", "c")
    assert graph.shortest_path("c", "a") is None
    assert graph.shortest_path("c", "a", direction="both") == ("c", "b", "a")
    assert graph.connected_components() == (("a", "b", "c"), ("isolated",))


def test_relationship_graph_rejects_missing_nodes_and_edges():
    edge = HistoricalRelationship(
        id="r1", subject_id="a", predicate="related_to", object_id="missing"
    )
    with pytest.raises(ValueError, match="absent"):
        RelationshipGraph(("a",), (edge,))
    graph = RelationshipGraph(("a",), ())
    with pytest.raises(KeyError, match="Unknown entity"):
        graph.neighbors("missing")


def test_rejects_boolean_coordinates_and_confidence():
    with pytest.raises(ValueError, match="latitude"):
        HistoricalPlace(id="p", name="Place", latitude=True, longitude=0.0)
    with pytest.raises(ValueError, match="confidence"):
        HistoricalRelationship(
            id="r", subject_id="a", predicate="related_to", object_id="b",
            confidence=True,
        )


def test_dataset_detects_entity_id_collisions_across_types():
    dataset = HistoricalDataset(
        people=(HistoricalPerson(id="same-id", name="Person"),),
        places=(HistoricalPlace(id="same-id", name="Place"),),
    )
    assert any(issue.code == "duplicate_entity_id" for issue in dataset.validate())


def test_relationship_graph_can_be_built_from_dataset():
    person = HistoricalPerson(id="person", name="Person")
    place = HistoricalPlace(id="place", name="Place")
    relation = HistoricalRelationship(
        id="r1", subject_id="person", predicate="associated_with", object_id="place"
    )
    dataset = HistoricalDataset(
        people=(person,), places=(place,), relationships=(relation,)
    )
    graph = RelationshipGraph.from_dataset(dataset)
    assert graph.neighbors("person") == ("place",)
