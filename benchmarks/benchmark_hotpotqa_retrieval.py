"""Evaluate HistoryPy retrieval on English HotpotQA multi-hop questions.

HotpotQA is a general Wikipedia multi-hop benchmark, not a history-only corpus.
Its supplied context paragraphs are deduplicated into one searchable corpus;
supporting-fact titles are the relevance labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

if __package__:
    from .benchmark_hybrid_retrieval import evaluate, split_summary, stratified_holdout
else:
    from benchmark_hybrid_retrieval import evaluate, split_summary, stratified_holdout

from historypy import (
    BM25SearchIndex,
    DatasetSearchIndex,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HybridSearchIndex,
)


def load_hotpotqa(path: Path) -> tuple[HistoricalDataset, list[dict[str, Any]]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    documents: dict[str, list[str]] = {}
    questions: list[dict[str, Any]] = []
    for row in rows:
        for title, sentences in row["context"]:
            bucket = documents.setdefault(title, [])
            for sentence in sentences:
                if sentence not in bucket:
                    bucket.append(sentence)
        gold_titles = sorted({
            fact[0] for fact in row.get("supporting_facts", [])
        })
        if not gold_titles:
            continue
        questions.append({
            "id": row.get("_id") or row.get("id"),
            "question": row["question"],
            "question_type": f"{row.get('type', 'unknown')}:{row.get('level', 'unknown')}",
            "gold_titles": gold_titles,
        })

    title_to_id = {
        title: "wiki-" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:20]
        for title in documents
    }
    dataset = HistoricalDataset(events=tuple(
        HistoricalEvent(
            id=title_to_id[title],
            title=title,
            date=HistoricalDate(
                original_expression="date not supplied by HotpotQA",
                calendar="unspecified",
            ),
            summary=" ".join(sentences),
            tags=("hotpotqa", "english-wikipedia-context"),
        )
        for title, sentences in sorted(documents.items())
    ))
    resolved = [
        {
            **row,
            "gold_ids": [title_to_id[title] for title in row["gold_titles"]
                         if title in title_to_id],
        }
        for row in questions
    ]
    return dataset, resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")

    dataset, questions = load_hotpotqa(args.data)
    train, held_out = stratified_holdout(
        questions, test_fraction=args.test_fraction, seed=args.split_seed
    )
    trigram = DatasetSearchIndex.build(dataset)
    bm25 = BM25SearchIndex.build(dataset)
    hybrid = HybridSearchIndex(trigram, bm25)
    methods = {
        "trigram_all_terms": evaluate(trigram, held_out, args.top_k),
        "bm25": evaluate(bm25, held_out, args.top_k),
        "hybrid_trigram_bm25_rrf": evaluate(hybrid, held_out, args.top_k),
        "hybrid_trigram_bm25_decomposed_rrf": evaluate(
            hybrid, held_out, args.top_k, decompose=True
        ),
    }
    report = {
        "benchmark": "hotpotqa-english-multi-hop",
        "language": "English",
        "corpus_documents": len(dataset.events),
        "available_questions": len(questions),
        "held_out_questions": len(held_out),
        "train_questions": len(train),
        "split": {
            "strategy": "deterministic question-type-stratified SHA-256 holdout",
            "seed": args.split_seed,
            "test_fraction": args.test_fraction,
            "train_by_type": split_summary(train),
            "held_out_by_type": split_summary(held_out),
        },
        "methods_held_out": methods,
        "limitations": [
            "HotpotQA is general Wikipedia multi-hop QA, not history-only.",
            "The searchable corpus is the union of context paragraphs supplied with the dataset.",
            "Supporting-fact titles are relevance labels, not historical truth labels.",
            "This split is for evaluation; no model is trained on the held-out questions.",
        ],
        "license": "CC BY-SA 4.0; preserve dataset attribution and share-alike terms.",
        "citation": (
            "Yang et al. (2018), HotpotQA: A Dataset for Diverse, Explainable "
            "Multi-hop Question Answering, EMNLP 2018."
        ),
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
