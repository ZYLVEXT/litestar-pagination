# Changelog

## 1.0.0 (2026-08-08)

- Preserve developer and database exceptions instead of translating SQLAlchemy `ArgumentError` into HTTP 400.
- Validate and execute the requested page before totals so invalid cursors never trigger count queries.
- Add optional-import isolation, mixed-ordering, async database-error, wheel-install, and documentation-build gates.
- Pin the PostgreSQL CI service and all GitHub Actions to immutable versions and digests.
- Restrict source distributions to public package, test, documentation, and release-verification files.
- Raise the SQLAlchemy floor to the current stable 2.0.51 release verified by the full matrix.
- Add tag-bound release verification, reproducible builds, CycloneDX SBOMs, build attestations, Trusted Publishing, and guarded Pages deployment.
- Refresh the build, lint, type-checking, test, documentation, and prek toolchain to current stable releases.

## 0.2.0 (2026-07-14)

- Add `CursorParams`, rich bidirectional `CursorPage`, and SQLAlchemy keyset pagination.
- Add synchronous and asynchronous implementations of Litestar's native cursor paginator abstractions.
- Add SQLite and PostgreSQL coverage, including Advanced Alchemy and DTO integration.
