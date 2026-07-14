"""Core cursor contract tests."""

from __future__ import annotations

from dataclasses import asdict

import pytest
from litestar.exceptions import ValidationException

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.cursor import decode_cursor, encode_cursor

pytestmark = pytest.mark.unit

DEFAULT_SIZE = 50
BAD_REQUEST = 400


def test_default_params() -> None:
    """Expose the documented defaults without making total a query field."""
    params = CursorParams()

    assert params.cursor is None
    assert params.size == DEFAULT_SIZE
    assert params.include_total is True
    assert "include_total" not in asdict(params)


@pytest.mark.parametrize("bookmark", [">i:42", "<dt:2026-07-14~i:42"])
def test_cursor_round_trip(bookmark: str) -> None:
    """Preserve sqlakeyset bookmarks through the external representation."""
    assert decode_cursor(encode_cursor(bookmark)) == bookmark


def test_empty_cursor_is_an_absent_cursor() -> None:
    """Match fastapi-pagination's first-page behavior for an empty query value."""
    assert decode_cursor("") is None
    assert decode_cursor(None) is None
    assert encode_cursor(None) is None


@pytest.mark.parametrize("cursor", ["%%%", "/w==", "aW52YWxpZC0"])
def test_invalid_cursor_is_a_validation_error(cursor: str) -> None:
    """Reject malformed Base64 and non-UTF-8 payloads at the client boundary."""
    with pytest.raises(ValidationException, match="Invalid cursor") as error:
        decode_cursor(cursor)

    assert error.value.status_code == BAD_REQUEST


def test_page_is_a_dataclass_serialization_contract() -> None:
    """Keep the stable response field names and nullable totals."""
    page = CursorPage(
        items=("Ada",),
        total=None,
        current_page="current",
        current_page_backwards="backwards",
        previous_page=None,
        next_page="next",
    )

    assert asdict(page) == {
        "items": ("Ada",),
        "total": None,
        "current_page": "current",
        "current_page_backwards": "backwards",
        "previous_page": None,
        "next_page": "next",
    }
