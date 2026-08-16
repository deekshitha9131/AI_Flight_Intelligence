from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from app.auth.password import hash_password, verify_password
from app.exceptions.base import (
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from sqlalchemy.orm import Session


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

    def update_user_profile(self, *, user_id: UUID, payload: UserUpdate) -> User:
        """Partially update the authenticated user's profile and preferences."""
        user = self.get_user_profile(user_id=user_id)
        changes = payload.model_dump(exclude_unset=True)
        updates: dict[str, object] = {}

        if "first_name" in changes and changes["first_name"] is not None:
            updates["first_name"] = str(changes["first_name"]).strip()
        if "last_name" in changes and changes["last_name"] is not None:
            updates["last_name"] = str(changes["last_name"]).strip()
        if "phone_number" in changes:
            updates["phone_number"] = changes["phone_number"]
        if "profile_image" in changes:
            updates["profile_image"] = changes["profile_image"]
        if "preferred_airport" in changes and changes["preferred_airport"] is not None:
            updates["preferred_airport"] = str(changes["preferred_airport"]).upper()
        if "preferred_cabin" in changes and changes["preferred_cabin"] is not None:
            updates["preferred_cabin"] = str(changes["preferred_cabin"]).upper()
        if (
            "currency_preference" in changes
            and changes["currency_preference"] is not None
        ):
            updates["currency_preference"] = str(
                changes["currency_preference"]
            ).upper()
        if "notification_settings" in changes:
            updates["notification_settings"] = json.dumps(
                changes["notification_settings"]
            )
        if "is_active" in changes:
            updates["is_active"] = changes["is_active"]
        if "is_verified" in changes:
            updates["is_verified"] = changes["is_verified"]
        if "role" in changes and changes["role"] is not None:
            role_val = (
                changes["role"].value
                if hasattr(changes["role"], "value")
                else changes["role"]
            )
            updates["role"] = role_val

        return self.repository.update_user(user=user, updates=updates)

    def change_password(
        self, *, user_id: UUID, current_password: str, new_password: str
    ) -> User:
        """Validate current password and update persistent record."""
        user = self.get_user_profile(user_id=user_id)
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedException(message="Current password is incorrect.")

        UserCreate.validate_password(new_password)
        new_hash = hash_password(new_password)
        return self.repository.update_user(
            user=user, updates={"password_hash": new_hash}
        )
