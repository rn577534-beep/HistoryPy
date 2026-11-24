"""Transactional SQLite persistence using the versioned JSON interchange format."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from historypy.core.dataset import HistoricalDataset
from historypy.io.json import dataset_from_json, dataset_to_json

_SCHEMA_VERSION = 1


class SQLiteDatasetStore:
    """Store complete datasets as versioned JSON payloads in a small SQLite index.

    SQLite is optional at runtime because it is part of Python's standard library.
    Each save replaces one named dataset atomically within a transaction.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS historypy_datasets (
                    name TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save(self, name: str, dataset: HistoricalDataset) -> None:
        if not name.strip():
            raise ValueError("dataset name cannot be empty")
        dataset.require_valid()
        payload = dataset_to_json(dataset)
        with self._connect() as connection:
            with connection:
                connection.execute(
                    """INSERT INTO historypy_datasets(name, schema_version, payload)
                       VALUES (?, ?, ?)
                       ON CONFLICT(name) DO UPDATE SET
                         schema_version=excluded.schema_version,
                         payload=excluded.payload,
                         updated_at=CURRENT_TIMESTAMP""",
                    (name, _SCHEMA_VERSION, payload),
                )

    def load(self, name: str) -> HistoricalDataset:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT schema_version, payload FROM historypy_datasets WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            raise KeyError(name)
        version, payload = row
        if version != _SCHEMA_VERSION:
            raise ValueError(f"Unsupported SQLite dataset schema version: {version}")
        return dataset_from_json(payload)

    def names(self) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM historypy_datasets ORDER BY name"
            ).fetchall()
        return tuple(row[0] for row in rows)

    def delete(self, name: str) -> bool:
        with self._connect() as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM historypy_datasets WHERE name = ?", (name,)
                )
        return cursor.rowcount > 0
