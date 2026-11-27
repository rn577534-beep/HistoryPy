"""Bounded, thread-safe caching and ordered batch execution for hybrid search."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import RLock

from historypy.research.hybrid import EmbeddingBatch, HybridSearchHit, HybridSearchIndex


@dataclass(frozen=True, slots=True)
class SearchCacheStats:
    """Snapshot of cache activity; counters reset only when clear(reset_stats=True)."""

    hits: int
    misses: int
    evictions: int
    size: int
    capacity: int


class CachedHybridSearchIndex:
    """LRU cache around a hybrid index, with deterministic multi-query results.

    Cached values are immutable result tuples. Query options form part of the
    cache key, including the identity of a supplied embedder. The embedder
    reference is retained with each entry so its identity cannot be recycled
    while that entry is cached. A cache instance should be scoped to one
    immutable index snapshot.
    """

    def __init__(self, index: HybridSearchIndex, *, capacity: int = 512) -> None:
        if not isinstance(index, HybridSearchIndex):
            raise TypeError("index must be a HybridSearchIndex")
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 0:
            raise ValueError("capacity must be a non-negative integer")
        self.index = index
        self.capacity = capacity
        self._cache: OrderedDict[tuple[object, ...], tuple[EmbeddingBatch | None, tuple[HybridSearchHit, ...]]] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _key(
        self,
        query: str,
        *,
        embedder: EmbeddingBatch | None,
        kinds: tuple[str, ...] | None,
        limit: int,
        decompose: bool,
        entity_fuzzy_threshold: float | None,
        entity_language: str | None,
    ) -> tuple[object, ...]:
        return (
            query,
            kinds,
            limit,
            decompose,
            entity_fuzzy_threshold,
            entity_language,
            id(embedder) if embedder is not None else None,
        )

    def search(
        self,
        query: str,
        *,
        embedder: EmbeddingBatch | None = None,
        kinds: Iterable[str] | None = None,
        limit: int = 20,
        decompose: bool = False,
        entity_fuzzy_threshold: float | None = None,
        entity_language: str | None = None,
    ) -> tuple[HybridSearchHit, ...]:
        """Search with LRU reuse; set capacity=0 to bypass caching."""
        normalized_kinds = tuple(sorted(set(kinds))) if kinds is not None else None
        if self.capacity == 0:
            return self.index.search(
                query,
                embedder=embedder,
                kinds=normalized_kinds,
                limit=limit,
                decompose=decompose,
                entity_fuzzy_threshold=entity_fuzzy_threshold,
                entity_language=entity_language,
            )
        key = self._key(
            query,
            embedder=embedder,
            kinds=normalized_kinds,
            limit=limit,
            decompose=decompose,
            entity_fuzzy_threshold=entity_fuzzy_threshold,
            entity_language=entity_language,
        )
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._hits += 1
                self._cache.move_to_end(key)
                return cached[1]
            self._misses += 1

        result = self.index.search(
            query,
            embedder=embedder,
            kinds=normalized_kinds,
            limit=limit,
            decompose=decompose,
            entity_fuzzy_threshold=entity_fuzzy_threshold,
            entity_language=entity_language,
        )
        with self._lock:
            # Another thread may have completed the same query while this
            # thread was searching. Reuse its result and avoid duplicate writes.
            existing = self._cache.get(key)
            if existing is not None:
                self._cache.move_to_end(key)
                return existing[1]
            self._cache[key] = (embedder, result)
            if len(self._cache) > self.capacity:
                self._cache.popitem(last=False)
                self._evictions += 1
        return result

    def search_many(
        self,
        queries: Sequence[str],
        *,
        workers: int = 1,
        **search_options: object,
    ) -> tuple[tuple[HybridSearchHit, ...], ...]:
        """Search several queries and preserve input order in the returned tuple.

        Parallel execution is opt-in. It is most useful when an embedder or
        other retrieval component performs I/O or releases the GIL. A custom
        embedder used with workers > 1 must be safe for concurrent calls.
        """
        if isinstance(queries, (str, bytes)):
            raise TypeError("queries must be a sequence of query strings")
        if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
            raise ValueError("workers must be a positive integer")
        query_list = tuple(queries)
        if any(not isinstance(query, str) for query in query_list):
            raise TypeError("every query must be a string")
        if not query_list:
            return ()
        if "kinds" in search_options and search_options["kinds"] is not None:
            search_options["kinds"] = tuple(search_options["kinds"])  # type: ignore[arg-type]
        if workers == 1 or len(query_list) == 1:
            return tuple(self.search(query, **search_options) for query in query_list)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.search, query, **search_options)
                for query in query_list
            ]
            return tuple(future.result() for future in futures)

    def cache_info(self) -> SearchCacheStats:
        """Return a consistent snapshot of hit, miss, eviction, and size counts."""
        with self._lock:
            return SearchCacheStats(
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                size=len(self._cache),
                capacity=self.capacity,
            )

    def clear(self, *, reset_stats: bool = False) -> None:
        """Remove cached results; optionally reset the cumulative counters."""
        with self._lock:
            self._cache.clear()
            if reset_stats:
                self._hits = self._misses = self._evictions = 0
