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
results by question type. The baseline is HistoryPy's current lexical
all-query-terms substring retrieval with trigram candidate filtering. It is
not a dense retrieval or BM25 comparison.

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
