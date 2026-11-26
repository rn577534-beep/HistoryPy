# Releasing HistoryPy

This project is not published on PyPI yet. Do not advertise `pip install historypy`
as working until a release has actually appeared at
https://pypi.org/project/historypy/.

## Before the first public release

1. Confirm that the `historypy` project name can be registered on PyPI. A
   missing search result is not proof that a name is available; PyPI may have
   reserved or blocked it.
2. HistoryPy's repository metadata declares the MIT License, with the complete
   terms in the root `LICENSE` file. Before distributing a release, confirm
   that every included contribution is owned by its contributor or is
   compatible with MIT, and retain all required third-party notices.
3. Review the current version and development status in `pyproject.toml`.
   The project currently describes itself as pre-alpha; release metadata must
   accurately reflect that status.
4. Create/verify the maintainer's PyPI account and enable two-factor
   authentication.
5. Configure a PyPI Trusted Publisher for this GitHub repository:
   - Owner: `rn577534-beep`
   - Repository: `HistoryPy`
   - Workflow filename: `publish.yml`
   - Environment name: `pypi`
6. Create the GitHub environment named `pypi` in repository settings. Do not
   add a long-lived PyPI API token to GitHub secrets; the workflow uses
   OpenID Connect Trusted Publishing.
7. Run the normal test workflow and review the release contents before tagging.

## Publishing

After the prerequisites are complete:

1. Update the package version in `pyproject.toml` and update the changelog.
2. Commit the release preparation to the default branch.
3. Create a matching Git tag (for example, `v0.1.0a1`) and push it.
4. Create a GitHub Release for that tag and publish the release.
5. The `.github/workflows/publish.yml` workflow builds both an sdist and a
   wheel, runs `twine check --strict`, then publishes the exact build
   artifacts through PyPI Trusted Publishing.
6. Verify the release page and install it in a clean environment:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install historypy
   python -c "import historypy; print(historypy.__version__)"
   ```

PyPI release files are immutable in practice: do not reuse a version number
for a changed build. If a release has a serious issue, publish a new version
and consider yanking the broken release rather than trying to replace its files.

## TestPyPI rehearsal (recommended)

Before the first production release, rehearse the build and installation on
TestPyPI with a separately configured TestPyPI Trusted Publisher. TestPyPI and
PyPI have separate accounts, projects, and publisher configurations. Do not
reuse production credentials for the rehearsal.

## Important project boundaries

A successful package upload only makes the Python library installable. It does
not certify historical claims, source reliability, or research conclusions.
