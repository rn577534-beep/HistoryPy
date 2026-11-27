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

    # Link every source-cited entity to its bibliographic source node.
    for node in tuple(nodes):
        for source_id in node.get("source_ids", []):
            edges.append({
                "id": f"entity-source:{node['id']}:{source_id}",
                "source": node["id"],
                "target": "source:" + source_id,
                "kind": "entity_source",
                "predicate": "cited_by",
            })

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


def render_visualization_html(
    dataset: HistoricalDataset,
    *,
    title: str = "HistoryPy research visualization",
    max_nodes: int = 250,
) -> str:
    """Render a dependency-free, self-contained interactive HTML research view.

    The report contains a schematic relationship network, a date-interval
    table, and a coordinate scatter for geocoded places. The coordinate panel
    is not a basemap or historical-boundary reconstruction. Use GeoJSON with
    a dedicated GIS renderer for geographic context.
    """
    from html import escape
    from math import cos, pi, sin

    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title cannot be empty")
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int):
        raise TypeError("max_nodes must be an integer")
    if not 1 <= max_nodes <= 500:
        raise ValueError("max_nodes must be between 1 and 500")

    graph = dataset_graph_data(dataset)
    nodes = graph["nodes"]
    if len(nodes) > max_nodes:
        raise ValueError(
            f"HTML graph view supports at most {max_nodes} nodes; "
            "use dataset_graph_data() for larger networks"
        )
    width, height = 900, 600
    center_x, center_y = width / 2, height / 2
    radius = min(width, height) * 0.36
    positions = {}
    for index, node in enumerate(nodes):
        angle = -pi / 2 + 2 * pi * index / max(1, len(nodes))
        positions[node["id"]] = (
            center_x + radius * cos(angle),
            center_y + radius * sin(angle),
        )

    edge_svg = []
    for edge in graph["edges"]:
        start = positions.get(edge["source"])
        end = positions.get(edge["target"])
        if start is None or end is None:
            continue
        edge_svg.append(
            f'<line x1="{start[0]:.2f}" y1="{start[1]:.2f}" '
            f'x2="{end[0]:.2f}" y2="{end[1]:.2f}" '
            f'class="edge" data-kind="{escape(str(edge["kind"]), quote=True)}">'
            f'<title>{escape(str(edge.get("predicate", edge["kind"])))}</title></line>'
        )
    node_svg = []
    for node in nodes:
        x, y = positions[node["id"]]
        node_svg.append(
            f'<g class="node" tabindex="0" role="img" '
            f'aria-label="{escape(str(node["label"]), quote=True)}">'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8"></circle>'
            f'<title>{escape(str(node["label"]))} ({escape(str(node["kind"]))})</title>'
            f'<text x="{x + 11:.2f}" y="{y + 4:.2f}">'
            f'{escape(str(node["label"])[:42])}</text></g>'
        )
    graph_svg = (
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Schematic historical relationship network">'
        + "".join(edge_svg) + "".join(node_svg) + "</svg>"
    )

    timeline = timeline_visualization_data(dataset)
    timeline_rows = []
    for entry in timeline["entries"]:
        timeline_rows.append(
            "<tr>"
            f'<th scope="row">{escape(str(entry["label"]))}</th>'
            f'<td>{escape(str(entry["date_label"]))}</td>'
            f'<td>{escape(str(entry["calendar"] or "unknown"))}</td>'
            f'<td>{escape(str(entry["precision"]))}</td>'
            f'<td>{"Yes" if entry["interval_is_uncertain"] else "No"}</td>'
            "</tr>"
        )
    if not timeline_rows:
        timeline_rows.append('<tr><td colspan="5">No dated records available.</td></tr>')
    timeline_html = (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Event</th><th>Date expression</th><th>Calendar</th>'
        '<th>Precision</th><th>Uncertain interval</th>'
        '</tr></thead><tbody>' + "".join(timeline_rows) + "</tbody></table></div>"
    )

    places = [
        place for place in dataset.places
        if place.latitude is not None and place.longitude is not None
    ]
    map_marks = []
    if places:
        min_lon = min(place.longitude for place in places)
        max_lon = max(place.longitude for place in places)
        min_lat = min(place.latitude for place in places)
        max_lat = max(place.latitude for place in places)
        lon_span = max(max_lon - min_lon, 1e-9)
        lat_span = max(max_lat - min_lat, 1e-9)
        for place in places:
            x = 40 + (place.longitude - min_lon) / lon_span * 820
            y = 540 - (place.latitude - min_lat) / lat_span * 480
            map_marks.append(
                f'<g class="node" tabindex="0" role="img" '
                f'aria-label="{escape(place.name, quote=True)}">'
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7"></circle>'
                f'<title>{escape(place.name)}: {place.latitude}, {place.longitude}</title>'
                f'<text x="{x + 10:.2f}" y="{y + 4:.2f}">'
                f'{escape(place.name[:42])}</text></g>'
            )
    map_svg = (
        '<svg viewBox="0 0 900 600" role="img" '
        'aria-label="Schematic latitude and longitude coordinate plot">'
        '<rect x="1" y="1" width="898" height="598" class="plot-bg"></rect>'
        + "".join(map_marks) + "</svg>"
    )
    if not map_marks:
        map_svg = "<p>No places with researcher-supplied coordinates are available.</p>"

    safe_title = escape(title)
    return f\'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
