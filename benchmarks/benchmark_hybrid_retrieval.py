"""Compare trigram, BM25, hybrid, and optional semantic retrieval.

Uses HistoriQA-ThirdRepublic helpers and preserves the dataset's attribution.
An external embedding model is opt-in; no model or network provider is selected.
"""
from __future__ import annotations

import argparse
import hashlib
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


def evaluate(
    index: Any, questions: list[dict[str, Any]], top_k: int,
    embedder=None, decompose: bool = False,
):
    groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {"n": 0, "recall": 0.0, "mrr": 0.0, "success": 0.0}
    )
    start = time.perf_counter()
    for row in questions:
        query = str(row.get("question") or "").strip()
        gold = set(row["gold_ids"])
        if isinstance(index, HybridSearchIndex):
            hits = index.search(
                query, embedder=embedder, limit=top_k, decompose=decompose
            )
        elif isinstance(index, SemanticSearchIndex):
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


def stratified_holdout(
    questions: list[dict[str, Any]],
    *,
    test_fraction: float = 0.2,
    seed: int = 2026,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create a deterministic question-type-stratified holdout.

    Gold labels are never used to select the split. For every category with at
    least two questions, at least one remains in each partition.
    """
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between 0 and 1")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        groups[str(row.get("question_type") or "unspecified")].append(row)
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for category, rows in sorted(groups.items()):
        ordered = sorted(
            rows,
            key=lambda row: hashlib.sha256(
                f"{seed}|{category}|{row.get('id') or row.get('question_id') or row.get('question')}".encode()
            ).hexdigest(),
        )
        if len(ordered) < 2:
            train.extend(ordered)
            continue
        test_count = min(
            len(ordered) - 1,
            max(1, round(len(ordered) * test_fraction)),
        )
        test.extend(ordered[:test_count])
        train.extend(ordered[test_count:])
    return train, test


def split_summary(
    questions: list[dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in questions:
        counts[str(row.get("question_type") or "unspecified")] += 1
    return dict(sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--semantic-embedder", help="Optional module:callable embedder")
    parser.add_argument("--semantic-model-id", help="Stable ID of the embedding model")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if not 0.0 < args.test_fraction < 1.0:
        parser.error("--test-fraction must be between 0 and 1")

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
    hybrid = HybridSearchIndex(trigram, bm25)
    train_questions, held_out_questions = stratified_holdout(
        questions, test_fraction=args.test_fraction, seed=args.split_seed
    )
    held_out_methods = {
        "trigram_all_terms": evaluate(trigram, held_out_questions, args.top_k),
        "bm25": evaluate(bm25, held_out_questions, args.top_k),
        "hybrid_trigram_bm25_rrf": evaluate(hybrid, held_out_questions, args.top_k),
        "hybrid_trigram_bm25_decomposed_rrf": evaluate(
            hybrid, held_out_questions, args.top_k, decompose=True
        ),
    }
    report: dict[str, Any] = {
        "dataset": "HistoriQA-ThirdRepublic",
        "corpus_records": len(corpus),
        "questions": len(questions),
        "top_k": args.top_k,
        "methods": {
            "trigram_all_terms": evaluate(trigram, questions, args.top_k),
            "bm25": evaluate(bm25, questions, args.top_k),
            "hybrid_trigram_bm25_rrf": evaluate(
                hybrid, questions, args.top_k
            ),
            "hybrid_trigram_bm25_decomposed_rrf": evaluate(
                hybrid, questions, args.top_k, decompose=True
            ),
        },
        "question_split": {
            "strategy": "deterministic question-type-stratified SHA-256 holdout",
            "seed": args.split_seed,
            "test_fraction_requested": args.test_fraction,
            "train_questions": len(train_questions),
            "held_out_questions": len(held_out_questions),
            "train_by_question_type": split_summary(train_questions),
            "held_out_by_question_type": split_summary(held_out_questions),
            "note": (
                "No retriever is trained on question labels; the holdout measures "
                "unseen questions against the same searchable corpus."
            ),
        },
        "held_out_methods": held_out_methods,
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
        hybrid_semantic = HybridSearchIndex(trigram, bm25, semantic)
        report["methods"]["hybrid_trigram_bm25_semantic_rrf"] = evaluate(
            hybrid_semantic, questions, args.top_k, embedder
        )
        report["methods"]["hybrid_trigram_bm25_semantic_decomposed_rrf"] = evaluate(
            hybrid_semantic, questions, args.top_k, embedder, decompose=True
        )
        report["held_out_methods"]["semantic"] = evaluate(
            semantic, held_out_questions, args.top_k, embedder
        )
        report["held_out_methods"]["hybrid_trigram_bm25_semantic_rrf"] = evaluate(
            hybrid_semantic, held_out_questions, args.top_k, embedder
        )
        report["held_out_methods"]["hybrid_trigram_bm25_semantic_decomposed_rrf"] = evaluate(
            hybrid_semantic, held_out_questions, args.top_k, embedder, decompose=True
        )
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
