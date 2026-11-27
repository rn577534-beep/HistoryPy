from __future__ import annotations

import importlib.util
from pathlib import Path


def load_benchmark_module():
    path = Path(__file__).parents[1] / "benchmarks" / "benchmark_cached_search.py"
    spec = importlib.util.spec_from_file_location("benchmark_cached_search", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cached_search_benchmark_reports_parity_and_cache_metrics():
    module = load_benchmark_module()
    report = module.run_benchmark(record_count=1000, repeat=1, workers=2)
    assert report["cache_result_parity"] is True
    assert report["batch_result_parity"] is True
    assert report["result_count"] > 0
    assert report["warm_cache_search_median_ms"] >= 0
    assert report["uncached_search_median_ms"] >= 0
    assert report["warm_batch_cache_hits"] == 4
    assert report["cache_stats"]["capacity"] == 64
