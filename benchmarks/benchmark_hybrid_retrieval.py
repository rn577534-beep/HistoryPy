"""Compare trigram, BM25, hybrid, and optional semantic retrieval.

Uses HistoriQA-ThirdRepublic helpers and preserves the dataset's attribution.
An external embedding model is opt-in; no model or network provider is selected.
"""
from __future__ import annotations

import argparse
import importlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark_historian_relevance import (
    build_historypy_dataset,
    load_jsonl,
    resolve_gold_ids,
)
from historypy import (
    BM25SearchIndex,
    DatasetSearchIndex,
    HybridSearchIndex,
    SemanticSearchIndex,
)


def evaluate(index: Any, questions: list[dict[str, Any]], top_k: int, embedder=None):
    groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {"n": 0, "recall": 0.0, "mrr": 0.0, "success": 0.0}
    )
    start = time.perf_counter()
    for row in questions:
        query = str(row.get("question") or "").strip()
        gold = set(row["gold_ids"])
        if isinstance(index, (HybridSearchIndex, SemanticSearchIndex)):
            hits = index.search(query, embedder=embedder, limit=top_k)
        else:
            hits = index.search(query, limit=top_k)
        ids = [hit.record_id for hit in hits]
        ranks = [rank for rank, value in enumerate(ids, 1) if value in gold]
        bucket = groups[str(row.get("question_type") or "unspecified")]
        bucket["n"] += 1
        bucket["recall"] += len(set(ids) & gold) / len(gold)
        bucket["mrr"] += 1 / ranks[0] if ranks else 0.0
        bucket["success"] += float(bool(ranks))
    elapsed = (time.perf_counter() - start) * 1000
    count = sum(int(value["n"]) for value in groups.values())
    summary = {
        key: {
            "questions": int(value["n"]),
            f"recall@{top_k}": round(value["recall"] / value["n"], 4),
            f"mrr@{top_k}": round(value["mrr"] / value["n"], 4),
            f"success@{top_k}": round(value["success"] / value["n"], 4),
        }
        for key, value in sorted(groups.items())
    }
    return {
        "evaluated_questions": count,
        "mean_query_ms": round(elapsed / count, 3) if count else 0.0,
        f"overall_recall@{top_k}": round(
            sum(value["recall"] for value in groups.values()) / count, 4
        ) if count else 0.0,
        f"overall_mrr@{top_k}": round(
            sum(value["mrr"] for value in groups.values()) / count, 4
        ) if count else 0.0,
        "by_question_type": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--semantic-embedder", help="Optional module:callable embedder")
    parser.add_argument("--semantic-model-id", help="Stable ID of the embedding model")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")

    corpus = load_jsonl(args.corpus)
    questions = load_jsonl(args.questions)
    dataset, id_map = build_historypy_dataset(corpus)
    questions = [
        {**row, "gold_ids": resolve_gold_ids(row, id_map)}
        for row in questions
        if row.get("question") and row.get("gold_ids")
    ]
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    report: dict[str, Any] = {
        "dataset": "HistoriQA-ThirdRepublic",
        "corpus_records": len(corpus),
        "questions": len(questions),
        "top_k": args.top_k,
        "methods": {
            "trigram_all_terms": evaluate(trigram, questions, args.top_k),
            "bm25": evaluate(bm25, questions, args.top_k),
            "hybrid_trigram_bm25_rrf": evaluate(
                HybridSearchIndex(trigram, bm25), questions, args.top_k
            ),
        },
        "semantic_model_id": None,
        "limitations": [
            "French-language 1887 corpus only; not a global historical benchmark.",
            "Gold document labels measure retrieval relevance, not historical truth.",
            "RRF scores are rank-fusion signals, not calibrated probabilities.",
        ],
    }
    if args.semantic_embedder:
        if not args.semantic_model_id or ":" not in args.semantic_embedder:
            parser.error("semantic options require module:callable and --semantic-model-id")
        module_name, attribute = args.semantic_embedder.split(":", 1)
        embedder = getattr(importlib.import_module(module_name), attribute)
        semantic = SemanticSearchIndex.build(
            dataset, embedder=embedder, model_id=args.semantic_model_id
        )
        report["semantic_model_id"] = semantic.model_id
        report["methods"]["semantic"] = evaluate(
            semantic, questions, args.top_k, embedder
        )
        report["methods"]["hybrid_trigram_bm25_semantic_rrf"] = evaluate(
            HybridSearchIndex(trigram, bm25, semantic),
            questions, args.top_k, embedder,
        )
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
