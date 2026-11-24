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
- Document limitations and assumptions.

## Code quality

Run pytest and ruff check . before submitting changes. Public APIs should include docstrings and type annotations. Prefer small, composable modules and dependency-light core functionality.
