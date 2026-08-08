import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.engine import create_db_engine
from app.infrastructure.database.models.attachment import AttachmentModel
from app.infrastructure.database.models.email import EmailModel
from app.infrastructure.database.models.thread import ThreadModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.email_repository import EmailRepository


async def main() -> None:
    settings = get_settings()
    engine = create_db_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.drop_all,
            tables=[
                AttachmentModel.__table__,
                EmailModel.__table__,
                ThreadModel.__table__,
                UserModel.__table__,
            ],
        )
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                UserModel.__table__,
                ThreadModel.__table__,
                EmailModel.__table__,
                AttachmentModel.__table__,
            ],
        )

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        user = UserModel(email="x@example.com", full_name="User", google_sub_id="sub-1")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        thread = ThreadModel(user_id=user.id, gmail_thread_id="t1", subject="s", snippet="sn")
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

        repo = EmailRepository(session)
        print("creating")
        created = await repo.create(
            thread_id=thread.id,
            user_id=user.id,
            gmail_message_id="m1",
            sender="s",
            recipients=["r"],
            received_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        print("created", created.id)
        print("fetching")
        fetched = await repo.get_by_id(created.id)
        print("fetched", fetched.id if fetched else None)

    await engine.dispose()


asyncio.run(main())
