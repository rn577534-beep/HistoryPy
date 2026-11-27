import pytest

from historypy.research.probabilistic_evidence import (
    bayesian_update,
    combine_dempster_shafer,
)


def test_bayesian_update_matches_odds_formula():
    result = bayesian_update(0.2, 4.0)
    assert result.posterior == pytest.approx(0.5)
    assert result.prior == 0.2
    assert "researcher" in result.assumption


@pytest.mark.parametrize("prior", [-0.1, 1.1, float("nan"), True])
def test_bayesian_rejects_invalid_prior(prior):
    with pytest.raises(ValueError):
        bayesian_update(prior, 2.0)


def test_dempster_shafer_combines_independent_mass_assignments():
    result = combine_dempster_shafer(
        {"support": 0.6, "opposition": 0.1, "ignorance": 0.3},
        {"support": 0.5, "opposition": 0.2, "ignorance": 0.3},
    )
    assert result.support + result.opposition + result.ignorance == pytest.approx(1.0)
    assert result.conflict == pytest.approx(0.17)
    assert result.support > result.opposition


def test_dempster_shafer_rejects_total_conflict_and_bad_mass():
    with pytest.raises(ValueError, match="total conflict"):
        combine_dempster_shafer(
            {"support": 1, "opposition": 0, "ignorance": 0},
            {"support": 0, "opposition": 1, "ignorance": 0},
        )
    with pytest.raises(ValueError, match="sum to 1"):
        combine_dempster_shafer(
            {"support": 0.5, "opposition": 0.1, "ignorance": 0.1},
            {"support": 0.5, "opposition": 0.2, "ignorance": 0.3},
        )
