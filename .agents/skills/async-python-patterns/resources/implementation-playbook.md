# Async Pagination — Implementation Playbook

## Request-scoped session

```python
@get("/users")
async def list_users(
    db_session: AsyncSession,
    pagination: CursorParams,
) -> CursorPage[User]:
    statement = select(User).order_by(User.created_at, User.id)
    return await apaginate(db_session, statement, pagination)
```

The session is injected and owned by Litestar/Advanced Alchemy. `apaginate()` only executes statements.

## Shared query construction

Keep statement validation, count-statement construction, cursor decoding, and result normalization in synchronous pure helpers. Sync and async entrypoints should differ only at execution boundaries.

## Do not parallelize one session

Do not run count and page statements concurrently on the same `AsyncSession`. Execute them in the documented order so transaction and driver behavior remains predictable.

## Async tests

```python
import pytest


pytestmark = pytest.mark.integration


async def test_next_page(async_session: AsyncSession) -> None:
    first = await apaginate(async_session, statement, CursorParams(size=2))
    second = await apaginate(async_session, statement, CursorParams(cursor=first.next_page, size=2))
    assert [item.id for item in second.items] == [3, 4]
```

Use real async database drivers and pytest-asyncio auto mode.
