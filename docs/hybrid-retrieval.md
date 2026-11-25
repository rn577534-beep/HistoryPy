# Hybrid and entity-aware retrieval

## API

`decompose_research_question(question)` conservatively splits explicit
multi-part constructions (for example, a question followed by a second
`and when/what/how...` clause, or `versus` comparisons). It does not use an
LLM and does not claim that every multi-hop question can be decomposed.

`EntityAwareSearchIndex.build(dataset)` indexes researcher-supplied canonical
names and aliases for people, places, civilizations, and organizations.
`resolve(query)` returns exact normalized name/alias phrases found in the
query. Ambiguous aliases return all matches. This is entity mention resolution,
not a decision that two records refer to the same historical entity; no records
are merged.

`HybridSearchIndex(trigram, bm25, semantic=None)` fuses result lists with
reciprocal-rank fusion (RRF). The optional semantic index must use the same
caller-supplied embedder and model vector space at build and query time.
Individual component ranks are included in each result for auditability.

Example:

~~~python
from historypy import (
    BM25SearchIndex, DatasetSearchIndex, EntityAwareSearchIndex,
    HybridSearchIndex, decompose_research_question,
)

trigram = DatasetSearchIndex.build(dataset)
bm25 = BM25SearchIndex.build(dataset)
hybrid = HybridSearchIndex(trigram, bm25)
parts = decompose_research_question(
    "Who was the ruler and when did the treaty take place?"
)
hits = hybrid.search(
    "Who was the ruler and when did the treaty take place?",
    decompose=True,
    limit=20,
)
entities = EntityAwareSearchIndex.build(dataset).resolve("Iskandar in Byzantium")
~~~

The real-corpus benchmark now has an RRF comparison for trigram + BM25.
A production semantic comparison is opt-in: pass an importable
`module:callable` embedder and a stable `--semantic-model-id`. HistoryPy does
not silently select a model, send corpus text to a provider, or treat cosine
similarity as truth probability. A benchmark using a deterministic toy
embedder is not evidence of semantic quality.

## Limits and interpretation

- Query decomposition is rule-based and deliberately conservative.
- Alias resolution only finds supplied aliases; it cannot discover every
  historical spelling, transliteration, title, exonym, or name change.
- Shared or ambiguous names can return multiple entities.
- RRF combines ranks, not calibrated probabilities.
- Semantic quality depends on the selected model, language, domain, and corpus.
- Retrieval relevance is not source reliability or historical truth.

## Relevance benchmark

Use `benchmarks/benchmark_hybrid_retrieval.py` with the pinned HistoriQA
corpus and question JSONL files to compare trigram, BM25, and lexical hybrid
RRF on the same questions:

~~~bash
python benchmarks/benchmark_hybrid_retrieval.py \
  --corpus corpus_dataset.jsonl \
  --questions question_dataset.jsonl \
  --top-k 10 \
  --output hybrid-relevance.json
~~~

To add a real embedding model, provide an importable callable that accepts a
sequence of strings and returns one vector per string, plus a stable model ID:

~~~bash
python benchmarks/benchmark_hybrid_retrieval.py \
  --corpus corpus_dataset.jsonl \
  --questions question_dataset.jsonl \
  --semantic-embedder my_embeddings:embed_texts \
  --semantic-model-id provider/model-version
~~~

No semantic benchmark score is published until an actual model/provider is
chosen and the evaluation is run. Do not substitute a toy fixture embedder
for a real semantic relevance result.
