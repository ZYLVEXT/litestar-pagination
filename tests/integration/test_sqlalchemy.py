"""SQLite integration tests for the SQLAlchemy adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

import pytest
from litestar.exceptions import ValidationException
from litestar.pagination import CursorPagination
from sqlalchemy import ForeignKey, Integer, String, create_engine, desc, false, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, aliased, joinedload, mapped_column, relationship

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.cursor import encode_cursor
from litestar_pagination.ext.sqlalchemy import (
    SQLAlchemyAsyncCursorPaginator,
    SQLAlchemySyncCursorPaginator,
    _default_count_query,
    apaginate,
    paginate,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from pathlib import Path

    from sqlalchemy.sql import Select

pytestmark = pytest.mark.integration

PAGE_SIZE = 2
CUSTOM_TOTAL = 3
FILTERED_TOTAL = 4
BAD_REQUEST = 400
GREATER_THAN_TOTAL_PAGE_SIZE = 7
FIRST_PAGE_IDS = [1, 2]
SECOND_PAGE_IDS = [3, 4]
THIRD_PAGE_IDS = [5, 6]
ALL_IDS = FIRST_PAGE_IDS + SECOND_PAGE_IDS + THIRD_PAGE_IDS


class Base(DeclarativeBase):
    """Test declarative base."""


class Widget(Base):
    """A deterministically ordered test entity."""

    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    bucket: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[list[WidgetNote]] = relationship()


class WidgetNote(Base):
    """A child entity used to exercise ORM result uniquification."""

    __tablename__ = "widget_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    widget_id: Mapped[int] = mapped_column(ForeignKey("widgets.id"), nullable=False)


@dataclass
class NoTotalParams(CursorParams):
    """Disable counting without adding a public query parameter."""

    include_total: ClassVar[bool] = False


@pytest.fixture
def sync_session(tmp_path: Path) -> Iterator[Session]:
    """Provide a fresh synchronous SQLite session.

    Yields:
        An empty session with the test schema installed.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'pagination.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
async def async_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    """Provide a fresh asynchronous SQLite session.

    Yields:
        An empty session with the test schema installed.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'pagination.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _seed_sync(session: Session) -> None:
    """Insert rows with duplicate leading ordering values."""
    session.add_all([
        Widget(id=1, rank=1, bucket="blue"),
        Widget(id=2, rank=1, bucket="blue"),
        Widget(id=3, rank=2, bucket="red"),
        Widget(id=4, rank=2, bucket="blue"),
        Widget(id=5, rank=3, bucket="red"),
        Widget(id=6, rank=3, bucket="blue"),
    ])
    session.commit()


async def _seed_async(session: AsyncSession) -> None:
    """Insert rows with duplicate leading ordering values asynchronously."""
    session.add_all([
        Widget(id=1, rank=1, bucket="blue"),
        Widget(id=2, rank=1, bucket="blue"),
        Widget(id=3, rank=2, bucket="red"),
        Widget(id=4, rank=2, bucket="blue"),
        Widget(id=5, rank=3, bucket="red"),
        Widget(id=6, rank=3, bucket="blue"),
    ])
    await session.commit()


def _page_ids(page: CursorPage[Widget]) -> list[int]:
    """Return the entity identifiers in a page."""
    return [item.id for item in page.items]


def _ordered_widgets() -> Select[tuple[Widget]]:
    """Return the canonical compound ordering used by the tests."""
    return select(Widget).order_by(Widget.rank, Widget.id)


def test_sync_navigation_and_bookmark_refetch(sync_session: Session) -> None:
    """Navigate forward and backward without duplicates or omissions."""
    _seed_sync(sync_session)
    statement = _ordered_widgets()
    first = paginate(sync_session, statement, CursorParams(size=PAGE_SIZE))
    second = paginate(sync_session, statement, CursorParams(cursor=first.next_page, size=PAGE_SIZE))
    third = paginate(sync_session, statement, CursorParams(cursor=second.next_page, size=PAGE_SIZE))

    assert _page_ids(first) == FIRST_PAGE_IDS
    assert _page_ids(second) == SECOND_PAGE_IDS
    assert _page_ids(third) == THIRD_PAGE_IDS
    assert _page_ids(first) + _page_ids(second) + _page_ids(third) == ALL_IDS
    assert first.total == len(ALL_IDS)
    assert first.previous_page is None
    assert first.next_page is not None
    assert second.previous_page is not None
    assert second.next_page is not None
    assert third.previous_page is not None
    assert third.next_page is None

    previous = paginate(sync_session, statement, CursorParams(cursor=third.previous_page, size=PAGE_SIZE))
    forwards = paginate(sync_session, statement, CursorParams(cursor=second.current_page, size=PAGE_SIZE))
    backwards = paginate(
        sync_session,
        statement,
        CursorParams(cursor=second.current_page_backwards, size=PAGE_SIZE),
    )

    assert _page_ids(previous) == SECOND_PAGE_IDS
    assert _page_ids(forwards) == SECOND_PAGE_IDS
    assert _page_ids(backwards) == SECOND_PAGE_IDS


def test_native_litestar_sync_paginator(sync_session: Session) -> None:
    """Return Litestar's forward-only container through its abstract paginator API."""
    _seed_sync(sync_session)
    paginator = SQLAlchemySyncCursorPaginator(sync_session, _ordered_widgets())

    first = paginator(cursor=None, results_per_page=PAGE_SIZE)
    second = paginator(cursor=first.cursor, results_per_page=PAGE_SIZE)

    assert isinstance(first, CursorPagination)
    assert [item.id for item in first.items] == FIRST_PAGE_IDS
    assert [item.id for item in second.items] == SECOND_PAGE_IDS
    assert first.results_per_page == PAGE_SIZE
    assert first.cursor is not None


