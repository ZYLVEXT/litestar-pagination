---
name: python-packaging
description: Packaging guide for litestar-pagination: hatchling, uv, commitizen, optional SQLAlchemy/Advanced Alchemy extras, dependency groups, builds, and releases. Use for pyproject, dependencies, lockfiles, CI packaging, or publishing work.
---

# Python Packaging — litestar-pagination

## Evidence first

- Read `AGENTS.md`, `PRD.md`, `TECHSTACK.md`, and `pyproject.toml`.
- Use Context7 or official project docs when tool/dependency behavior matters.
- Treat `pyproject.toml` and `uv.lock` as authoritative.

## Project shape

- Distribution: `litestar-pagination`; flat import package: `litestar_pagination`.
- Build backend: hatchling.
- Supported Python: `>=3.12.0,<3.15.0`.
- Base dependency: Litestar.
- Public extras: `sqlalchemy`, `advanced-alchemy`, and `all`.
- Dev/docs tools belong in PEP 735 dependency groups, not public extras.
- `[tool.uv] default-groups = []` keeps installs minimal.

## Dependency rules

- Use uv, not ad-hoc pip or manually managed virtualenvs.
- Use compatible ranges `>=X,<NEXT_MAJOR`; exact resolutions belong in `uv.lock`.
- SQLAlchemy and sqlakeyset remain optional and must not leak into root imports.
- The Advanced Alchemy extra includes the SQLAlchemy integration.
- Update extras, lockfile, docs, deptry configuration, and CI together when dependencies change.

```bash
uv sync
uv sync --frozen --all-extras --group dev
uv lock
```

## Version and release

- Commitizen uses conventional commits and PEP 621 versioning.
- Version is mirrored in `pyproject.toml` and `litestar_pagination/__init__.py`.
- Tags are bare semantic versions without a `v` prefix.
- Build with `uv build`; publish only when explicitly authorized.
- Verify wheel contents include `py.typed` and optional imports remain absent from base installation.

## Verification

Run the full block in `AGENTS.md`, plus `uv build` for build/release changes. `uv run pip-audit` is best effort when network is available.

See `resources/implementation-playbook.md` for common commands.
