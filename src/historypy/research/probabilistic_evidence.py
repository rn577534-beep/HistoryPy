"""Transparent probabilistic evidence updates with explicit assumptions.

These models combine user-supplied quantities. They do not infer source
reliability, priors, likelihoods, or historical truth from citation counts.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class BayesianUpdate:
    """Posterior from a prior and an explicitly supplied likelihood ratio."""

    prior: float
    likelihood_ratio: float
    posterior: float
    assumption: str = "Likelihood ratio is supplied by the researcher, not learned from source counts."


def bayesian_update(prior: float, likelihood_ratio: float) -> BayesianUpdate:
    """Update binary-hypothesis odds using a researcher-supplied likelihood ratio."""
    if isinstance(prior, bool) or not isinstance(prior, (int, float)) or not isfinite(prior):
        raise ValueError("prior must be a finite number")
    if not 0.0 <= prior <= 1.0:
        raise ValueError("prior must be between 0 and 1")
    if (
        isinstance(likelihood_ratio, bool)
        or not isinstance(likelihood_ratio, (int, float))
        or not isfinite(likelihood_ratio)
        or likelihood_ratio < 0
    ):
        raise ValueError("likelihood_ratio must be a finite non-negative number")
    if prior == 0.0:
        posterior = 0.0
    elif prior == 1.0:
        posterior = 1.0
    else:
        numerator = prior * likelihood_ratio
        denominator = numerator + (1.0 - prior)
        posterior = numerator / denominator if denominator else 0.0
    return BayesianUpdate(float(prior), float(likelihood_ratio), posterior)


@dataclass(frozen=True, slots=True)
class DempsterShaferResult:
    """Combined mass on support, opposition, and ignorance plus conflict."""

    support: float
    opposition: float
    ignorance: float
    conflict: float
    combination_rule: str = "normalized Dempster rule"


def combine_dempster_shafer(
    first: Mapping[str, float],
    second: Mapping[str, float],
) -> DempsterShaferResult:
    """Combine two mass assignments over {support, opposition}.

    Each mapping must contain exactly support, opposition, and ignorance,
    with non-negative finite masses summing to one. High conflict is exposed;
    total conflict is rejected because normalized Dempster combination is
    undefined when the conflict mass equals one.
    """
    keys = {"support", "opposition", "ignorance"}

    def validate(mass: Mapping[str, float], name: str) -> dict[str, float]:
        if set(mass) != keys:
            raise ValueError(f"{name} must contain exactly {', '.join(sorted(keys))}")
        values: dict[str, float] = {}
        for key in keys:
            value = mass[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"{name}.{key} must be a finite number")
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name}.{key} must be between 0 and 1")
            values[key] = float(value)
        if abs(sum(values.values()) - 1.0) > 1e-9:
            raise ValueError(f"{name} masses must sum to 1")
        return values

    a = validate(first, "first")
    b = validate(second, "second")
    # Focal sets: support={H}, opposition={not H}, ignorance={H, not H}.
    conflict = a["support"] * b["opposition"] + a["opposition"] * b["support"]
    remaining = 1.0 - conflict
    if remaining <= 1e-12:
        raise ValueError("total conflict: normalized Dempster combination is undefined")
    support = (
        a["support"] * b["support"]
        + a["support"] * b["ignorance"]
        + a["ignorance"] * b["support"]
    ) / remaining
    opposition = (
        a["opposition"] * b["opposition"]
        + a["opposition"] * b["ignorance"]
        + a["ignorance"] * b["opposition"]
    ) / remaining
    ignorance = (a["ignorance"] * b["ignorance"]) / remaining
    return DempsterShaferResult(support, opposition, ignorance, conflict)
