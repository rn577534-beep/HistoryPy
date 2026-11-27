# Releasing HistoryPy

The first production release, `historypy==1.0.0`, is published on PyPI:
https://pypi.org/project/historypy/

## Release checklist

1. Review open issues and all changes merged into `main`.
2. Confirm `pyproject.toml` and `src/historypy/__init__.py` contain the same version.
3. Update `CHANGELOG.md` with an accurate release section. Do not mark a release as published before PyPI verification.
4. Run tests and lint on Python 3.10–3.13 using `.github/workflows/tests.yml`.
5. Build and validate both distributions:

   ```bash
   python -m pip install --upgrade build twine
   python -m build
   python -m twine check --strict dist/*
   ```

6. Inspect the wheel and source archive for package modules, README metadata, and the MIT license. Install the wheel in a clean environment and verify the imported version.
7. Before creating a production GitHub Release, verify the PyPI Trusted Publisher configuration below.
8. Create a tag matching the version (for example, `v1.0.2`) and publish the GitHub Release only after all checks pass.
9. Monitor `.github/workflows/publish.yml`. Both build and publish jobs must succeed.
10. Verify the exact version and distribution files on PyPI, then test a clean installation:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install --no-cache-dir historypy==VERSION
   python -c "import historypy; print(historypy.__version__)"
   ```

## Trusted Publishing configuration

The PyPI project must have a Trusted Publisher configured with:

- Owner: `rn577534-beep`
- Repository: `HistoryPy`
- Workflow filename: `publish.yml`
- GitHub environment: `pypi`

The workflow uses OpenID Connect. Do not store a long-lived PyPI API token in repository secrets. If the publisher is not configured, stop before publishing a GitHub Release and complete the setup in the PyPI project settings.

A separate rehearsal is possible with `.github/workflows/publish-testpypi.yml`, but TestPyPI requires its own project and publisher configuration.

## Version immutability and project boundaries

Never reuse a version number for changed package contents. If a published release has a serious issue, publish a new version and consider yanking the affected release.

A successful package upload only makes the Python library installable. It does not certify historical claims, source reliability, or research conclusions.
