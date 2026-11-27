"""Explainable cost-weighted relationship path search.

Costs are caller-defined traversal preferences, not probabilities or truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from typing import Mapping

from historypy.core.dataset import HistoricalDataset
from historypy.core.entities import HistoricalRelationship


@dataclass(frozen=True, slots=True)
class WeightedRelationshipPath:
    entity_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    total_cost: float
    source_ids: tuple[str, ...]
    relationships_missing_sources: tuple[str, ...]

    @property
    def hop_count(self) -> int:
        return len(self.relationship_ids)


@dataclass(frozen=True, slots=True)
class WeightedPathReport:
    paths: tuple[WeightedRelationshipPath, ...]
    explored_states: int
    truncated: bool
    cost_policy: str


def find_weighted_relationship_paths(
    dataset: HistoricalDataset,
    start_entity_id: str,
    end_entity_id: str,
    *,
    edge_costs: Mapping[str, float] | None = None,
    default_edge_cost: float = 1.0,
    max_hops: int = 8,
    limit: int = 20,
    max_explored_states: int = 10000,
) -> WeightedPathReport:
    """Find simple paths ordered by explicit positive edge traversal costs.

    Unspecified edges use default_edge_cost. Costs are not source reliability
    estimates. Source gaps are returned separately for researcher review.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    for value, name, minimum, maximum in (
        (max_hops, "max_hops", 1, 12),
        (limit, "limit", 1, 500),
        (max_explored_states, "max_explored_states", 1, 100000),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    if isinstance(default_edge_cost, bool) or not isinstance(default_edge_cost, (int, float)):
        raise TypeError("default_edge_cost must be a number")
    if default_edge_cost <= 0:
        raise ValueError("default_edge_cost must be positive")
    costs = dict(edge_costs or {})
    relationships = {edge.id: edge for edge in dataset.relationships}
    unknown = set(costs) - set(relationships)
    if unknown:
        raise KeyError(f"Unknown relationship cost IDs: {', '.join(sorted(unknown))}")
    for key, value in costs.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Cost for {key!r} must be numeric")
        if value <= 0:
            raise ValueError(f"Cost for {key!r} must be positive")
    nodes = {
        item.id for collection in (
            dataset.events, dataset.people, dataset.places,
            dataset.civilizations, dataset.organizations,
        ) for item in collection
    }
    if start_entity_id not in nodes:
        raise KeyError(f"Unknown start entity id: {start_entity_id}")
    if end_entity_id not in nodes:
        raise KeyError(f"Unknown end entity id: {end_entity_id}")
    if start_entity_id == end_entity_id:
        return WeightedPathReport((), 0, False, "caller-supplied positive edge costs")

    adjacency: dict[str, list[tuple[str, HistoricalRelationship, float]]] = {
        node: [] for node in nodes
    }
    for edge in sorted(dataset.relationships, key=lambda item: item.id):
        adjacency[edge.subject_id].append((
            edge.object_id, edge, float(costs.get(edge.id, default_edge_cost))
        ))
    serial = count()
    queue = [(0.0, next(serial), (start_entity_id,), ())]
    results: list[WeightedRelationshipPath] = []
    explored = 0
    truncated = False
    while queue and len(results) < limit:
        total_cost, _, entity_path, edge_path = heappop(queue)
        explored += 1
        if explored > max_explored_states:
            truncated = True
            break
        current = entity_path[-1]
        if current == end_entity_id:
            sources = tuple(sorted({
                source_id for edge in edge_path for source_id in edge.source_ids
            }))
            missing = tuple(edge.id for edge in edge_path if not edge.source_ids)
            results.append(WeightedRelationshipPath(
                entity_path, tuple(edge.id for edge in edge_path),
                round(total_cost, 12), sources, missing,
            ))
            continue
        if len(edge_path) >= max_hops:
            continue
        for neighbor, edge, cost in adjacency[current]:
            if neighbor in entity_path:
                continue
            heappush(queue, (
                total_cost + cost, next(serial),
                entity_path + (neighbor,), edge_path + (edge,),
            ))
    if queue and len(results) >= limit:
        truncated = True
    return WeightedPathReport(
        tuple(results), explored, truncated,
        "sum of caller-supplied positive traversal costs; not credibility",
    )
