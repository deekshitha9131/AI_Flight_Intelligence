"""Integration tests for the database layer — Base, mixins, and pgvector
against a real PostgreSQL instance.

Requires DATABASE_URL to point at a reachable pgvector-enabled Postgres
(the docker-compose `postgres` service, or CI's service container).
Skips gracefully via the `db_engine` fixture (tests/conftest.py) when
none is reachable — this is expected and correct outside `docker
compose up` or CI, not a failure.
"""

import uuid

import pytest
from sqlalchemy import String, select, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.infrastructure.vector.types import embedding_column

pytestmark = pytest.mark.integration


class _IntegrationCheckModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A throwaway table, created and dropped within this test module only —
    never part of the application's real schema. Exercises the exact
    same base class, mixins, and pgvector column type real models will
    use once they exist."""

    __tablename__ = "_integration_check_model"

    label: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float] | None] = embedding_column()


@pytest.fixture
async def prepared_db(db_engine: AsyncEngine):
    async with db_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all, tables=[_IntegrationCheckModel.__table__])
    yield db_engine
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=[_IntegrationCheckModel.__table__])


async def test_uuid_primary_key_is_generated_client_side(prepared_db: AsyncEngine) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=prepared_db, expire_on_commit=False)
    async with session_factory() as session:
        row = _IntegrationCheckModel(label="test-row")
        assert row.id is not None  # generated at construction, before insert
        session.add(row)
        await session.commit()

        result = await session.execute(
            select(_IntegrationCheckModel).where(_IntegrationCheckModel.id == row.id)
        )
        fetched = result.scalar_one()
        assert fetched.label == "test-row"
        assert isinstance(fetched.id, uuid.UUID)


async def test_timestamps_are_server_generated(prepared_db: AsyncEngine) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=prepared_db, expire_on_commit=False)
    async with session_factory() as session:
        row = _IntegrationCheckModel(label="timestamp-test")
        session.add(row)
        await session.commit()
        await session.refresh(row)

        assert row.created_at is not None
        assert row.updated_at is not None


async def test_embedding_column_stores_and_retrieves_vector(prepared_db: AsyncEngine) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.constants import EMBEDDING_DIMENSIONS

    session_factory = async_sessionmaker(bind=prepared_db, expire_on_commit=False)
    vector = [0.1] * EMBEDDING_DIMENSIONS

    async with session_factory() as session:
        row = _IntegrationCheckModel(label="vector-test", embedding=vector)
        session.add(row)
        await session.commit()

        result = await session.execute(
            select(_IntegrationCheckModel).where(_IntegrationCheckModel.id == row.id)
        )
        fetched = result.scalar_one()
        assert fetched.embedding is not None
        assert len(fetched.embedding) == EMBEDDING_DIMENSIONS
