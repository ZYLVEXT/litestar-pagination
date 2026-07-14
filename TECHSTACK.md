# Technology Stack

## Runtime

- Python `>=3.12.0,<3.15.0`
- Litestar `>=2.24.0,<3.0`
- Standard-library dataclasses for public models

## Optional integrations

- SQLAlchemy `>=2.0,<3.0`
- sqlakeyset `>=2.0.1775222100,<3.0`
- Advanced Alchemy `>=1.11.0,<2.0`

SQLite and PostgreSQL are the supported database backends for the MVP. Both sync and async SQLAlchemy sessions are required.

## Toolchain

- uv for dependency resolution and locked environments
- hatchling for wheel and sdist builds
- Ruff for linting and formatting
- ty for static type checking
- pytest, pytest-asyncio, pytest-xdist, and pytest-cov for tests
- deptry and pip-audit for dependency checks
- prek for local hooks
- Commitizen for versioning
- Zensical and mkdocstrings for documentation
- GitHub Actions, CodeQL, Dependabot, and trusted PyPI publishing for CI and release

`pyproject.toml` and `uv.lock` are authoritative for exact dependency and tool versions.
