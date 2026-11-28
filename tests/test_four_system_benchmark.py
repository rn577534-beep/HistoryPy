import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from benchmark_four_systems import build_cases


def test_build_cases_preserves_researcher_gold_document_ids():
    rows = [{
        "question_id": "q-001",
        "question": "What reforms were discussed?",
        "gold_ids": ["document-1"],
    }]
    cases = build_cases(rows, {"document-1": ("parliament::document-1",)})
    assert cases == [{
        "id": "q-001",
        "source_question_id": "q-001",
        "query": "What reforms were discussed?",
        "question_type": "unspecified",
        "relevant": ["event:parliament::document-1"],
    }]


def test_build_cases_disambiguates_reused_ids_and_deduplicates_exact_rows():
    rows = [
        {"question_id": "q-001", "question": "first", "gold_ids": ["doc-1"]},
        {"question_id": "q-001", "question": "second", "gold_ids": ["doc-1"]},
        {"question_id": "q-001", "question": "second", "gold_ids": ["doc-1"]},
    ]
    cases = build_cases(rows, {"doc-1": ("collection::doc-1",)})
    assert len(cases) == 2
    assert cases[0]["id"] == "q-001"
    assert cases[1]["id"].startswith("q-001::")
    assert {case["source_question_id"] for case in cases} == {"q-001"}
    assert len({case["id"] for case in cases}) == 2
