"""Evidence-aware multi-hop traversal over typed historical relationships.

The planner accepts explicit canonical entity IDs and predicate constraints.
It does not infer entities or predicates from free text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from historypy.core.dataset import HistoricalDataset
from historypy.core.entities import HistoricalRelationship
from historypy.core.models import HistoricalDate
from historypy.graph.relationships import Direction, RelationshipGraph

Traversal = Literal["forward", "reverse"]


@dataclass(frozen=True, slots=True)
class RelationshipPathQuery:
    """A bounded path request between two canonical entity identifiers."""

    start_entity_id: str
    end_entity_id: str
    max_hops: int = 3
    predicates: tuple[str | None, ...] = ()
    direction: Direction = "outgoing"
    limit: int = 20

    def __post_init__(self) -> None:
        if not self.start_entity_id.strip() or not self.end_entity_id.strip():
            raise ValueError("start_entity_id and end_entity_id cannot be empty")
        if (
            not isinstance(self.max_hops, int) or isinstance(self.max_hops, bool)
            or not 1 <= self.max_hops <= 12
        ):
            raise ValueError("max_hops must be an integer between 1 and 12")
        if len(self.predicates) > self.max_hops:
            raise ValueError("predicates cannot contain more entries than max_hops")
        if any(value is not None and not value.strip() for value in self.predicates):
            raise ValueError("predicate constraints cannot be empty strings")
        if self.direction not in {"outgoing", "incoming", "both"}:
            raise ValueError(f"Unsupported direction: {self.direction}")
        if (
            not isinstance(self.limit, int) or isinstance(self.limit, bool)
            or not 1 <= self.limit <= 500
        ):
            raise ValueError("limit must be an integer between 1 and 500")


@dataclass(frozen=True, slots=True)
class RelationshipPathStep:
    """One directed relationship traversed in its recorded or reverse direction."""

    relationship_id: str
    subject_id: str
    predicate: str
    object_id: str
    traversal: Traversal
    source_ids: tuple[str, ...]
    valid_from: HistoricalDate | None
    valid_to: HistoricalDate | None


@dataclass(frozen=True, slots=True)
class RelationshipPath:
    """A simple entity path retaining every relationship and source reference."""

    entity_ids: tuple[str, ...]
    steps: tuple[RelationshipPathStep, ...]
    source_ids: tuple[str, ...]
    relationships_missing_sources: tuple[str, ...]

    @property
    def hop_count(self) -> int:
        return len(self.steps)

    @property
    def has_source_gap(self) -> bool:
        return bool(self.relationships_missing_sources)


@dataclass(frozen=True, slots=True)
class RelationshipPathSearchReport:
    """Bounded path-search results with explicit truncation and work counters."""

    query: RelationshipPathQuery
    paths: tuple[RelationshipPath, ...]
    explored_states: int
    truncated: bool


def find_relationship_paths(
    dataset: HistoricalDataset,
    query: RelationshipPathQuery,
) -> RelationshipPathSearchReport:
    """Enumerate deterministic simple paths while preserving relationship evidence.

    Each edge remains directed in the result even when the traversal follows it
    in reverse. Repeated entities are prohibited within a path, so cycles cannot
    create infinite searches. A path is a structural hypothesis, not proof that
    the whole chain is historically true or contemporaneous.
    """
    if not isinstance(query, RelationshipPathQuery):
        raise TypeError("query must be a RelationshipPathQuery")
    dataset.require_valid()
    graph = RelationshipGraph.from_dataset(dataset)
    if query.start_entity_id not in graph.entity_ids:
        raise KeyError(f"Unknown start entity id: {query.start_entity_id}")
    if query.end_entity_id not in graph.entity_ids:
        raise KeyError(f"Unknown end entity id: {query.end_entity_id}")
    if query.start_entity_id == query.end_entity_id:
        return RelationshipPathSearchReport(query, (), 0, False)

    adjacency: dict[str, list[tuple[str, HistoricalRelationship, Traversal]]] = {
        entity_id: [] for entity_id in graph.entity_ids
    }
    for edge in sorted(graph.relationships, key=lambda item: item.id):
        if query.direction in {"outgoing", "both"}:
            adjacency[edge.subject_id].append((edge.object_id, edge, "forward"))
        if query.direction in {"incoming", "both"}:
            adjacency[edge.object_id].append((edge.subject_id, edge, "reverse"))

    paths: list[RelationshipPath] = []
    explored = 0
    truncated = False
    stack: list[tuple[tuple[str, ...], tuple[RelationshipPathStep, ...]]] = [
        ((query.start_entity_id,), ())
    ]
    while stack:
        entity_path, steps = stack.pop()
        explored += 1
        current = entity_path[-1]
        depth = len(steps)
        if depth >= query.max_hops:
            continue
        expected = query.predicates[depth] if depth < len(query.predicates) else None
        candidates = adjacency[current]
        for neighbor, edge, traversal in reversed(candidates):
            if neighbor in entity_path:
                continue
            if expected is not None and edge.predicate != expected:
                continue
            step = RelationshipPathStep(
                relationship_id=edge.id,
                subject_id=edge.subject_id,
                predicate=edge.predicate,
                object_id=edge.object_id,
                traversal=traversal,
                source_ids=tuple(edge.source_ids),
                valid_from=edge.valid_from,
                valid_to=edge.valid_to,
            )
            next_entities = entity_path + (neighbor,)
            next_steps = steps + (step,)
            if neighbor == query.end_entity_id:
                source_ids = tuple(sorted({
                    source_id for item in next_steps for source_id in item.source_ids
                }))
                missing = tuple(sorted(
                    item.relationship_id for item in next_steps if not item.source_ids
                ))
                paths.append(RelationshipPath(
                    entity_ids=next_entities,
                    steps=next_steps,
                    source_ids=source_ids,
                    relationships_missing_sources=missing,
                ))
                if len(paths) > query.limit:
                    truncated = True
                    break
            else:
                stack.append((next_entities, next_steps))
        if truncated:
            break

    selected = tuple(paths[:query.limit])
    return RelationshipPathSearchReport(
        query=query,
        paths=selected,
        explored_states=explored,
        truncated=truncated,
    )


__all__ = [
    "RelationshipPath",
    "RelationshipPathQuery",
    "RelationshipPathSearchReport",
    "RelationshipPathStep",
    "find_relationship_paths",
]
