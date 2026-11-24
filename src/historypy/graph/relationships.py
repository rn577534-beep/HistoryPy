"""Deterministic graph operations over historical relationship records."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Literal

from historypy.core.entities import HistoricalRelationship

Direction = Literal["outgoing", "incoming", "both"]


class RelationshipGraph:
    """A directed multigraph preserving relationship predicates and provenance."""

    def __init__(
        self,
        entity_ids: Iterable[str],
        relationships: Iterable[HistoricalRelationship],
    ) -> None:
        self._nodes = frozenset(entity_ids)
        self._edges = tuple(relationships)
        for edge in self._edges:
            if edge.subject_id not in self._nodes or edge.object_id not in self._nodes:
                raise ValueError(
                    f"Relationship {edge.id!r} references an entity absent from the graph"
                )

    @property
    def entity_ids(self) -> frozenset[str]:
        """All entity identifiers represented in this graph."""
        return self._nodes

    @property
    def relationships(self) -> tuple[HistoricalRelationship, ...]:
        """All original relationship records in insertion order."""
        return self._edges

    def neighbors(
        self,
        entity_id: str,
        *,
        predicate: str | None = None,
        direction: Direction = "outgoing",
    ) -> tuple[str, ...]:
        """Return unique adjacent entity IDs in stable insertion order."""
        self._require_node(entity_id)
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError(f"Unsupported direction: {direction}")
        found: list[str] = []
        for edge in self._edges:
            if predicate is not None and edge.predicate != predicate:
                continue
            candidate = None
            if direction in {"outgoing", "both"} and edge.subject_id == entity_id:
                candidate = edge.object_id
            elif direction in {"incoming", "both"} and edge.object_id == entity_id:
                candidate = edge.subject_id
            if candidate is not None and candidate not in found:
                found.append(candidate)
        return tuple(found)

    def shortest_path(
        self,
        start_id: str,
        end_id: str,
        *,
        predicate: str | None = None,
        direction: Direction = "outgoing",
    ) -> tuple[str, ...] | None:
        """Find a shortest unweighted path; return None if no path exists."""
        self._require_node(start_id)
        self._require_node(end_id)
        if direction not in {"outgoing", "incoming", "both"}:
            raise ValueError(f"Unsupported direction: {direction}")
        if start_id == end_id:
            return (start_id,)
        queue = deque([(start_id,)])
        visited = {start_id}
        while queue:
            path = queue.popleft()
            current = path[-1]
            for neighbor in self.neighbors(
                current, predicate=predicate, direction=direction
            ):
                if neighbor in visited:
                    continue
                next_path = path + (neighbor,)
                if neighbor == end_id:
                    return next_path
                visited.add(neighbor)
                queue.append(next_path)
        return None

    def connected_components(self) -> tuple[tuple[str, ...], ...]:
        """Return weakly connected components, including isolated entities."""
        remaining = set(self._nodes)
        components: list[tuple[str, ...]] = []
        for start in sorted(self._nodes):
            if start not in remaining:
                continue
            queue = deque([start])
            remaining.remove(start)
            component = []
            while queue:
                current = queue.popleft()
                component.append(current)
                for neighbor in self.neighbors(current, direction="both"):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
            components.append(tuple(sorted(component)))
        return tuple(components)

    def _require_node(self, entity_id: str) -> None:
        if entity_id not in self._nodes:
            raise KeyError(f"Unknown entity id: {entity_id}")
