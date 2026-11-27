from historypy import (
    CachedHybridSearchIndex,
    DatasetSearchIndex,
    HistoricalDataset,
    HistoricalPerson,
    HybridSearchIndex,
    BM25SearchIndex,
)


def build_cached_search(capacity=2):
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="alexander", name="Alexander"),
        HistoricalPerson(id="alexandria", name="Alexandria"),
        HistoricalPerson(id="cleopatra", name="Cleopatra"),
    ))
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    return CachedHybridSearchIndex(
        HybridSearchIndex(trigram, bm25), capacity=capacity
    )


def test_cache_reuses_results_and_tracks_statistics():
    cached = build_cached_search()
    first = cached.search("Alexander")
    second = cached.search("Alexander")
    assert first == second
    assert first is second
    assert cached.cache_info().hits == 1
    assert cached.cache_info().misses == 1
    assert cached.cache_info().size == 1


def test_cache_key_includes_search_options_and_lru_evicts_oldest():
    cached = build_cached_search(capacity=1)
    cached.search("Alexander", limit=1)
    cached.search("Alexander", limit=2)
    stats = cached.cache_info()
    assert stats.misses == 2
    assert stats.evictions == 1
    assert stats.size == 1
    cached.search("Alexander", limit=1)
    assert cached.cache_info().misses == 3


def test_cache_normalizes_kinds_and_clear_can_reset_counters():
    cached = build_cached_search()
    first = cached.search("Alexander", kinds=("person",))
    second = cached.search("Alexander", kinds=("person", "person"))
    assert first == second
    cached.clear(reset_stats=True)
    assert cached.cache_info().hits == 0
    assert cached.cache_info().misses == 0
    assert cached.cache_info().size == 0


def test_search_many_preserves_order_and_matches_sequential_results():
    cached = build_cached_search()
    queries = ("Alexander", "Cleopatra", "Alexandria")
    sequential = cached.search_many(queries)
    parallel = cached.search_many(queries, workers=3)
    assert parallel == sequential
    assert len(parallel) == len(queries)


def test_search_many_handles_empty_input_and_validates_arguments():
    cached = build_cached_search()
    assert cached.search_many(()) == ()
    try:
        cached.search_many(("Alexander",), workers=0)
    except ValueError as exc:
        assert "workers" in str(exc)
    else:
        raise AssertionError("workers=0 should fail")
    try:
        cached.search_many("Alexander")
    except TypeError as exc:
        assert "sequence" in str(exc)
    else:
        raise AssertionError("a string should not be accepted as a query sequence")


def test_zero_capacity_bypasses_cache():
    cached = build_cached_search(capacity=0)
    cached.search("Alexander")
    cached.search("Alexander")
    stats = cached.cache_info()
    assert stats.size == 0
    assert stats.hits == 0
    assert stats.misses == 0
