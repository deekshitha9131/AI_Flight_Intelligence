from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request payload for user login."""

    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponseData(BaseModel):
    """JWT access token payload returned after a successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """Login response payload."""

    success: bool
    message: str
    data: LoginResponseData
