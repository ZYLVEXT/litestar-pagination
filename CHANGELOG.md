# Changelog

## 0.2.0 (2026-07-14)

- Add `CursorParams`, rich bidirectional `CursorPage`, and SQLAlchemy keyset pagination.
- Add synchronous and asynchronous implementations of Litestar's native cursor paginator abstractions.
- Add SQLite and PostgreSQL coverage, including Advanced Alchemy and DTO integration.
- Preserve developer and database exceptions instead of translating SQLAlchemy `ArgumentError` into HTTP 400.
- Validate and execute the requested page before totals so invalid cursors never trigger count queries.
- Add optional-import isolation, mixed-ordering, async database-error, wheel-install, and documentation-build gates.
- Pin the PostgreSQL CI service to an exact version and multi-architecture image digest.
- Restrict source distributions to public package, test, and documentation files.
- Raise the SQLAlchemy floor to the current stable 2.0.51 release verified by the full matrix.
- Verify reproducibility of both wheel and source-distribution release artifacts.
