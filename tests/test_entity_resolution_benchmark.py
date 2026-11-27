import pytest

from benchmarks.benchmark_entity_resolution import evaluate


def test_multilingual_benchmark_reports_metrics_per_language():
    rows = [
        {"language": "en", "left": "Alexander", "right": "Alexander", "match": True},
        {"language": "en", "left": "Alexander", "right": "Alexandria", "match": False},
        {"language": "bn", "left": "ঢাকা", "right": "ঢাকা", "match": True},
        {"language": "fr", "left": "Paris", "right": "Paris", "match": True},
    ]
    report = evaluate(rows, 0.9)
    assert report["languages"]["en"]["tp"] == 1
    assert report["languages"]["en"]["tn"] == 1
    assert report["languages"]["bn"]["recall"] == 1.0
    assert report["languages"]["fr"]["precision"] == 1.0


def test_benchmark_rejects_non_boolean_gold_label():
    with pytest.raises(ValueError, match="boolean"):
        evaluate([{"language": "en", "left": "a", "right": "b", "match": 1}], 0.5)
