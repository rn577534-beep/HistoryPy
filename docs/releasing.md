# Releasing HistoryPy

HistoryPy 1.0.0 is published on PyPI:

- Project: https://pypi.org/project/historypy/
- Installation: `python -m pip install --upgrade historypy`
- GitHub release: https://github.com/rn577534-beep/HistoryPy/releases/tag/v1.0.0

## Before preparing another release

1. Review open issues and the changes merged into the default branch.
2. Run the full test suite and lint checks on Python 3.10, 3.11, 3.12,
   and 3.13 using `.github/workflows/tests.yml`.
3. Review the public API and README examples. Confirm that every documented
   import and example matches the code.
4. Update the version in both `pyproject.toml` and
   `src/historypy/__init__.py`; keep them identical.
5. Add a dated release section to `CHANGELOG.md` and update the README only
   when user-facing behavior or installation instructions change.
6. Build the wheel and source distribution and validate them:

   ```bash
   python -m pip install --upgrade build twine
   python -m build
   python -m twine check --strict dist/*
   ```

7. Inspect both distribution archives. Confirm that the package modules,
   README metadata, and MIT license are included. Install the built wheel in
   a clean environment and run an import/version smoke test.

## Publishing

1. Commit the release preparation to the default branch.
2. Create a Git tag matching the package version, for example `v1.0.1`.
3. Create and publish a GitHub Release for that tag.
4. The `.github/workflows/publish.yml` workflow runs the test suite and lint,
   builds and validates both distribution formats, then publishes them to
   PyPI using Trusted Publishing.
5. Check the GitHub Actions run. Both the build and publish jobs must succeed.
6. Verify the new version and its release files on PyPI, then install it in a
   clean environment:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install --upgrade historypy
   python -c "import historypy; print(historypy.__version__)"
   ```

PyPI release files are immutable in practice. Never reuse a version number
for changed contents. If a published version has a serious issue, publish a
new version and consider yanking the affected release rather than trying to
replace its files.

## Trusted Publishing configuration

The production GitHub Actions workflow expects:

- PyPI project: `historypy`
- Owner: `rn577534-beep`
- Repository: `HistoryPy`
- Workflow filename: `publish.yml`
- GitHub environment: `pypi`

The workflow uses OpenID Connect Trusted Publishing. Do not add a long-lived
PyPI API token to repository secrets for this workflow.

A separate TestPyPI rehearsal can be run with
`.github/workflows/publish-testpypi.yml`. TestPyPI has a separate project
namespace and publisher configuration; it is not the production PyPI project.

## Important project boundaries

A successful package upload only makes the Python library installable. It does
not certify historical claims, source reliability, or research conclusions.
