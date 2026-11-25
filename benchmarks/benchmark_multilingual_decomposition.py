"""Compare multi-hop decomposition before/after Recall@k and MRR by language.

French: HistoriQA-ThirdRepublic. English: HotpotQA. Both use deterministic,
question-type-stratified held-out questions and the same trigram+BM25 RRF index
within each language. This measures retrieval relevance, not historical truth.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from benchmark_historian_relevance import (
    build_historypy_dataset,
    load_jsonl,
    resolve_gold_ids,
)
from benchmark_hotpotqa_retrieval import load_hotpotqa
from benchmark_hybrid_retrieval import stratified_holdout, split_summary

from historypy import BM25SearchIndex, DatasetSearchIndex, HybridSearchIndex


def evaluate_hybrid(
    index: HybridSearchIndex,
    questions: list[dict[str, Any]],
    *,
    top_k: int,
    decompose: bool,
) -> dict[str, Any]:
    """Evaluate the same held-out rows with decomposition switched on/off."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    reciprocal_ranks: list[float] = []
    recalls: list[float] = []
    successes: list[float] = []
    for row in questions:
        query = str(row.get("question") or "").strip()
        gold_ids = {str(value) for value in row.get("gold_ids", ())}
        if not query or not gold_ids:
            continue
        hits = index.search(query, limit=top_k, decompose=decompose)
        retrieved = [hit.record_id for hit in hits]
        relevant_ranks = [
            rank for rank, record_id in enumerate(retrieved, start=1)
            if record_id in gold_ids
        ]
        recalls.append(len(set(retrieved) & gold_ids) / len(gold_ids))
        reciprocal_ranks.append(1 / relevant_ranks[0] if relevant_ranks else 0.0)
        successes.append(float(bool(relevant_ranks)))
    count = len(recalls)
    return {
        "evaluated_questions": count,
        f"recall@{top_k}": round(statistics.mean(recalls), 4) if count else 0.0,
        f"mrr@{top_k}": round(statistics.mean(reciprocal_ranks), 4) if count else 0.0,
        f"success@{top_k}": round(statistics.mean(successes), 4) if count else 0.0,
    }


def compare_decomposition(
    index: HybridSearchIndex,
    questions: list[dict[str, Any]],
    *,
    top_k: int = 10,
) -> dict[str, Any]:
    """Return paired baseline/decomposed metrics and absolute metric deltas."""
    baseline = evaluate_hybrid(index, questions, top_k=top_k, decompose=False)
    decomposed = evaluate_hybrid(index, questions, top_k=top_k, decompose=True)
    recall_key = f"recall@{top_k}"
    mrr_key = f"mrr@{top_k}"
    return {
        "baseline": baseline,
        "decomposed": decomposed,
        "delta_decomposed_minus_baseline": {
            recall_key: round(decomposed[recall_key] - baseline[recall_key], 4),
            mrr_key: round(decomposed[mrr_key] - baseline[mrr_key], 4),
        },
    }


def evaluate_language(
    dataset,
    questions: list[dict[str, Any]],
    *,
    language: str,
    top_k: int,
    test_fraction: float,
    split_seed: int,
) -> dict[str, Any]:
    """Build a same-corpus lexical hybrid index and evaluate held-out questions."""
    if not questions:
        raise ValueError(f"No evaluable {language} questions were supplied")
    train, held_out = stratified_holdout(
        questions, test_fraction=test_fraction, seed=split_seed
    )
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    hybrid = HybridSearchIndex(trigram, bm25)
    comparison = compare_decomposition(hybrid, held_out, top_k=top_k)
    return {
        "language": language,
        "corpus_records": len(dataset.events),
        "available_questions": len(questions),
        "train_questions": len(train),
        "held_out_questions": len(held_out),
        "split_by_question_type": split_summary(held_out),
        **comparison,
    }


def macro_average(
    language_reports: dict[str, dict[str, Any]], *, top_k: int
) -> dict[str, float | int]:
    """Unweighted language macro-average; each language contributes once."""
    if not language_reports:
        return {"languages": 0, f"recall@{top_k}": 0.0, f"mrr@{top_k}": 0.0}
    recall_key = f"recall@{top_k}"
    mrr_key = f"mrr@{top_k}"
    return {
        "languages": len(language_reports),
        recall_key: round(statistics.mean(
            row["decomposed"][recall_key] for row in language_reports.values()
        ), 4),
        mrr_key: round(statistics.mean(
            row["decomposed"][mrr_key] for row in language_reports.values()
        ), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--french-corpus", type=Path, required=True)
    parser.add_argument("--french-questions", type=Path, required=True)
    parser.add_argument("--english-hotpotqa", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if not 0.0 < args.test_fraction < 1.0:
        parser.error("--test-fraction must be between 0 and 1")

    french_corpus = load_jsonl(args.french_corpus)
    french_questions = load_jsonl(args.french_questions)
    french_dataset, id_map = build_historypy_dataset(french_corpus)
    french_questions = [
        {**row, "gold_ids": resolve_gold_ids(row, id_map)}
        for row in french_questions
        if row.get("question") and row.get("gold_ids")
    ]
    english_dataset, english_questions = load_hotpotqa(args.english_hotpotqa)

    reports = {
        "French": evaluate_language(
            french_dataset, french_questions, language="French",
            top_k=args.top_k, test_fraction=args.test_fraction,
            split_seed=args.split_seed,
        ),
        "English": evaluate_language(
            english_dataset, english_questions, language="English",
            top_k=args.top_k, test_fraction=args.test_fraction,
            split_seed=args.split_seed,
        ),
    }
    recall_key = f"recall@{args.top_k}"
    mrr_key = f"mrr@{args.top_k}"
    report = {
        "benchmark": "multilingual-multi-hop-decomposition-ablation",
        "methods": {
            "baseline": "Trigram + BM25 reciprocal-rank fusion on the full question",
            "decomposed": (
                "Same index and full-question anchor, plus conservative explicit "
                "English/French sub-question splitting"
            ),
        },
        "top_k": args.top_k,
        "split": {
            "strategy": "deterministic question-type-stratified SHA-256 holdout",
            "seed": args.split_seed,
            "test_fraction": args.test_fraction,
            "same_held_out_rows_for_both_methods": True,
        },
        "languages": reports,
        "macro_average_decomposed": macro_average(reports, top_k=args.top_k),
        "macro_delta_decomposed_minus_baseline": {
            recall_key: round(statistics.mean(
                row["delta_decomposed_minus_baseline"][recall_key]
                for row in reports.values()
            ), 4),
            mrr_key: round(statistics.mean(
                row["delta_decomposed_minus_baseline"][mrr_key]
                for row in reports.values()
            ), 4),
        },
        "limitations": [
            "French HistoriQA and English HotpotQA differ in corpus, domain, and annotation.",
            "The macro-average gives each language equal weight, not each question.",
            "The decomposition switch adds sub-questions but retains the full question.",
            "No semantic embedder is used in this ablation.",
            "Gold labels measure retrieval relevance, not historical truth.",
        ],
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
