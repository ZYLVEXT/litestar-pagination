"""Storage-independent cursor pagination contracts."""

from __future__ import annotations

from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from collections.abc import Sequence  # noqa: TC003 - Litestar resolves dataclass annotations at runtime.
from dataclasses import dataclass
from typing import Annotated, ClassVar
from urllib.parse import quote, unquote

from litestar.exceptions import ValidationException
from litestar.params import QueryParameter


@dataclass
class CursorParams:
    """Query parameters for cursor pagination."""

    cursor: Annotated[str | None, QueryParameter(name="cursor", required=False)] = None
    size: Annotated[int, QueryParameter(name="size", ge=1, le=100, required=False)] = 50
    include_total: ClassVar[bool] = True


@dataclass
class CursorPage[T]:
    """A page of items and opaque navigation bookmarks."""

    items: Sequence[T]
    total: int | None
    current_page: str | None
    current_page_backwards: str | None
    previous_page: str | None
    next_page: str | None


def decode_cursor(cursor: str | None) -> str | None:
    """Decode a client cursor or raise Litestar's native validation error.

    Returns:
        The internal bookmark, or ``None`` for a first-page request.

    Raises:
        ValidationException: If ``cursor`` is not valid Base64-encoded UTF-8.
    """
    if not cursor:
        return None

    try:
        return b64decode(unquote(cursor).encode(), validate=True).decode()
    except (BinasciiError, UnicodeDecodeError) as exc:
        raise ValidationException(detail="Invalid cursor") from exc


def encode_cursor(cursor: str | None) -> str | None:
    """Encode an internal bookmark for use as a query parameter.

    Returns:
        An escaped Base64 cursor, or ``None`` when no bookmark exists.
    """
    if cursor is None:
        return None

    return quote(b64encode(cursor.encode()).decode())
