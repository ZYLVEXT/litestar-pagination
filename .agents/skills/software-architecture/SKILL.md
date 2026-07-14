---
name: software-architecture
description: Architecture guide for litestar-pagination: storage-independent cursor contracts, Litestar DI/DTO boundaries, optional SQLAlchemy adapters, Advanced Alchemy compatibility, and minimal public APIs. Use when designing features, modules, or refactors.
---

# Software Architecture — litestar-pagination

Use this skill for module boundaries, public API design, features, and refactors.

## Evidence first

- Read `AGENTS.md`, `PRD.md`, and `TECHSTACK.md`.
- Use CodeGraph for structure and impact when available.
- Use Context7 for framework/library extension points rather than inventing integrations.

## Product shape

This is a reusable library with one MVP purpose: cursor/keyset pagination for Litestar. SQLAlchemy is the first optional storage adapter; Advanced Alchemy supplies compatible sessions and DTOs but is not patched or subclassed.

```text
litestar_pagination/
  __init__.py              # lightweight public CursorParams/CursorPage surface
  cursor.py                # storage-independent contracts and codec
  ext/
    sqlalchemy.py          # sync/async SQLAlchemy + sqlakeyset adapter
```

## Design rules

1. Keep public APIs explicit: Litestar `Provide(CursorParams)` plus `paginate()` / `apaginate()`.
2. Keep optional dependencies lazy. Importing `litestar_pagination` must not require SQLAlchemy, sqlakeyset, or Advanced Alchemy.
3. Reuse native dataclasses, Litestar DI/DTO/OpenAPI, SQLAlchemy `Select`, and sqlakeyset bookmarks.
4. Keep session ownership outside the package. Never commit, rollback, or close caller sessions.
5. Keep HTTP validation separate from developer query errors and database execution failures.
6. Add storage adapters under `ext/` only when implemented; reuse core page/parameter contracts.
7. Update docs with public API, response, cursor, compatibility, or dependency changes.

## Anti-patterns

- Reimplementing classic or limit/offset pagination.
- A Litestar or Advanced Alchemy plugin when native DI already covers the use case.
- Adapter registries, flow engines, factories, or abstract paginator hierarchies for hypothetical backends.
- Automatic primary-key/order inference.
- Eager root imports of optional integrations.
- Repository/service layers owned by this package.
- Compatibility shims for APIs that have never shipped.
