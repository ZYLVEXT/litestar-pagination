"""SQLAlchemy cursor pagination backed by :mod:`sqlakeyset`."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from litestar.pagination import AbstractAsyncCursorPaginator, AbstractSyncCursorPaginator
from sqlakeyset import BadBookmark, InvalidPage, Page, select_page
from sqlakeyset.asyncio import select_page as aselect_page
from sqlalchemy import func, select
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import noload
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from sqlalchemy.engine import Row
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

from litestar.exceptions import ValidationException

from litestar_pagination.cursor import CursorPage, CursorParams, decode_cursor, encode_cursor

__all__ = (
    "SQLAlchemyAsyncCursorPaginator",
    "SQLAlchemySyncCursorPaginator",
    "apaginate",
    "paginate",
)


class _NoTotalCursorParams(CursorParams):
    """Cursor parameters for Litestar's forward-only paginator contract."""

    include_total: ClassVar[bool] = False


class SQLAlchemySyncCursorPaginator[T](AbstractSyncCursorPaginator[str, T]):
    """Expose an ordered SQLAlchemy select through Litestar's native cursor paginator."""

    def __init__(self, session: Session, statement: Select[tuple[T]], *, unique: bool = True) -> None:
        """Create a forward-only Litestar paginator.

        Args:
            session: The SQLAlchemy session that executes keyset queries.
            statement: An ordered ``select(Model)`` statement.
            unique: Whether ``sqlakeyset`` should uniquify ORM rows.
        """
        self._session = session
        self._statement = statement
        self._unique = unique

    def get_items(self, cursor: str | None, results_per_page: int) -> tuple[list[T], str | None]:
        """Return one forward page in Litestar's paginator shape.

        Args:
            cursor: An opaque bookmark from the preceding page.
            results_per_page: The maximum number of items to return.

        Returns:
            The entity instances and their next-page cursor.
        """
        page = paginate(
            self._session,
            self._statement,
            _NoTotalCursorParams(cursor=cursor, size=results_per_page),
            unique=self._unique,
        )
        return list(page.items), page.next_page


class SQLAlchemyAsyncCursorPaginator[T](AbstractAsyncCursorPaginator[str, T]):
    """Expose an ordered SQLAlchemy select through Litestar's async cursor paginator."""

    def __init__(self, session: AsyncSession, statement: Select[tuple[T]], *, unique: bool = True) -> None:
        """Create a forward-only asynchronous Litestar paginator.

        Args:
            session: The SQLAlchemy asynchronous session that executes keyset queries.
            statement: An ordered ``select(Model)`` statement.
            unique: Whether ``sqlakeyset`` should uniquify ORM rows.
        """
        self._session = session
        self._statement = statement
        self._unique = unique

    async def get_items(self, cursor: str | None, results_per_page: int) -> tuple[list[T], str | None]:
        """Return one forward page in Litestar's paginator shape.

        Args:
            cursor: An opaque bookmark from the preceding page.
            results_per_page: The maximum number of items to return.

        Returns:
            The entity instances and their next-page cursor.
        """
        page = await apaginate(
            self._session,
            self._statement,
            _NoTotalCursorParams(cursor=cursor, size=results_per_page),
            unique=self._unique,
        )
        return list(page.items), page.next_page


def paginate[T](
    session: Session,
    statement: Select[tuple[T]],
    params: CursorParams,
    *,
    count_query: Select[tuple[int]] | None = None,
    unique: bool = True,
) -> CursorPage[T]:
    """Paginate one ordered ORM entity select with a synchronous session.

    Args:
        session: The SQLAlchemy session that executes the queries.
        statement: An ordered ``select(Model)`` statement.
        params: Cursor query parameters resolved by Litestar.
        count_query: Optional query that returns the total item count.
        unique: Whether ``sqlakeyset`` should uniquify ORM rows.

    Returns:
        The requested cursor page.

    Raises:
        ValidationException: If the supplied cursor is invalid.
    """
    _validate_statement(statement)
    cursor = decode_cursor(params.cursor)
    total = _sync_total(session, statement, params, count_query)

    try:
        page = select_page(session, statement, page=cursor, per_page=params.size, unique=unique)
    except (ArgumentError, BadBookmark, InvalidPage) as exc:
        raise ValidationException(detail="Invalid cursor") from exc

    return _cursor_page(page, total)


