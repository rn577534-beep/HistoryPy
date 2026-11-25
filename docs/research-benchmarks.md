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

## Total process RSS measurement (2026-11-25)

The scale benchmark now records process peak RSS in addition to the incremental
Python allocations measured by `tracemalloc`. Run:
https://github.com/rn577534-beep/HistoryPy/actions/runs/45516214661

| Records | Index build | Additional Python allocation peak | Total process peak RSS | Indexed query | Linear query | Speedup |
|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 1.113 s | 44.325 MiB | 132.832 MiB | 3.884 ms | 68.359 ms | 17.60x |
| 1,000,000 | 10.343 s | 440.223 MiB | 1,015.484 MiB | 53.795 ms | 639.322 ms | 11.88x |

Peak RSS is the total process high-water mark and includes the synthetic
dataset, Python runtime, index, and native allocations. It is not the index's
standalone memory cost. These values are specific to the GitHub Actions Linux
runner and selective synthetic query.

## Persistent normalized SQLite results (2026-11-25)

Both SQLite FTS5 scale jobs completed successfully:
https://github.com/rn577534-beep/HistoryPy/actions/runs/45516615547

| Records | Save time | Additional traced Python memory during save | SQLite file size | Total process peak RSS | Query | Query after reopen |
|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 11.78 s | 68.897 MiB | 84.637 MiB | 221.082 MiB | 1.986 ms | 1.518 ms |
| 1,000,000 | 127.84 s | 687.305 MiB | 845.113 MiB | 1,877.465 MiB | 6.579 ms | 5.995 ms |

FTS5 was available in both runs, and the script verified identical query
record IDs after reopening the database. Peak process RSS includes the
synthetic in-memory dataset, Python runtime, SQLite caches, and native
allocations; it is not just the persistent index. The benchmark uses a
selective phrase query and synthetic records. It does not establish broad-query
latency, write-concurrency behavior, crash recovery under power loss, or
performance on real historical source material.

## Real-corpus lexical retrieval comparison (HistoriQA-ThirdRepublic)

Pinned benchmark run:
https://github.com/rn577534-beep/HistoryPy/actions/runs/45516315463

All 1,782 questions over the 3,386-document French 1887 corpus were evaluated
at Recall@10 and MRR@10:

| Method | Recall@10 | MRR@10 | Mean query time |
|---|---:|---:|---:|
| Trigram all-terms | 0.22% | 0.0015 | 32.107 ms |
| BM25 | 55.64% | 0.4889 | 24.316 ms |
| Trigram + BM25 RRF | 55.42% | 0.4800 | 62.626 ms |

On this corpus the simple lexical RRF did not improve over BM25 and was slower.
This is an important negative result: combining ranked lists does not guarantee
better relevance. The current benchmark workflow additionally evaluates
French-aware query decomposition; its results are reported separately when
that run completes. No real semantic embedding model has yet been selected,
so semantic metrics are intentionally absent.


## Held-out question evaluation

The hybrid HistoriQA benchmark now creates a deterministic, question-type-
stratified 80/20 holdout by default (seed 2026). It reports training-side and
held-out question counts separately and measures trigram, BM25, RRF, and
decomposed RRF on the same held-out questions. Search indexes are built from
the searchable corpus, not question labels; no model is trained on the
question split. The split is a guard against selecting a method using every
question and then presenting the same full-set score as independent evidence.
The current split is deterministic and suitable for reproducible model
selection; a future publication-quality evaluation should additionally freeze
a final untouched test split before tuning.

## English multi-hop benchmark

HistoryPy includes an adapter for the HotpotQA distractor development set.
The official CMU download host was unavailable in CI, so the workflow uses a
pinned Hugging Face mirror and verifies its SHA-256 before parsing. HotpotQA
contains English Wikipedia multi-hop questions with sentence-level supporting
facts; HistoryPy evaluates retrieval of supporting document titles from the
union of context paragraphs supplied in the benchmark. It is general Wikipedia
multi-hop QA, not a historical-only corpus, and its metrics must not be pooled
with HistoriQA's French historical-domain metrics.

The workflow is .github/workflows/english-multihop.yml; the report is uploaded
as a workflow artifact. Dataset license is CC BY-SA 4.0. Cite Yang et al. (2018),
HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering,
EMNLP 2018, and preserve attribution/share-alike terms.

## Persistent SQLite journal modes

NormalizedSQLiteStore supports the default DELETE journal mode and an
opt-in WAL mode. WAL mode exposes explicit checkpoint_wal() and
integrity_check() diagnostics. The SQLite scale workflow now runs both modes
at 100k and 1m synthetic records, recording broad/selective query latency,
reopen parity, file size, process RSS, checkpoint results, and integrity
status. Concurrent writer tests use separate store instances and transactions
to confirm SQLite serializes writes without losing committed datasets. A
rollback test simulates an interrupted replacement transaction and verifies
that the previously committed dataset remains readable.

These tests do not replace power-loss testing on physical hardware, filesystem
fault injection, or long-duration concurrent workload testing. WAL should be
selected based on deployment workload and checkpoint/backup policy, not assumed
to be universally faster.


## DELETE versus WAL scale results

Pinned GitHub Actions run:
https://github.com/rn577534-beep/HistoryPy/actions/runs/45518628486

| Records | Journal | Save time | Selective query | Broad query (top 1,000) | Reopen query | SQLite file | Peak process RSS |
|---:|---|---:|---:|---:|---:|---:|---:|
| 100,000 | DELETE | 9.065 s | 1.496 ms | 123.862 ms | 1.250 ms | 84.637 MiB | 221.223 MiB |
| 100,000 | WAL | 13.600 s | 2.374 ms | 169.867 ms | 1.978 ms | 84.637 MiB | 221.324 MiB |
| 1,000,000 | DELETE | 87.035 s | 5.694 ms | 1,145.411 ms | 4.962 ms | 845.113 MiB | 1,877.562 MiB |
| 1,000,000 | WAL | 175.482 s | 7.513 ms | 2,052.605 ms | 7.227 ms | 845.113 MiB | 1,879.277 MiB |

All four runs reported FTS5 available and SQLite integrity_check = ok.
Both WAL runs completed a PASSIVE checkpoint with no busy pages remaining.
The broad query intentionally returns at most 1,000 rows, so its timing is a
bounded top-k query, not a full corpus export. WAL was slower than DELETE for
this synthetic single-writer workload; WAL is retained as an opt-in mode for
deployment concurrency requirements, not as a universal performance setting.
Peak RSS includes the Python process, source dataset, SQLite cache, and native
allocations; it is not an isolated measurement of index-only RAM.
