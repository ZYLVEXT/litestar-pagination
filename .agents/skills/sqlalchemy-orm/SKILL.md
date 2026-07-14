---
name: sqlalchemy-orm
description: SQLAlchemy ORM guidance for litestar-pagination. Use when changing or reviewing statement validation, count queries, sqlakeyset paging, entity result shapes, sync/async sessions, dialect behavior, or Advanced Alchemy compatibility.
---

# SQLAlchemy ORM — litestar-pagination

Combine this skill with `python-pro`; add `async-python-patterns` for `AsyncSession` work.

## Evidence first

- Read `AGENTS.md`, `PRD.md`, and `TECHSTACK.md`.
- Use Context7 for SQLAlchemy, sqlakeyset, and Advanced Alchemy behavior.
- Inspect every caller before changing shared query/count/unwrap helpers.

## Supported query contract

- SQLAlchemy 2 `Select` only.
- MVP accepts one mapped ORM entity result shape.
- Require explicit `ORDER BY` and document a unique tie-breaker.
- Never infer or append a primary key.
- Reject legacy `Query`, raw SQL, `TextClause`, `FromStatement`, `CompoundSelect`, scalar, and multi-column row shapes until the PRD changes.

## Query discipline

- Use SQLAlchemy expressions and bound values; never interpolate cursor values into SQL.
- Let sqlakeyset construct keyset predicates and bookmarks.
- Preserve ascending, descending, mixed compound, forward, and backward ordering semantics.
- Default total count removes ordering and counts the unpaginated filtered statement through a subquery.
- Accept a caller-provided `count_query` for joins, distinct semantics, and tuning.
- Skip all count execution when `include_total` is false.
- Entity uniquification defaults to enabled; document that count semantics remain those of the count query.

## Session ownership

- Accept existing `Session` or `AsyncSession` objects.
- Do not create, commit, rollback, or close sessions.
- Preserve transaction context and underlying SQLAlchemy exceptions.
- Treat Advanced Alchemy sessions exactly like equivalent SQLAlchemy sessions.

## Tests

- Test real SQLite and PostgreSQL, sync and async.
- Cover duplicate leading sort values, compound order, empty pages, filtered queries, backward traversal, custom count, no-total mode, and invalid bookmarks.
- Assert generated behavior/results; avoid brittle full-SQL string snapshots unless a dialect regression requires one.
