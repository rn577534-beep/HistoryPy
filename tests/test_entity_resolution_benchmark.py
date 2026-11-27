import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "benchmarks" / "benchmark_entity_resolution.py"
SPEC = importlib.util.spec_from_file_location("historypy_entity_resolution_benchmark", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate = MODULE.evaluate


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
    with pytest.raises(TypeError, match="boolean"):
        evaluate([{"language": "en", "left": "a", "right": "b", "match": 1}], 0.5)
