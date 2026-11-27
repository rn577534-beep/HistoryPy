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
| Dijkstra-style cost-ordered search | Caller-weighted relationship paths | Implemented; positive explicit costs, source gaps surfaced separately |
| PageRank / HITS | Structural graph centrality | Proposed; not evidence of truth |
| Allen interval algebra | 13 directed relations between bounded historical intervals | Implemented; returns unknown for incompatible or incomplete dates |
| Shannon entropy | Describe category diversity in recorded evidence | Implemented; descriptive only, not truth or credibility |
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

## Next research and implementation stages

1. Build a reviewed Bengali, English, and French name-pair gold set; report
   precision, recall, F1, and false-merge candidate rates by language/script.
2. Add optional interactive renderers for graph, map, and timeline exports,
   while keeping the core data exports dependency-free.
3. Evaluate graph-centrality measures (PageRank and HITS) as structural
   descriptors only, never as source credibility or truth.
4. Add Monte Carlo sensitivity analysis for explicitly bounded uncertain dates
   and researcher-supplied assumptions.
5. Consider Bayesian models only after priors and conditional assumptions can
   be justified, documented, and tested independently.
6. Compare every proposed model against simple baselines on held-out datasets;
   do not report performance gains without measured results.


## Visualization and export layer

The dependency-free visualization module exports structured data for external
renderers instead of forcing a plotting dependency into the core package:

- `dataset_graph_data(dataset)`: typed entity, relationship, claim, source,
  evidence, and source-derivation graph data.
- `to_graphviz_dot(dataset)`: Graphviz DOT for network diagrams.
- `to_geojson(dataset)`: GeoJSON point features for places with recorded
  coordinates, including source IDs and associated event IDs.
- `timeline_visualization_data(dataset)`: interval-aware data for Gantt and
  timeline renderers, including calendar, precision, circa, and uncertainty.
- `export_visualization_json(data)`: stable JSON serialization.

Example:

```python
from historypy import (
    dataset_graph_data, to_geojson, to_graphviz_dot,
    timeline_visualization_data,
)

graph = dataset_graph_data(dataset)
geojson = to_geojson(dataset)
dot_text = to_graphviz_dot(dataset)
timeline = timeline_visualization_data(dataset)
```

GeoJSON coordinates are only exported when supplied by the researcher. They
are not inferred from place names. A map point represents a recorded location,
not necessarily a precise historical boundary. Timeline exports preserve
calendar and date uncertainty; renderers must not silently normalize calendars.
