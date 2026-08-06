"""User request/response schemas.

These are the API contract boundary — never the same objects as the
domain entity (app/domain/entities/user.py) or the ORM model, per this
project's Clean Architecture rule that presentation-layer schemas are
distinct from domain entities. `UserRead` in particular is not just a
1:1 mirror of the domain entity: it deliberately omits `google_sub_id`,
since that's an internal identity-linkage detail with no reason to ever
reach a client response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums.user_status import UserStatus


class UserCreate(BaseModel):
    """Internal creation input — used when the OAuth callback creates a new
    user record, not exposed as a public "create user" endpoint (there
    isn't one; accounts are created only via Google OAuth)."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    google_sub_id: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    """Fields a user can update about themselves. Deliberately narrow —
    email and google_sub_id are identity, not profile data, and are
    never user-editable through this schema."""

    full_name: str = Field(min_length=1, max_length=255)


class UserStatusUpdate(BaseModel):
    """Separate from UserUpdate on purpose: changing account status is a
    distinct, more privileged operation than editing a display name,
    and keeping its schema separate makes that distinction visible at
    the endpoint level rather than folded into a general-purpose PATCH."""

    status: UserStatus


class UserRead(BaseModel):
    """Public response shape. Excludes google_sub_id — see module docstring."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime
