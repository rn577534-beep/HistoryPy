"""Export one small historical dataset for graph, map, and timeline tools.

Run with: python examples/visualization_exports.py
"""
from __future__ import annotations

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
    SourceRecord,
    dataset_graph_data,
    export_visualization_json,
    timeline_visualization_data,
    to_geojson,
    to_graphviz_dot,
)


def main() -> None:
    dataset = HistoricalDataset(
        sources=(SourceRecord(
            "source-archive-1", "Example archival catalogue", "archival",
            url="https://example.org/catalogue",
        ),),
        claims=(HistoricalClaim(
            "claim-1", "The example event was associated with the example place."
        ),),
        people=(HistoricalPerson(
            "person-1", "Example historical person",
            source_ids=("source-archive-1",),
        ),),
        places=(HistoricalPlace(
            "place-1", "Example historical place",
            place_type="city", latitude=23.7, longitude=90.4,
            source_ids=("source-archive-1",),
        ),),
        events=(HistoricalEvent(
            "event-1", "Example historical event",
            HistoricalDate(
                earliest_year=1900, latest_year=1902,
                precision="year", calendar="gregorian",
            ),
            place_ids=("place-1",), source_ids=("source-archive-1",),
        ),),
        relationships=(HistoricalRelationship(
            "relationship-1", "person-1", "associated_with", "event-1",
            source_ids=("source-archive-1",),
        ),),
        evidence=(EvidenceLink(
            "claim-1", "source-archive-1", "supports",
            locator="catalogue entry 12",
        ),),
    )

    dataset.require_valid()
    graph = dataset_graph_data(dataset)
    geojson = to_geojson(dataset)
    timeline = timeline_visualization_data(dataset)

    print("Graph JSON:")
    print(export_visualization_json(graph))
    print("\nGeoJSON:")
    print(export_visualization_json(geojson))
    print("\nTimeline JSON:")
    print(export_visualization_json(timeline))
    print("\nGraphviz DOT:")
    print(to_graphviz_dot(dataset))


if __name__ == "__main__":
    main()
