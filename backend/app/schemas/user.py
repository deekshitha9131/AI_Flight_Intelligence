from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Common base schema for users."""

    first_name: str = Field(
        ..., min_length=2, max_length=50, description="User first name"
    )
    last_name: str = Field(
        ..., min_length=2, max_length=50, description="User last name"
    )
    email: EmailStr = Field(..., description="User email address")
    phone_number: str | None = Field(
        default=None, max_length=20, description="Phone number in international format"
    )
    profile_image: str | None = Field(
        default=None, description="Optional profile image URL"
    )
    role: UserRole = Field(default=UserRole.USER, description="Assigned role")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"^\+?[1-9]\d{1,14}$", normalized):
            raise ValueError("Phone number must be a valid international format")
        return normalized


class UserCreate(UserBase):
    """Input schema for creating a user account."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password that meets complexity requirements",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(value) > 128:
            raise ValueError("Password must be at most 128 characters long")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must include at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must include at least one number")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must include at least one special character")
        return value


class UserUpdate(BaseModel):
    """Input schema for updating an existing user account."""

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    phone_number: str | None = Field(default=None, max_length=20)
    profile_image: str | None = Field(default=None)
    is_active: bool | None = None
    is_verified: bool | None = None
    role: UserRole | None = None


class UserResponse(UserBase):
    """Public-facing user response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class UserInDB(UserResponse):
    """Internal schema containing persisted fields such as password hash."""

    password_hash: str


class UserRegistrationData(BaseModel):
    """Public payload returned after a successful registration."""

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool


class UserRegistrationResponse(BaseModel):
    """Registration response payload."""

    success: bool
    message: str
    data: UserRegistrationData
