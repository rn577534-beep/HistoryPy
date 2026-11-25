import pytest

from historypy import (
    HistoricalDataset,
    HistoricalDate,
    HistoricalPerson,
    HistoricalRelationship,
    SourceRecord,
)
from historypy.research.relationship_paths import (
    RelationshipPathQuery,
    find_relationship_paths,
)


def _dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("s1", "Genealogy source", "secondary"),
            SourceRecord("s2", "Historical register", "archival"),
        ),
        people=(
            HistoricalPerson("p1", "Person One"),
            HistoricalPerson("p2", "Person Two"),
            HistoricalPerson("p3", "Person Three"),
            HistoricalPerson("p4", "Person Four"),
        ),
        relationships=(
            HistoricalRelationship(
                "r1", "p1", "parent_of", "p2", source_ids=("s1",),
                valid_from=HistoricalDate(earliest_year=1800, calendar="gregorian"),
            ),
            HistoricalRelationship("r2", "p2", "member_of", "p3"),
            HistoricalRelationship(
                "r3", "p1", "related_to", "p3", source_ids=("s2",)
            ),
            HistoricalRelationship(
                "r4", "p3", "located_in", "p4", source_ids=("s1",)
            ),
        ),
    )


def test_finds_multihop_paths_and_keeps_each_relationship_and_source():
    report = find_relationship_paths(
        _dataset(),
        RelationshipPathQuery(
            "p1", "p3", max_hops=2, predicates=("parent_of", "member_of")
        ),
    )
    assert len(report.paths) == 1
    path = report.paths[0]
    assert path.entity_ids == ("p1", "p2", "p3")
    assert [step.relationship_id for step in path.steps] == ["r1", "r2"]
    assert path.source_ids == ("s1",)
    assert path.relationships_missing_sources == ("r2",)
    assert path.has_source_gap
    assert path.steps[0].valid_from.earliest_year == 1800


def test_reverse_traversal_preserves_original_relationship_direction():
    report = find_relationship_paths(
        _dataset(),
        RelationshipPathQuery(
            "p3", "p1", max_hops=2,
            predicates=("member_of", "parent_of"), direction="both",
        ),
    )
    assert len(report.paths) == 1
    path = report.paths[0]
    assert path.entity_ids == ("p3", "p2", "p1")
    assert [step.traversal for step in path.steps] == ["reverse", "reverse"]
    assert [(step.subject_id, step.object_id) for step in path.steps] == [
        ("p2", "p3"), ("p1", "p2")
    ]


def test_path_search_is_bounded_and_reports_truncation():
    report = find_relationship_paths(
        _dataset(),
        RelationshipPathQuery("p1", "p3", max_hops=2, limit=1),
    )
    assert len(report.paths) == 1
    assert report.truncated
    assert report.explored_states > 0


def test_missing_paths_and_unknown_entities_are_explicit():
    report = find_relationship_paths(
        _dataset(), RelationshipPathQuery("p4", "p1", max_hops=3)
    )
    assert report.paths == ()
    with pytest.raises(KeyError, match="Unknown start entity"):
        find_relationship_paths(
            _dataset(), RelationshipPathQuery("missing", "p1")
        )


def test_query_bounds_and_predicate_constraints_are_validated():
    with pytest.raises(ValueError, match="max_hops"):
        RelationshipPathQuery("p1", "p2", max_hops=0)
    with pytest.raises(ValueError, match="predicates"):
        RelationshipPathQuery("p1", "p2", max_hops=1, predicates=("a", "b"))
    with pytest.raises(ValueError, match="direction"):
        RelationshipPathQuery("p1", "p2", direction="sideways")



def test_path_search_honors_hard_exploration_budget():
    report = find_relationship_paths(
        _dataset(),
        RelationshipPathQuery(
            "p1", "p4", max_hops=4, direction="both",
            max_explored_states=1,
        ),
    )
    assert report.explored_states == 1
    assert report.truncated
    assert report.paths == ()
