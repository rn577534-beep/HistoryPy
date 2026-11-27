"""Structural network analysis for historical relationship graphs.

Centrality describes position in a recorded graph only. It is not evidence of
historical importance, source credibility, influence, or truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class NodeCentrality:
    """Structural scores for one node in the recorded relationship graph."""

    node_id: str
    pagerank: float
    hub_score: float
    authority_score: float


@dataclass(frozen=True, slots=True)
class GraphCentralityReport:
    """PageRank and HITS scores with convergence metadata and caveats."""

    scores: tuple[NodeCentrality, ...]
    iterations: int
    converged: bool
    damping: float
    tolerance: float
    node_count: int
    edge_count: int
    interpretation_note: str


def _normalize(values: dict[str, float]) -> dict[str, float]:
    norm = sqrt(sum(value * value for value in values.values()))
    if norm == 0:
        return {key: 0.0 for key in values}
    return {key: value / norm for key, value in values.items()}


def analyze_graph_centrality(
    dataset: HistoricalDataset,
    *,
    damping: float = 0.85,
    tolerance: float = 1e-10,
    max_iterations: int = 500,
) -> GraphCentralityReport:
    """Calculate PageRank and HITS on recorded directed relationships.

    All dataset entities are included, including isolated nodes. Only explicit
    HistoricalRelationship edges are used; evidence/source links are not
    mixed into entity centrality. Parallel relationships count as parallel
    edges. No score is a truth, credibility, or moral-importance measure.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    if isinstance(damping, bool) or not isinstance(damping, (int, float)):
        raise TypeError("damping must be numeric")
    if not isfinite(damping) or not 0 < damping < 1:
        raise ValueError("damping must be finite and strictly between 0 and 1")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise TypeError("tolerance must be numeric")
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be finite and positive")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise TypeError("max_iterations must be an integer")
    if not 1 <= max_iterations <= 100_000:
        raise ValueError("max_iterations must be between 1 and 100,000")

    records = (
        *dataset.events, *dataset.people, *dataset.places,
        *dataset.civilizations, *dataset.organizations,
    )
    node_ids = sorted({record.id for record in records})
    if not node_ids:
        return GraphCentralityReport(
            (), 0, True, float(damping), float(tolerance), 0, 0,
            "No entity nodes are present; no centrality scores were calculated.",
        )
    outgoing = {node_id: [] for node_id in node_ids}
    incoming = {node_id: [] for node_id in node_ids}
    for relationship in dataset.relationships:
        outgoing[relationship.subject_id].append(relationship.object_id)
        incoming[relationship.object_id].append(relationship.subject_id)

    count = len(node_ids)
    rank = {node_id: 1.0 / count for node_id in node_ids}
    pagerank_converged = False
    for iteration in range(1, max_iterations + 1):
        dangling_mass = sum(rank[node_id] for node_id in node_ids if not outgoing[node_id])
        base = (1.0 - damping) / count + damping * dangling_mass / count
        updated = {node_id: base for node_id in node_ids}
        for source_id in node_ids:
            targets = outgoing[source_id]
            if targets:
                contribution = damping * rank[source_id] / len(targets)
                for target_id in targets:
                    updated[target_id] += contribution
        difference = sum(abs(updated[node_id] - rank[node_id]) for node_id in node_ids)
        rank = updated
        if difference <= tolerance:
            pagerank_converged = True
            break

    hubs = {node_id: 1.0 for node_id in node_ids}
    authorities = {node_id: 1.0 for node_id in node_ids}
    hits_converged = False
    hits_iterations = 0
    for hits_iterations in range(1, max_iterations + 1):
        new_authorities = {
            node_id: sum(hubs[source_id] for source_id in incoming[node_id])
            for node_id in node_ids
        }
        new_authorities = _normalize(new_authorities)
        new_hubs = {
            node_id: sum(new_authorities[target_id] for target_id in outgoing[node_id])
            for node_id in node_ids
        }
        new_hubs = _normalize(new_hubs)
        difference = sum(
            abs(new_hubs[node_id] - hubs[node_id])
            + abs(new_authorities[node_id] - authorities[node_id])
            for node_id in node_ids
        )
        hubs, authorities = new_hubs, new_authorities
        if difference <= tolerance:
            hits_converged = True
            break

    scores = tuple(
        NodeCentrality(node_id, rank[node_id], hubs[node_id], authorities[node_id])
        for node_id in node_ids
    )
    scores = tuple(sorted(scores, key=lambda item: (-item.pagerank, item.node_id)))
    return GraphCentralityReport(
        scores=scores,
        iterations=max(iteration, hits_iterations),
        converged=pagerank_converged and hits_converged,
        damping=float(damping),
        tolerance=float(tolerance),
        node_count=count,
        edge_count=len(dataset.relationships),
        interpretation_note=(
            "Scores describe only structural position in the recorded directed "
            "relationship graph. They do not measure historical importance, "
            "causation, source credibility, influence, or truth."
        ),
    )