def test_sync_counts_filters_and_descending_order(sync_session: Session) -> None:
    """Count the filtered set and retain descending compound ordering."""
    _seed_sync(sync_session)
    filtered = select(Widget).where(Widget.bucket == "blue").order_by(Widget.rank, Widget.id)
    descending = select(Widget).order_by(desc(Widget.rank), desc(Widget.id))

    filtered_page = paginate(sync_session, filtered, CursorParams(size=PAGE_SIZE))
    descending_page = paginate(sync_session, descending, CursorParams(size=CUSTOM_TOTAL))
    larger_page = paginate(sync_session, _ordered_widgets(), CursorParams(size=GREATER_THAN_TOTAL_PAGE_SIZE))

    assert _page_ids(filtered_page) == [1, 2]
    assert filtered_page.total == FILTERED_TOTAL
    assert _page_ids(descending_page) == [6, 5, 4]
    assert _page_ids(larger_page) == ALL_IDS


def test_sync_custom_count_and_no_total(sync_session: Session) -> None:
    """Use caller-controlled counts and skip them through a params subclass."""
    _seed_sync(sync_session)
    count_query = select(func.count()).select_from(Widget).where(Widget.id < CUSTOM_TOTAL)
    prohibited_count_query = cast("Select[tuple[int]]", select(text("missing_count_column")))

    custom = paginate(sync_session, _ordered_widgets(), CursorParams(size=PAGE_SIZE), count_query=count_query)
    without_total = paginate(
        sync_session,
        _ordered_widgets(),
        NoTotalParams(size=PAGE_SIZE),
        count_query=prohibited_count_query,
    )

    assert custom.total == PAGE_SIZE
    assert without_total.total is None


def test_default_count_query_removes_ordering() -> None:
    """Build the documented count statement over the original filtered select."""
    query = _default_count_query(_ordered_widgets().where(Widget.bucket == "blue"))

    assert "ORDER BY" not in str(query)
    assert "count" in str(query).lower()


def test_sync_empty_page_and_entity_uniquification(sync_session: Session) -> None:
    """Return entities rather than rows for empty and joined queries."""
    _seed_sync(sync_session)
    sync_session.add_all([
        WidgetNote(id=1, widget_id=1),
        WidgetNote(id=2, widget_id=1),
        WidgetNote(id=3, widget_id=2),
    ])
    sync_session.commit()

    empty = paginate(sync_session, _ordered_widgets().where(false()), CursorParams(size=PAGE_SIZE))
    joined = paginate(
        sync_session,
        select(Widget).options(joinedload(Widget.notes)).order_by(Widget.id),
        CursorParams(size=len(ALL_IDS)),
    )

    assert empty.items == []
    assert empty.total == 0
    assert empty.previous_page is None
    assert empty.next_page is None
    assert empty.current_page is not None
    assert empty.current_page_backwards is not None
    assert _page_ids(joined) == ALL_IDS
    assert joined.total == len(ALL_IDS)


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        (cast("Select[tuple[Widget]]", text("SELECT 1")), "Select statement"),
        (select(Widget), "requires ordering"),
        (cast("Select[tuple[Widget]]", select(Widget.id).order_by(Widget.id)), "exactly one"),
        (
            cast("Select[tuple[Widget]]", select(Widget.id, Widget.bucket).order_by(Widget.id)),
            "exactly one",
        ),
        (select(aliased(Widget)).order_by(Widget.id), "exactly one"),
        (
            cast("Select[tuple[Widget]]", select(Widget).from_statement(text("SELECT * FROM widgets"))),
            "Select statement",
        ),
        (cast("Select[tuple[Widget]]", select(Widget).union_all(select(Widget))), "Select statement"),
    ],
)
def test_sync_rejects_unsupported_statements(
    sync_session: Session,
    statement: Select[tuple[Widget]],
    message: str,
) -> None:
    """Fail fast for statements outside the documented ORM entity contract."""
    with pytest.raises((TypeError, ValueError), match=message):
        paginate(sync_session, statement, CursorParams())


def test_sync_rejects_legacy_query(sync_session: Session) -> None:
    """Reject SQLAlchemy's legacy ``Query`` interface before execution."""
    legacy_query = cast("Select[tuple[Widget]]", sync_session.query(Widget))

    with pytest.raises(TypeError, match="Select statement"):
        paginate(sync_session, legacy_query, CursorParams())


