# litestar-pagination

Cursor/keyset pagination for Litestar, with SQLAlchemy and Advanced Alchemy integration.

The package supports rich bidirectional `CursorPage` responses and Litestar's native
forward-only `CursorPagination` through `AbstractAsyncCursorPaginator` and
`AbstractSyncCursorPaginator` implementations.

See the [documentation](https://zylvext.github.io/litestar-pagination/) for installation,
quickstarts, navigation, totals, and Advanced Alchemy examples. The detailed contract is in
[PRD.md](PRD.md).
