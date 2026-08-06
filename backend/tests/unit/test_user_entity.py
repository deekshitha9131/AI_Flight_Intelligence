"""Tests for app/domain/entities/user.py.

No database, no FastAPI app, no mocks — this is exactly what "zero
framework dependency" in the domain layer buys: these tests construct
a User directly and assert on its behavior.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.base import BusinessValidationError


def _make_user(**overrides: object) -> User:
    defaults: dict = {
        "id": uuid4(),
        "email": "test@example.com",
        "full_name": "Test User",
        "google_sub_id": "google-sub-123",
        "status": UserStatus.ACTIVE,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "deleted_at": None,
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


def test_is_active_true_for_active_non_deleted_user() -> None:
    user = _make_user(status=UserStatus.ACTIVE, deleted_at=None)
    assert user.is_active is True


def test_is_active_false_for_inactive_user() -> None:
    user = _make_user(status=UserStatus.INACTIVE, deleted_at=None)
    assert user.is_active is False


def test_is_active_false_for_deleted_user_even_if_status_active() -> None:
    user = _make_user(status=UserStatus.ACTIVE, deleted_at=datetime.now(UTC))
    assert user.is_active is False


def test_is_deleted_reflects_deleted_at() -> None:
    assert _make_user(deleted_at=None).is_deleted is False
    assert _make_user(deleted_at=datetime.now(UTC)).is_deleted is True


def test_activate_sets_status_active() -> None:
    user = _make_user(status=UserStatus.INACTIVE)
    user.activate()
    assert user.status == UserStatus.ACTIVE


def test_activate_raises_for_deleted_user() -> None:
    user = _make_user(status=UserStatus.INACTIVE, deleted_at=datetime.now(UTC))
    with pytest.raises(BusinessValidationError) as exc_info:
        user.activate()
    assert exc_info.value.code == "CANNOT_ACTIVATE_DELETED_USER"
    # The failed activation must not have silently mutated state.
    assert user.status == UserStatus.INACTIVE


def test_deactivate_sets_status_inactive() -> None:
    user = _make_user(status=UserStatus.ACTIVE)
    user.deactivate()
    assert user.status == UserStatus.INACTIVE


def test_deactivate_is_idempotent_on_already_inactive_user() -> None:
    user = _make_user(status=UserStatus.INACTIVE)
    user.deactivate()  # must not raise
    assert user.status == UserStatus.INACTIVE


def test_deactivate_does_not_raise_for_deleted_user() -> None:
    # Unlike activate(), deactivate() has no illegal transition to guard —
    # see the entity's own docstring for why.
    user = _make_user(status=UserStatus.ACTIVE, deleted_at=datetime.now(UTC))
    user.deactivate()
    assert user.status == UserStatus.INACTIVE
