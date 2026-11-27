"""Reproducible cache and batch-search benchmark on synthetic datasets.

Example:
    python benchmarks/benchmark_cached_search.py --records 100000 --repeat 5
"""
from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
import tracemalloc

from historypy import (
    BM25SearchIndex,
    CachedHybridSearchIndex,
    DatasetSearchIndex,
    HistoricalDataset,
    HistoricalPerson,
    HybridSearchIndex,
    __version__,
)


def build_dataset(record_count: int) -> HistoricalDataset:
    """Build a deterministic corpus with searchable rare-marker records."""
    return HistoricalDataset(people=tuple(
        HistoricalPerson(
            id=f"cache-person-{index:08d}",
            name=f"Historical Person {index:08d}",
            occupations=("merchant", "scholar") if index % 1000 == 0 else ("administrator",),
            description=(
                "CacheProbe raremarker Bengal maritime archive"
                if index % 1000 == 0
                else "Synthetic administrative biography fixture"
            ),
        )
        for index in range(record_count)
    ))


def median_ms(operation, repeat: int) -> float:
    operation()
    samples = []
    for _ in range(repeat):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


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


def run_benchmark(record_count: int, repeat: int, workers: int) -> dict[str, object]:
    dataset = build_dataset(record_count)
    started = time.perf_counter()
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    hybrid = HybridSearchIndex(trigram, bm25)
    build_ms = (time.perf_counter() - started) * 1000

    cached = CachedHybridSearchIndex(hybrid, capacity=64)
    query = "CacheProbe raremarker"
    queries = (
        query,
        "CacheProbe Bengal",
        "raremark er maritime archive",
        "Historical Person",
    )
    baseline = hybrid.search(query, limit=20)
    first_cached = cached.search(query, limit=20)
    if first_cached != baseline:
        raise RuntimeError("cached and uncached search results differ")

    cold_cache_ms = median_ms(
        lambda: (cached.clear(), cached.search(query, limit=20)), repeat
    )
    cached.search(query, limit=20)
    warm_cache_ms = median_ms(lambda: cached.search(query, limit=20), repeat)
    uncached_ms = median_ms(lambda: hybrid.search(query, limit=20), repeat)

    cached.clear(reset_stats=True)
    sequential = cached.search_many(queries, workers=1, limit=20)
    sequential_stats = cached.cache_info()
    cached.clear(reset_stats=True)
    parallel = cached.search_many(queries, workers=workers, limit=20)
    parallel_stats = cached.cache_info()
    if parallel != sequential:
        raise RuntimeError("parallel and sequential batch results differ")

    warm_hits_before = cached.cache_info().hits
    cached.search_many(queries, workers=workers, limit=20)
    warm_batch_hits = cached.cache_info().hits - warm_hits_before

    return {
        "benchmark": "historypy-cache-and-batch-search",
        "historypy_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "synthetic_record_count": record_count,
        "repeat": repeat,
        "workers": workers,
        "index_build_ms": round(build_ms, 3),
        "query": query,
        "top_k": 20,
        "result_count": len(baseline),
        "cache_result_parity": True,
        "batch_result_parity": True,
        "uncached_search_median_ms": round(uncached_ms, 4),
        "cold_cache_search_median_ms": round(cold_cache_ms, 4),
        "warm_cache_search_median_ms": round(warm_cache_ms, 4),
        "observed_warm_cache_speedup": round(uncached_ms / warm_cache_ms, 3) if warm_cache_ms else None,
        "sequential_batch_median_ms": round(median_ms(
            lambda: cached.search_many(queries, workers=1, limit=20), repeat
        ), 4),
        "parallel_batch_median_ms": round(median_ms(
            lambda: cached.search_many(queries, workers=workers, limit=20), repeat
        ), 4),
        "sequential_batch_cache_misses": sequential_stats.misses,
        "parallel_batch_cache_misses": parallel_stats.misses,
        "warm_batch_cache_hits": warm_batch_hits,
        "cached_query_peak_additional_mib": round(
            peak_additional_bytes(lambda: cached.search(query, limit=20)) / (1024 * 1024), 4
        ),
        "cache_stats": {
            "hits": cached.cache_info().hits,
            "misses": cached.cache_info().misses,
            "evictions": cached.cache_info().evictions,
            "size": cached.cache_info().size,
            "capacity": cached.cache_info().capacity,
        },
        "scope_note": (
            "Synthetic lexical retrieval stress test only. Threaded execution is "
            "not expected to accelerate CPU-bound pure-Python search in general. "
            "Memory is additional Python allocation measured with tracemalloc, "
            "not total process RSS. Results do not measure historical accuracy."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(1000, 100000, 1000000), required=True)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")
    print(json.dumps(
        run_benchmark(args.records, args.repeat, args.workers),
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
