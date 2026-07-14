from collections.abc import Generator

from app.database.session import SessionLocal
from sqlalchemy.orm import Session


def get_db_session() -> Generator[Session, None, None]:
    """Provide a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
