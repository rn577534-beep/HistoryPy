"""Time-aware graph views using HistoryPy's explicit calendar semantics."""

from __future__ import annotations

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import HistoricalDate
from historypy.graph.knowledge import HistoricalKnowledgeGraph


def temporal_graph(
    dataset: HistoricalDataset, period: HistoricalDate, *, include_indeterminate: bool = False
) -> HistoricalKnowledgeGraph:
    """Project a graph containing date-compatible events and their linked records.

    Unknown or incomparable dates are excluded unless explicitly requested.
    This is a dataset filter, not a claim that an event happened throughout its range.
    """
    dataset.require_valid()
    selected_events = []
    for event in dataset.events:
        overlap = event.date.overlaps(period)
        if overlap is True or (overlap is None and include_indeterminate):
            selected_events.append(event)
    selected_ids = {item.id for item in selected_events}
    source_ids = {source_id for item in selected_events for source_id in item.source_ids}
    place_ids = {place_id for item in selected_events for place_id in item.place_ids}
    selected_dataset = HistoricalDataset(
        sources=tuple(item for item in dataset.sources if item.id in source_ids),
        events=tuple(selected_events),
        places=tuple(item for item in dataset.places if item.id in place_ids),
        relationships=tuple(
            item for item in dataset.relationships
            if item.subject_id in selected_ids | place_ids
            and item.object_id in selected_ids | place_ids
        ),
    )
    return HistoricalKnowledgeGraph.from_dataset(selected_dataset)
