"""Reproducible information-retrieval evaluation without third-party dependencies.

Gold labels are researcher-supplied relevance judgments. Metrics measure ranking
agreement with those labels, not historical truth or source credibility.
"""
from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricValues:
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank_at_k: float
    ndcg_at_k: float
    success_at_k: float


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    mean: float
    lower: float
    upper: float
    samples: int


@dataclass(frozen=True, slots=True)
class SystemEvaluation:
    system: str
    query_count: int
    metrics: MetricValues
    intervals: Mapping[str, ConfidenceInterval]
    mean_latency_ms: float | None = None
    median_latency_ms: float | None = None
    p95_latency_ms: float | None = None


@dataclass(frozen=True, slots=True)
class PairedComparison:
    baseline: str
    candidate: str
    metric: str
    mean_delta: float
    ci95_lower: float
    ci95_upper: float
    bootstrap_samples: int


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    schema_version: str
    cutoff: int
    query_count: int
    systems: tuple[SystemEvaluation, ...]
    paired_comparisons: tuple[PairedComparison, ...]
    warnings: tuple[str, ...]


_METRICS = (
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank_at_k",
    "ndcg_at_k",
    "success_at_k",
)


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _query_metrics(
    relevance: Mapping[str, float], ranking: Sequence[str], cutoff: int
) -> MetricValues:
    top = ranking[:cutoff]
    relevant = {key for key, grade in relevance.items() if grade > 0}
    found = [doc_id for doc_id in top if doc_id in relevant]
    precision = len(found) / cutoff
    recall = len(found) / len(relevant) if relevant else 0.0
    reciprocal_rank = next(
        (1.0 / rank for rank, doc_id in enumerate(top, start=1) if doc_id in relevant),
        0.0,
    )
    dcg = sum(
        (2.0 ** relevance.get(doc_id, 0.0) - 1.0) / math.log2(rank + 1)
        for rank, doc_id in enumerate(top, start=1)
    )
    ideal = sorted((grade for grade in relevance.values() if grade > 0), reverse=True)[:cutoff]
    idcg = sum(
        (2.0 ** grade - 1.0) / math.log2(rank + 1)
        for rank, grade in enumerate(ideal, start=1)
    )
    return MetricValues(
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank_at_k=reciprocal_rank,
        ndcg_at_k=dcg / idcg if idcg else 0.0,
        success_at_k=1.0 if found else 0.0,
    )


def _bootstrap_interval(
    values: Sequence[float], *, samples: int, rng: random.Random
) -> ConfidenceInterval:
    if not values:
        return ConfidenceInterval(0.0, 0.0, 0.0, samples)
    estimates = [
        mean(values[rng.randrange(len(values))] for _ in range(len(values)))
        for _ in range(samples)
    ]
    return ConfidenceInterval(
        mean=mean(values),
        lower=_percentile(estimates, 0.025),
        upper=_percentile(estimates, 0.975),
        samples=samples,
    )


