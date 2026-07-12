from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.exceptions.base import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest


class AuthService:
    """Authentication business logic for login and token issuance."""

    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def login(self, *, payload: LoginRequest) -> dict[str, object]:
        """Authenticate a user and return a signed access token payload."""
        normalized_email = str(payload.email).lower()
        user = self.repository.get_by_email(email=normalized_email)
        if user is None:
            raise UnauthorizedException(message="Invalid email or password.")

        if not verify_password(plain_password=payload.password, hashed_password=user.password_hash):
            raise UnauthorizedException(message="Invalid email or password.")

        if not user.is_active:
            raise ForbiddenException(message="User account is inactive.")

        token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    def get_user_by_email(self, *, email: str) -> User | None:
        """Fetch a user by email for authentication checks."""
        return self.repository.get_by_email(email=email)
