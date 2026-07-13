"""
test_auth_service.py
--------------------
Unit tests for AuthService business logic.

These tests stub the repository layer directly — no database required.
They verify the service's internal guard logic in isolation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.exceptions.base import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.services.auth_service import AuthService


def build_user(**overrides) -> User:
    user = User(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        password_hash="hashed-password",
        is_active=True,
        is_verified=False,
    )
    user.id = uuid4()
    user.deleted_at = None
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


def test_get_authenticated_user_returns_active_user() -> None:
    service = AuthService(session=object())
    user = build_user()
    service.user_repo.get_by_id = lambda user_id: user  # type: ignore[assignment]

    result = service.get_authenticated_user(user_id=str(user.id))

    assert result is user


def test_get_authenticated_user_rejects_deleted_user() -> None:
    service = AuthService(session=object())
    user = build_user(deleted_at=datetime.now(timezone.utc))
    service.user_repo.get_by_id = lambda user_id: user  # type: ignore[assignment]

    with pytest.raises(ForbiddenException):
        service.get_authenticated_user(user_id=str(user.id))


def test_get_authenticated_user_rejects_inactive_user() -> None:
    service = AuthService(session=object())
    user = build_user(is_active=False)
    service.user_repo.get_by_id = lambda user_id: user  # type: ignore[assignment]

    with pytest.raises(ForbiddenException):
        service.get_authenticated_user(user_id=str(user.id))


def test_get_authenticated_user_rejects_missing_user() -> None:
    service = AuthService(session=object())
    service.user_repo.get_by_id = lambda user_id: None  # type: ignore[assignment]

    with pytest.raises(UnauthorizedException):
        service.get_authenticated_user(user_id=str(uuid4()))


def test_get_authenticated_user_rejects_invalid_uuid() -> None:
    service = AuthService(session=object())

    with pytest.raises(UnauthorizedException):
        service.get_authenticated_user(user_id="not-a-uuid")