def evaluate_rankings(
    relevance: Mapping[str, Mapping[str, float] | Sequence[str]],
    rankings: Mapping[str, Mapping[str, Sequence[str]]],
    *,
    cutoff: int = 10,
    latencies_ms: Mapping[str, Mapping[str, float]] | None = None,
    bootstrap_samples: int = 2000,
    seed: int = 2026,
) -> EvaluationReport:
    """Compare ranked systems on identical judged queries with paired intervals.

    Relevance maps query IDs to relevant document IDs or graded relevance maps.
    Rankings map system -> query ID -> ordered document IDs. IDs should be
    stable and namespaced, for example event:event-12.
    """
    if not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 1:
        raise ValueError("cutoff must be a positive integer")
    if not isinstance(bootstrap_samples, int) or isinstance(bootstrap_samples, bool) or bootstrap_samples < 100:
        raise ValueError("bootstrap_samples must be an integer of at least 100")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if not relevance:
        raise ValueError("relevance judgments cannot be empty")
    if not rankings:
        raise ValueError("at least one ranked system is required")

    judged: dict[str, dict[str, float]] = {}
    for query_id, labels in relevance.items():
        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError("query IDs must be non-empty strings")
        converted = dict(labels) if isinstance(labels, Mapping) else {doc_id: 1.0 for doc_id in labels}
        normalized: dict[str, float] = {}
        for doc_id, grade in converted.items():
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError("relevance document IDs must be non-empty strings")
            if isinstance(grade, bool) or not isinstance(grade, (int, float)):
                raise TypeError("relevance grades must be numeric")
            if not math.isfinite(grade) or grade < 0:
                raise ValueError("relevance grades must be finite and non-negative")
            normalized[doc_id] = float(grade)
        judged[query_id] = normalized

    expected_queries = set(judged)
    system_rows: list[SystemEvaluation] = []
    per_system: dict[str, dict[str, MetricValues]] = {}
    rng = random.Random(seed)
    for system, query_rankings in rankings.items():
        if not isinstance(system, str) or not system.strip():
            raise ValueError("system names must be non-empty strings")
        if set(query_rankings) != expected_queries:
            missing = sorted(expected_queries - set(query_rankings))
            extra = sorted(set(query_rankings) - expected_queries)
            raise ValueError(f"{system}: query mismatch; missing={missing}, extra={extra}")
        rows: dict[str, MetricValues] = {}
        for query_id, ranking in query_rankings.items():
            if isinstance(ranking, (str, bytes)):
                raise TypeError("each ranking must be a sequence of document IDs")
            if any(not isinstance(item, str) or not item.strip() for item in ranking):
                raise ValueError("ranked document IDs must be non-empty strings")
            if len(set(ranking)) != len(ranking):
                raise ValueError(f"{system}/{query_id}: ranking contains duplicate IDs")
            rows[query_id] = _query_metrics(judged[query_id], ranking, cutoff)
        per_system[system] = rows
        columns = {
            name: [getattr(rows[qid], name) for qid in judged]
            for name in _METRICS
        }
        intervals = {
            name: _bootstrap_interval(values, samples=bootstrap_samples, rng=rng)
            for name, values in columns.items()
        }
        latency_values = list(latencies_ms.get(system, {}).values()) if latencies_ms and system in latencies_ms else []
        if latency_values and (
            len(latency_values) != len(judged)
            or any(not math.isfinite(value) or value < 0 for value in latency_values)
        ):
            raise ValueError("latencies must be finite, non-negative, and cover every query")
        system_rows.append(SystemEvaluation(
            system=system,
            query_count=len(judged),
            metrics=MetricValues(**{name: mean(values) for name, values in columns.items()}),
            intervals=intervals,
            mean_latency_ms=mean(latency_values) if latency_values else None,
            median_latency_ms=_percentile(latency_values, 0.5) if latency_values else None,
            p95_latency_ms=_percentile(latency_values, 0.95) if latency_values else None,
        ))

    baseline = next(iter(per_system))
    comparisons: list[PairedComparison] = []
    for candidate, candidate_rows in list(per_system.items())[1:]:
        for metric in _METRICS:
            deltas = [
                getattr(candidate_rows[qid], metric) - getattr(per_system[baseline][qid], metric)
                for qid in judged
            ]
            interval = _bootstrap_interval(deltas, samples=bootstrap_samples, rng=rng)
            comparisons.append(PairedComparison(
                baseline=baseline,
                candidate=candidate,
                metric=metric,
                mean_delta=mean(deltas),
                ci95_lower=interval.lower,
                ci95_upper=interval.upper,
                bootstrap_samples=bootstrap_samples,
            ))

    return EvaluationReport(
        schema_version="1.0",
        cutoff=cutoff,
        query_count=len(judged),
        systems=tuple(system_rows),
        paired_comparisons=tuple(comparisons),
        warnings=(
            "Metrics measure agreement with supplied relevance judgments, not historical truth.",
            "Bootstrap intervals quantify query-sample variability; they do not correct biased or incomplete judgments.",
            "Keep threshold/model selection separate from a final untouched test set.",
            "Latency depends on hardware, cache state, index construction, and runtime environment.",
        ),
    )


def evaluation_report_dict(report: EvaluationReport) -> dict[str, Any]:
    """Convert a report into JSON-compatible built-in values."""
    return asdict(report)
