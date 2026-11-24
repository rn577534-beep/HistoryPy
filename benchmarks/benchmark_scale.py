"""Scale benchmark for selective lexical retrieval at large corpus sizes.

Run from the repository root:
    python benchmarks/benchmark_scale.py --records 1000000 --repeat 1

The generated corpus is synthetic. Memory figures are additional Python
allocations observed by tracemalloc, not total process RSS.
"""
from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
import tracemalloc

from historypy import DatasetSearchIndex, HistoricalDataset, HistoricalPerson, __version__, search_dataset


def build_dataset(record_count: int) -> HistoricalDataset:
    """Build deterministic people records with one rare marker per 1,000 rows."""
    people = tuple(
        HistoricalPerson(
            id=f"scale-person-{index:08d}",
            name=f"Historical Person {index:08d}",
            occupations=("merchant", "scholar") if index % 1000 == 0 else ("administrator",),
            description=(
                "ScaleProbe raremarker Bengal maritime archive"
                if index % 1000 == 0
                else "Synthetic administrative biography fixture"
            ),
        )
        for index in range(record_count)
    )
    dataset = HistoricalDataset(people=people)
    dataset.require_valid()
    return dataset


def peak_additional_bytes(operation) -> int:
    gc.collect()
    tracemalloc.start()
    try:
        baseline, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        operation()
        _, peak = tracemalloc.get_traced_memory()
        return max(0, peak - baseline)
    finally:
        tracemalloc.stop()


def median_ms(operation, repeat: int) -> float:
    operation()
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def ids(hits):
    return tuple((hit.kind, hit.record_id) for hit in hits)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(100000, 1000000), required=True)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")

    dataset = build_dataset(args.records)
    # Trace a dedicated build, then discard it before measuring normal build time.
    index_peak = peak_additional_bytes(lambda: DatasetSearchIndex.build(dataset))
    gc.collect()
    started = time.perf_counter()
    index = DatasetSearchIndex.build(dataset)
    index_build_ms = (time.perf_counter() - started) * 1000

    query = "scalep robe raremarker"
    # Deliberately use a rare, stable query to avoid materializing hundreds of
    # thousands of broad-query hits at the largest scale.
    query = "scaleprobe raremarker"
    linear_hits = search_dataset(dataset, query, limit=None)
    indexed_hits = index.search(query, limit=None)
    if ids(linear_hits) != ids(indexed_hits):
        raise RuntimeError("Indexed and linear search results differ")
    linear_ms = median_ms(lambda: search_dataset(dataset, query, limit=None), args.repeat)
    indexed_ms = median_ms(lambda: index.search(query, limit=None), args.repeat)
    linear_peak = peak_additional_bytes(lambda: search_dataset(dataset, query, limit=None))
    indexed_query_peak = peak_additional_bytes(lambda: index.search(query, limit=None))

    mib = lambda value: round(value / (1024 * 1024), 3)
    print(json.dumps({
        "benchmark": "historypy-large-scale-selective-search",
        "historypy_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "synthetic_record_count": args.records,
        "query": query,
        "result_count": len(linear_hits),
        "result_parity": True,
        "index_build_ms": round(index_build_ms, 3),
        "index_build_peak_additional_mib": mib(index_peak),
        "linear_search_median_ms": round(linear_ms, 3),
        "indexed_search_median_ms": round(indexed_ms, 3),
        "linear_search_peak_additional_mib": mib(linear_peak),
        "indexed_search_peak_additional_mib": mib(indexed_query_peak),
        "observed_speedup": round(linear_ms / indexed_ms, 3) if indexed_ms else None,
        "memory_note": (
            "tracemalloc measures additional Python allocations; it excludes "
            "pre-existing dataset memory, native allocations, and total process RSS."
        ),
        "scope_note": (
            "Synthetic selective-query stress test only; not historical relevance, "
            "accuracy, or a production workload guarantee."
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