@pytest.mark.parametrize("bookmark", ["not-a-bookmark", ">i:1~i:2~i:3", ">x:1"])
def test_sync_invalid_sqlakeyset_bookmark_is_a_validation_error(sync_session: Session, bookmark: str) -> None:
    """Map malformed and incompatible bookmarks to Litestar validation errors."""
    _seed_sync(sync_session)

    with pytest.raises(ValidationException, match="Invalid cursor") as error:
        paginate(
            sync_session,
            _ordered_widgets(),
            CursorParams(cursor=encode_cursor(bookmark), size=PAGE_SIZE),
        )

    assert error.value.status_code == BAD_REQUEST


def test_sync_database_errors_are_preserved(sync_session: Session) -> None:
    """Do not turn database failures into client cursor errors."""
    _seed_sync(sync_session)
    statement = select(Widget).where(text("missing_column = 1")).order_by(Widget.id)

    with pytest.raises(OperationalError):
        paginate(sync_session, statement, CursorParams(size=PAGE_SIZE))


async def test_async_navigation_and_bookmark_refetch(async_session: AsyncSession) -> None:
    """Provide the same keyset navigation semantics for asynchronous sessions."""
    await _seed_async(async_session)
    statement = _ordered_widgets()
    first = await apaginate(async_session, statement, CursorParams(size=PAGE_SIZE))
    second = await apaginate(async_session, statement, CursorParams(cursor=first.next_page, size=PAGE_SIZE))
    third = await apaginate(async_session, statement, CursorParams(cursor=second.next_page, size=PAGE_SIZE))

    assert _page_ids(first) == FIRST_PAGE_IDS
    assert _page_ids(second) == SECOND_PAGE_IDS
    assert _page_ids(third) == THIRD_PAGE_IDS
    assert first.total == len(ALL_IDS)
    assert first.previous_page is None
    assert second.previous_page is not None
    assert third.next_page is None

    previous = await apaginate(async_session, statement, CursorParams(cursor=third.previous_page, size=PAGE_SIZE))
    forwards = await apaginate(async_session, statement, CursorParams(cursor=second.current_page, size=PAGE_SIZE))
    backwards = await apaginate(
        async_session,
        statement,
        CursorParams(cursor=second.current_page_backwards, size=PAGE_SIZE),
    )

    assert _page_ids(previous) == SECOND_PAGE_IDS
    assert _page_ids(forwards) == SECOND_PAGE_IDS
    assert _page_ids(backwards) == SECOND_PAGE_IDS


async def test_native_litestar_async_paginator(async_session: AsyncSession) -> None:
    """Return Litestar's async forward-only container through its abstract paginator API."""
    await _seed_async(async_session)
    paginator = SQLAlchemyAsyncCursorPaginator(async_session, _ordered_widgets())

    first = await paginator(cursor=None, results_per_page=PAGE_SIZE)
    second = await paginator(cursor=first.cursor, results_per_page=PAGE_SIZE)

    assert isinstance(first, CursorPagination)
    assert [item.id for item in first.items] == FIRST_PAGE_IDS
    assert [item.id for item in second.items] == SECOND_PAGE_IDS
    assert first.results_per_page == PAGE_SIZE
    assert first.cursor is not None


async def test_async_custom_count_and_no_total(async_session: AsyncSession) -> None:
    """Support count customization and no-total requests asynchronously."""
    await _seed_async(async_session)
    count_query = select(func.count()).select_from(Widget).where(Widget.id < CUSTOM_TOTAL)
    prohibited_count_query = cast("Select[tuple[int]]", select(text("missing_count_column")))

    custom = await apaginate(
        async_session,
        _ordered_widgets(),
        CursorParams(size=PAGE_SIZE),
        count_query=count_query,
    )
    without_total = await apaginate(
        async_session,
        _ordered_widgets(),
        NoTotalParams(size=PAGE_SIZE),
        count_query=prohibited_count_query,
    )

    async_session.add_all([
        WidgetNote(id=1, widget_id=1),
        WidgetNote(id=2, widget_id=1),
        WidgetNote(id=3, widget_id=2),
    ])
    await async_session.commit()
    joined = await apaginate(
        async_session,
        select(Widget).options(joinedload(Widget.notes)).order_by(Widget.id),
        CursorParams(size=len(ALL_IDS)),
    )

    assert custom.total == PAGE_SIZE
    assert without_total.total is None
    assert _page_ids(joined) == ALL_IDS


async def test_async_invalid_sqlakeyset_bookmark_is_a_validation_error(async_session: AsyncSession) -> None:
    """Map an async invalid bookmark to the same native validation response."""
    await _seed_async(async_session)

    with pytest.raises(ValidationException, match="Invalid cursor") as error:
        await apaginate(
            async_session,
            _ordered_widgets(),
            CursorParams(cursor=encode_cursor(">x:1"), size=PAGE_SIZE),
        )

    assert error.value.status_code == BAD_REQUEST
