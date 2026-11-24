from benchmarks.benchmark_historian_relevance import (
    build_historypy_dataset,
    evaluate,
)
from historypy import DatasetSearchIndex


def test_real_corpus_benchmark_loader_and_relevance_metrics():
    corpus = [
        {
            "id": "debate-1",
            "collection": "parliament",
            "document": ["M. Blanc présente ses réformes", "priorités de session"],
            "year": 1887,
            "month": 1,
            "day": 12,
        },
        {
            "id": "press-2",
            "collection": "newspaper",
            "document": "Le budget est discuté au parlement.",
            "year": 1887,
        },
    ]
    questions = [
        {
            "question": "réformes priorités session",
            "gold_ids": ["debate-1"],
            "question_type": "SH",
        },
        {
            "question": "budget parlement",
            "gold_ids": ["press-2"],
            "question_type": "SH",
        },
    ]

    dataset = build_historypy_dataset(corpus)
    report = evaluate(DatasetSearchIndex.build(dataset), questions, top_k=1)

    assert len(dataset.events) == 2
    assert report["evaluated_questions"] == 2
    assert report["overall_recall@1"] == 1.0
    assert report["overall_mrr@1"] == 1.0
    assert report["by_question_type"]["SH"]["success@1"] == 1.0
