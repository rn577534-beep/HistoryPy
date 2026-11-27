import pytest

from historypy.research.geography import distance_interval_km


def test_distance_interval_includes_coordinate_uncertainty():
    lower, upper = distance_interval_km(
        0, 0, 0, 1, uncertainty_radius_a_km=2, uncertainty_radius_b_km=3
    )
    assert lower == pytest.approx(106.195, abs=0.02)
    assert upper == pytest.approx(116.195, abs=0.02)


def test_distance_interval_rejects_invalid_uncertainty():
    with pytest.raises(ValueError, match="non-negative"):
        distance_interval_km(0, 0, 0, 1, uncertainty_radius_a_km=-1)
