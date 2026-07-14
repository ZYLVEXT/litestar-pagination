"""Litestar integration tests through the public package API."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest
from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO
from litestar import Controller, Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.pagination import CursorPagination  # noqa: TC002 - Litestar resolves handler annotations at runtime.
from litestar.testing import TestClient
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import SQLAlchemySyncCursorPaginator, paginate

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

pytestmark = pytest.mark.e2e

PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
TOO_LARGE_PAGE_SIZE = 101
BAD_REQUEST = 400
OK = 200
TOTAL_USERS = 2


class Base(DeclarativeBase):
    """Test declarative base."""


class User(Base):
    """A minimal ORM entity returned through a DTO."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


@pytest.fixture
def litestar_app(tmp_path: Path) -> Iterator[Litestar]:
    """Build a Litestar app with application-scoped cursor parameters.

    Yields:
        An application backed by a seeded SQLite session.
    """
    engine = create_engine(f"sqlite:///{tmp_path / 'litestar.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all([User(id=1, name="Ada"), User(id=2, name="Grace")])
    session.commit()

    @get("/users", return_dto=SQLAlchemyDTO[User], sync_to_thread=False)
    def list_users(pagination: NamedDependency[CursorParams]) -> CursorPage[User]:
        """Return a DTO-serialized cursor page."""
        return paginate(session, select(User).order_by(User.id), pagination)

    native_paginator = SQLAlchemySyncCursorPaginator(session, select(User).order_by(User.id))

    @get("/native-users", return_dto=SQLAlchemyDTO[User], sync_to_thread=False)
    def list_native_users(pagination: NamedDependency[CursorParams]) -> CursorPagination[str, User]:
        """Return Litestar's native forward-only cursor page."""
        return native_paginator(pagination.cursor, pagination.size)

    yield Litestar(
        route_handlers=[list_users, list_native_users],
        dependencies={"pagination": Provide(CursorParams, sync_to_thread=False)},
    )

    session.close()
    engine.dispose()


@get("/handler", dependencies={"pagination": Provide(CursorParams, sync_to_thread=False)}, sync_to_thread=False)
def handler_scoped(pagination: NamedDependency[CursorParams]) -> dict[str, int | str | None]:
    """Expose handler-scoped dependency values.

    Returns:
        The resolved cursor query parameters.
    """
    return {"cursor": pagination.cursor, "size": pagination.size}


class ControllerScoped(Controller):
    """Expose controller-scoped dependency values."""

    path = "/controller"
    dependencies = MappingProxyType({"pagination": Provide(CursorParams, sync_to_thread=False)})

    @get("/", sync_to_thread=False)
    def get_page(self, pagination: NamedDependency[CursorParams]) -> dict[str, int | str | None]:
        """Return resolved cursor parameters.

        Returns:
            The resolved cursor query parameters.
        """
        return {"cursor": pagination.cursor, "size": pagination.size}


def test_litestar_serializes_dto_items_and_validates_cursors(litestar_app: Litestar) -> None:
    """Use native DI, response serialization, and validation end to end."""
    with TestClient(litestar_app) as client:
        first = client.get("/users", params={"size": PAGE_SIZE})

        assert first.status_code == OK
        assert first.json()["items"] == [{"id": 1, "name": "Ada"}]
        assert first.json()["total"] == TOTAL_USERS
        assert first.json()["previous_page"] is None
        assert first.json()["next_page"] is not None

        second = client.get("/users", params={"size": PAGE_SIZE, "cursor": first.json()["next_page"]})
        invalid_cursor = client.get("/users", params={"cursor": "%%%"})

    assert second.status_code == OK
    assert second.json()["items"] == [{"id": 2, "name": "Grace"}]
    assert invalid_cursor.status_code == BAD_REQUEST


def test_litestar_validates_size_boundaries(litestar_app: Litestar) -> None:
    """Accept documented bounds and reject values outside the query contract."""
    with TestClient(litestar_app) as client:
        minimum = client.get("/users", params={"size": PAGE_SIZE})
        maximum = client.get("/users", params={"size": MAX_PAGE_SIZE})
        too_small = client.get("/users", params={"size": 0})
        too_large = client.get("/users", params={"size": TOO_LARGE_PAGE_SIZE})
        malformed = client.get("/users", params={"size": "not-an-integer"})

    assert minimum.status_code == OK
    assert maximum.status_code == OK
    assert too_small.status_code == BAD_REQUEST
    assert too_large.status_code == BAD_REQUEST
    assert malformed.status_code == BAD_REQUEST


def test_openapi_describes_params_and_page_fields(litestar_app: Litestar) -> None:
    """Publish the documented query constraints and response contract."""
    with TestClient(litestar_app) as client:
        schema = client.get("/schema/openapi.json").json()

    operation = schema["paths"]["/users"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    component_name = response_schema["$ref"].rsplit("/", maxsplit=1)[-1]
    fields = schema["components"]["schemas"][component_name]["properties"]
    native_fields = schema["paths"]["/native-users"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["properties"]

    assert set(parameters) == {"cursor", "size"}
    assert parameters["size"]["schema"] == {"type": "integer", "maximum": 100.0, "minimum": 1.0, "default": 50}
    assert set(fields) == {
        "items",
        "total",
        "current_page",
        "current_page_backwards",
        "previous_page",
        "next_page",
    }
    assert set(native_fields) == {"items", "results_per_page", "cursor"}


def test_native_litestar_paginator_uses_cursor_pagination(litestar_app: Litestar) -> None:
    """Return Litestar's built-in container through the SQLAlchemy paginator class."""
    with TestClient(litestar_app) as client:
        first = client.get("/native-users", params={"size": PAGE_SIZE})
        second = client.get("/native-users", params={"size": PAGE_SIZE, "cursor": first.json()["cursor"]})

    assert first.status_code == OK
    assert first.json()["items"] == [{"id": 1, "name": "Ada"}]
    assert first.json()["results_per_page"] == PAGE_SIZE
    assert first.json()["cursor"] is not None
    assert "total" not in first.json()
    assert second.json()["items"] == [{"id": 2, "name": "Grace"}]


def test_handler_and_controller_scoped_dependencies() -> None:
    """Resolve ordinary Litestar dependencies at narrower routing scopes."""
    app = Litestar(route_handlers=[handler_scoped, ControllerScoped])

    with TestClient(app) as client:
        handler_response = client.get("/handler", params={"cursor": "bookmark", "size": PAGE_SIZE})
        controller_response = client.get("/controller/", params={"size": PAGE_SIZE})

    assert handler_response.json() == {"cursor": "bookmark", "size": PAGE_SIZE}
    assert controller_response.json() == {"cursor": None, "size": PAGE_SIZE}
