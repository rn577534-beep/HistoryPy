"""Dependency-free exports for historical graph, map, and timeline visualizations.

The returned structures can be consumed by NetworkX, Cytoscape, D3, Plotly,
Leaflet, GeoPandas, or custom applications. Exports preserve provenance and
mark missing coordinates/dates rather than inventing them.
"""
from __future__ import annotations

import json
from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.research.timeline import timeline_for_dataset


def dataset_graph_data(dataset: HistoricalDataset) -> dict[str, Any]:
    """Return JSON-ready nodes and edges for entity and evidence network views."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    collections = (
        ("event", dataset.events, lambda item: item.title),
        ("person", dataset.people, lambda item: item.name),
        ("place", dataset.places, lambda item: item.name),
        ("civilization", dataset.civilizations, lambda item: item.name),
        ("organization", dataset.organizations, lambda item: item.name),
    )
    for kind, records, label_fn in collections:
        for item in records:
            nodes.append({
                "id": item.id, "label": label_fn(item), "kind": kind,
                "source_ids": list(getattr(item, "source_ids", ())),
            })
    for item in dataset.claims:
        nodes.append({"id": "claim:" + item.id, "label": item.statement, "kind": "claim"})
    for item in dataset.sources:
        nodes.append({"id": "source:" + item.id, "label": item.title, "kind": "source"})

    for relationship in dataset.relationships:
        edges.append({
            "id": relationship.id,
            "source": relationship.subject_id,
            "target": relationship.object_id,
            "kind": "relationship",
            "predicate": relationship.predicate,
            "source_ids": list(relationship.source_ids),
            "claim_ids": list(relationship.claim_ids),
            "valid_from": relationship.valid_from.display() if relationship.valid_from else None,
            "valid_to": relationship.valid_to.display() if relationship.valid_to else None,
            "confidence": relationship.confidence,
        })
    for event in dataset.events:
        for place_id in event.place_ids:
            edges.append({
                "id": f"event-place:{event.id}:{place_id}",
                "source": event.id, "target": place_id,
                "kind": "occurred_at", "predicate": "occurred_at",
                "source_ids": list(event.source_ids),
            })
    for index, link in enumerate(dataset.evidence):
        edges.append({
            "id": f"evidence:{index}:{link.claim_id}:{link.source_id}",
            "source": "claim:" + link.claim_id,
            "target": "source:" + link.source_id,
            "kind": "evidence",
            "predicate": link.relation,
            "locator": link.locator or link.page or link.paragraph or link.archive_shelfmark,
            "quotation": link.quotation,
        })
    for source in dataset.sources:
        for derived_id in source.derived_from_source_ids:
            edges.append({
                "id": f"derived:{source.id}:{derived_id}",
                "source": "source:" + source.id,
                "target": "source:" + derived_id,
                "kind": "source_derivation",
                "predicate": "derived_from",
            })
    return {"nodes": nodes, "edges": edges}


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def to_graphviz_dot(dataset: HistoricalDataset) -> str:
    """Export entity, claim, and source relationships as Graphviz DOT."""
    graph = dataset_graph_data(dataset)
    lines = ["digraph HistoryPy {", '  graph [rankdir="LR"];', '  node [shape="box"];']
    for node in graph["nodes"]:
        label = _dot_escape(str(node["label"]))
        kind = _dot_escape(str(node["kind"]))
        lines.append(f'  "{_dot_escape(node["id"])}" [label="{label}", kind="{kind}"];')
    for edge in graph["edges"]:
        label = _dot_escape(str(edge.get("predicate", edge["kind"])))
        lines.append(
            f'  "{_dot_escape(edge["source"])}" -> "{_dot_escape(edge["target"])}" '
            f'[label="{label}", kind="{_dot_escape(edge["kind"])}"];'
        )
    lines.append("}")
    return "\n".join(lines)


def to_geojson(dataset: HistoricalDataset) -> dict[str, Any]:
    """Export geocoded historical places as a GeoJSON FeatureCollection."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    event_ids_by_place: dict[str, list[str]] = {}
    for event in dataset.events:
        for place_id in event.place_ids:
            event_ids_by_place.setdefault(place_id, []).append(event.id)
    features = []
    for place in dataset.places:
        if place.latitude is None or place.longitude is None:
            continue
        features.append({
            "type": "Feature",
            "id": place.id,
            "geometry": {
                "type": "Point",
                "coordinates": [place.longitude, place.latitude],
            },
            "properties": {
                "name": place.name,
                "place_type": place.place_type,
                "description": place.description,
                "source_ids": list(place.source_ids),
                "event_ids": sorted(event_ids_by_place.get(place.id, [])),
                "coordinates_are_historical_estimates": True,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def timeline_visualization_data(
    dataset: HistoricalDataset, *, include_indeterminate: bool = True
) -> dict[str, Any]:
    """Return interval data for Gantt/timeline renderers without date conversion."""
    result = timeline_for_dataset(dataset, include_indeterminate=include_indeterminate)
    entries = []
    for entry in result.entries:
        value = entry.date
        entries.append({
            "id": entry.record_id,
            "kind": entry.kind,
            "label": entry.label,
            "date_label": entry.date_label,
            "calendar": value.calendar if value else None,
            "start": value.earliest or value.earliest_year if value else None,
            "end": value.latest or value.latest_year if value else None,
            "precision": value.precision if value else "unknown",
            "circa": value.circa if value else False,
            "source_ids": list(entry.source_ids),
            "interval_is_uncertain": bool(
                value and (
                    value.circa or value.precision != "day"
                    or value.earliest != value.latest
                    or value.earliest_year != value.latest_year
                )
            ),
        })
    return {
        "entries": entries,
        "undated_count": result.undated_count,
        "excluded_indeterminate_count": result.excluded_indeterminate_count,
    }


def export_visualization_json(data: dict[str, Any], *, indent: int = 2) -> str:
    """Serialize an exported visualization structure as stable JSON text."""
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")
    if isinstance(indent, bool) or not isinstance(indent, int) or indent < 0:
        raise ValueError("indent must be a non-negative integer")
    return json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True)
