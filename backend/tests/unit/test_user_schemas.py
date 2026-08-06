"""Tests for app/presentation/api/v1/schemas/user.py."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums.user_status import UserStatus
from app.presentation.api.v1.schemas.user import (
    UserCreate,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
)


def test_user_create_accepts_valid_input() -> None:
    schema = UserCreate(email="test@example.com", full_name="Test User", google_sub_id="sub-123")
    assert schema.email == "test@example.com"


def test_user_create_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", full_name="Test User", google_sub_id="sub-123")


def test_user_create_rejects_empty_full_name() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="test@example.com", full_name="", google_sub_id="sub-123")


def test_user_update_accepts_valid_full_name() -> None:
    schema = UserUpdate(full_name="New Name")
    assert schema.full_name == "New Name"


def test_user_update_rejects_empty_full_name() -> None:
    with pytest.raises(ValidationError):
        UserUpdate(full_name="")


def test_user_status_update_accepts_valid_status() -> None:
    schema = UserStatusUpdate(status=UserStatus.INACTIVE)
    assert schema.status == UserStatus.INACTIVE


def test_user_status_update_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        UserStatusUpdate(status="not-a-real-status")  # type: ignore[arg-type]


def test_user_read_excludes_google_sub_id() -> None:
    """The whole point of UserRead being a distinct schema from the domain
    entity: google_sub_id must never appear in it, even if someone tries
    to construct it from an object that has one."""
    payload = {
        "id": uuid4(),
        "email": "test@example.com",
        "full_name": "Test User",
        "status": UserStatus.ACTIVE,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    schema = UserRead(**payload)
    assert "google_sub_id" not in schema.model_dump()


def test_user_read_from_attributes_works_with_domain_entity() -> None:
    """UserRead must be constructible directly from a domain entity via
    from_attributes — this is how a router turns a User into a response
    without manually copying each field."""
    from app.domain.entities.user import User

    entity = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        google_sub_id="sub-123",
        status=UserStatus.ACTIVE,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    schema = UserRead.model_validate(entity)
    assert schema.email == entity.email
    assert "google_sub_id" not in schema.model_dump()
