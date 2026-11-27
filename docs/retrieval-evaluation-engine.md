# Retrieval evaluation engine

HistoryPy can compare trigram, BM25, and reciprocal-rank-fusion retrieval on
the same researcher-reviewed query set. It reports Precision@k, Recall@k,
MRR@k, nDCG@k, Success@k, latency summaries, per-system bootstrap confidence
intervals, and paired bootstrap differences against the first listed system.

## Input format

Create a UTF-8 JSON array. Each case needs a stable query ID, a natural-language
query, and a list of relevant record IDs in kind:id form.

~~~json
[
  {
    "id": "q001",
    "query": "Alexander Tyre siege",
    "relevant": ["event:siege-of-tyre"]
  },
  {
    "id": "q002",
    "query": "Constantinople 1453",
    "relevant": ["event:fall-constantinople", "place:constantinople"]
  }
]
~~~

Only include relevance judgments reviewed by a researcher. Empty relevant lists
are permitted for genuinely unanswerable queries, but should be used
deliberately and documented.

## Run

~~~bash
historypy evaluate research.json benchmark-cases.json \
  --top-k 10 \
  --bootstrap-samples 2000 \
  --seed 2026 \
  --output retrieval-evaluation.json
~~~

The runner builds the three indexes from the same dataset snapshot, evaluates
the same query IDs for every method, and measures query latency. Index-build
time is not included in per-query latency; measure it separately when studying
end-to-end cold-start cost. Semantic retrieval is intentionally not included
in this base command because it requires a chosen model, model revision,
hardware policy, and explicit embedding configuration.

## Metrics and statistics

- Precision@k: relevant returned records divided by k.
- Recall@k: relevant returned records divided by all judged relevant records.
- MRR@k: reciprocal rank of the first relevant result.
- nDCG@k: rank-sensitive gain supporting graded relevance labels.
- Success@k: whether at least one relevant record appears in the top k.
- Paired bootstrap: resamples query-level metric differences with a fixed seed;
  the first named method is the baseline.

The confidence intervals quantify variation across the supplied query sample.
They do not repair incomplete judgments, leakage, or biased query selection.
Use a development set for model selection and preserve an untouched final test
set for reporting. Results are retrieval-quality measurements, not historical
truth, source credibility, or causal evidence.

## Python API

~~~python
from historypy import evaluate_rankings

report = evaluate_rankings(
    relevance={
        "q1": ["event:a", "place:b"],
        "q2": {"event:c": 3, "event:d": 1},
    },
    rankings={
        "baseline": {
            "q1": ["event:a", "event:x"],
            "q2": ["event:d", "event:c"],
        },
        "candidate": {
            "q1": ["event:a", "place:b"],
            "q2": ["event:c", "event:d"],
        },
    },
    cutoff=10,
    bootstrap_samples=2000,
    seed=2026,
)
for system in report.systems:
    print(system.system, system.metrics, system.p95_latency_ms)
~~~

For custom retrievers, call evaluate_rankings with the ranked document IDs and
optional per-query latency mapping. For the built-in trigram/BM25/RRF suite,
use run_retrieval_benchmark(dataset, cases).
