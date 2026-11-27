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
| PageRank / HITS | Structural centrality on recorded directed relationships | Implemented; structural descriptors only, never credibility or truth |
| Allen interval algebra | 13 directed relations between bounded historical intervals | Implemented; returns unknown for incompatible or incomplete dates |
| Shannon entropy | Describe category diversity in recorded evidence | Implemented; descriptive only, not truth or credibility |
| Bayesian networks | Model explicit conditional assumptions | Proposed; requires defensible priors |
| Dempster-Shafer | Represent belief and ignorance under explicit evidence rules | Proposed; requires careful conflict policy |
| Monte Carlo | Reproducible sensitivity analysis for two bounded event dates | Implemented; discrete uniform independent sampling with Wilson intervals, not calibrated historical probabilities |
| TF-IDF | Alternative lexical vector-space retrieval | Proposed; compare against BM25 |
| Logistic regression | Learn relevance ranking/classification | Proposed; requires labeled training data |
| PCA / SVD | Reduce high-dimensional feature spaces | Proposed |
| MinHash / LSH | Approximate near-duplicate candidate search at scale | Proposed |

## Implemented temporal sensitivity analysis

`analyze_temporal_sensitivity(dataset, first_event_id, second_event_id)`
compares two fully bounded event dates by independently sampling each date
from its inclusive researcher-supplied bounds. It reports the estimated
probabilities that the first event is earlier, simultaneous, or later, with
95% Wilson intervals and a reproducible random seed.

The current policy uses discrete uniform sampling over explicit ISO-day bounds
or astronomical-year bounds. It requires matching calendars and matching
bound representations. It does not widen circa ranges, convert calendars,
infer event duration, model dependence between dates, or establish causation.
The output is a sensitivity analysis under an explicit assumption, not a
historical probability.

```python
from historypy import analyze_temporal_sensitivity

report = analyze_temporal_sensitivity(
    dataset, "event-a", "event-b", iterations=20_000, seed=2026
)
print(report.first_before_second_probability)
print(report.first_before_second_ci95)
print(report.simultaneous_probability)
```

## Interactive visualization report

`render_visualization_html(dataset)` creates a self-contained HTML file with
switchable relationship-network, timeline-table, and place-coordinate views.
It has no plotting dependency and escapes researcher-supplied labels before
embedding them in markup. The graph view is intentionally capped for small
networks. The place panel is a coordinate scatter, not a basemap; use GeoJSON
with a GIS tool for actual geographic context.

## Implemented graph centrality

`analyze_graph_centrality(dataset)` calculates PageRank and HITS hub/authority
scores using only explicit directed `HistoricalRelationship` records. Isolated
entities are retained. Parallel relationships count as separate edges.
Convergence metadata is included. These values describe network position only;
they do not measure historical importance, causation, influence, source
credibility, or truth.

```python
from historypy import analyze_graph_centrality

report = analyze_graph_centrality(dataset)
for item in report.scores[:10]:
    print(item.node_id, item.pagerank, item.hub_score, item.authority_score)
```

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
2. Add a true map renderer with an explicit projection, map tiles or offline
   basemap choice, coordinate uncertainty, and historical boundary provenance.
3. Extend Monte Carlo analysis to researcher-defined distributions only when
   the assumptions, dependence structure, and calibration evidence are recorded.
4. Benchmark PageRank/HITS and graph traversal on sparse networks at 10k,
   100k, and 1M nodes; report runtime, memory, and convergence.
5. Add an optional command-line interface for dataset validation, audits,
   exports, and reproducible reports.
6. Compare lexical, semantic, and hybrid retrieval on held-out multilingual
   questions using Recall@k, MRR, nDCG, latency, and memory.
7. Consider Bayesian or Dempster-Shafer models only after defensible priors,
   conflict policies, and independent evaluation data are available.
8. Compare every proposed model against simple baselines; do not report
   performance gains without measured, reproducible results.


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
