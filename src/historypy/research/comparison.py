"""Transparent side-by-side metric comparisons for historical entities."""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricObservation:
    entity_id: str
    metric: str
    value: float | None
    unit: str
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_id.strip() or not self.metric.strip():
            raise ValueError("entity_id and metric cannot be empty")
        if not self.unit.strip():
            raise ValueError("unit cannot be empty")
        if self.value is not None and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
            or not math.isfinite(self.value)
        ):
            raise ValueError("value must be a finite number or None")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must not contain duplicates")


@dataclass(frozen=True, slots=True)
class MetricComparison:
    metric: str
    unit: str
    observations: tuple[MetricObservation, ...]

    @property
    def known_values(self) -> tuple[MetricObservation, ...]:
        return tuple(item for item in self.observations if item.value is not None)

    @property
    def unknown_entity_ids(self) -> tuple[str, ...]:
        return tuple(item.entity_id for item in self.observations if item.value is None)

    @property
    def spread(self) -> float | None:
        values = [item.value for item in self.observations if item.value is not None]
        return max(values) - min(values) if len(values) >= 2 else None


def compare_metrics(
    observations: Iterable[MetricObservation], *, metric: str | None = None
) -> tuple[MetricComparison, ...]:
    """Group observations by metric and unit without treating missing values as zero."""
    groups: dict[tuple[str, str], list[MetricObservation]] = {}
    seen: set[tuple[str, str, str]] = set()
    for item in observations:
        if not isinstance(item, MetricObservation):
            raise TypeError("observations must contain MetricObservation records")
        if metric is not None and item.metric != metric:
            continue
        identity = (item.metric, item.unit, item.entity_id)
        if identity in seen:
            raise ValueError(f"Duplicate observation for {item.entity_id!r}, {item.metric!r}, {item.unit!r}")
        seen.add(identity)
        groups.setdefault((item.metric, item.unit), []).append(item)
    return tuple(
        MetricComparison(name, unit, tuple(sorted(items, key=lambda x: x.entity_id)))
        for (name, unit), items in sorted(groups.items())
    )