:root{{color-scheme:light dark;font-family:system-ui,sans-serif}}
body{{margin:0;padding:1.25rem;line-height:1.5}}
main{{max-width:1100px;margin:auto}}
nav{{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0}}
button{{padding:.65rem 1rem;border:1px solid #888;border-radius:.5rem;background:transparent;color:inherit;cursor:pointer}}
button[aria-pressed="true"]{{background:#245b85;color:white;border-color:#245b85}}
.panel{{display:none;border:1px solid #8886;border-radius:.75rem;padding:1rem;overflow:auto}}
.panel.active{{display:block}}
svg{{width:100%;height:auto;min-width:320px;max-height:650px}}
.edge{{stroke:#8795a3;stroke-width:1.5;opacity:.7}}
.node circle{{fill:#2878a8;stroke:currentColor;stroke-width:1}}
.node text{{font-size:12px;fill:currentColor}}
.plot-bg{{fill:none;stroke:#8795a3;stroke-dasharray:5 5}}
table{{border-collapse:collapse;width:100%;font-size:.95rem}}
th,td{{text-align:left;padding:.6rem;border-bottom:1px solid #8886}}
.table-wrap{{overflow-x:auto}}
.note{{font-size:.9rem;opacity:.8}}
:focus-visible{{outline:3px solid #e09b32;outline-offset:3px}}
</style>
</head>
<body>
<main>
<h1>{safe_title}</h1>
<p class="note">Self-contained report. Visual layouts are exploratory summaries;
inspect source records and provenance before drawing conclusions.</p>
<nav aria-label="Visualization views">
<button type="button" data-target="network" aria-pressed="true">Network</button>
<button type="button" data-target="timeline" aria-pressed="false">Timeline</button>
<button type="button" data-target="places" aria-pressed="false">Places</button>
</nav>
<section id="network" class="panel active"><h2>Relationship network</h2>
<p class="note">Circular schematic layout; line direction follows recorded relationships.</p>
{graph_svg}</section>
<section id="timeline" class="panel"><h2>Timeline records</h2>
<p class="note">Date expressions and uncertainty are preserved; dates are not normalized.</p>
{timeline_html}</section>
<section id="places" class="panel"><h2>Place coordinates</h2>
<p class="note">Schematic latitude/longitude scatter only; not a basemap, projection,
historical border, or inferred location.</p>
{map_svg}</section>
</main>
<script>
document.querySelectorAll("button[data-target]").forEach((button) => {{
  button.addEventListener("click", () => {{
    document.querySelectorAll("button[data-target]").forEach((item) => {{
      item.setAttribute("aria-pressed", String(item === button));
    }});
    document.querySelectorAll(".panel").forEach((panel) => {{
      panel.classList.toggle("active", panel.id === button.dataset.target);
    }});
  }});
}});
</script>
</body>
</html>\'''
