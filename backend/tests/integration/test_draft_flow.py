import uuid
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.ai.context.draft_context import DraftContext
from app.core.di_container import get_current_user, get_draft_generator, get_retrieval_service
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.ai import AIProviderError
from app.infrastructure.database.base import Base
from app.infrastructure.database.models.attachment import AttachmentModel
from app.infrastructure.database.models.draft import DraftModel
from app.infrastructure.database.models.email import EmailModel
from app.infrastructure.database.models.email_ai_understanding import EmailAIUnderstandingModel
from app.infrastructure.database.models.thread import ThreadModel
from app.infrastructure.database.models.user import UserModel

pytestmark = pytest.mark.integration

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
async def prepared_db(db_engine: AsyncEngine):
    async with db_engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                UserModel.__table__,
                ThreadModel.__table__,
                EmailModel.__table__,
                AttachmentModel.__table__,
                EmailAIUnderstandingModel.__table__,
                DraftModel.__table__,
            ],
        )
    yield db_engine
    async with db_engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.drop_all,
            tables=[
                DraftModel.__table__,
                EmailAIUnderstandingModel.__table__,
                AttachmentModel.__table__,
                EmailModel.__table__,
                ThreadModel.__table__,
                UserModel.__table__,
            ],
        )
        await conn.execute(text("DROP TYPE IF EXISTS user_status"))
        await conn.execute(text("DROP TYPE IF EXISTS draft_status"))


@pytest.fixture
def session_factory(prepared_db: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(bind=prepared_db, expire_on_commit=False)


def _entity_user(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        full_name=model.full_name,
        google_sub_id=model.google_sub_id,
        status=UserStatus.ACTIVE,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


async def _create_user_thread_email(
    session_factory: async_sessionmaker, *, with_understanding: bool = True
) -> tuple[User, uuid.UUID]:
    async with session_factory() as session:
        user_model = UserModel(
            email=f"{uuid.uuid4()}@example.com",
            full_name="Draft Flow Test User",
            google_sub_id=f"sub-{uuid.uuid4()}",
        )
        session.add(user_model)
        await session.commit()
        await session.refresh(user_model)

        thread = ThreadModel(
            user_id=user_model.id, gmail_thread_id=f"thread-{uuid.uuid4()}", subject="s", snippet="sn"
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

        email = EmailModel(
            thread_id=thread.id,
            user_id=user_model.id,
            gmail_message_id=f"msg-{uuid.uuid4()}",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            cc=[],
            bcc=[],
            subject="Flight Cancelled",
            snippet="Your flight has been cancelled",
            body_text="Your flight booking has been cancelled. Please contact us immediately.",
            received_at=_BASE_TIME,
            label_ids=[],
        )
        session.add(email)
        await session.commit()
        await session.refresh(email)

        if with_understanding:
            understanding = EmailAIUnderstandingModel(
                email_id=email.id,
                category="travel",
                intent="cancellation",
                urgency="high",
                sentiment="negative",
                entities=[{"type": "organization", "value": "Delta Airlines"}],
                summary="Flight booking was cancelled.",
                confidence=0.94,
            )
            session.add(understanding)
            await session.commit()

        return _entity_user(user_model), email.id


class FakeRetrievalService:
    async def retrieve_relevant_chunks(self, user, *, query, top_k=5):
        return []


class FakeDraftGenerator:
    def __init__(
        self,
        *,
        text: str = "Thank you for letting us know. We're sorry for the "
        "inconvenience and will assist with rebooking.",
        raise_error: Exception | None = None,
    ) -> None:
        self._text = text
        self._raise_error = raise_error

    async def generate(self, context: DraftContext) -> str:
        if self._raise_error is not None:
            raise self._raise_error
        return self._text


def _override(app: FastAPI, *, user: User, draft_generator: FakeDraftGenerator | None = None) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_draft_generator] = lambda: (draft_generator or FakeDraftGenerator())

async def test_successful_draft_flow(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user, email_id = await _create_user_thread_email(session_factory)
    _override(
        app_no_lifespan,
        user=user,
        draft_generator=FakeDraftGenerator(text="Sounds good, we'll follow up shortly."),
    )

    response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id)})

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["email_id"] == str(email_id)
    assert body["body"] == "Sounds good, we'll follow up shortly."
    assert body["status"] == "generated"

    app_no_lifespan.dependency_overrides.clear()

async def test_retrieve_created_draft(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user, email_id = await _create_user_thread_email(session_factory)
    _override(
        app_no_lifespan, user=user, draft_generator=FakeDraftGenerator(text="Distinctive persisted content.")
    )

    create_response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id)})
    draft_id = create_response.json()["id"]

    get_response = integration_client.get(f"/api/v1/drafts/{draft_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["id"] == draft_id
    assert body["body"] == "Distinctive persisted content."
    assert body["email_id"] == str(email_id)

    app_no_lifespan.dependency_overrides.clear()

async def test_user_cannot_generate_draft_for_another_users_email(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user_a, _ = await _create_user_thread_email(session_factory)
    _, email_id_b = await _create_user_thread_email(session_factory)

    _override(app_no_lifespan, user=user_a)

    response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id_b)})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMAIL_NOT_FOUND"

    app_no_lifespan.dependency_overrides.clear()


async def test_user_cannot_retrieve_another_users_draft(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user_a, email_id_a = await _create_user_thread_email(session_factory)
    user_b, _ = await _create_user_thread_email(session_factory)

    _override(app_no_lifespan, user=user_a)
    create_response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id_a)})
    draft_id = create_response.json()["id"]

    _override(app_no_lifespan, user=user_b)
    response = integration_client.get(f"/api/v1/drafts/{draft_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DRAFT_NOT_FOUND"

    app_no_lifespan.dependency_overrides.clear()

async def test_generation_failure_does_not_persist_a_draft(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user, email_id = await _create_user_thread_email(session_factory)
    _override(
        app_no_lifespan,
        user=user,
        draft_generator=FakeDraftGenerator(raise_error=AIProviderError("LLM call failed.")),
    )

    response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id)})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_PROVIDER_ERROR"

    async with session_factory() as session:
        count = (
            await session.execute(
                select(func.count()).select_from(DraftModel).where(DraftModel.email_id == email_id)
            )
        ).scalar_one()
    assert count == 0

    app_no_lifespan.dependency_overrides.clear()


async def test_missing_understanding_returns_409_and_persists_nothing(
    app_no_lifespan: FastAPI, integration_client: TestClient, session_factory
) -> None:
    user, email_id = await _create_user_thread_email(session_factory, with_understanding=False)
    _override(app_no_lifespan, user=user)

    response = integration_client.post("/api/v1/drafts", json={"email_id": str(email_id)})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DRAFT_UNDERSTANDING_MISSING"

    async with session_factory() as session:
        count = (
            await session.execute(
                select(func.count()).select_from(DraftModel).where(DraftModel.email_id == email_id)
            )
        ).scalar_one()
    assert count == 0

    app_no_lifespan.dependency_overrides.clear()