async def apaginate[T](
    session: AsyncSession,
    statement: Select[tuple[T]],
    params: CursorParams,
    *,
    count_query: Select[tuple[int]] | None = None,
    unique: bool = True,
) -> CursorPage[T]:
    """Paginate one ordered ORM entity select with an asynchronous session.

    Args:
        session: The SQLAlchemy asynchronous session that executes the queries.
        statement: An ordered ``select(Model)`` statement.
        params: Cursor query parameters resolved by Litestar.
        count_query: Optional query that returns the total item count.
        unique: Whether ``sqlakeyset`` should uniquify ORM rows.

    Returns:
        The requested cursor page.

    Raises:
        ValidationException: If the supplied cursor is invalid.
    """
    _validate_statement(statement)
    cursor = decode_cursor(params.cursor)
    total = await _async_total(session, statement, params, count_query)

    try:
        page = await aselect_page(session, statement, page=cursor, per_page=params.size, unique=unique)
    except (ArgumentError, BadBookmark, InvalidPage) as exc:
        raise ValidationException(detail="Invalid cursor") from exc

    return _cursor_page(page, total)


def _validate_statement[T](statement: Select[tuple[T]]) -> None:
    """Reject unsupported result shapes before querying the database.

    Raises:
        TypeError: If the statement is not a one-entity ``Select``.
        ValueError: If the statement has no explicit ordering.
    """
    if not isinstance(statement, Select):
        message = "Cursor pagination requires a SQLAlchemy Select statement."
        raise TypeError(message)
    if not statement._order_by_clauses:  # noqa: SLF001 - SQLAlchemy exposes no public ORDER BY inspector.
        message = "Cursor pagination requires ordering"
        raise ValueError(message)

    descriptions = statement.column_descriptions
    if len(descriptions) != 1:
        message = "Cursor pagination requires a Select of exactly one mapped ORM entity."
        raise TypeError(message)

    description = descriptions[0]
    entity = description["entity"]
    if entity is None or description["aliased"] or description["expr"] is not entity:
        message = "Cursor pagination requires a Select of exactly one mapped ORM entity."
        raise TypeError(message)


def _default_count_query[T](statement: Select[tuple[T]]) -> Select[tuple[int]]:
    """Count the filtered result without ordering or eager relationship loading.

    Returns:
        A scalar count statement over the filtered select.
    """
    return select(func.count()).select_from(statement.order_by(None).options(noload("*")).subquery())


def _sync_total[T](
    session: Session,
    statement: Select[tuple[T]],
    params: CursorParams,
    count_query: Select[tuple[int]] | None,
) -> int | None:
    """Execute the optional synchronous total count.

    Returns:
        The count, or ``None`` when totals are disabled.
    """
    if not params.include_total:
        return None

    query = count_query if count_query is not None else _default_count_query(statement)
    return int(session.scalar(query) or 0)


async def _async_total[T](
    session: AsyncSession,
    statement: Select[tuple[T]],
    params: CursorParams,
    count_query: Select[tuple[int]] | None,
) -> int | None:
    """Execute the optional asynchronous total count.

    Returns:
        The count, or ``None`` when totals are disabled.
    """
    if not params.include_total:
        return None

    query = count_query if count_query is not None else _default_count_query(statement)
    return int(await session.scalar(query) or 0)


def _cursor_page[T](page: Page[Row[tuple[T]]], total: int | None) -> CursorPage[T]:
    """Unwrap ORM entities and expose encoded sqlakeyset navigation bookmarks.

    Returns:
        A storage-independent page response.
    """
    paging = page.paging
    return CursorPage(
        items=[row[0] for row in page],
        total=total,
        current_page=encode_cursor(paging.bookmark_current_forwards),
        current_page_backwards=encode_cursor(paging.bookmark_current_backwards),
        previous_page=encode_cursor(paging.bookmark_previous) if paging.has_previous else None,
        next_page=encode_cursor(paging.bookmark_next) if paging.has_next else None,
    )
