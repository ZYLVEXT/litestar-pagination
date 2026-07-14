---
name: async-python-patterns
description: Async patterns for litestar-pagination: AsyncSession execution, async cursor pagination, Litestar request-scoped sessions, cancellation, sync/async parity, and pytest-asyncio tests. Use when implementing or reviewing async code in this project.
---

# Async Python Patterns — litestar-pagination

Combine this skill with `python-pro` for async implementation or review.

## Evidence first

- Read `AGENTS.md`, `PRD.md`, and `TECHSTACK.md`.
- Use Context7 for current `AsyncSession`, Litestar DI, Advanced Alchemy session, sqlakeyset async, and pytest-asyncio behavior.
- Trace the sync path before duplicating it asynchronously; shared pure query construction belongs in one helper.

## Rules

- `apaginate()` accepts an existing request-scoped `AsyncSession`; it never creates, commits, closes, or owns that session.
- Await count and page queries explicitly and preserve their SQLAlchemy exceptions.
- Do not call sync session methods, blocking I/O, `time.sleep()`, or synchronous database drivers in async code.
- Keep cursor decoding and query construction synchronous when they are CPU-only and trivial.
- Re-raise `asyncio.CancelledError` after cleanup; do not convert cancellation into pagination errors.
- Do not add concurrent count/page execution without evidence: they share a session/transaction and many drivers prohibit simultaneous operations.
- Keep `paginate()` and `apaginate()` behavior symmetric. Differences require tests and documentation.

## Litestar and Advanced Alchemy

- Advanced Alchemy owns engine/session lifecycle; consume its injected session unchanged.
- Use Litestar dependency injection for `CursorParams`; no pagination plugin or route patching.
- Request state must not be stored in module globals or mutable singletons.

## Tests

- pytest-asyncio runs in auto mode; do not add `@pytest.mark.asyncio` by habit.
- Test against real async SQLite and PostgreSQL drivers, not `AsyncMock` session behavior.
- Pair important sync and async cases: first/last page, forward/backward traversal, malformed cursor, count override, and no-total mode.
- Assert observable page contents and bookmarks, not internal await counts.

See `resources/implementation-playbook.md` for the canonical shape.
