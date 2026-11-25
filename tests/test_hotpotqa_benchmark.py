import json
import runpy
import sys
from pathlib import Path

benchmark_dir = Path(__file__).parents[1] / "benchmarks"
sys.path.insert(0, str(benchmark_dir))
benchmark = runpy.run_path(str(benchmark_dir / "benchmark_hotpotqa_retrieval.py"))
load_hotpotqa = benchmark["load_hotpotqa"]


def test_hotpotqa_loader_builds_unique_documents_and_gold_support_titles(tmp_path):
    rows = [
        {
            "_id": "q1",
            "question": "Which city is the birthplace of the founder of X?",
            "type": "bridge",
            "level": "medium",
            "supporting_facts": [["Person", 0], ["City", 1]],
            "context": [
                ["Person", ["Person founded X.", "Person was born in City."]],
                ["City", ["City is a historical settlement."]],
                ["Distractor", ["An unrelated paragraph."]],
            ],
        },
        {
            "_id": "q2",
            "question": "Compare two facts about Person and City.",
            "type": "comparison",
            "level": "hard",
            "supporting_facts": [["Person", 0], ["City", 0]],
            "context": [
                ["Person", ["Person founded X."]],
                ["City", ["City is a historical settlement."]],
            ],
        },
    ]
    path = tmp_path / "hotpot.json"
    path.write_text(json.dumps(rows), encoding="utf-8")

    dataset, questions = load_hotpotqa(path)

    assert len(dataset.events) == 3
    assert len(questions) == 2
    assert questions[0]["question_type"] == "bridge:medium"
    assert len(questions[0]["gold_ids"]) == 2
    assert questions[0]["gold_ids"] == questions[1]["gold_ids"]
