---
name: python-testing-patterns
description: Test-writing guide for litestar-pagination. Use for pytest tests covering cursor codecs, keyset traversal, SQLAlchemy sync/async behavior, Litestar DI/OpenAPI/DTO integration, Advanced Alchemy sessions, and supported databases.
---

# Python Testing Patterns — litestar-pagination

Combine this skill with `python-pro`; also use `async-python-patterns` for async tests.

## Evidence first

- Read `AGENTS.md`, `PRD.md`, `TECHSTACK.md`, and the public API under test.
- Use Context7 when assertions depend on current Litestar, SQLAlchemy, sqlakeyset, Advanced Alchemy, or pytest behavior.
- Use CodeGraph for test-impact discovery when available.

## Test shape

- Use markers: `unit`, `integration`, and `e2e`.
- pytest-asyncio uses auto mode and a session-scoped loop.
- Prefer behavior assertions through public imports and functions.
- Keep fixtures narrow and data deterministic. Avoid helper layers that hide ordering or bookmark inputs.
- Do not mock SQLAlchemy/sqlakeyset semantics. Use real SQLite/PostgreSQL engines and sessions.

## Required behavior coverage

- Codec round trips and malformed cursor HTTP 400 behavior.
- Size defaults and boundaries through Litestar DI.
- Forward and backward traversal without duplicates or omissions on a stable dataset.
- Ascending, descending, and compound ordering with duplicate leading values and a unique tie-breaker.
- Missing ordering and unsupported select shapes as developer errors.
- Entity result unwrapping and uniquification.
- Default, custom, and disabled total counting.
- Sync/async parity on SQLite and PostgreSQL.
- OpenAPI, dataclass serialization, and `SQLAlchemyDTO` transformation inside `items`.
- Sessions injected by Advanced Alchemy without an additional plugin.

## Quality

- Tests should fail for one clear reason and assert external behavior before implementation details.
- Use parametrization for small matrices; keep dialect-specific expectations explicit.
- Do not add tautological tests or branches solely to satisfy coverage.
- Run the verification block from `AGENTS.md` for library/test changes.
