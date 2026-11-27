import pytest

from historypy.research.evaluation import evaluate_rankings


def test_metrics_and_paired_comparison_are_computed_on_same_queries():
    report = evaluate_rankings(
        {"q1": ["a", "b"], "q2": ["c"]},
        {
            "baseline": {"q1": ["x", "a"], "q2": ["c"]},
            "improved": {"q1": ["a", "b"], "q2": ["c"]},
        },
        cutoff=2,
        bootstrap_samples=500,
        seed=9,
    )
    baseline, improved = report.systems
    assert baseline.metrics.recall_at_k == 0.75
    assert improved.metrics.recall_at_k == 1.0
    assert improved.metrics.reciprocal_rank_at_k == 1.0
    assert report.paired_comparisons[0].mean_delta > 0
    assert report.paired_comparisons[0].baseline == "baseline"


def test_bootstrap_is_reproducible_and_latency_is_reported():
    args = (
        {"q1": ["a"], "q2": ["b"]},
        {"bm25": {"q1": ["a"], "q2": ["b"]}},
    )
    first = evaluate_rankings(*args, latencies_ms={"bm25": {"q1": 2.0, "q2": 4.0}}, seed=42)
    second = evaluate_rankings(*args, latencies_ms={"bm25": {"q1": 2.0, "q2": 4.0}}, seed=42)
    assert first == second
    assert first.systems[0].median_latency_ms == 3.0
    assert first.systems[0].p95_latency_ms is not None


def test_evaluator_rejects_mismatched_queries_and_duplicate_ranked_ids():
    with pytest.raises(ValueError, match="query mismatch"):
        evaluate_rankings({"q1": ["a"]}, {"bm25": {}})
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_rankings({"q1": ["a"]}, {"bm25": {"q1": ["a", "a"]}})


def test_evaluator_supports_graded_relevance_and_empty_gold_set():
    report = evaluate_rankings(
        {"q1": {"a": 3, "b": 1}, "q2": []},
        {"system": {"q1": ["b", "a"], "q2": []}},
        cutoff=2,
        bootstrap_samples=200,
    )
    assert 0 < report.systems[0].metrics.ndcg_at_k < 1
    assert report.systems[0].metrics.recall_at_k == 0.5


def test_evaluator_validates_cutoff_and_bootstrap_count():
    with pytest.raises(ValueError, match="cutoff"):
        evaluate_rankings({"q": ["a"]}, {"s": {"q": ["a"]}}, cutoff=0)
    with pytest.raises(ValueError, match="100"):
        evaluate_rankings(
            {"q": ["a"]}, {"s": {"q": ["a"]}}, bootstrap_samples=10
        )
