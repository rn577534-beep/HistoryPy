import pytest

from historypy import HistoricalDataset, HistoricalPlace
from historypy.research.geography import (
    great_circle_distance_km,
    places_within_radius,
)


def test_great_circle_distance_known_city_pair():
    distance = great_circle_distance_km(0, 0, 0, 1)
    assert distance == pytest.approx(111.195, abs=0.01)


def test_places_within_radius_sorts_and_omits_ungeocoded():
    dataset = HistoricalDataset(places=(
        HistoricalPlace(id="far", name="Far", latitude=23.0, longitude=91.0),
        HistoricalPlace(id="near", name="Near", latitude=23.7, longitude=90.4),
        HistoricalPlace(id="unknown", name="Unknown"),
    ))
    results = places_within_radius(dataset, 23.7, 90.4, 100)
    assert [item.place_id for item in results] == ["near", "far"][:len(results)]
    assert results[0].distance_km == pytest.approx(0)


def test_places_within_radius_limit_and_validation():
    dataset = HistoricalDataset(places=(
        HistoricalPlace(id="a", name="A", latitude=0, longitude=0),
        HistoricalPlace(id="b", name="B", latitude=0, longitude=0.1),
    ))
    assert len(places_within_radius(dataset, 0, 0, 100, limit=1)) == 1
    with pytest.raises(ValueError, match="radius_km"):
        places_within_radius(dataset, 0, 0, -1)
    with pytest.raises(ValueError, match="latitude"):
        great_circle_distance_km(91, 0, 0, 0)
