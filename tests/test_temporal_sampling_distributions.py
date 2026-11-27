import pytest

from historypy import HistoricalDataset, HistoricalDate, HistoricalEvent
from historypy.research.temporal_sensitivity import analyze_temporal_sensitivity


def make_dataset():
    return HistoricalDataset(events=(
        HistoricalEvent("a", "A", HistoricalDate(
            earliest_year=0, latest_year=100, calendar="julian"
        )),
        HistoricalEvent("b", "B", HistoricalDate(
            earliest_year=40, latest_year=60, calendar="julian"
        )),
    ))


def test_triangular_sampling_is_reproducible_and_explicit():
    first = analyze_temporal_sensitivity(
        make_dataset(), "a", "b", iterations=5000, seed=7,
        distribution="triangular", mode_quantile=0.8,
    )
    second = analyze_temporal_sensitivity(
        make_dataset(), "a", "b", iterations=5000, seed=7,
        distribution="triangular", mode_quantile=0.8,
    )
    assert first == second
    assert "triangular" in first.sampling_policy


def test_temporal_distribution_options_are_validated():
    with pytest.raises(ValueError, match="distribution"):
        analyze_temporal_sensitivity(
            make_dataset(), "a", "b", distribution="normal"
        )
    with pytest.raises(ValueError, match="mode_quantile"):
        analyze_temporal_sensitivity(
            make_dataset(), "a", "b", distribution="triangular", mode_quantile=1.5
        )
