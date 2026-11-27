# Changelog

All notable changes to HistoryPy are documented here.

This project follows a lightweight Keep a Changelog structure. Versions follow
PEP 440; pre-release versions are identified explicitly.

## [Unreleased]

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
