"""Time-aware graph views using HistoryPy's explicit calendar semantics."""

from __future__ import annotations

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import HistoricalDate
from historypy.graph.knowledge import HistoricalKnowledgeGraph


def temporal_graph(
    dataset: HistoricalDataset, period: HistoricalDate, *, include_indeterminate: bool = False
) -> HistoricalKnowledgeGraph:
    """Return a graph view around events overlapping a requested period.

    Associated source/place records are retained, as are parent places needed to
    preserve recorded geographic hierarchy edges. Unknown or incomparable event
    dates are excluded unless explicitly requested.
    """
    dataset.require_valid()
    selected_events = []
    for event in dataset.events:
        overlap = event.date.overlaps(period)
        if overlap is True or (overlap is None and include_indeterminate):
            selected_events.append(event)

    keep_ids = {item.id for item in selected_events}
    place_map = {item.id: item for item in dataset.places}
    pending_places = [place_id for event in selected_events for place_id in event.place_ids]
    while pending_places:
        place_id = pending_places.pop()
        if place_id in keep_ids:
            continue
        keep_ids.add(place_id)
        place = place_map.get(place_id)
        if place is not None:
            pending_places.extend(place.parent_place_ids)
    keep_ids.update(source_id for event in selected_events for source_id in event.source_ids)

    full_graph = HistoricalKnowledgeGraph.from_dataset(dataset)
    nodes = tuple(node for node in full_graph.nodes if node.id in keep_ids)
    edges = tuple(
        edge for edge in full_graph.edges
        if edge.source_id in keep_ids and edge.target_id in keep_ids
    )
    return HistoricalKnowledgeGraph(nodes, edges)
