"""Synthetic scale and parity benchmark for HistoryPy lexical retrieval.

Run from the repository root:
    python benchmarks/benchmark_search.py --records 10000 --repeat 7

Timings describe this generated fixture and machine only, not historical
accuracy, source quality, or production-corpus performance.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable

from historypy import (
    DatasetSearchIndex,
    HistoricalDataset,
    HistoricalPerson,
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


def result_ids(hits: tuple) -> tuple[tuple[str, str], ...]:
    return tuple((hit.kind, hit.record_id) for hit in hits)


def peak_traced_bytes(operation: Callable[[], object]) -> int:
    """Measure additional peak Python allocations made by one operation."""
    tracemalloc.start()
    try:
        baseline, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        operation()
        _, peak = tracemalloc.get_traced_memory()
        return max(0, peak - baseline)
    finally:
        tracemalloc.stop()


def mib(byte_count: int) -> float:
    return round(byte_count / (1024 * 1024), 3)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=5000)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    if args.records < 1 or args.repeat < 1:
        parser.error("--records and --repeat must both be positive")

    dataset = build_dataset(args.records)
    queries = (
        "Bengal maritime trade",
        "synthetic administrative",
        "scholar archive",
        "no matching phrase xyz",
    )
    build_started = time.perf_counter()
    index = DatasetSearchIndex.build(dataset)
    index_build_ms = (time.perf_counter() - build_started) * 1000
    # Measure allocations in a separate build so tracemalloc overhead does not
    # distort the wall-clock build-time measurement.
    index_build_peak_bytes = peak_traced_bytes(lambda: DatasetSearchIndex.build(dataset))

    query_results = []
    for query in queries:
        linear_hits = search_dataset(dataset, query, limit=None)
        indexed_hits = index.search(query, limit=None)
        if result_ids(linear_hits) != result_ids(indexed_hits):
            raise RuntimeError(f"Indexed and linear results differ for query: {query!r}")
        linear_ms = median_ms(
            lambda query=query: search_dataset(dataset, query, limit=None), args.repeat
        )
        indexed_ms = median_ms(lambda query=query: index.search(query, limit=None), args.repeat)
        indexed_peak_bytes = peak_traced_bytes(
            lambda query=query: index.search(query, limit=None)
        )
        linear_peak_bytes = peak_traced_bytes(
            lambda query=query: search_dataset(dataset, query, limit=None)
        )
        query_results.append(
            {
                "query": query,
                "result_count": len(linear_hits),
                "linear_search_median_ms": round(linear_ms, 3),
                "trigram_index_search_median_ms": round(indexed_ms, 3),
                "observed_speedup": (
                    round(linear_ms / indexed_ms, 3) if indexed_ms else None
                ),
                "linear_search_peak_additional_mib": mib(linear_peak_bytes),
                "trigram_index_search_peak_additional_mib": mib(indexed_peak_bytes),
                "result_parity": True,
            }
        )

    report = {
        "benchmark": "historypy-lexical-search",
        "historypy_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "synthetic_record_count": args.records,
        "repeat": args.repeat,
        "index_build_ms": round(index_build_ms, 3),
        "index_build_peak_additional_mib": mib(index_build_peak_bytes),
        "memory_measurement": (
            "Python allocations measured with tracemalloc; excludes pre-existing "
            "dataset memory, native allocations, and process RSS."
        ),
        "queries": query_results,
        "all_query_results_match": True,
        "interpretation": (
            "Synthetic-fixture timing only; not a historical-accuracy, "
            "source-quality, or production-scale guarantee."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
