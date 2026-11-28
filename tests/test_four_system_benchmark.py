from benchmarks.benchmark_four_systems import build_cases


def test_build_cases_preserves_researcher_gold_document_ids():
    rows = [{
        "question_id": "q-001",
        "question": "What reforms were discussed?",
        "gold_ids": ["document-1"],
    }]
    cases = build_cases(rows, {"document-1": ("parliament::document-1",)})
    assert cases == [{
        "id": "q-001",
        "query": "What reforms were discussed?",
        "question_type": "unspecified",
        "relevant": ["event:parliament::document-1"],
    }]


def test_build_cases_rejects_duplicate_question_ids():
    import pytest

    rows = [
        {"question_id": "q-001", "question": "first", "gold_ids": ["doc-1"]},
        {"question_id": "q-001", "question": "second", "gold_ids": ["doc-1"]},
    ]
    with pytest.raises(ValueError, match="Duplicate question ID"):
        build_cases(rows, {"doc-1": ("collection::doc-1",)})
