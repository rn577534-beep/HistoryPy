"""Evaluate name matching on a researcher-reviewed multilingual JSONL gold set.

Each row must contain language, left, right, and match (boolean). The file
should be versioned and licensed independently; this script invents no labels.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from historypy import compare_names


def evaluate(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    groups: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0}
    )
    for row in rows:
        language = str(row["language"])
        expected = row["match"]
        if not isinstance(expected, bool):
            raise TypeError("match must be a JSON boolean")
        predicted = compare_names(str(row["left"]), str(row["right"])).combined >= threshold
        bucket = groups[language]
        bucket["total"] += 1
        if predicted and expected:
            bucket["tp"] += 1
        elif predicted:
            bucket["fp"] += 1
        elif expected:
            bucket["fn"] += 1
        else:
            bucket["tn"] += 1

    def metrics(counts: dict[str, int]) -> dict[str, float | int]:
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            **counts,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positive_rate": round(
                fp / (fp + counts["tn"]), 4
            ) if fp + counts["tn"] else 0.0,
        }

    return {
        "threshold": threshold,
        "languages": {language: metrics(counts) for language, counts in sorted(groups.items())},
        "limitations": [
            "Metrics apply only to the supplied reviewed gold set.",
            "A string-similarity threshold does not establish identity or transliteration.",
            "Tune thresholds on training data and report final metrics on a separate holdout.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-jsonl", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("--threshold must be between 0 and 1")
    rows = [
        json.loads(line)
        for line in args.gold_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = json.dumps(evaluate(rows, args.threshold), ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
