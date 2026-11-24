"""Dataset-wide knowledge graph projection with explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class KnowledgeNode:
    id: str
    kind: str
    label: str


@dataclass(frozen=True, slots=True)
class KnowledgeEdge:
    source_id: str
    predicate: str
    target_id: str
    provenance_ids: tuple[str, ...] = ()


class HistoricalKnowledgeGraph:
    """A read-only projection; edges describe recorded links, not verified truth."""

    def __init__(self, nodes: tuple[KnowledgeNode, ...], edges: tuple[KnowledgeEdge, ...]):
        self.nodes = nodes
        self.edges = edges
        self._by_id = {node.id: node for node in nodes}
        if len(self._by_id) != len(nodes):
            raise ValueError("Knowledge graph node IDs must be unique")
        for edge in edges:
            if edge.source_id not in self._by_id or edge.target_id not in self._by_id:
                raise ValueError("Knowledge graph edge references an unknown node")

    @classmethod
    def from_dataset(cls, dataset: HistoricalDataset) -> HistoricalKnowledgeGraph:
        dataset.require_valid()
        groups = (
            ("source", dataset.sources, "title"),
            ("claim", dataset.claims, "statement"),
            ("event", dataset.events, "title"),
            ("person", dataset.people, "name"),
            ("place", dataset.places, "name"),
            ("civilization", dataset.civilizations, "name"),
            ("organization", dataset.organizations, "name"),
            ("relationship", dataset.relationships, "predicate"),
        )
        nodes = tuple(
            KnowledgeNode(item.id, kind, str(getattr(item, label)))
            for kind, records, label in groups for item in records
        )
        edges: list[KnowledgeEdge] = []

        def add(source: str, predicate: str, target: str, provenance: tuple[str, ...] = ()) -> None:
            edges.append(KnowledgeEdge(source, predicate, target, provenance))

        for event in dataset.events:
            for place_id in event.place_ids:
                add(event.id, "occurred_at", place_id, event.source_ids)
            for source_id in event.source_ids:
                add(event.id, "documented_by", source_id)
        for person in dataset.people:
            for source_id in person.source_ids:
                add(person.id, "documented_by", source_id)
        for place in dataset.places:
            for parent_id in place.parent_place_ids:
                add(place.id, "part_of", parent_id, place.source_ids)
            for source_id in place.source_ids:
                add(place.id, "documented_by", source_id)
        for civilization in dataset.civilizations:
            for place_id in civilization.region_place_ids:
                add(civilization.id, "associated_region", place_id, civilization.source_ids)
            for predecessor_id in civilization.predecessor_ids:
                add(civilization.id, "predecessor", predecessor_id, civilization.source_ids)
            for source_id in civilization.source_ids:
                add(civilization.id, "documented_by", source_id)
        for organization in dataset.organizations:
            for place_id in organization.place_ids:
                add(organization.id, "associated_place", place_id, organization.source_ids)
            for person_id in organization.member_person_ids:
                add(organization.id, "has_member", person_id, organization.source_ids)
            for parent_id in organization.parent_organization_ids:
                add(organization.id, "part_of", parent_id, organization.source_ids)
            for source_id in organization.source_ids:
                add(organization.id, "documented_by", source_id)
        for relationship in dataset.relationships:
            add(relationship.subject_id, relationship.predicate, relationship.object_id,
                relationship.source_ids)
        for claim in dataset.claims:
            for subject_id in claim.subject_ids:
                add(claim.id, "concerns", subject_id)
            for event_id in claim.event_ids:
                add(claim.id, "concerns_event", event_id)
        for evidence in dataset.evidence:
            add(evidence.claim_id, evidence.relation, evidence.source_id)
        return cls(nodes, tuple(edges))

    def node(self, node_id: str) -> KnowledgeNode:
        return self._by_id[node_id]

    def neighbors(self, node_id: str, *, predicate: str | None = None) -> tuple[KnowledgeNode, ...]:
        if node_id not in self._by_id:
            raise KeyError(node_id)
        return tuple(
            self._by_id[edge.target_id] for edge in self.edges
            if edge.source_id == node_id and (predicate is None or edge.predicate == predicate)
        )
