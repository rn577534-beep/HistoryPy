"""Geospatial queries for historical places with known coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from historypy.core.dataset import HistoricalDataset
from historypy.core.entities import HistoricalPlace


@dataclass(frozen=True, slots=True)
class PlaceDistance:
    """A place and its great-circle distance from a query point, in kilometres."""

    place_id: str
    name: str
    latitude: float
    longitude: float
    distance_km: float


def _validate_coordinate(value: float, name: str, lower: float, upper: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not lower <= value <= upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")


def great_circle_distance_km(
    latitude_a: float, longitude_a: float,
    latitude_b: float, longitude_b: float,
) -> float:
    """Return spherical great-circle distance using the mean Earth radius."""
    for value, name, lower, upper in (
        (latitude_a, "latitude_a", -90, 90),
        (latitude_b, "latitude_b", -90, 90),
        (longitude_a, "longitude_a", -180, 180),
        (longitude_b, "longitude_b", -180, 180),
    ):
        _validate_coordinate(value, name, lower, upper)
    lat1, lat2 = radians(latitude_a), radians(latitude_b)
    delta_lat = lat2 - lat1
    delta_lon = radians(longitude_b - longitude_a)
    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 6371.0088 * 2 * asin(sqrt(min(1.0, haversine)))


def places_within_radius(
    dataset: HistoricalDataset,
    latitude: float,
    longitude: float,
    radius_km: float,
    *,
    limit: int | None = None,
) -> tuple[PlaceDistance, ...]:
    """Find geocoded places within a radius, nearest first.

    Places without coordinates are omitted. Distances are approximate spherical
    distances, not survey-grade measurements; historical location uncertainty
    must be represented and assessed separately by researchers.
    """
    _validate_coordinate(latitude, "latitude", -90, 90)
    _validate_coordinate(longitude, "longitude", -180, 180)
    if isinstance(radius_km, bool) or not isinstance(radius_km, (int, float)):
        raise TypeError("radius_km must be a number")
    if radius_km < 0:
        raise ValueError("radius_km cannot be negative")
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int)
    ):
        raise TypeError("limit must be an integer or None")
    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative")
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")

    matches: list[PlaceDistance] = []
    for place in dataset.places:
        if place.latitude is None or place.longitude is None:
            continue
        distance = great_circle_distance_km(
            latitude, longitude, place.latitude, place.longitude
        )
        if distance <= radius_km:
            matches.append(PlaceDistance(
                place_id=place.id,
                name=place.name,
                latitude=place.latitude,
                longitude=place.longitude,
                distance_km=distance,
            ))
    matches.sort(key=lambda item: (item.distance_km, item.place_id))
    return tuple(matches if limit is None else matches[:limit])
