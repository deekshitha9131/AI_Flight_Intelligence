from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.exceptions.base import NotFoundException, ValidationException
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Business logic for user registration and profile access."""

    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def register_user(self, *, payload: UserCreate) -> User:
        """Create a new user account after validating uniqueness rules."""
        normalized_email = str(payload.email).lower()
        if self.check_email_exists(email=normalized_email):
            raise ValidationException(message="Email already registered")

        user = User(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            email=normalized_email,
            password_hash=hash_password(payload.password),
            phone_number=payload.phone_number,
            profile_image=payload.profile_image,
            role=(
                payload.role.value
                if isinstance(payload.role, UserRole)
                else payload.role
            ),
            is_active=True,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return self.repository.create_user(user=user)

    def check_email_exists(self, *, email: str) -> bool:
        """Return True when a user already exists for the provided email."""
        return self.repository.get_by_email(email=email) is not None

    def get_user_profile(self, *, user_id: UUID) -> User:
        """Fetch a user profile by identifier."""
        user = self.repository.get_by_id(user_id=user_id)
        if user is None:
            raise NotFoundException(message="User not found")
        return user
