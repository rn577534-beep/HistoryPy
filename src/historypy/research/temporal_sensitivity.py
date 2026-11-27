"""Reproducible Monte Carlo sensitivity analysis for uncertain event dates.

Sampling is deliberately explicit and conservative: only fully bounded dates
with matching calendars and matching bound representations can be compared.
The default distribution is discrete uniform over the researcher-supplied
inclusive bounds. It is a sensitivity assumption, not a claim about historical
probability.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from math import floor

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import HistoricalDate


@dataclass(frozen=True, slots=True)
class TemporalSensitivityReport:
    """Estimated ordering frequencies for a pair of uncertain historical events."""

    first_event_id: str
    second_event_id: str
    iterations: int
    seed: int | None
    first_before_second_probability: float
    simultaneous_probability: float
    second_before_first_probability: float
    first_before_second_ci95: tuple[float, float]
    simultaneous_ci95: tuple[float, float]
    second_before_first_ci95: tuple[float, float]
    sampling_policy: str
    limitations: tuple[str, ...]


def _bounds(value: HistoricalDate) -> tuple[int, int, str]:
    if value.calendar == "unspecified":
        raise ValueError("Dates with an unspecified calendar cannot be sampled together")
    if value.earliest is not None or value.latest is not None:
        if value.earliest is None or value.latest is None:
            raise ValueError("Monte Carlo sampling requires both inclusive date bounds")
        if value.precision not in {"day", "month", "year", "decade", "century", "unknown"}:
            raise ValueError("Unsupported date precision")
        return (
            date.fromisoformat(value.earliest).toordinal(),
            date.fromisoformat(value.latest).toordinal(),
            "iso-day",
        )
    if value.earliest_year is None or value.latest_year is None:
        raise ValueError("Monte Carlo sampling requires both inclusive year bounds")
    return value.earliest_year, value.latest_year, "astronomical-year"


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    """Return a two-sided 95% Wilson score interval for a binomial proportion."""
    if total <= 0:
        raise ValueError("total must be positive")
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5)
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def analyze_temporal_sensitivity(
    dataset: HistoricalDataset,
    first_event_id: str,
    second_event_id: str,
    *,
    iterations: int = 10_000,
    seed: int | None = 0,
    distribution: str = "uniform",
    mode_quantile: float = 0.5,
) -> TemporalSensitivityReport:
    """Estimate how often one uncertain event date precedes another.

    Each event is sampled independently and uniformly from its explicit,
    inclusive bounds. No date range is widened for circa notation. Use a
    documented seed for reproducibility. This method does not infer causation,
    event duration, calendar conversion, or a historically calibrated prior.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    if not isinstance(first_event_id, str) or not first_event_id.strip():
        raise ValueError("first_event_id cannot be empty")
    if not isinstance(second_event_id, str) or not second_event_id.strip():
        raise ValueError("second_event_id cannot be empty")
    if first_event_id == second_event_id:
        raise ValueError("Choose two different event IDs")
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise TypeError("iterations must be an integer")
    if not 100 <= iterations <= 1_000_000:
        raise ValueError("iterations must be between 100 and 1,000,000")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("seed must be an integer or None")
    if distribution not in {"uniform", "triangular"}:
        raise ValueError("distribution must be 'uniform' or 'triangular'")
    if (
        isinstance(mode_quantile, bool)
        or not isinstance(mode_quantile, (int, float))
        or not 0.0 <= mode_quantile <= 1.0
    ):
        raise ValueError("mode_quantile must be between 0 and 1")

    events = {event.id: event for event in dataset.events}
    if first_event_id not in events:
        raise KeyError(f"Unknown event ID: {first_event_id}")
    if second_event_id not in events:
        raise KeyError(f"Unknown event ID: {second_event_id}")
    first_date = events[first_event_id].date
    second_date = events[second_event_id].date
    if first_date.calendar != second_date.calendar:
        raise ValueError("Events must use the same calendar; no conversion is performed")
    first_low, first_high, first_unit = _bounds(first_date)
    second_low, second_high, second_unit = _bounds(second_date)
    if first_unit != second_unit:
        raise ValueError("Events must use the same date-bound representation")
    if first_low > first_high or second_low > second_high:
        raise ValueError("Date bounds must be ordered")

    rng = random.Random(seed)

    def sample(low: int, high: int) -> int:
        if distribution == "uniform":
            return rng.randint(low, high)
        mode = low + float(mode_quantile) * (high - low)
        # Half-unit-expanded bounds approximate a discrete triangular distribution.
        value = rng.triangular(low - 0.5, high + 0.5, mode)
        return min(high, max(low, floor(value + 0.5)))

    first_before = simultaneous = second_before = 0
    for _ in range(iterations):
        first_sample = sample(first_low, first_high)
        second_sample = sample(second_low, second_high)
        if first_sample < second_sample:
            first_before += 1
        elif first_sample > second_sample:
            second_before += 1
        else:
            simultaneous += 1

    limitations = [
        "Uniform independent sampling is an explicit sensitivity assumption, not a historical probability model.",
        "Only the supplied inclusive date bounds are sampled; circa notation does not widen them.",
        "Calendar conversion, event duration, causal direction, and dependence between event dates are not inferred.",
    ]
    return TemporalSensitivityReport(
        first_event_id=first_event_id,
        second_event_id=second_event_id,
        iterations=iterations,
        seed=seed,
        first_before_second_probability=first_before / iterations,
        simultaneous_probability=simultaneous / iterations,
        second_before_first_probability=second_before / iterations,
        first_before_second_ci95=_wilson_interval(first_before, iterations),
        simultaneous_ci95=_wilson_interval(simultaneous, iterations),
        second_before_first_ci95=_wilson_interval(second_before, iterations),
        sampling_policy=(
            f"Discrete {distribution}, independent samples over each event's inclusive "
            f"{'day' if first_unit == 'iso-day' else 'astronomical-year'} bounds"
            + (f"; mode quantile={mode_quantile}" if distribution == "triangular" else "")
        ),
        limitations=tuple(limitations),
    )
