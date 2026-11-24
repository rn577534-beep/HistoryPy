"""Normalized, indexed SQLite storage for scalable HistoryPy research."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.io.json import SCHEMA_NAME, SCHEMA_VERSION, dataset_from_dict, dataset_to_dict

_STORE_SCHEMA_VERSION = 1
_RECORD_KINDS = (
    "sources", "claims", "events", "people", "places",
    "civilizations", "organizations", "relationships", "evidence",
)
_KIND_ALIASES = {kind: kind for kind in _RECORD_KINDS}


@dataclass(frozen=True, slots=True)
class StoredRecord:
    """A normalized record returned by a paginated query."""

    kind: str
    record_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SourceUsage:
    """Usage counts for one source across records and evidence links."""

    source_id: str
    record_links: int
    evidence_links: int

    @property
    def total_links(self) -> int:
        return self.record_links + self.evidence_links


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [part for item in value.values() for part in _strings(item)]
    if isinstance(value, (list, tuple)):
        return [part for item in value for part in _strings(item)]
    return []


def _year_bounds(record: Mapping[str, Any]) -> tuple[int | None, int | None, str | None]:
    date_value: Any = None
    for field in ("date", "birth_date", "start_date", "founded", "valid_from"):
        if record.get(field) is not None:
            date_value = record[field]
            break
    if not isinstance(date_value, Mapping):
        return None, None, None
    calendar = date_value.get("calendar")
    start = date_value.get("earliest_year")
    end = date_value.get("latest_year")
    if start is None and date_value.get("earliest"):
        start = date.fromisoformat(date_value["earliest"]).year
    if end is None and date_value.get("latest"):
        end = date.fromisoformat(date_value["latest"]).year
    return start, end, calendar


def _record_id(kind: str, record: Mapping[str, Any], index: int) -> str:
    if kind == "evidence":
        return f"evidence:{index:012d}"
    return str(record["id"])


class NormalizedSQLiteStore:
    """Store dataset records in indexed relational tables.

    This store coexists with :class:`SQLiteDatasetStore`. It uses a versioned
    schema, atomic dataset replacement, normalized source-reference rows, and
    bounded substring search. It does not require optional SQLite extensions.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        with closing(self._connect()) as connection, connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > _STORE_SCHEMA_VERSION:
                raise ValueError(
                    f"Database schema {version} is newer than supported "
                    f"schema {_STORE_SCHEMA_VERSION}"
                )
            self._migrate(connection, version)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    @staticmethod
    def _migrate(connection: sqlite3.Connection, version: int) -> None:
        if version < 1:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS hp06_datasets (
                    name TEXT PRIMARY KEY,
                    schema_name TEXT NOT NULL,
                    data_schema_version INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS hp06_records (
                    dataset_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    search_text TEXT NOT NULL,
                    start_year INTEGER,
                    end_year INTEGER,
                    calendar TEXT,
                    PRIMARY KEY (dataset_name, kind, record_id),
                    FOREIGN KEY (dataset_name) REFERENCES hp06_datasets(name)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS hp06_source_links (
                    dataset_name TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    record_kind TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    FOREIGN KEY (dataset_name) REFERENCES hp06_datasets(name)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS hp06_records_kind_id
                    ON hp06_records(dataset_name, kind, record_id);
                CREATE INDEX IF NOT EXISTS hp06_records_years
                    ON hp06_records(dataset_name, kind, start_year, end_year);
                CREATE INDEX IF NOT EXISTS hp06_source_links_source
                    ON hp06_source_links(dataset_name, source_id);
                CREATE INDEX IF NOT EXISTS hp06_source_links_record
                    ON hp06_source_links(dataset_name, record_kind, record_id);
                PRAGMA user_version = 1;
                """
            )

    def save(self, name: str, dataset: HistoricalDataset) -> None:
        """Atomically replace one named dataset with normalized record rows."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("dataset name cannot be empty")
        dataset.require_valid()
        payload = dataset_to_dict(dataset)
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM hp06_datasets WHERE name = ?", (name,))
            connection.execute(
                """INSERT INTO hp06_datasets
                   (name, schema_name, data_schema_version, metadata_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    name, SCHEMA_NAME, SCHEMA_VERSION,
                    json.dumps(payload["metadata"], ensure_ascii=False, sort_keys=True),
                ),
            )
            for kind in _RECORD_KINDS:
                for index, record in enumerate(payload[kind]):
                    record_id = _record_id(kind, record, index)
                    start, end, calendar = _year_bounds(record)
                    serialized = json.dumps(
                        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    )
                    searchable = " ".join(_strings(record)).casefold()
                    connection.execute(
                        """INSERT INTO hp06_records
                           (dataset_name, kind, record_id, payload_json, search_text,
                            start_year, end_year, calendar)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (name, kind, record_id, serialized, searchable, start, end, calendar),
                    )
                    source_ids = record.get("source_ids", [])
                    for source_id in source_ids:
                        connection.execute(
                            """INSERT INTO hp06_source_links
                               (dataset_name, source_id, record_kind, record_id, relation)
                               VALUES (?, ?, ?, ?, 'record')""",
                            (name, source_id, kind, record_id),
                        )
                    if kind == "evidence":
                        connection.execute(
                            """INSERT INTO hp06_source_links
                               (dataset_name, source_id, record_kind, record_id, relation)
                               VALUES (?, ?, 'evidence', ?, ?)""",
                            (name, record["source_id"], record_id, record["relation"]),
                        )

    def load(self, name: str) -> HistoricalDataset:
        """Rebuild and validate a dataset from its normalized rows."""
        with closing(self._connect()) as connection:
            dataset_row = connection.execute(
                """SELECT schema_name, data_schema_version, metadata_json
                   FROM hp06_datasets WHERE name = ?""",
                (name,),
            ).fetchone()
            if dataset_row is None:
                raise KeyError(name)
            if (
                dataset_row["schema_name"] != SCHEMA_NAME
                or dataset_row["data_schema_version"] != SCHEMA_VERSION
            ):
                raise ValueError("Unsupported HistoryPy dataset interchange schema")
            payload: dict[str, Any] = {
                "schema": SCHEMA_NAME,
                "schema_version": SCHEMA_VERSION,
                "metadata": json.loads(dataset_row["metadata_json"]),
            }
            for kind in _RECORD_KINDS:
                rows = connection.execute(
                    """SELECT payload_json FROM hp06_records
                       WHERE dataset_name = ? AND kind = ?
                       ORDER BY record_id""",
                    (name, kind),
                ).fetchall()
                payload[kind] = [json.loads(row["payload_json"]) for row in rows]
        return dataset_from_dict(payload)

    def names(self) -> tuple[str, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT name FROM hp06_datasets ORDER BY name"
            ).fetchall()
        return tuple(row["name"] for row in rows)

    def delete(self, name: str) -> bool:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM hp06_datasets WHERE name = ?", (name,)
            )
        return cursor.rowcount > 0

    def count_records(self, name: str, *, kind: str | None = None) -> int:
        """Count normalized records, optionally restricted to a record kind."""
        if kind is not None and kind not in _KIND_ALIASES:
            raise ValueError(f"Unsupported record kind: {kind}")
        with closing(self._connect()) as connection:
            if kind is None:
                row = connection.execute(
                    "SELECT COUNT(*) AS amount FROM hp06_records WHERE dataset_name = ?",
                    (name,),
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT COUNT(*) AS amount FROM hp06_records
                       WHERE dataset_name = ? AND kind = ?""",
                    (name, kind),
                ).fetchone()
        if row["amount"] == 0 and name not in self.names():
            raise KeyError(name)
        return int(row["amount"])

    def search_records(
        self, name: str, query: str, *, kind: str | None = None,
        limit: int = 50, offset: int = 0,
    ) -> tuple[StoredRecord, ...]:
        """Search normalized record text with deterministic pagination."""
        if not query.strip():
            raise ValueError("query cannot be empty")
        if kind is not None and kind not in _KIND_ALIASES:
            raise ValueError(f"Unsupported record kind: {kind}")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit must be 1..1000 and offset cannot be negative")
        with closing(self._connect()) as connection:
            if name not in {
                row["name"] for row in connection.execute(
                    "SELECT name FROM hp06_datasets"
                ).fetchall()
            }:
                raise KeyError(name)
            sql = """SELECT kind, record_id, payload_json FROM hp06_records
                     WHERE dataset_name = ? AND instr(search_text, ?) > 0"""
            params: list[Any] = [name, query.casefold()]
            if kind is not None:
                sql += " AND kind = ?"
                params.append(kind)
            sql += " ORDER BY kind, record_id LIMIT ? OFFSET ?"
            params.extend((limit, offset))
            rows = connection.execute(sql, params).fetchall()
        return tuple(
            StoredRecord(row["kind"], row["record_id"], json.loads(row["payload_json"]))
            for row in rows
        )

    def source_usage(self, name: str, source_id: str | None = None) -> tuple[SourceUsage, ...]:
        """Return source usage across direct record references and evidence links."""
        with closing(self._connect()) as connection:
            if name not in {
                row["name"] for row in connection.execute(
                    "SELECT name FROM hp06_datasets"
                ).fetchall()
            }:
                raise KeyError(name)
            sql = """SELECT source_id,
                     SUM(CASE WHEN relation = 'record' THEN 1 ELSE 0 END) AS record_links,
                     SUM(CASE WHEN relation != 'record' THEN 1 ELSE 0 END) AS evidence_links
                     FROM hp06_source_links WHERE dataset_name = ?"""
            params: list[Any] = [name]
            if source_id is not None:
                sql += " AND source_id = ?"
                params.append(source_id)
            sql += " GROUP BY source_id ORDER BY source_id"
            rows = connection.execute(sql, params).fetchall()
        return tuple(
            SourceUsage(row["source_id"], int(row["record_links"]), int(row["evidence_links"]))
            for row in rows
        )
