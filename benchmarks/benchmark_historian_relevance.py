"""Evaluate lexical retrieval against a real, historian-validated corpus.

Dataset: HistoriQA-ThirdRepublic (French, 1887), CC-BY 4.0.
See docs/research-benchmarks.md for attribution and scope.

Run:
    python benchmarks/benchmark_historian_relevance.py \
        --corpus corpus_dataset.jsonl --questions question_dataset.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from historypy import DatasetSearchIndex, HistoricalDataset, HistoricalDate, HistoricalEvent


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSON objects from a UTF-8 JSONL file with line-specific errors."""
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def document_text(value: Any) -> str:
    """Normalize a source document that may be a string or a list of segments."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(str(part) for part in value if part is not None)
    return ""


def record_date(row: dict[str, Any]) -> HistoricalDate:
    year = row.get("year")
    if year is None:
        return HistoricalDate(original_expression="date not supplied")
    year = int(year)
    month, day = row.get("month"), row.get("day")
    if month is not None and day is not None:
        iso = f"{year:04d}-{int(month):02d}-{int(day):02d}"
        return HistoricalDate(
            earliest=iso, latest=iso, precision="day", calendar="gregorian"
        )
    return HistoricalDate(
        earliest_year=year, latest_year=year, precision="year", calendar="gregorian"
    )


def build_historypy_dataset(corpus_rows: list[dict[str, Any]]) -> HistoricalDataset:
    events = []
    seen_ids = set()
    for row in corpus_rows:
        record_id = str(row.get("id", "")).strip()
        if not record_id:
            raise ValueError("Every corpus record must have a non-empty id")
        if record_id in seen_ids:
            raise ValueError(f"Duplicate corpus record id: {record_id}")
        seen_ids.add(record_id)
        collection = str(row.get("collection") or "unspecified")
        title = str(row.get("sommaire") or row.get("base_name") or record_id)
        text = document_text(row.get("document"))
        events.append(HistoricalEvent(
            id=record_id,
            title=title,
            date=record_date(row),
            summary=text,
            tags=(collection,),
        ))
    return HistoricalDataset(events=tuple(events))


def evaluate(
    index: DatasetSearchIndex,
    questions: list[dict[str, Any]],
    *,
    top_k: int,
    max_questions: int | None = None,
) -> dict[str, Any]:
    selected = questions[:max_questions] if max_questions else questions
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"questions": 0, "recall": 0.0, "success": 0.0, "mrr": 0.0, "zero_hits": 0}
    )
    all_reciprocal_ranks = []
    all_recalls = []
    started = time.perf_counter()
    evaluated = 0
    skipped = 0

    for row in selected:
        query = str(row.get("question") or "").strip()
        gold_ids = tuple(str(value) for value in row.get("gold_ids", ()) if value is not None)
        if not query or not gold_ids:
            skipped += 1
            continue
        category = str(row.get("question_type") or "unspecified")
        hits = index.search(query, limit=top_k)
        retrieved_ids = [hit.record_id for hit in hits]
        gold = set(gold_ids)
        relevant_ranks = [
            rank for rank, record_id in enumerate(retrieved_ids, start=1)
            if record_id in gold
        ]
        recall = len(set(retrieved_ids) & gold) / len(gold)
        reciprocal_rank = 1 / relevant_ranks[0] if relevant_ranks else 0.0
        bucket = totals[category]
        bucket["questions"] += 1
        bucket["recall"] += recall
        bucket["success"] += float(bool(relevant_ranks))
        bucket["mrr"] += reciprocal_rank
        bucket["zero_hits"] += int(not hits)
        all_recalls.append(recall)
        all_reciprocal_ranks.append(reciprocal_rank)
        evaluated += 1

    elapsed_ms = (time.perf_counter() - started) * 1000

    def summarize(bucket: dict[str, float]) -> dict[str, float | int]:
        count = int(bucket["questions"])
        return {
            "questions": count,
            f"recall@{top_k}": round(bucket["recall"] / count, 4) if count else 0.0,
            f"success@{top_k}": round(bucket["success"] / count, 4) if count else 0.0,
            f"mrr@{top_k}": round(bucket["mrr"] / count, 4) if count else 0.0,
            "zero_hit_questions": int(bucket["zero_hits"]),
        }

    return {
        "evaluated_questions": evaluated,
        "skipped_questions": skipped,
        "top_k": top_k,
        "query_evaluation_total_ms": round(elapsed_ms, 3),
        "mean_query_ms": round(elapsed_ms / evaluated, 3) if evaluated else 0.0,
        f"overall_recall@{top_k}": round(statistics.mean(all_recalls), 4) if all_recalls else 0.0,
        f"overall_mrr@{top_k}": round(statistics.mean(all_reciprocal_ranks), 4)
        if all_reciprocal_ranks else 0.0,
        "by_question_type": {
            category: summarize(bucket)
            for category, bucket in sorted(totals.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--max-questions", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if args.max_questions is not None and args.max_questions < 1:
        parser.error("--max-questions must be positive")

    corpus_rows = load_jsonl(args.corpus)
    question_rows = load_jsonl(args.questions)
    dataset = build_historypy_dataset(corpus_rows)
    build_started = time.perf_counter()
    index = DatasetSearchIndex.build(dataset)
    index_build_ms = (time.perf_counter() - build_started) * 1000
    metrics = evaluate(
        index, question_rows, top_k=args.top_k, max_questions=args.max_questions
    )
    report = {
        "benchmark": "historiqa-thirdrepublic-real-corpus",
        "corpus_records": len(corpus_rows),
        "available_questions": len(question_rows),
        "index_build_ms": round(index_build_ms, 3),
        "metrics": metrics,
        "retrieval_method": (
            "HistoryPy trigram candidate index with all-query-terms substring matching; "
            "deterministic record-ID tie-breaking."
        ),
        "dataset_note": (
            "French historical corpus from 1887. Gold document IDs are benchmark labels, "
            "not a claim that other documents are historically irrelevant."
        ),
        "limitations": (
            "One year, one national context, French language, and a finite set of "
            "historian-validated questions. This is a relevance benchmark, not a "
            "test of global historical coverage or truth."
        ),
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
