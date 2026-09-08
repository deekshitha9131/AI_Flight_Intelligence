from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def create_db_engine(settings: Settings) -> AsyncEngine:

    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )


async def dispose_engine(engine: AsyncEngine) -> None:

    await engine.dispose()
