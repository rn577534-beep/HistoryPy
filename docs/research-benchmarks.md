# Real historical retrieval benchmarks

## HistoriQA-ThirdRepublic

HistoryPy's first real-corpus relevance benchmark uses
[HistoriQA-ThirdRepublic](https://github.com/atomegoyan/historiqa-thirdrepublic),
a French-language 1887 corpus containing 3,386 document chunks and 1,782
historical questions. The corpus combines parliamentary debates with two
newspapers that represent different political perspectives. The dataset README
describes historian involvement in question validation and cross-source
question types.

- Dataset license: Creative Commons Attribution 4.0 International (CC-BY 4.0).
- Pinned upstream revision: 08bf3cc5f25ae5cd065ce8330f4275147081ab66.
- Corpus file:
  https://github.com/atomegoyan/historiqa-thirdrepublic/blob/08bf3cc5f25ae5cd065ce8330f4275147081ab66/dataset/corpus_dataset.jsonl
- Question file:
  https://github.com/atomegoyan/historiqa-thirdrepublic/blob/08bf3cc5f25ae5cd065ce8330f4275147081ab66/dataset/question_dataset.jsonl
- Project paper and dataset description:
  https://hal.science/hal-05438255

### Reproduce

Download the two upstream JSONL files from the pinned revision, then run:

~~~bash
python benchmarks/benchmark_historian_relevance.py \
  --corpus corpus_dataset.jsonl \
  --questions question_dataset.jsonl \
  --top-k 10 \
  --output historical-relevance-report.json
~~~

The GitHub Actions workflow at .github/workflows/historical-relevance.yml
performs this download and stores the JSON report as an artifact.

### Metrics and limits

The benchmark reports Recall@10, MRR@10, success@10, zero-hit counts, and
results by question type. The report compares two lexical methods: (1) the existing trigram candidate
index with all-query-terms substring matching, and (2) BM25 with Unicode
accent-folding, OR term matching, and document-length normalization. BM25 is
still lexical retrieval; neither method is a dense/semantic retriever.

This dataset is narrow: French-language material from one year and one
national context. Gold document IDs are benchmark relevance labels, not proof
that all unlabelled documents are irrelevant. The benchmark measures retrieval
against the dataset's annotations; it does not validate historical truth,
global coverage, source independence, or the reliability of the newspapers.
The upstream README notes historian involvement but also identifies limits
including a single historian reviewer and limited temporal/geographic scope.

### Citation and attribution

Please cite the dataset creators and preserve CC-BY 4.0 attribution when
reusing the dataset:

Pellet, Aurélien; Puren, Marie; Perez, Julien. HistoriQA-ThirdRepublic:
Multi-Hop Question Answering Corpus for Historical Research, Parliamentary
Debates from the Third Republic. HAL, 2026.
https://hal.science/hal-05438255

The benchmark downloads the original files at runtime; HistoryPy does not
commit a copy of the dataset.


## BM25 lexical retrieval

The public API also exposes `BM25SearchIndex` and `BM25SearchHit`. BM25 ranks
documents using term frequency, inverse document frequency, and document
length normalization. Query terms are accent-folded (for example, French
`é` and `e` compare equally), and a document can match some rather than all
query terms. Scores are ranking signals, not confidence or truth probabilities.
The real-corpus benchmark compares BM25 with the existing all-terms trigram
retriever so relevance changes can be measured rather than assumed.


## Synthetic scale benchmark results

On the GitHub Actions Python 3.12.16 Linux runner, the compact trigram index
completed both requested synthetic scales with exact ordered result parity:

| Records | Index build | Additional Python memory during build | Indexed query | Linear query | Observed speedup |
|---:|---:|---:|---:|---:|---:|
| 100,000 | 1.459 s | 44.325 MiB | 4.397 ms | 91.849 ms | 20.89× |
| 1,000,000 | 14.581 s | 440.223 MiB | 57.124 ms | 899.139 ms | 15.74× |

These are single-run observations from one selective synthetic query, not
production guarantees. The 1M build's measured Python allocation peak was
about 80% lower than the earlier set-based postings implementation
(2,178.113 MiB on the same benchmark setup). The compact index uses packed
32-bit posting lists; its current limit is 2^32 records. Query-time temporary
allocations and pre-existing dataset memory are separate from index-build
memory, and tracemalloc does not report total process RSS.


### HistoriQA-ThirdRepublic measured results

The pinned 3,386-document / 1,782-question run completed on GitHub Actions
(Python 3.12). At k=10:

| Method | Recall@10 | MRR@10 | Mean query time |
|---|---:|---:|---:|
| Trigram, all query terms required | 0.22% | 0.15% | 31.68 ms |
| BM25, OR term matching | 55.64% | 48.89% | 20.21 ms |

BM25 Recall@10 by question type:

| Question type | Questions | Recall@10 | MRR@10 |
|---|---:|---:|---:|
| Single-hop | 897 | 82.39% | 67.17% |
| Multi-hop generic | 541 | 28.65% | 30.12% |
| Multi-hop comparative | 192 | 28.39% | 28.60% |
| Multi-hop bridge-entity | 152 | 28.29% | 33.42% |

This is a large improvement over the all-terms baseline on this particular
French 1887 corpus. It also shows a remaining gap: multi-hop and cross-source
questions are substantially harder than single-hop questions. These metrics
are retrieval relevance against the dataset's gold document IDs, not proof of
historical correctness, source independence, or general performance on other
periods, languages, and archives. BM25 remains a lexical method; semantic
retrieval and historian-reviewed cross-source evaluation are still future work.


## First measured baseline (2026-11-24)

Pinned-corpus CI run:
https://github.com/rn577534-beep/HistoryPy/actions/runs/45460098472

| Method / question group | Questions | Recall@10 | MRR@10 | Success@10 |
|---|---:|---:|---:|---:|
| BM25 — overall | 1,782 | 0.5564 | 0.4889 | — |
| BM25 — single-hop (SH) | 897 | 0.8239 | 0.6717 | 0.8239 |
| BM25 — multi-hop generic | 541 | 0.2865 | 0.3012 | 0.5379 |
| BM25 — comparative multi-hop | 192 | 0.2839 | 0.2860 | 0.4583 |
| BM25 — bridge-entity multi-hop | 152 | 0.2829 | 0.3342 | 0.5658 |
| Trigram all-terms — overall | 1,782 | 0.0022 | 0.0015 | — |

All 1,782 questions were evaluated; none were skipped. BM25's mean query
evaluation time was 32.531 ms on the CI runner. Index build measurements were
2,892.785 ms for the trigram index and 3,011.505 ms for BM25. These are
single-run machine-specific timings, not latency guarantees.

The results show a large improvement over strict substring matching. They
also show the remaining weakness: multi-hop questions are materially harder
than single-hop questions. Next retrieval experiments should compare query
decomposition, entity-aware retrieval, and a hybrid semantic/BM25 reranker
against the same pinned question set. Do not tune against the test questions
and then present the same scores as an independent evaluation; preserve a
held-out split for model selection.


## Synthetic scale test results (2026-11-24)

CI run: https://github.com/rn577534-beep/HistoryPy/actions/runs/45460840022

Both 100,000 and 1,000,000 synthetic person records completed with exact
result parity between indexed and linear search for the selective query
`scaleprobe raremarker`.

| Records | Index build | Build peak additional Python memory | Linear search | Indexed search | Speedup |
|---:|---:|---:|---:|---:|---:|
| 100,000 | 1.304 s | 44.325 MiB | 77.110 ms | 3.747 ms | 20.581x |
| 1,000,000 | 12.849 s | 440.223 MiB | 742.973 ms | 66.297 ms | 11.207x |

At one million records the indexed query used 64.795 MiB of additional
traced Python allocations; the linear query used 0.193 MiB. This reflects
candidate-set and result materialization costs for this particular query and
does not imply the index is always more memory-efficient per query. The
index's build memory is a substantial cost and should be planned for.

These figures are synthetic selective-query stress tests on a GitHub Actions
Python 3.12 runner. `tracemalloc` excludes pre-existing dataset memory,
native allocations, and total process RSS. Broad queries, different text
distributions, different hardware, and real historical corpora can behave
very differently. The million-record run demonstrates that this fixture and
index can complete at that size; it is not a guarantee for every dataset.


## Persistent SQLite index benchmark

Run the optional persistent-index stress test with:

~~~bash
python benchmarks/benchmark_sqlite_store.py --records 100000
python benchmarks/benchmark_sqlite_store.py --records 1000000
~~~

The manual GitHub Actions workflow `.github/workflows/sqlite-index-benchmark.yml`
provides the same two sizes. It measures save time, traced Python allocation
peak during save, database file size, process peak RSS, FTS5 availability,
query latency, and a search repeated after reopening the database. These are
synthetic event records, not real historical data. Process peak RSS includes
the in-memory synthetic dataset and should be interpreted separately from
tracemalloc. SQLite's FTS5 phrase semantics are not BM25 ranking and are not
comparable to a semantic embedding score without a relevance evaluation.
