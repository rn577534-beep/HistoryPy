"""Run a held-out four-system benchmark on pinned HistoriQA-ThirdRepublic data.

The dataset is downloaded by the workflow from its pinned upstream revision.
No relevance labels are generated or altered by this script.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

if __package__:
    from .benchmark_historian_relevance import (
        build_historypy_dataset,
        load_jsonl,
        resolve_gold_ids,
    )
    from .benchmark_hybrid_retrieval import split_summary, stratified_holdout
else:
    from benchmark_historian_relevance import (
        build_historypy_dataset,
        load_jsonl,
        resolve_gold_ids,
    )
    from benchmark_hybrid_retrieval import split_summary, stratified_holdout

from historypy import build_multilingual_semantic_index, run_retrieval_benchmark


def build_cases(
    question_rows: list[dict[str, Any]],
    id_map: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Convert gold IDs to unique stable query IDs without losing collisions.

    Exact duplicate question/label rows are deduplicated. If the upstream
    question identifier is reused for a different query or gold set, a stable
    content hash is appended so both judgments remain independently evaluable.
    """
    cases = []
    seen_ids: dict[str, str] = {}
    seen_payloads: set[tuple[str, str, tuple[str, ...]]] = set()
    for row in question_rows:
        base_id = str(row.get("question_id") or row.get("id") or "").strip()
        query = str(row.get("question") or "").strip()
        if not query:
            continue
        resolved = resolve_gold_ids(row, id_map)
        if not resolved:
            continue
        question_type = str(row.get("question_type") or "unspecified")
        payload = (query, question_type, tuple(sorted(resolved)))
        if payload in seen_payloads:
            continue
        seen_payloads.add(payload)
        if not base_id:
            raise ValueError("Every evaluable question must have a question_id or id")
        fingerprint = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:12]
        query_id = base_id
        if query_id in seen_ids:
            query_id = f"{base_id}::{fingerprint}"
        if query_id in seen_ids:
            if seen_ids[query_id] == fingerprint:
                continue
            raise ValueError(f"Stable question ID collision for {base_id!r}")
        seen_ids[query_id] = fingerprint
        cases.append({
            "id": query_id,
            "source_question_id": base_id,
            "query": query,
            "question_type": question_type,
            "relevant": [f"event:{record_id}" for record_id in resolved],
        })
    if not cases:
        raise ValueError("No benchmark questions with resolvable gold document IDs")
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument(
        "--semantic-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if not 0.0 < args.test_fraction < 1.0:
        parser.error("--test-fraction must be between 0 and 1")
    if args.bootstrap_samples < 100:
        parser.error("--bootstrap-samples must be at least 100")

    corpus_rows = load_jsonl(args.corpus)
    question_rows = load_jsonl(args.questions)
    dataset, id_map = build_historypy_dataset(corpus_rows)
    all_cases = build_cases(question_rows, id_map)
    train_cases, held_out_cases = stratified_holdout(
        all_cases, test_fraction=args.test_fraction, seed=args.split_seed
    )
    if not held_out_cases:
        raise ValueError("The held-out split is empty")

    index_started = time.perf_counter()
    semantic_index, embedder = build_multilingual_semantic_index(
        dataset, model_name=args.semantic_model, device="cpu"
    )
    semantic_index_build_ms = (time.perf_counter() - index_started) * 1000.0

    evaluation = run_retrieval_benchmark(
        dataset,
        held_out_cases,
        cutoff=args.top_k,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.split_seed,
        semantic_index=semantic_index,
        embedder=embedder,
    )
    report = {
        "benchmark": "HistoriQA-ThirdRepublic-four-system-held-out",
        "dataset_revision": "08bf3cc5f25ae5cd065ce8330f4275147081ab66",
        "corpus_records": len(corpus_rows),
        "available_questions": len(all_cases),
        "top_k": args.top_k,
        "split": {
            "strategy": "deterministic question-type-stratified SHA-256 holdout",
            "seed": args.split_seed,
            "test_fraction": args.test_fraction,
            "train_questions": len(train_cases),
            "held_out_questions": len(held_out_cases),
            "held_out_by_question_type": split_summary(held_out_cases),
            "same_held_out_queries_for_all_systems": True,
        },
        "semantic_model": args.semantic_model,
        "semantic_device": "cpu",
        "semantic_index_build_ms": round(semantic_index_build_ms, 3),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "evaluation": asdict(evaluation),
        "interpretation": [
            "Recall, MRR, nDCG and confidence intervals measure agreement with supplied gold document IDs, not historical truth.",
            "Bootstrap intervals reflect variation across held-out questions and do not correct annotation bias.",
            "Latency is query execution only; semantic model download and index construction are reported separately.",
            "The corpus is French-language and focuses on 1887; it is not a Bengali or global-history benchmark.",
            "This fixed test split is for reporting; tune on training data and preserve a fresh untouched split for future model selection.",
        ],
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
