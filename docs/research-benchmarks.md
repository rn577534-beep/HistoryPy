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
