# Changelog

All notable changes to HistoryPy are documented here. Versions follow PEP 440.

## [Unreleased]

### Added
- Live HTTP(S) source URL checks with bounded downloads and quotation-presence checks; these checks do not authenticate a source or establish context.
- Claim documentation-completeness scoring with explicit, non-probabilistic interpretation.
- Federated cross-provider claim research with duplicate and metadata-conflict reporting; provider count is not treated as independent corroboration.
- Open catalog and news discovery adapters for Open Library, Gutendex/Project Gutenberg metadata, GDELT DOC 2.0, and The Guardian Open Platform.
- Bounded catalog pagination and provider-specific API-key, rate-limit, licensing, and copyright guidance.
- Retrieval evaluation with Precision@k, Recall@k, MRR@k, nDCG@k, Success@k, bootstrap confidence intervals, paired comparisons, and latency reporting.
- Bounded, thread-safe LRU caching and ordered batch hybrid retrieval.
- Reproducible cache/batch and large-scale selective-search benchmarks with result-parity checks.
- Dependency-free CLI for dataset validation, citation audits, and GeoJSON, Graphviz, timeline, and HTML exports.
- Explicit-prior Bayesian likelihood-ratio updates and Dempster-Shafer mass combination with conflict reporting.
- Multilingual entity-resolution benchmark harness, coordinate uncertainty bounds, and reproducible temporal sensitivity sampling.
- Self-contained interactive HTML research report, Monte Carlo temporal sensitivity analysis, PageRank/HITS structural centrality, Allen interval algebra, entropy summaries, and weighted relationship-path search.
- Explainable multi-metric name similarity using Jaro-Winkler, Levenshtein, Damerau-Levenshtein, character-trigram Dice, and token Jaccard scores.
- Mathematical model inventory and evaluation policy.

### Changed
- Entity duplicate suggestions and fuzzy alias retrieval use a transparent name-similarity ensemble; candidates remain review-only.

### Notes
- Catalog integrations discover bibliographic/news metadata at runtime. They do not bundle thousands of complete books or copyrighted news articles.
- Confidence and source-verification outputs are research aids, not probabilities of historical truth or proof of source authenticity.
- Synthetic benchmark results are workload-specific and do not establish real-world historical retrieval quality.

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

## [1.0.0] - 2026-11-27

### Added
- Evidence-centered historical research workflows with source provenance and conservative source-independence auditing.
- Researcher-reviewed multilingual entity aliases and bounded multi-hop relationship exploration.
- Paired French/English retrieval evaluation harnesses.
- MIT licensing and automated wheel/source-distribution validation.
- PyPI and TestPyPI Trusted Publishing workflows.

### Release
- Published `historypy==1.0.0` to PyPI.
- GitHub Actions built and validated the wheel and source distribution, ran tests and lint, and published with Trusted Publishing.
