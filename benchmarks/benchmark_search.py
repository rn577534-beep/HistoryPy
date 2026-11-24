"""Reproducible synthetic benchmark for HistoryPy lexical retrieval.

Run from the repository root:
    python benchmarks/benchmark_search.py --records 10000 --repeat 7

Results measure this synthetic fixture and machine only; they are not measures
of historical accuracy, source quality, or production-corpus performance.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from collections.abc import Callable

from historypy import (
    HistoricalDataset,
    HistoricalPerson,
    DatasetSearchIndex,
    __version__,
    search_dataset,
)


def build_dataset(record_count: int) -> HistoricalDataset:
    """Create a deterministic synthetic corpus with periodic target records."""
    people = tuple(
        HistoricalPerson(
            id=f"person-{index:08d}",
            name=f"Historical Person {index:08d}",
            occupations=("merchant", "scholar") if index % 10 == 0 else ("administrator",),
            description=(
                "Synthetic Bengal maritime trade archive record"
                if index % 10 == 0
                else "Synthetic administrative biography fixture"
            ),
        )
        for index in range(record_count)
    )
    dataset = HistoricalDataset(people=people)
    dataset.require_valid()
    return dataset


def median_ms(operation: Callable[[], object], repeat: int) -> float:
    """Return median wall-clock milliseconds after one warm-up call."""
    operation()
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=5000)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    if args.records < 1 or args.repeat < 1:
        parser.error("--records and --repeat must both be positive")

    dataset = build_dataset(args.records)
    query = "Bengal maritime trade"
    build_started = time.perf_counter()
    index = DatasetSearchIndex.build(dataset)
    index_build_ms = (time.perf_counter() - build_started) * 1000

    linear_hits = search_dataset(dataset, query, limit=None)
    indexed_hits = index.search(query, limit=None)
    linear_ids = tuple((hit.kind, hit.record_id) for hit in linear_hits)
    indexed_ids = tuple((hit.kind, hit.record_id) for hit in indexed_hits)
    if linear_ids != indexed_ids:
        raise RuntimeError("Indexed and linear lexical results differ")

    linear_ms = median_ms(lambda: search_dataset(dataset, query, limit=None), args.repeat)
    indexed_ms = median_ms(lambda: index.search(query, limit=None), args.repeat)
    report = {
        "benchmark": "historypy-lexical-search",
        "historypy_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "synthetic_record_count": args.records,
        "repeat": args.repeat,
        "query": query,
        "result_count": len(linear_hits),
        "index_build_ms": round(index_build_ms, 3),
        "linear_search_median_ms": round(linear_ms, 3),
        "trigram_index_search_median_ms": round(indexed_ms, 3),
        "observed_speedup": round(linear_ms / indexed_ms, 3) if indexed_ms else None,
        "result_parity": True,
        "interpretation": (
            "Synthetic-fixture timing only; not a historical-accuracy, "
            "source-quality, or production-scale guarantee."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
