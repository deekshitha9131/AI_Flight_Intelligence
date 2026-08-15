import logging
from collections.abc import Generator
from typing import Any

from app.core.config import get_settings
from app.database.base import Base
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine: Engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True if not settings.database_url.startswith("sqlite") else False,
    pool_recycle=1800 if not settings.database_url.startswith("sqlite") else -1,
    echo=settings.environment == "development",
    future=True,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependency injection.

    The session is automatically closed after use, and any exception triggers a
    rollback so the transaction state remains consistent.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """Execute a lightweight SELECT 1 probe against the configured database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection check failed: %s", exc)
        return False

