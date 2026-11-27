# Changelog

## [1.0.1] - 2026-11-27

### Added
- Retrieval evaluation with Precision@k, Recall@k, MRR@k, nDCG@k, Success@k, bootstrap confidence intervals, paired comparisons, and latency reporting.
- Bounded, thread-safe LRU caching and ordered batch hybrid retrieval.
- Reproducible cache/batch and large-scale selective-search benchmarks, including correctness parity checks.

### Performance observations
- On the GitHub Actions synthetic 100,000-record fixture, indexed selective search took 3.066 ms versus 53.309 ms for linear search (17.39x observed speedup).
- On the synthetic 1,000,000-record fixture, indexed search took 66.977 ms versus 861.430 ms for linear search (12.86x observed speedup), with exact result parity. Peak process RSS was 1,022.281 MiB; this is a high-memory stress-test result, not a claim of low-memory production readiness.
- Cache and batch benchmark results are workload-dependent. Parallel execution was slower than sequential execution in the tested small synthetic batch, so parallelism remains opt-in.

### Notes
- Benchmarks use synthetic data and do not measure historical truth, evidence quality, or real-world historical retrieval relevance.


All notable changes to HistoryPy are documented here.

This project follows a lightweight Keep a Changelog structure. Versions follow
PEP 440; pre-release versions are identified explicitly.

## [Unreleased]

### Added
- Retrieval evaluation engine comparing trigram, BM25, and hybrid RRF with Precision@k, Recall@k, MRR@k, nDCG@k, Success@k, latency percentiles, bootstrap intervals, and paired comparisons.
- CLI command to run reproducible retrieval evaluations from researcher-reviewed relevance judgments.
- Tests and documentation for statistical evaluation and identical-query comparisons.
- Dependency-free `historypy` CLI for dataset validation, citation audits, and GeoJSON, Graphviz, timeline, and HTML exports.
- Explicit-prior Bayesian likelihood-ratio updates and Dempster-Shafer mass combination with conflict reporting; neither infers source credibility or historical truth.
- Tests for CLI workflows and probabilistic evidence calculations.\n- A multilingual entity-resolution gold-set benchmark harness reporting per-language precision, recall, F1, and false-positive rate without inventing labels.\n- Conservative point-distance uncertainty bounds from researcher-supplied coordinate error radii.\n- Optional discrete triangular temporal sensitivity sampling with reproducible seeds and explicit mode quantiles.


### Added
- Self-contained interactive HTML research report with network, timeline, and coordinate views; researcher text is HTML-escaped.
- Reproducible Monte Carlo sensitivity analysis for two bounded event dates,
  including explicit uniform sampling assumptions and Wilson intervals.
- PageRank and HITS structural centrality for recorded directed relationships,
  retaining isolated entities and reporting convergence metadata.
- Parameter, reproducibility, calendar-compatibility, and graph-structure tests.
- Allen interval algebra for thirteen temporal relations between comparable,
  fully bounded historical dates.
- Shannon entropy summaries for recorded evidence-relation and source-type
  distributions; these are descriptive, not truth or credibility scores.
- Caller-cost-weighted relationship path search with explicit provenance gaps.
- Dependency-free graph, Graphviz DOT, GeoJSON, and uncertainty-aware timeline
  visualization exports.
- Tests for temporal relations, entropy, weighted paths, and visual exports.

### Fixed
- Correct import ordering in the name-similarity implementation.


### Added
- Explainable multi-metric name similarity using Jaro-Winkler, Levenshtein,
  Damerau-Levenshtein, character-trigram Dice, and token Jaccard scores.
- Mathematical model inventory and evaluation policy in `docs/mathematical-models.md`.

### Changed
- Entity duplicate suggestions and fuzzy alias retrieval use the transparent
  name-similarity ensemble; candidates remain review-only.

### Notes
- Add new changes here. Benchmark results must be generated from the
  documented licensed datasets; no unmeasured performance gains are claimed.

## [1.0.0] - 2026-11-27

### Added
- Evidence-centered historical research workflows with source provenance and
  conservative source-independence auditing.
- Researcher-reviewed multilingual entity aliases and bounded multi-hop
  relationship exploration.
- Paired French/English retrieval evaluation harnesses.
- MIT licensing and automated wheel/source-distribution validation.
- PyPI and TestPyPI Trusted Publishing workflows.

### Release
- Published `historypy==1.0.0` to the Python Package Index (PyPI).
- GitHub Actions built and validated the wheel and source distribution,
  ran the test suite and lint checks, and published with Trusted Publishing.
