import runpy
import sys
from pathlib import Path

benchmark_dir = Path(__file__).parents[1] / "benchmarks"
sys.path.insert(0, str(benchmark_dir))
benchmark = runpy.run_path(str(benchmark_dir / "benchmark_historian_relevance.py"))
hybrid_benchmark = runpy.run_path(str(benchmark_dir / "benchmark_hybrid_retrieval.py"))
build_historypy_dataset = benchmark["build_historypy_dataset"]
evaluate = benchmark["evaluate"]
resolve_gold_ids = benchmark["resolve_gold_ids"]
stratified_holdout = hybrid_benchmark["stratified_holdout"]
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


def test_stratified_holdout_is_deterministic_and_preserves_question_types():
    questions = [
        {"id": f"fr-{i}", "question": f"Question {i}", "question_type": "MH"}
        for i in range(10)
    ] + [
        {"id": f"en-{i}", "question": f"Question EN {i}", "question_type": "SH"}
        for i in range(5)
    ]
    train, test = stratified_holdout(questions, test_fraction=0.2, seed=41)
    train_again, test_again = stratified_holdout(
        questions, test_fraction=0.2, seed=41
    )
    assert train == train_again
    assert test == test_again
    assert len(train) + len(test) == len(questions)
    assert {row["question_type"] for row in train} == {"MH", "SH"}
    assert {row["question_type"] for row in test} == {"MH", "SH"}
    assert not ({row["id"] for row in train} & {row["id"] for row in test})
