from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.models.user import User, UserRole
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    """Repository layer for user persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_user(self, *, user: User) -> User:
        """Persist a new user in the database."""
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_email(self, *, email: str) -> User | None:
        """Return a user by email, if present."""
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)

    def get_by_id(self, *, user_id: UUID) -> User | None:
        """Return a user by identifier, if present."""
        statement = select(User).where(User.id == user_id)
        return self.session.scalar(statement)

    def update_user(self, *, user: User, updates: dict[str, Any]) -> User:
        """Apply field updates to an existing user."""
        for field, value in updates.items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        self.session.flush()
        return user

    def soft_delete_user(self, *, user: User) -> User:
        """Mark a user as deleted without removing the row."""
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        self.session.add(user)
        self.session.flush()
        return user
