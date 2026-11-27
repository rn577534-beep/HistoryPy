from historypy import HistoricalDataset, HistoricalDate, HistoricalEvent
from historypy.research.benchmark import run_retrieval_benchmark


def test_runner_compares_trigram_bm25_and_rrf_on_same_gold_queries():
    dataset = HistoricalDataset(events=(
        HistoricalEvent(
            "e1", "Siege of Tyre",
            HistoricalDate(earliest_year=-332, latest_year=-332, calendar="gregorian"),
            summary="Alexander besieged the Phoenician city.",
        ),
        HistoricalEvent(
            "e2", "Fall of Constantinople",
            HistoricalDate(earliest_year=1453, latest_year=1453, calendar="gregorian"),
            summary="Ottoman forces captured the city.",
        ),
    ))
    report = run_retrieval_benchmark(
        dataset,
        [{"id": "q1", "query": "Alexander Tyre", "relevant": ["event:e1"]}],
        cutoff=2,
        bootstrap_samples=200,
    )
    assert report.query_count == 1
    assert {item.system for item in report.systems} == {"trigram", "bm25", "hybrid_rrf"}
    assert all(item.query_count == 1 for item in report.systems)
    assert all(item.mean_latency_ms is not None for item in report.systems)
