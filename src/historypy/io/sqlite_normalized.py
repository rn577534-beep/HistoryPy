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

_STORE_SCHEMA_VERSION = 2
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
            self._fts5_available = self._ensure_fts(connection)

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
        if version < 2:
            connection.execute(
                "CREATE INDEX IF NOT EXISTS hp06_records_calendar_years "
                "ON hp06_records(dataset_name, kind, calendar, start_year, end_year)"
            )
            connection.execute("PRAGMA user_version = 2")

    @staticmethod
    def _ensure_fts(connection: sqlite3.Connection) -> bool:
        """Create and initialize the optional FTS5 index when SQLite supports it."""
        try:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'hp06_records_fts'"
            ).fetchone() is not None
            connection.execute(
                """CREATE VIRTUAL TABLE IF NOT EXISTS hp06_records_fts USING fts5(
                    dataset_name UNINDEXED, kind UNINDEXED, record_id UNINDEXED,
                    search_text, tokenize='unicode61'
                )"""
            )
            if not exists:
                connection.execute(
                    """INSERT INTO hp06_records_fts(dataset_name, kind, record_id, search_text)
                       SELECT dataset_name, kind, record_id, search_text FROM hp06_records"""
                )
            return True
        except sqlite3.OperationalError:
            return False

    def save(self, name: str, dataset: HistoricalDataset) -> None:
        """Atomically replace one named dataset with normalized record rows."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("dataset name cannot be empty")
        dataset.require_valid()
        payload = dataset_to_dict(dataset)
        with closing(self._connect()) as connection, connection:
            if self._fts5_available:
                connection.execute(
                    "DELETE FROM hp06_records_fts WHERE dataset_name = ?", (name,)
                )
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
                    if self._fts5_available:
                        connection.execute(
                            """INSERT INTO hp06_records_fts
                               (dataset_name, kind, record_id, search_text)
                               VALUES (?, ?, ?, ?)""",
                            (name, kind, record_id, searchable),
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
            if self._fts5_available:
                connection.execute(
                    "DELETE FROM hp06_records_fts WHERE dataset_name = ?", (name,)
                )
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
        """Search with FTS5 when available; otherwise use safe substring matching.

        FTS5 treats input as a quoted phrase. The fallback preserves the
        original case-insensitive substring behavior.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if kind is not None and kind not in _KIND_ALIASES:
            raise ValueError(f"Unsupported record kind: {kind}")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit must be 1..1000 and offset cannot be negative")
        with closing(self._connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM hp06_datasets WHERE name = ?", (name,)
            ).fetchone() is None:
                raise KeyError(name)
            rows = None
            if self._fts5_available:
                phrase = '"' + query.strip().replace('"', '""') + '"'
                sql = """SELECT records.kind, records.record_id, records.payload_json
                         FROM hp06_records_fts AS matches
                         JOIN hp06_records AS records
                           ON records.dataset_name = matches.dataset_name
                          AND records.kind = matches.kind
                          AND records.record_id = matches.record_id
                         WHERE matches.dataset_name = ? AND matches MATCH ?"""
                params: list[Any] = [name, phrase]
                if kind is not None:
                    sql += " AND records.kind = ?"
                    params.append(kind)
                sql += " ORDER BY records.kind, records.record_id LIMIT ? OFFSET ?"
                params.extend((limit, offset))
                try:
                    rows = connection.execute(sql, params).fetchall()
                except sqlite3.OperationalError:
                    self._fts5_available = False
            if rows is None:
                sql = """SELECT kind, record_id, payload_json FROM hp06_records
                         WHERE dataset_name = ? AND instr(search_text, ?) > 0"""
                params = [name, query.casefold()]
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

    def query_year_range(
        self, name: str, start_year: int, end_year: int, *,
        kind: str | None = None, calendar: str | None = None,
        limit: int = 100, offset: int = 0, include_undated: bool = False,
    ) -> tuple[StoredRecord, ...]:
        """Return records whose stored year bounds overlap an inclusive range.

        Years use astronomical numbering (1 CE=1, 1 BCE=0, 2 BCE=-1).
        Calendar filtering is exact when supplied; calendars are never converted.
        One-sided record bounds are treated as open-ended. Undated records are
        excluded unless explicitly requested.
        """
        for field, value in (("start_year", start_year), ("end_year", end_year)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{field} must be an integer")
        if start_year > end_year:
            raise ValueError("start_year cannot be greater than end_year")
        if kind is not None and kind not in _KIND_ALIASES:
            raise ValueError(f"Unsupported record kind: {kind}")
        if calendar is not None and (not isinstance(calendar, str) or not calendar.strip()):
            raise ValueError("calendar must be a non-empty string or None")
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit must be 1..1000 and offset cannot be negative")
        with closing(self._connect()) as connection:
            if connection.execute(
                "SELECT 1 FROM hp06_datasets WHERE name = ?", (name,)
            ).fetchone() is None:
                raise KeyError(name)
            sql = """SELECT kind, record_id, payload_json FROM hp06_records
                     WHERE dataset_name = ?"""
            params: list[Any] = [name]
            if not include_undated:
                sql += " AND (start_year IS NOT NULL OR end_year IS NOT NULL)"
            sql += " AND (start_year IS NULL OR start_year <= ?)"
            sql += " AND (end_year IS NULL OR end_year >= ?)"
            params.extend((end_year, start_year))
            if calendar is not None:
                sql += " AND calendar = ?"
                params.append(calendar)
            if kind is not None:
                sql += " AND kind = ?"
                params.append(kind)
            sql += " ORDER BY kind, start_year, end_year, record_id LIMIT ? OFFSET ?"
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
            sql = """SELECT sources.record_id AS source_id,
                     SUM(CASE WHEN links.relation = 'record' THEN 1 ELSE 0 END)
                         AS record_links,
                     SUM(CASE WHEN links.relation IS NOT NULL
                                   AND links.relation != 'record' THEN 1 ELSE 0 END)
                         AS evidence_links
                     FROM hp06_records AS sources
                     LEFT JOIN hp06_source_links AS links
                       ON links.dataset_name = sources.dataset_name
                      AND links.source_id = sources.record_id
                     WHERE sources.dataset_name = ? AND sources.kind = 'sources'"""
            params: list[Any] = [name]
            if source_id is not None:
                sql += " AND sources.record_id = ?"
                params.append(source_id)
            sql += " GROUP BY sources.record_id ORDER BY sources.record_id"
            rows = connection.execute(sql, params).fetchall()
        return tuple(
            SourceUsage(row["source_id"], int(row["record_links"]), int(row["evidence_links"]))
            for row in rows
        )
