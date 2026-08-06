"""User-specific domain exceptions.

Subclasses of the base hierarchy in app/domain/exceptions/base.py — per
that module's own docstring, this is exactly where entity-specific
exceptions belong once the corresponding entity exists.
"""

from app.domain.exceptions.base import ConflictError, NotFoundError


class UserNotFoundError(NotFoundError):
    """Raised when a lookup by id/email/google_sub_id finds no matching user."""

    code = "USER_NOT_FOUND"


class UserAlreadyExistsError(ConflictError):
    """Raised when creating a user would violate a uniqueness constraint
    (duplicate email or duplicate google_sub_id)."""

    code = "USER_ALREADY_EXISTS"
