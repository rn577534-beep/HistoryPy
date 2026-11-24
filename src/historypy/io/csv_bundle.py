"""Lossless multi-table CSV bundle interchange for HistoryPy datasets.

Each record is represented by typed JSON-encoded cells in a CSV table. This
preserves nested values and uncertainty metadata without pretending that a
single flat CSV can represent the whole relational dataset.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.io.json import (
    SCHEMA_NAME,
    SCHEMA_VERSION,
    dataset_from_dict,
    dataset_to_dict,
)

_TABLES = (
    "sources", "claims", "events", "people", "places", "civilizations",
    "organizations", "relationships", "evidence",
)


def save_dataset_csv_bundle(
    dataset: HistoricalDataset,
    directory: str | Path,
    *,
    validate: bool = True,
) -> None:
    """Write a complete dataset as a directory of CSV tables plus a manifest."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if validate:
        dataset.require_valid()
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    payload = dataset_to_dict(dataset)
    manifest = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "metadata": payload["metadata"],
        "tables": list(_TABLES),
        "cell_encoding": "json",
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for table in _TABLES:
        records = payload[table]
        headers = sorted({key for record in records for key in record})
        if not headers:
            headers = ["record_json"]
        with (target / f"{table}.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="raise")
            writer.writeheader()
            for record in records:
                writer.writerow({
                    key: json.dumps(record[key], ensure_ascii=False, separators=(",", ":"))
                    for key in headers if key in record
                })


def load_dataset_csv_bundle(
    directory: str | Path,
    *,
    validate: bool = True,
) -> HistoricalDataset:
    """Load a complete CSV bundle, rejecting malformed or incomplete tables."""
    target = Path(directory)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("CSV bundle manifest must be a JSON object")
    if manifest.get("schema") != SCHEMA_NAME:
        raise ValueError(f"Expected schema {SCHEMA_NAME!r}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported HistoryPy schema version: {manifest.get('schema_version')!r}"
        )
    if manifest.get("tables") != list(_TABLES) or manifest.get("cell_encoding") != "json":
        raise ValueError("CSV bundle manifest has an unsupported table layout")
    metadata = manifest.get("metadata", {})
    if not isinstance(metadata, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in metadata.items()
    ):
        raise TypeError("manifest metadata must contain only string keys and values")

    payload: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "metadata": metadata,
    }
    for table in _TABLES:
        table_path = target / f"{table}.csv"
        with table_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError(f"{table}.csv is missing its header")
            records = []
            for row_number, row in enumerate(reader, start=2):
                record = {}
                for key, raw in row.items():
                    if key is None or raw is None or raw == "":
                        continue
                    try:
                        record[key] = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Invalid JSON cell in {table}.csv row {row_number}, "
                            f"column {key!r}"
                        ) from exc
                records.append(record)
            payload[table] = records
    return dataset_from_dict(payload, validate=validate)
