import runpy
from pathlib import Path

benchmark = runpy.run_path(
    str(Path(__file__).parents[1] / "benchmarks" / "benchmark_historian_relevance.py")
)
build_historypy_dataset = benchmark["build_historypy_dataset"]
evaluate = benchmark["evaluate"]
resolve_gold_ids = benchmark["resolve_gold_ids"]
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

    dataset, id_map = build_historypy_dataset(corpus)
    resolved_questions = [
        {**row, "gold_ids": resolve_gold_ids(row, id_map)}
        for row in questions
    ]
    report = evaluate(DatasetSearchIndex.build(dataset), resolved_questions, top_k=1)

    assert len(dataset.events) == 2
    assert report["evaluated_questions"] == 2
    assert report["overall_recall@1"] == 1.0
    assert report["overall_mrr@1"] == 1.0
    assert report["by_question_type"]["SH"]["success@1"] == 1.0
