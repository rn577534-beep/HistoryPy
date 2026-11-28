# Multilingual retrieval and evidence benchmark

HistoryPy compares retrieval systems on the **same researcher-judged query set**.
The benchmark never invents relevance labels. A case has this shape:

```json
[
  {
    "id": "bn-001",
    "query": "পলাশীর যুদ্ধের কারণ",
    "relevant": ["event:plassey", "claim:plassey-causes"]
  },
  {
    "id": "en-001",
    "query": "causes of the Battle of Plassey",
    "relevant": ["event:plassey", "claim:plassey-causes"]
  }
]
```

The identifiers above are illustrative only. Replace them with IDs from your own dataset and have qualified reviewers judge relevance before using the file as a benchmark. Keep a held-out test set separate from query/model tuning.

## Lexical benchmark

```bash
historypy evaluate research.json reviewed-cases.json \
  --top-k 10 --bootstrap-samples 5000 --seed 2026 \
  --output lexical-results.json
```

This compares Trigram, BM25, and reciprocal-rank-fusion (RRF) hybrid. All systems receive the same queries and judgments.

## Four-system benchmark

Install the optional semantic dependency and choose a multilingual model explicitly:

```bash
pip install "historypy[semantic]"
historypy evaluate research.json reviewed-cases.json \
  --top-k 10 --bootstrap-samples 5000 --seed 2026 \
  --semantic-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 \
  --output four-system-results.json
```

This compares Trigram, BM25, Semantic, and Hybrid RRF (Trigram + BM25 + Semantic). The semantic index is built from the same dataset snapshot. Model download, hardware, device, batch size, and cache state affect runtime; record them with any published benchmark.

## Reported statistics

- Precision@k, Recall@k, MRR@k, nDCG@k, and Success@k.
- Query-level bootstrap 95% intervals for each metric.
- Paired bootstrap intervals for candidate-minus-baseline metric differences.
- Mean, median, and p95 query latency in milliseconds.

Latency measures query execution after index construction, not model download or index-building time. Run repeated trials on documented hardware for performance claims. Confidence intervals reflect variation across judged queries; they do not repair incomplete judgments, sampling bias, or leakage.

## Entity names and transliteration

Canonical names, legacy aliases, and verified alias assertions are distinct. Add Bengali/English transliterations and historical forms as explicit alias assertions with a source, locator, language, license, reviewer, and review date. Only verified assertions are used as verified aliases. Ambiguous forms remain ambiguous. No automatic transliteration, silent identity merge, or fuzzy identity decision is performed.

## Evidence dossier

The dossier reports supporting, contradicting, contextualizing, and mentioning links separately. It also reports known source-dependency clusters and sources whose independence is unknown. A source with no recorded dependency is **not** automatically independent. Event date precision, approximate-date flags, and original source wording are shown when present.

Retrieval metrics evaluate ranking against supplied relevance labels. They are not measures of historical truth, source authenticity, or claim confidence.
