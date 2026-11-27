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
    allen_interval_relation,
    dataset_graph_data,
    evidence_relation_entropy,
    find_weighted_relationship_paths,
    render_visualization_html,
    shannon_entropy,
    source_type_entropy,
    timeline_visualization_data,
    to_geojson,
    to_graphviz_dot,
)


def interval(start, end, calendar="gregorian"):
    return HistoricalDate(
        earliest_year=start, latest_year=end, precision="year", calendar=calendar
    )


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ((1, 2), (4, 5), "before"),
        ((1, 4), (3, 6), "overlaps"),
        ((1, 3), (1, 5), "starts"),
        ((2, 3), (1, 5), "during"),
        ((3, 5), (1, 5), "finishes"),
        ((1, 5), (1, 5), "equals"),
        ((1, 7), (1, 5), "started_by"),
        ((1, 7), (3, 5), "contains"),
        ((1, 5), (3, 5), "finished_by"),
        ((3, 7), (1, 5), "overlapped_by"),
        ((4, 5), (1, 2), "after"),
    ],
)
def test_allen_interval_relations(first, second, expected):
    assert allen_interval_relation(interval(*first), interval(*second)) == expected


def test_allen_meets_and_met_by_use_touching_explicit_date_bounds():
    first = HistoricalDate(
        earliest="1900-01-01", latest="1900-01-02", calendar="gregorian"
    )
    second = HistoricalDate(
        earliest="1900-01-02", latest="1900-01-03", calendar="gregorian"
    )
    assert allen_interval_relation(first, second) == "meets"
    assert allen_interval_relation(second, first) == "met_by"


def test_allen_relations_preserve_unknown_and_calendar_incomparability():
    assert allen_interval_relation(
        interval(1, 2, "julian"), interval(1, 2, "gregorian")
    ) is None
    unknown = HistoricalDate(original_expression="sometime in antiquity")
    assert allen_interval_relation(unknown, interval(1, 2)) is None


def test_shannon_entropy_known_values_and_validation():
    report = shannon_entropy({"supports": 2, "contradicts": 2})
    assert report.entropy_bits == pytest.approx(1.0)
    assert report.normalized_entropy == pytest.approx(1.0)
    assert shannon_entropy({"one": 10}).normalized_entropy == 0.0
    assert shannon_entropy({}).normalized_entropy is None
    with pytest.raises(ValueError, match="non-negative"):
        shannon_entropy({"bad": -1})


def sample_dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("s1", "Archive record", "archival"),
            SourceRecord("s2", "Later study", "secondary", derived_from_source_ids=("s1",)),
        ),
        claims=(HistoricalClaim("c1", "A sample historical claim"),),
        events=(HistoricalEvent(
            "e1", "Sample event", interval(1800, 1801),
            place_ids=("place1",), source_ids=("s1",),
        ),),
        people=(HistoricalPerson("p1", "Sample person", source_ids=("s1",)),),
        places=(HistoricalPlace(
            "place1", "Sample place", place_type="city",
            latitude=23.7, longitude=90.4, source_ids=("s1",),
        ),),
        relationships=(
            HistoricalRelationship("r1", "p1", "participated_in", "e1", source_ids=("s1",)),
            HistoricalRelationship("r2", "e1", "occurred_at", "place1"),
        ),
        evidence=(
            EvidenceLink("c1", "s1", "supports", locator="page 4"),
            EvidenceLink("c1", "s2", "contradicts", locator="page 9"),
        ),
    )


def test_evidence_entropy_reports_category_distribution_not_truth():
    dataset = sample_dataset()
    assert evidence_relation_entropy(dataset, claim_id="c1").entropy_bits == pytest.approx(1)
    assert dict(source_type_entropy(dataset, claim_id="c1").counts) == {
        "archival": 1, "secondary": 1
    }


def test_weighted_paths_follow_caller_costs_and_report_source_gaps():
    report = find_weighted_relationship_paths(
        sample_dataset(), "p1", "place1",
        edge_costs={"r1": 1.0, "r2": 4.0},
    )
    assert len(report.paths) == 1
    path = report.paths[0]
    assert path.relationship_ids == ("r1", "r2")
    assert path.total_cost == 5.0
    assert path.source_ids == ("s1",)
    assert path.relationships_missing_sources == ("r2",)
    assert "not credibility" in report.cost_policy
    with pytest.raises(ValueError, match="finite"):
        find_weighted_relationship_paths(
            sample_dataset(), "p1", "place1", edge_costs={"r1": float("inf")}
        )


def test_graph_dot_geojson_and_timeline_exports_keep_provenance():
    dataset = sample_dataset()
    graph = dataset_graph_data(dataset)
    assert any(node["kind"] == "claim" for node in graph["nodes"])
    assert any(edge["kind"] == "evidence" for edge in graph["edges"])
    assert any(edge["kind"] == "entity_source" for edge in graph["edges"])
    dot = to_graphviz_dot(dataset)
    assert "digraph HistoryPy" in dot
    assert "participated_in" in dot

    geo = to_geojson(dataset)
    assert geo["type"] == "FeatureCollection"
    feature = geo["features"][0]
    assert feature["geometry"]["coordinates"] == [90.4, 23.7]
    assert feature["properties"]["event_ids"] == ["e1"]
    assert feature["properties"]["source_ids"] == ["s1"]

    timeline = timeline_visualization_data(dataset)
    assert timeline["entries"][0]["id"] == "e1"
    assert timeline["entries"][0]["start"] == 1800
    assert timeline["entries"][0]["interval_is_uncertain"]



def test_interactive_html_report_is_self_contained_and_escapes_user_content():
    dataset = sample_dataset()
    html = render_visualization_html(dataset, title="<script>alert('x')</script>")
    assert "<!doctype html>" in html
    assert "&lt;script&gt;" in html
    assert "<script>alert('x')</script>" not in html
    assert 'data-target="network"' in html
    assert 'data-target="timeline"' in html
    assert 'data-target="places"' in html
    assert "Sample person" in html
    assert "Schematic latitude/longitude scatter only" in html


def test_interactive_html_report_limits_large_networks_and_bad_options():
    dataset = sample_dataset()
    with pytest.raises(ValueError, match="at most"):
        render_visualization_html(dataset, max_nodes=2)
    with pytest.raises(ValueError, match="cannot be empty"):
        render_visualization_html(dataset, title=" ")
