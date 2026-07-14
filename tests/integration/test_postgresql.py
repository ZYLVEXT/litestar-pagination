"""PostgreSQL integration tests for synchronous and asynchronous pagination."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar
from uuid import uuid4

import pytest
from litestar.exceptions import ValidationException
from sqlalchemy import Integer, String, create_engine, desc, false, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.schema import CreateSchema, DropSchema

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import apaginate, paginate

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.sql import Select

SYNC_DSN = os.environ.get("TEST_POSTGRES_DSN")
ASYNC_DSN = os.environ.get("TEST_POSTGRES_ASYNC_DSN")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        SYNC_DSN is None or ASYNC_DSN is None,
        reason="TEST_POSTGRES_DSN and TEST_POSTGRES_ASYNC_DSN are required",
    ),
]

PAGE_SIZE = 2
CUSTOM_TOTAL = 3
TOTAL_ROWS = 6
BAD_REQUEST = 400
FIRST_PAGE_IDS = [1, 2]
SECOND_PAGE_IDS = [3, 4]
THIRD_PAGE_IDS = [5, 6]


class Base(DeclarativeBase):
    """Test declarative base."""


class PostgresWidget(Base):
    """A PostgreSQL entity with duplicate leading sort values."""

    __tablename__ = "postgres_widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    bucket: Mapped[str] = mapped_column(String, nullable=False)


@dataclass
class NoTotalParams(CursorParams):
    """Disable separate count execution."""

    include_total: ClassVar[bool] = False


@pytest.fixture
def sync_session() -> Iterator[Session]:
    """Provide a synchronous PostgreSQL session in a private schema.

    Yields:
        An empty session with the test table installed.
    """
    engine = create_engine(_sync_dsn())
    schema = _schema_name()
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    schema_engine = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(schema_engine)

    try:
        with Session(schema_engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(schema_engine)
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()


@pytest.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """Provide an asynchronous PostgreSQL session in a private schema.

    Yields:
        An empty session with the test table installed.
    """
    engine = create_async_engine(_async_dsn())
    schema = _schema_name()
    async with engine.begin() as connection:
        await connection.execute(CreateSchema(schema))
    schema_engine = engine.execution_options(schema_translate_map={None: schema})
    async with schema_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        factory = async_sessionmaker(schema_engine, expire_on_commit=False)
        async with factory() as session:
            yield session
    finally:
        async with schema_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        async with engine.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True))
        await engine.dispose()


def _sync_dsn() -> str:
    """Return the configured synchronous DSN.

    Raises:
        RuntimeError: If PostgreSQL integration testing is not configured.
    """
    if SYNC_DSN is None:
        message = "TEST_POSTGRES_DSN is required"
        raise RuntimeError(message)
    return SYNC_DSN


def _async_dsn() -> str:
    """Return the configured asynchronous DSN.

    Raises:
        RuntimeError: If PostgreSQL integration testing is not configured.
    """
    if ASYNC_DSN is None:
        message = "TEST_POSTGRES_ASYNC_DSN is required"
        raise RuntimeError(message)
    return ASYNC_DSN


def _schema_name() -> str:
    """Return a schema identifier that cannot collide across xdist workers."""
    return f"pagination_{uuid4().hex}"


def _seed_sync(session: Session) -> None:
    """Insert deterministic test data."""
    session.add_all(
        [
            PostgresWidget(id=1, rank=1, bucket="blue"),
            PostgresWidget(id=2, rank=1, bucket="blue"),
            PostgresWidget(id=3, rank=2, bucket="red"),
            PostgresWidget(id=4, rank=2, bucket="blue"),
            PostgresWidget(id=5, rank=3, bucket="red"),
            PostgresWidget(id=6, rank=3, bucket="blue"),
        ]
    )
    session.commit()


async def _seed_async(session: AsyncSession) -> None:
    """Insert deterministic test data asynchronously."""
    session.add_all(
        [
            PostgresWidget(id=1, rank=1, bucket="blue"),
            PostgresWidget(id=2, rank=1, bucket="blue"),
            PostgresWidget(id=3, rank=2, bucket="red"),
            PostgresWidget(id=4, rank=2, bucket="blue"),
            PostgresWidget(id=5, rank=3, bucket="red"),
            PostgresWidget(id=6, rank=3, bucket="blue"),
        ]
    )
    await session.commit()


def _ordered_widgets() -> Select[tuple[PostgresWidget]]:
    """Return the canonical ordering with an explicit unique tie-breaker."""
    return select(PostgresWidget).order_by(PostgresWidget.rank, PostgresWidget.id)


def _page_ids(page: CursorPage[PostgresWidget]) -> list[int]:
    """Return ordered entity identifiers from a page."""
    return [item.id for item in page.items]


def test_postgres_sync_navigation_counts_and_incompatible_cursor(sync_session: Session) -> None:
    """Traverse all PostgreSQL rows and reject a bookmark for another ordering."""
    _seed_sync(sync_session)
    statement = _ordered_widgets()
    first = paginate(sync_session, statement, CursorParams(size=PAGE_SIZE))
    second = paginate(sync_session, statement, CursorParams(cursor=first.next_page, size=PAGE_SIZE))
    third = paginate(sync_session, statement, CursorParams(cursor=second.next_page, size=PAGE_SIZE))

    assert _page_ids(first) == FIRST_PAGE_IDS
    assert _page_ids(second) == SECOND_PAGE_IDS
    assert _page_ids(third) == THIRD_PAGE_IDS
    assert first.total == TOTAL_ROWS
    assert (
        _page_ids(paginate(sync_session, statement, CursorParams(cursor=third.previous_page, size=PAGE_SIZE)))
        == SECOND_PAGE_IDS
    )

    with pytest.raises(ValidationException, match="Invalid cursor") as error:
        paginate(
            sync_session,
            select(PostgresWidget).order_by(PostgresWidget.id),
            CursorParams(cursor=first.next_page, size=PAGE_SIZE),
        )

    assert error.value.status_code == BAD_REQUEST


def test_postgres_sync_custom_count_and_no_total(sync_session: Session) -> None:
    """Support custom totals and the no-total variant on PostgreSQL."""
    _seed_sync(sync_session)
    count_query = select(func.count()).select_from(PostgresWidget).where(PostgresWidget.id < CUSTOM_TOTAL)

    custom = paginate(sync_session, _ordered_widgets(), CursorParams(size=PAGE_SIZE), count_query=count_query)
    without_total = paginate(sync_session, _ordered_widgets(), NoTotalParams(size=PAGE_SIZE))

    assert custom.total == PAGE_SIZE
    assert without_total.total is None


async def test_postgres_async_navigation_descending_empty_and_counts(async_session: AsyncSession) -> None:
    """Exercise asynchronous traversal, ordering, empty pages, and total modes."""
    await _seed_async(async_session)
    statement = _ordered_widgets()
    first = await apaginate(async_session, statement, CursorParams(size=PAGE_SIZE))
    second = await apaginate(async_session, statement, CursorParams(cursor=first.next_page, size=PAGE_SIZE))
    previous = await apaginate(async_session, statement, CursorParams(cursor=second.previous_page, size=PAGE_SIZE))
    descending = await apaginate(
        async_session,
        select(PostgresWidget).order_by(desc(PostgresWidget.rank), desc(PostgresWidget.id)),
        CursorParams(size=CUSTOM_TOTAL),
    )
    empty = await apaginate(
        async_session,
        _ordered_widgets().where(false()),
        CursorParams(size=PAGE_SIZE),
    )
    count_query = select(func.count()).select_from(PostgresWidget).where(PostgresWidget.id < CUSTOM_TOTAL)
    custom = await apaginate(async_session, _ordered_widgets(), CursorParams(size=PAGE_SIZE), count_query=count_query)
    without_total = await apaginate(async_session, _ordered_widgets(), NoTotalParams(size=PAGE_SIZE))

    assert _page_ids(first) == FIRST_PAGE_IDS
    assert _page_ids(second) == SECOND_PAGE_IDS
    assert _page_ids(previous) == FIRST_PAGE_IDS
    assert _page_ids(descending) == [6, 5, 4]
    assert empty.items == []
    assert empty.total == 0
    assert custom.total == PAGE_SIZE
    assert without_total.total is None
