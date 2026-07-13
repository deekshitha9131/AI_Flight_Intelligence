from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request payload for user login."""

    email: EmailStr = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponseData(BaseModel):
    """JWT token payload returned after a successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """Login response payload."""

    success: bool
    message: str
    data: LoginResponseData


class RefreshRequest(BaseModel):
    """Request payload for token refresh."""

    refresh_token: str = Field(..., min_length=1, description="Valid refresh token")


class RefreshResponseData(BaseModel):
    """New token pair returned after a successful refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshResponse(BaseModel):
    """Token refresh response payload."""

    success: bool
    message: str
    data: RefreshResponseData
