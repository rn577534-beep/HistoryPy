# Changelog

All notable changes to HistoryPy are documented here.

This project follows a lightweight Keep a Changelog structure. Versions follow
PEP 440; pre-release versions are identified explicitly.

## [Unreleased]

### Added
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
