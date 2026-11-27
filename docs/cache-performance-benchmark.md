# Cache and batch-search performance benchmark

Run a deterministic synthetic benchmark from the repository root:

~~~bash
python benchmarks/benchmark_cached_search.py --records 100000 --repeat 5 --workers 4
~~~

For a quick smoke test use `--records 1000 --repeat 1`. The script reports
index build time, uncached search, cold-cache and warm-cache medians, observed
warm-cache speedup, sequential and threaded batch medians, cache counters,
and additional Python allocations observed during a cached query.

The script checks exact result parity between cached and uncached retrieval and
between sequential and parallel batches before reporting timings. It emits one
JSON object suitable for archiving in CI artifacts or comparing across commits.

The corpus and queries are synthetic. The benchmark does not measure historical
accuracy, semantic relevance, or production workloads. Thread pools may be
slower for CPU-bound pure-Python searches; use the measurements from the target
machine and workload rather than assuming more workers are faster. The memory
measurement uses `tracemalloc` and excludes existing dataset memory and native
allocations.
