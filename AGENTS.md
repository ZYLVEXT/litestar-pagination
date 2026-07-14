# AGENTS.md - litestar-pagination

This repository is a reusable cursor/keyset pagination library for Litestar.

Read this file before changing code. Read `PRD.md` for product intent and `TECHSTACK.md` plus `pyproject.toml` for dependency and tool facts.

## Source order

1. `AGENTS.md` for repository rules.
2. `PRD.md` for goals, public contracts, non-goals, and acceptance criteria.
3. `TECHSTACK.md` and `pyproject.toml` for versions, extras, and tooling.
4. CodeGraph when `.codegraph/` exists and code structure or impact matters.
5. AgentMemory for prior reusable project decisions.
6. Context7 for current official Litestar, Advanced Alchemy, SQLAlchemy, sqlakeyset, pytest, and tool documentation.
7. Targeted file reads or `rg` for remaining details.

Do not guess framework APIs, SQLAlchemy result behavior, cursor semantics, or dependency versions.

## Product posture

- This is production library software, not an application.
- MVP scope is cursor/keyset pagination. Do not add classic or limit/offset pagination.
- Public APIs must be small, explicit, typed, and compatible with native Litestar DI, DTO, serialization, and OpenAPI behavior.
- SQLAlchemy and Advanced Alchemy are optional integrations. Keep root imports lightweight when their extras are absent.
- Advanced Alchemy owns session lifecycle. This package consumes its sync or async sessions without patching it or adding a plugin.
- Public API, query parameters, response fields, cursor behavior, extras, and supported database changes require same-change documentation.

## Architecture

- `litestar_pagination.cursor` owns storage-independent dataclass contracts and cursor encoding.
- `litestar_pagination.ext.sqlalchemy` owns SQLAlchemy validation, counting, sqlakeyset interaction, and sync/async execution.
- Root exports are the stable lightweight Litestar surface.
- SQLAlchemy integration is imported from `litestar_pagination.ext.sqlalchemy`, not eagerly re-exported from root.
- Additional storage integrations belong under `litestar_pagination.ext` only when a real adapter is requested.
- Do not add an adapter registry, plugin framework, flow engine, repository/service layer, or abstract hierarchy for hypothetical integrations.

## Python rules

- Python 3.12+ only; use modern syntax and built-in generics.
- Use dataclasses for public parameter and page contracts. Do not add Pydantic.
- Fully annotate public functions and preserve precise sync/async return types.
- Prefer `collections.abc` interfaces and narrow helpers.
- Catch the narrowest exception and preserve database exceptions.
- Invalid client cursors map to Litestar HTTP 400; developer query mistakes do not.
- Never assemble SQL from cursor or user-controlled strings. Use SQLAlchemy expressions and sqlakeyset bookmarks.
- Every `# pragma: no cover` in the package must include a reason.

## SQLAlchemy rules

- SQLAlchemy 2 `Select` only in MVP.
- Accept only one mapped ORM entity as the selected result shape.
- Require explicit deterministic `ORDER BY`; never infer or append a primary key.
- Document and test a unique tie-breaker.
- Preserve ascending, descending, compound, forward, and backward keyset semantics.
- Total counting is separate, optional, and overridable with `count_query`.
- SQLite and PostgreSQL behavior must both remain tested.

## Testing rules

- Tests are behavior-first and concise; avoid tautological assertions and excessive mocking.
- pytest-asyncio uses auto mode; do not add `@pytest.mark.asyncio` by habit.
- Use `unit`, `integration`, and `e2e` markers.
- Cover sync and async APIs symmetrically where both exist.
- Database integration tests must exercise real SQLite/PostgreSQL semantics.
- Test Litestar DI, validation, OpenAPI, serialization, and `SQLAlchemyDTO` integration through public APIs.
- Cursor tests must include malformed input, forward/backward traversal, duplicate leading sort values, and no-total behavior.

## Documentation rules

Update relevant docs with changes to public imports, parameters, response fields, cursor encoding, ordering requirements, totals, optional extras, or compatibility.

Use official documentation through Context7 when framework or library behavior matters.

## Verification

For Python, tests, packaging, dependencies, executable examples, or CI behavior:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check
uv run deptry .
just test
```

Use `just setup` when the environment or coverage subprocess hook is stale. Run `uv build` for package/build/release changes. `uv run pip-audit` is best effort when network is available; reported vulnerabilities remain real findings.

For instructions-only Markdown or skill changes, inspect the diff and run only directly applicable validators.

For GitHub Actions pin changes:

```bash
python3 .agents/skills/github-actions-pin-refresh/scripts/list_pinned_actions.py --check
rg "uses:" .github -n
git diff -- .github
```

## Repo-local skills

- Python code: `python-pro`
- Async code: `python-pro` + `async-python-patterns`
- Tests: `python-pro` + `python-testing-patterns`
- Packaging/dependencies/build/release: `python-packaging`
- Architecture/features/refactors: `software-architecture`
- SQLAlchemy queries/adapters: `python-pro` + `sqlalchemy-orm`
- GitHub Actions pins: `github-actions-pin-refresh`
- Before completion claims: `verification-before-completion`
