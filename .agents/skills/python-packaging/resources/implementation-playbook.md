# Packaging — Implementation Playbook

## Authoritative files

- `pyproject.toml`: metadata, dependencies, tools, build, and versioning.
- `uv.lock`: exact resolution used by CI.
- `litestar_pagination/__init__.py`: mirrored package version.
- `AGENTS.md`: verification commands.

## Common commands

```bash
uv lock
just setup
uv run ruff check --fix .
uv run ruff format .
uv run ty check
uv run deptry .
just test
uv build
```

## Extras

- Base: Litestar dataclass/DI/OpenAPI surface.
- `sqlalchemy`: SQLAlchemy and sqlakeyset adapter.
- `advanced-alchemy`: Advanced Alchemy compatibility plus SQLAlchemy adapter.
- `all`: every public integration.

Keep optional imports lazy and test a base-only installation before release.

## Release

Commitizen updates `pyproject.toml` and `litestar_pagination/__init__.py`, refreshes `uv.lock`, and creates a bare semantic-version tag. GitHub Actions builds reproducible artifacts and publishes through trusted PyPI OIDC only after the tag test workflow succeeds.
