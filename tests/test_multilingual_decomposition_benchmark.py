from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from benchmark_multilingual_decomposition import (
    compare_decomposition,
    macro_average,
)


class FakeHybridIndex:
    def search(self, query, *, limit, decompose):
        if decompose:
            return [
                SimpleNamespace(record_id="gold"),
                SimpleNamespace(record_id="other"),
            ][:limit]
        return [
            SimpleNamespace(record_id="other"),
            SimpleNamespace(record_id="gold"),
        ][:limit]


def test_paired_decomposition_comparison_uses_same_gold_rows():
    report = compare_decomposition(
        FakeHybridIndex(),
        [{"question": "multi-hop query", "gold_ids": ["gold"]}],
        top_k=2,
    )
    assert report["baseline"]["recall@2"] == 1.0
    assert report["baseline"]["mrr@2"] == 0.5
    assert report["decomposed"]["recall@2"] == 1.0
    assert report["decomposed"]["mrr@2"] == 1.0
    assert report["delta_decomposed_minus_baseline"] == {
        "recall@2": 0.0,
        "mrr@2": 0.5,
    }


def test_macro_average_weights_languages_equally():
    reports = {
        "French": {
            "decomposed": {"recall@10": 0.8, "mrr@10": 0.6},
            "delta_decomposed_minus_baseline": {"recall@10": 0.1, "mrr@10": 0.2},
        },
        "English": {
            "decomposed": {"recall@10": 0.4, "mrr@10": 0.2},
            "delta_decomposed_minus_baseline": {"recall@10": -0.1, "mrr@10": 0.0},
        },
    }
    assert macro_average(reports, top_k=10) == {
        "languages": 2,
        "recall@10": 0.6,
        "mrr@10": 0.4,
    }
