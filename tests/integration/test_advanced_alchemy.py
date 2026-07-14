"""Advanced Alchemy compatibility tests without package-specific plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from advanced_alchemy.base import UUIDAuditBase
from advanced_alchemy.config import SQLAlchemyAsyncConfig, SQLAlchemySyncConfig
from advanced_alchemy.extensions.litestar.dto import SQLAlchemyDTO
from litestar import Litestar, get
from litestar.di import NamedDependency, Provide
from litestar.testing import TestClient
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from litestar_pagination import CursorPage, CursorParams
from litestar_pagination.ext.sqlalchemy import apaginate, paginate

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

PAGE_SIZE = 1
OK = 200
TOTAL_WIDGETS = 2
FIRST_ID = UUID(int=1)
SECOND_ID = UUID(int=2)


class AdvancedAlchemyWidget(UUIDAuditBase):
    """An Advanced Alchemy model base used through the plain adapter API."""

    __tablename__ = "advanced_alchemy_widgets"

    name: Mapped[str] = mapped_column(String, nullable=False)


def _add_widgets(session: Session) -> None:
    """Insert deterministic UUID-keyed entities into a synchronous session."""
    session.add_all([
        AdvancedAlchemyWidget(id=FIRST_ID, name="Ada"),
        AdvancedAlchemyWidget(id=SECOND_ID, name="Grace"),
    ])
    session.commit()


def test_advanced_alchemy_sync_session_works_unchanged(tmp_path: Path) -> None:
    """Consume a session yielded by Advanced Alchemy without a plugin or mixin."""
    config = SQLAlchemySyncConfig(connection_string=f"sqlite:///{tmp_path / 'advanced-alchemy.db'}")
    engine = config.get_engine()
    AdvancedAlchemyWidget.metadata.create_all(engine)

    try:
        with config.create_session_maker()() as session:
            _add_widgets(session)
            page = paginate(
                session, select(AdvancedAlchemyWidget).order_by(AdvancedAlchemyWidget.id), CursorParams(size=PAGE_SIZE)
            )

        assert [item.id for item in page.items] == [FIRST_ID]
        assert page.total == TOTAL_WIDGETS
    finally:
        engine.dispose()


async def test_advanced_alchemy_async_session_works_unchanged(tmp_path: Path) -> None:
    """Consume an asynchronous session yielded by Advanced Alchemy unchanged."""
    config = SQLAlchemyAsyncConfig(connection_string=f"sqlite+aiosqlite:///{tmp_path / 'advanced-alchemy.db'}")
    engine = config.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(AdvancedAlchemyWidget.metadata.create_all)

    try:
        async with config.create_session_maker()() as session:
            session.add_all([
                AdvancedAlchemyWidget(id=FIRST_ID, name="Ada"),
                AdvancedAlchemyWidget(id=SECOND_ID, name="Grace"),
            ])
            await session.commit()
            page = await apaginate(
                session,
                select(AdvancedAlchemyWidget).order_by(AdvancedAlchemyWidget.id),
                CursorParams(size=PAGE_SIZE),
            )

        assert [item.id for item in page.items] == [FIRST_ID]
        assert page.total == TOTAL_WIDGETS
    finally:
        await engine.dispose()


def test_sqlalchemy_dto_transforms_advanced_alchemy_model_items(tmp_path: Path) -> None:
    """Apply ``SQLAlchemyDTO`` to entities inside the generic page wrapper."""
    config = SQLAlchemySyncConfig(connection_string=f"sqlite:///{tmp_path / 'advanced-alchemy-dto.db'}")
    engine = config.get_engine()
    AdvancedAlchemyWidget.metadata.create_all(engine)

    try:
        with config.create_session_maker()() as session:
            _add_widgets(session)

            @get("/widgets", return_dto=SQLAlchemyDTO[AdvancedAlchemyWidget], sync_to_thread=False)
            def list_widgets(pagination: NamedDependency[CursorParams]) -> CursorPage[AdvancedAlchemyWidget]:
                """Return an Advanced Alchemy model page through its native DTO."""
                return paginate(
                    session,
                    select(AdvancedAlchemyWidget).order_by(AdvancedAlchemyWidget.id),
                    pagination,
                )

            app = Litestar(
                route_handlers=[list_widgets],
                dependencies={"pagination": Provide(CursorParams, sync_to_thread=False)},
            )
            with TestClient(app) as client:
                response = client.get("/widgets", params={"size": PAGE_SIZE})

        assert response.status_code == OK
        assert response.json()["items"][0]["id"] == str(FIRST_ID)
        assert response.json()["items"][0]["name"] == "Ada"
    finally:
        engine.dispose()
