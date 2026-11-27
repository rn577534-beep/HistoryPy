# Mathematical models in HistoryPy

HistoryPy combines several models because historical research contains different
kinds of uncertainty. Search relevance, name similarity, chronology, graph
structure, and source dependence are separate questions.

## Model inventory and status

| Model | Main use | Status in HistoryPy |
|---|---|---|
| BM25 | Lexical document retrieval | Implemented |
| Character trigram index | Typo-tolerant lexical retrieval | Implemented |
| Cosine similarity | Embedding-based semantic retrieval | Implemented; caller supplies model |
| Reciprocal Rank Fusion | Combine ranked retrieval lists | Implemented |
| Jaro-Winkler | Similarity of names with common prefixes | Implemented in name ensemble |
| Levenshtein | Insert/delete/substitute spelling distance | Implemented in name ensemble |
| Damerau-Levenshtein | Also handles character transpositions | Implemented in name ensemble |
| Sørensen-Dice | Character n-gram overlap | Implemented as trigram Dice |
| Jaccard | Token-set overlap | Implemented in name ensemble |
| Interval overlap / three-valued logic | Compare uncertain historical dates | Implemented |
| Typed graph traversal | Explore recorded relationships | Implemented |
| Source-dependency graph | Report known dependence and unknown dependence | Implemented |
| Dijkstra / A* | Cost-aware relationship paths | Proposed; not yet implemented |
| PageRank / HITS | Structural graph centrality | Proposed; not evidence of truth |
| Allen interval algebra | Rich temporal relations | Proposed |
| Shannon entropy | Describe distributional uncertainty | Proposed |
| Bayesian networks | Model explicit conditional assumptions | Proposed; requires defensible priors |
| Dempster-Shafer | Represent belief and ignorance under explicit evidence rules | Proposed; requires careful conflict policy |
| Monte Carlo | Sensitivity analysis for uncertain dates/parameters | Proposed |
| TF-IDF | Alternative lexical vector-space retrieval | Proposed; compare against BM25 |
| Logistic regression | Learn relevance ranking/classification | Proposed; requires labeled training data |
| PCA / SVD | Reduce high-dimensional feature spaces | Proposed |
| MinHash / LSH | Approximate near-duplicate candidate search at scale | Proposed |

## Implemented name-similarity ensemble

The public `compare_names(left, right)` function returns five component scores
and one deterministic combined score:

- Jaro-Winkler: 0.65
- normalized Levenshtein similarity: 0.15
- normalized unrestricted Damerau-Levenshtein similarity: 0.10
- character-trigram Sørensen-Dice: 0.07
- token Jaccard: 0.03

The weights are transparent starting heuristics, not fitted parameters or
probabilities. The component scores are exposed so researchers can inspect why
two strings received a particular score.

Both `suggest_entity_matches` and
`EntityAwareSearchIndex.suggest` now use this ensemble. Very short names remain
excluded from duplicate-candidate generation because they are collision-prone.

Example:

```python
from historypy import compare_names

scores = compare_names("Alexandre", "Alexander")
print(scores.combined)
print(scores.jaro_winkler, scores.levenshtein)
print(scores.damerau_levenshtein, scores.trigram_dice, scores.token_jaccard)
```

A high score creates a review candidate only. It never merges entities,
establishes transliteration, or proves that two names refer to one person.
Historical aliases and transliterations must remain source-backed and
researcher-reviewed.

## Evaluation policy

Do not select weights or thresholds from the test set. Build a reviewed,
versioned multilingual gold set with positive pairs, hard negative pairs,
homonyms, transliterations, historical aliases, and ambiguous cases. Report
precision, recall, F1, false-merge candidate rate, and results separately by
language/script and entity type. A fuzzy candidate must never automatically
merge two records.

## Next implementation stages

1. Evaluate the name ensemble on reviewed Bengali, English, and French pairs.
2. Add interval-algebra relations while preserving unknown calendar semantics.
3. Add explainable weighted relationship paths without treating path length as
   historical plausibility.
4. Add information-theoretic summaries of evidence coverage and conflict.
5. Only add Bayesian or learned models after priors or labeled data can be
   documented and independently evaluated.
