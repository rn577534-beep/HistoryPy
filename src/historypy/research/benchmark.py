"""Run comparable retrieval methods over one HistoryPy dataset snapshot."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from time import perf_counter
from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.research.bm25 import BM25SearchIndex
from historypy.research.evaluation import EvaluationReport, evaluate_rankings
from historypy.research.hybrid import HybridSearchIndex
from historypy.research.search_index import DatasetSearchIndex


def run_retrieval_benchmark(
    dataset: HistoricalDataset,
    cases: Sequence[Mapping[str, Any]],
    *,
    cutoff: int = 10,
    bootstrap_samples: int = 2000,
    seed: int = 2026,
) -> EvaluationReport:
    """Evaluate trigram, BM25, and reciprocal-rank-fusion on identical cases.

    Each case is {"id": ..., "query": ..., "relevant": [...]}. Relevant IDs
    use kind:id form, such as event:event-12. All judgments must be
    researcher-supplied; no synthetic labels are generated.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    if not cases:
        raise ValueError("benchmark cases cannot be empty")
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    hybrid = HybridSearchIndex(trigram, bm25)
    relevance: dict[str, Sequence[str]] = {}
    rankings: dict[str, dict[str, Sequence[str]]] = {
        "trigram": {}, "bm25": {}, "hybrid_rrf": {}
    }
    latencies: dict[str, dict[str, float]] = {
        "trigram": {}, "bm25": {}, "hybrid_rrf": {}
    }
    for case in cases:
        query_id = case.get("id")
        query = case.get("query")
        relevant = case.get("relevant")
        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError("each case requires a non-empty id")
        if query_id in relevance:
            raise ValueError(f"duplicate benchmark query id: {query_id}")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{query_id}: query must be a non-empty string")
        if not isinstance(relevant, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in relevant
        ):
            raise ValueError(f"{query_id}: relevant must be a list of kind:id strings")
        relevance[query_id] = relevant
        methods = (
            ("trigram", lambda: trigram.search(query, limit=cutoff)),
            ("bm25", lambda: bm25.search(query, limit=cutoff)),
            ("hybrid_rrf", lambda: hybrid.search(query, limit=cutoff)),
        )
        for name, search in methods:
            started = perf_counter()
            hits = search()
            elapsed = (perf_counter() - started) * 1000.0
            rankings[name][query_id] = tuple(f"{hit.kind}:{hit.record_id}" for hit in hits)
            latencies[name][query_id] = elapsed
    return evaluate_rankings(
        relevance,
        rankings,
        cutoff=cutoff,
        latencies_ms=latencies,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
