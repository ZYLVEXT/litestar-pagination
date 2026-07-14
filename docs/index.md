# litestar-pagination

`litestar-pagination` adds production-ready SQLAlchemy keyset pagination to Litestar.
It uses `sqlakeyset` for deterministic forward and backward traversal, and consumes the
sessions that your application already manages. It does not install a Litestar or Advanced
Alchemy plugin.

## Installation

```bash
pip install litestar-pagination
pip install 'litestar-pagination[sqlalchemy]'
pip install 'litestar-pagination[advanced-alchemy]'
```

The base package contains the Litestar dataclasses and dependency contract. The `sqlalchemy`
extra adds SQLAlchemy 2 and `sqlakeyset`; `advanced-alchemy` adds Advanced Alchemy together
with that SQLAlchemy extra.

## Five-minute SQLAlchemy quickstart

Register `CursorParams` as an ordinary named Litestar dependency. `NamedDependency` is the
current Litestar 2.x annotation for a dependency registered by name.

```python
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import apaginate


@get("/users")
async def list_users(
    session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPage[User]:
    statement = select(User).order_by(User.created_at, User.id)
    return await apaginate(session, statement, pagination)


app = Litestar(
    route_handlers=[list_users],
    dependencies={"pagination": Provide(CursorParams, sync_to_thread=False)},
)
```

`paginate()` provides the equivalent synchronous API. The package never creates, commits,
rolls back, or closes a session.

Always provide deterministic ordering with a unique tie-breaker. The package will reject a
statement with no `ORDER BY`, but it intentionally does not infer or append a primary key:

```python
select(User).order_by(User.created_at, User.id)
```

## Two Litestar response contracts

### Rich bidirectional pages

`paginate()` and `apaginate()` return `CursorPage[T]`:

```json
{
  "items": [{"id": 42, "name": "Ada"}],
  "total": 100,
  "current_page": "...",
  "current_page_backwards": "...",
  "previous_page": null,
  "next_page": "..."
}
```

Use `next_page` as the next request's `cursor` to move forward, and `previous_page` to move
backward. `current_page` refetches the same page in forward direction;
`current_page_backwards` refetches it through its reverse bookmark. Clients must persist and
return each cursor unchanged.

### Native Litestar forward-only pages

When an endpoint should return Litestar's built-in `CursorPagination`, use the SQLAlchemy
paginator classes. They directly implement Litestar's `AbstractAsyncCursorPaginator` and
`AbstractSyncCursorPaginator`, so the result has Litestar's standard `items`,
`results_per_page`, and next `cursor` fields.

```python
from litestar import get
from litestar.di import NamedDependency
from litestar.pagination import CursorPagination
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pagination import CursorParams
from litestar_pagination.ext.sqlalchemy import SQLAlchemyAsyncCursorPaginator


@get("/users")
async def list_users(
    session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPagination[str, User]:
    paginator = SQLAlchemyAsyncCursorPaginator(
        session,
        select(User).order_by(User.created_at, User.id),
    )
    return await paginator(pagination.cursor, pagination.size)
```

The native paginator mode is intentionally forward-only and does not execute a total count.
Choose `CursorPage` when the API needs backward navigation or totals.

## Totals and custom counts

Rich pages count the full filtered result by default. The default query removes ordering and
counts a subquery of the original select. For joins, distinct queries, or a domain-specific
definition of “total”, provide the query explicitly:

```python
from sqlalchemy import func, select

count_query = select(func.count()).select_from(User).where(User.is_active)
page = await apaginate(session, statement, pagination, count_query=count_query)
```

To skip the extra count query, subclass the dependency contract. `total` remains present in the
response and is `null`.

```python
from typing import ClassVar


class NoTotalCursorParams(CursorParams):
    include_total: ClassVar[bool] = False


app = Litestar(
    route_handlers=[list_users],
    dependencies={"pagination": Provide(NoTotalCursorParams, sync_to_thread=False)},
)
```

## Advanced Alchemy and DTOs

Advanced Alchemy owns session lifecycle. Inject the session using its normal Litestar
configuration and pass it directly to this package; no repository mixin or package plugin is
needed. `SQLAlchemyDTO` transforms entities inside either generic page wrapper.

```python
from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO
from litestar import get
from litestar.di import NamedDependency
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import apaginate


@get("/users", return_dto=SQLAlchemyDTO[User])
async def list_users(
    db_session: AsyncSession,
    pagination: NamedDependency[CursorParams],
) -> CursorPage[User]:
    return await apaginate(
        db_session,
        select(User).order_by(User.created_at, User.id),
        pagination,
    )
```

Register the same dependency at application, router, controller, or handler scope according to
your application structure.

## Cursor safety and errors

Bookmarks are sqlakeyset strings encoded with Base64 and URL escaping, following the established
`fastapi-pagination` representation. They are opaque: their contents and encoding are not a
stable API schema. Malformed Base64, malformed sqlakeyset bookmarks, and a bookmark incompatible
with the query yield Litestar's HTTP 400 validation response.

Base64 is not encryption or signing. Cursors can reveal ordered values to a determined client and
must not be treated as confidential or tamper-proof. Add signing at an application boundary if
your threat model requires it.

## Compatibility and MVP limits

- Python `>=3.12,<3.15`
- Litestar `>=2.24,<3`
- SQLAlchemy `>=2,<3`
- Advanced Alchemy `>=1.11,<2`
- SQLite and PostgreSQL, both synchronous and asynchronous sessions

The SQLAlchemy adapter accepts only SQLAlchemy 2 `select(Model)` statements that select exactly
one mapped ORM entity. Legacy `Query`, raw SQL, scalar or multi-column results, implicit
ordering, offset pagination, signing, links, transformers, and storage integrations other than
SQLAlchemy are outside the MVP.
