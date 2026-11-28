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
from historypy.research.semantic import EmbeddingBatch, SemanticSearchIndex


def run_retrieval_benchmark(
    dataset: HistoricalDataset,
    cases: Sequence[Mapping[str, Any]],
    *,
    cutoff: int = 10,
    bootstrap_samples: int = 2000,
    seed: int = 2026,
    semantic_index: SemanticSearchIndex | None = None,
    embedder: EmbeddingBatch | None = None,
) -> EvaluationReport:
    """Evaluate trigram, BM25, optional semantic, and RRF on identical cases.

    Each case is {"id": ..., "query": ..., "relevant": [...]}. Relevant IDs
    use kind:id form, such as event:event-12. All judgments must be
    researcher-supplied; no synthetic labels are generated.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    dataset.require_valid()
    if not cases:
        raise ValueError("benchmark cases cannot be empty")
    if (semantic_index is None) != (embedder is None):
        raise ValueError("semantic_index and embedder must be supplied together")
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    if semantic_index is not None:
        expected = tuple((row[0], row[1]) for row in trigram.records)
        actual = tuple((row[0], row[1]) for row in semantic_index.records)
        if actual != expected:
            raise ValueError("semantic index must represent the same dataset snapshot")
    hybrid = HybridSearchIndex(trigram, bm25, semantic=semantic_index)
    relevance: dict[str, Sequence[str]] = {}
    system_names = ["trigram", "bm25"]
    if semantic_index is not None:
        system_names.append("semantic")
    system_names.append("hybrid_rrf")
    rankings: dict[str, dict[str, Sequence[str]]] = {name: {} for name in system_names}
    latencies: dict[str, dict[str, float]] = {name: {} for name in system_names}
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
        methods = [
            ("trigram", lambda query=query: trigram.search(query, limit=cutoff)),
            ("bm25", lambda query=query: bm25.search(query, limit=cutoff)),
        ]
        if semantic_index is not None and embedder is not None:
            methods.append((
                "semantic",
                lambda query=query: semantic_index.search(
                    query, embedder=embedder, limit=cutoff
                ),
            ))
        methods.append((
            "hybrid_rrf",
            lambda query=query: hybrid.search(
                query, embedder=embedder, limit=cutoff
            ),
        ))
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
