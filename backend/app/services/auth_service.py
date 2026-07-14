from __future__ import annotations

from uuid import UUID

from app.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.auth.password import verify_password
from app.exceptions.base import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.refresh_token_repository import (
    RefreshTokenRepository,
    hash_refresh_token,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest
from sqlalchemy.orm import Session


class AuthService:
    """Authentication business logic for login, token issuance, and rotation."""

    def __init__(self, session: Session) -> None:
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    def login(
        self,
        *,
        payload: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, object]:
        """Authenticate a user and return a signed access + refresh token pair."""
        normalized_email = str(payload.email).lower()
        user = self.user_repo.get_by_email(email=normalized_email)
        if user is None:
            raise UnauthorizedException(message="Invalid email or password.")

        if not verify_password(
            plain_password=payload.password, hashed_password=user.password_hash
        ):
            raise UnauthorizedException(message="Invalid email or password.")

        if not user.is_active:
            raise ForbiddenException(message="User account is inactive.")

        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
        )
        refresh_token, expires_at = create_refresh_token(user_id=str(user.id))

        self.token_repo.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    def refresh(self, *, refresh_token: str) -> dict[str, object]:
        """Validate a refresh token, rotate it, and return a new token pair."""
        try:
            payload = decode_refresh_token(token=refresh_token)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid refresh token.") from exc

        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException(message="Invalid refresh token.")

        token_hash = hash_refresh_token(refresh_token)
        record = self.token_repo.get_by_hash(token_hash=token_hash)

        if record is None or record.revoked_at is not None:
            raise UnauthorizedException(message="Invalid refresh token.")

        try:
            parsed_user_id = UUID(user_id_str)
        except ValueError as exc:
            raise UnauthorizedException(message="Invalid refresh token.") from exc

        user = self.user_repo.get_by_id(user_id=parsed_user_id)
        if user is None:
            raise UnauthorizedException(message="Invalid refresh token.")

        if not user.is_active or user.deleted_at is not None:
            raise ForbiddenException(message="User account is inactive.")

        # Revoke the consumed token before issuing a new pair (rotation)
        self.token_repo.revoke(record=record)

        new_access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
        )
        new_refresh_token, new_expires_at = create_refresh_token(user_id=str(user.id))

        self.token_repo.create(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=new_expires_at,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    def get_authenticated_user(self, *, user_id: str) -> User:
        """Return the authenticated user after validating account state."""
        try:
            parsed_user_id = UUID(user_id)
        except ValueError as exc:
            raise UnauthorizedException(message="Authentication failed.") from exc

        user = self.user_repo.get_by_id(user_id=parsed_user_id)
        if user is None:
            raise UnauthorizedException(message="Authentication failed.")

        if not user.is_active:
            raise ForbiddenException(message="User account is inactive.")

        if user.deleted_at is not None:
            raise ForbiddenException(message="User account is inactive.")

        return user

    def get_user_by_email(self, *, email: str) -> User | None:
        """Fetch a user by email for authentication checks."""
        return self.user_repo.get_by_email(email=email)
