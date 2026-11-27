import pytest

from historypy import (
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalRelationship,
    analyze_graph_centrality,
    analyze_temporal_sensitivity,
)


def make_network_dataset():
    return HistoricalDataset(
        people=(
            HistoricalPerson("a", "A"),
            HistoricalPerson("b", "B"),
            HistoricalPerson("c", "C"),
            HistoricalPerson("isolated", "Isolated"),
        ),
        relationships=(
            HistoricalRelationship("ab", "a", "linked_to", "b"),
            HistoricalRelationship("ac", "a", "linked_to", "c"),
            HistoricalRelationship("bc", "b", "linked_to", "c"),
        ),
    )


def test_graph_centrality_returns_normalized_pagerank_and_hubs():
    report = analyze_graph_centrality(make_network_dataset())
    assert report.converged
    assert report.node_count == 4
    assert report.edge_count == 3
    assert sum(item.pagerank for item in report.scores) == pytest.approx(1.0)
    assert report.scores[0].node_id == "c"
    scores = {item.node_id: item for item in report.scores}
    assert scores["a"].hub_score > scores["c"].hub_score
    assert scores["c"].authority_score > scores["a"].authority_score
    assert scores["isolated"].pagerank > 0


def test_graph_centrality_empty_and_non_converged_cases_are_reported():
    empty = analyze_graph_centrality(HistoricalDataset())
    assert empty.node_count == 0
    assert empty.converged
    one_step = analyze_graph_centrality(make_network_dataset(), max_iterations=1)
    assert not one_step.converged


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"damping": 1.0}, ValueError),
        ({"tolerance": 0.0}, ValueError),
        ({"max_iterations": 0}, ValueError),
    ],
)
def test_graph_centrality_validates_parameters(kwargs, error):
    with pytest.raises(error):
        analyze_graph_centrality(make_network_dataset(), **kwargs)


def make_temporal_dataset():
    return HistoricalDataset(
        events=(
            HistoricalEvent(
                "early", "Earlier event",
                HistoricalDate(
                    earliest_year=100, latest_year=100,
                    precision="year", calendar="gregorian",
                ),
            ),
            HistoricalEvent(
                "uncertain", "Uncertain event",
                HistoricalDate(
                    earliest_year=99, latest_year=101,
                    precision="year", calendar="gregorian", circa=True,
                ),
            ),
            HistoricalEvent(
                "later", "Later event",
                HistoricalDate(
                    earliest_year=110, latest_year=112,
                    precision="year", calendar="gregorian",
                ),
            ),
        )
    )


def test_temporal_sensitivity_is_reproducible_and_reports_uncertainty():
    dataset = make_temporal_dataset()
    first = analyze_temporal_sensitivity(
        dataset, "early", "uncertain", iterations=5000, seed=42
    )
    second = analyze_temporal_sensitivity(
        dataset, "early", "uncertain", iterations=5000, seed=42
    )
    assert first == second
    assert first.first_before_second_probability == pytest.approx(2 / 3, abs=0.03)
    assert first.first_before_second_ci95[0] <= first.first_before_second_probability
    assert first.first_before_second_ci95[1] >= first.first_before_second_probability
    assert sum((
        first.first_before_second_probability,
        first.simultaneous_probability,
        first.second_before_first_probability,
    )) == pytest.approx(1.0)
    assert "not a historical probability model" in first.limitations[0]


def test_temporal_sensitivity_validates_calendar_bounds_ids_and_iterations():
    dataset = make_temporal_dataset()
    with pytest.raises(ValueError, match="different event"):
        analyze_temporal_sensitivity(dataset, "early", "early")
    with pytest.raises(ValueError, match="between 100"):
        analyze_temporal_sensitivity(dataset, "early", "later", iterations=10)
    with pytest.raises(KeyError):
        analyze_temporal_sensitivity(dataset, "missing", "later")

    incompatible = HistoricalDataset(events=(
        HistoricalEvent("julian", "Julian event", HistoricalDate(
            earliest_year=1, latest_year=2, calendar="julian"
        )),
        HistoricalEvent("gregorian", "Gregorian event", HistoricalDate(
            earliest_year=1, latest_year=2, calendar="gregorian"
        )),
    ))
    with pytest.raises(ValueError, match="same calendar"):
        analyze_temporal_sensitivity(incompatible, "julian", "gregorian")


def test_temporal_sensitivity_requires_fully_bounded_dates():
    dataset = HistoricalDataset(events=(
        HistoricalEvent("bounded", "Bounded", HistoricalDate(
            earliest_year=1, latest_year=2, calendar="julian"
        )),
        HistoricalEvent("open", "Open", HistoricalDate(
            earliest_year=1, calendar="julian"
        )),
    ))
    with pytest.raises(ValueError, match="both inclusive"):
        analyze_temporal_sensitivity(dataset, "bounded", "open")
