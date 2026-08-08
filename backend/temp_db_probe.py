import asyncio

from sqlalchemy import text

from app.core.config import Settings
from app.infrastructure.database.engine import create_db_engine, dispose_engine


async def main() -> None:
    settings = Settings()
    print("DATABASE_URL=", settings.database_url)
    engine = create_db_engine(settings)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("RESULT", result.scalar_one())
    except Exception as exc:  # noqa: BLE001
        print(type(exc).__name__, exc)
    finally:
        await dispose_engine(engine)


asyncio.run(main())
