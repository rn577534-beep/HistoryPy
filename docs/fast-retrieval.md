# Fast repeated and batch retrieval

Wrap an existing `HybridSearchIndex` with `CachedHybridSearchIndex` when the
same research questions are likely to be asked repeatedly:

~~~python
from historypy import CachedHybridSearchIndex

cached = CachedHybridSearchIndex(hybrid_index, capacity=512)
hits = cached.search("Fall of Constantinople", limit=10)
again = cached.search("Fall of Constantinople", limit=10)  # LRU cache hit
print(cached.cache_info())
~~~

The cache is bounded, thread-safe, and scoped to the index snapshot supplied at
construction. Search options are part of the key, including entity filters,
decomposition settings, result limit, and embedder identity. Create a new cache
when rebuilding or replacing the underlying indexes. Use `clear()` to release
cached result tuples; `clear(reset_stats=True)` also resets counters. Set
`capacity=0` to bypass caching.

Batch search preserves input order:

~~~python
results = cached.search_many(
    ["Constantinople 1453", "Alexander Tyre", "Mughal Bengal"],
    workers=3,
)
~~~

The default `workers=1` avoids thread overhead. Parallel execution is opt-in
and can help when a caller-supplied embedder or retrieval component performs
I/O or releases the Python GIL. It is not guaranteed to accelerate CPU-bound
pure-Python workloads. A custom embedder used with multiple workers must be
safe for concurrent calls.

Cache hits reuse immutable result tuples. The cache does not alter ranking,
relevance scores, source evidence, or historical claims. A cache hit is not
new evidence and does not make a result more trustworthy.
