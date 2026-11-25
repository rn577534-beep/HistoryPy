"""Measure persistent normalized SQLite/FTS5 storage at configurable scale.

Example: python benchmarks/benchmark_sqlite_store.py --records 100000
This is a synthetic storage/retrieval stress test, not a historical corpus.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import tempfile
import time
import tracemalloc
from pathlib import Path

from historypy import HistoricalDataset, HistoricalDate, HistoricalEvent, NormalizedSQLiteStore


def build_dataset(count: int) -> HistoricalDataset:
    return HistoricalDataset(events=tuple(
        HistoricalEvent(
            f"event-{index:09d}",
            f"Synthetic historical record {index}",
            HistoricalDate(
                earliest_year=1000 + index % 900,
                latest_year=1000 + index % 900,
                precision="year",
                calendar="gregorian",
            ),
            summary=(
                f"scaleprobe raremarker synthetic record {index}"
                if index % 1000 == 0
                else f"ordinary historical record {index}"
            ),
        )
        for index in range(count)
    ))


def peak_rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes.
    return value / (1024 * 1024) if os.uname().sysname == "Darwin" else value / 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=100_000)
    parser.add_argument("--journal-mode", choices=("DELETE", "WAL"), default="DELETE")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    if args.records < 1:
        parser.error("--records must be positive")

    dataset = build_dataset(args.records)
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "historypy.sqlite"
        tracemalloc.start()
        started = time.perf_counter()
        store = NormalizedSQLiteStore(database, journal_mode=args.journal_mode)
        store.save("scale", dataset)
        save_seconds = time.perf_counter() - started
        _, save_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        query_started = time.perf_counter()
        first = store.search_records("scale", "scaleprobe raremarker", kind="events", limit=100)
        query_ms = (time.perf_counter() - query_started) * 1000
        expected = (args.records + 999) // 1000
        assert len(first) == min(expected, 100)
        assert store.count_records("scale", kind="events") == args.records

        broad_started = time.perf_counter()
        broad = store.search_records(
            "scale", "historical record", kind="events", limit=1000
        )
        broad_query_ms = (time.perf_counter() - broad_started) * 1000

        reopened = NormalizedSQLiteStore(database, journal_mode=args.journal_mode)
        reopen_started = time.perf_counter()
        persisted = reopened.search_records(
            "scale", "scaleprobe raremarker", kind="events", limit=100
        )
        reopen_query_ms = (time.perf_counter() - reopen_started) * 1000
        assert [item.record_id for item in persisted] == [
            item.record_id for item in first
        ]

        checkpoint = reopened.checkpoint_wal(mode="PASSIVE") if args.journal_mode == "WAL" else None
        report = {
            "records": args.records,
            "journal_mode": store.journal_mode,
            "fts5_available": store._fts5_available,
            "integrity_check": reopened.integrity_check(),
            "wal_checkpoint": checkpoint,
            "save_seconds": round(save_seconds, 3),
            "save_peak_traced_python_mib": round(save_peak / (1024 * 1024), 3),
            "query_ms": round(query_ms, 3),
            "broad_query_ms": round(broad_query_ms, 3),
            "broad_query_returned": len(broad),
            "broad_query_limit": 1000,
            "reopened_query_ms": round(reopen_query_ms, 3),
            "database_file_mib": round(database.stat().st_size / (1024 * 1024), 3),
            "process_peak_rss_mib": round(peak_rss_mib(), 3),
            "query_results_verified_after_reopen": True,
        }
        rendered = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)


if __name__ == "__main__":
    main()
