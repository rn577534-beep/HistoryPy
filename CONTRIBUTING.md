# Contributing to HistoryPy

Thank you for your interest in improving HistoryPy.

## Development setup

    git clone https://github.com/rn577534-beep/HistoryPy.git
    cd HistoryPy
    python -m venv .venv
    python -m pip install -e ".[dev]"

## Contribution principles

- Keep historical claims separate from interpretations and software-generated inferences.
- Include source provenance and licensing information for contributed datasets.
- Preserve conflicting accounts and uncertainty.
- Add tests for new behavior, including edge cases.
- Avoid silent conversion between calendar systems.
- Do not add copyrighted or restricted material without permission.
- Document limitations, assumptions, and known coverage gaps.
- Use stable identifiers and document the scope of each dataset.

## Data contributions

Every dataset contribution should include its maintainer, source catalogue, license or usage terms, retrieval date, version, transformation steps, language coverage, geographic and chronological coverage, and known biases or omissions. Do not describe a dataset as comprehensive unless its coverage has been measured and documented.

Historical interpretations should link to evidence. Conflicting evidence should be retained rather than silently resolved.

## Code quality

Run pytest and ruff check . before submitting changes. Public APIs should include docstrings and type annotations. Prefer small, composable modules and dependency-light core functionality.

## Pull requests

Describe the problem, the proposed change, compatibility implications, tests run, and any known limitations. For new data formats, document the schema and migration policy.
