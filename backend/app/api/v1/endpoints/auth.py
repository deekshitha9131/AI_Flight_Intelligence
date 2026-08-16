from __future__ import annotations

import json

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.schemas.user import UserCreate, UserRegistrationResponse, UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_user_payload(current_user: User) -> dict[str, object]:
    return {
        "id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "profile_image": current_user.profile_image,
        "preferred_airport": current_user.preferred_airport,
        "preferred_cabin": current_user.preferred_cabin,
        "currency_preference": current_user.currency_preference,
        "notification_settings": (
            json.loads(current_user.notification_settings)
            if current_user.notification_settings
            else {
                "email": True,
                "push": True,
                "price_alerts": True,
            }
        ),
    }


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a new user account with email, password, and profile information."
    ),
)
async def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserRegistrationResponse:
    """Register a new user account and return a sanitized public payload."""
    service = UserService(session=db)
    user = service.register_user(payload=payload)
    return UserRegistrationResponse(
        success=True,
        message="User registered successfully.",
        data={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_verified": user.is_verified,
        },
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    description="Validate credentials and return a JWT access token and refresh token.",
)
async def login_user(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and return a JWT access token and refresh token."""
    service = AuthService(session=db)
    token_payload = service.login(
        payload=payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return LoginResponse(
        success=True,
        message="Login successful",
        data={
            "access_token": token_payload["access_token"],
            "refresh_token": token_payload["refresh_token"],
            "token_type": token_payload["token_type"],
            "expires_in": token_payload["expires_in"],
        },
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token and "
        "rotated refresh token."
    ),
)
async def refresh_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """Rotate the refresh token and issue a new access token."""
    service = AuthService(session=db)
    token_payload = service.refresh(refresh_token=payload.refresh_token)
    return RefreshResponse(
        success=True,
        message="Token refreshed successfully",
        data={
            "access_token": token_payload["access_token"],
            "refresh_token": token_payload["refresh_token"],
            "token_type": token_payload["token_type"],
        },
    )


@router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Update the current user profile",
    description=(
        "Update profile details and travel preferences for the authenticated user."
    ),
)
async def update_current_user_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Update the authenticated user's basic profile and preference fields."""
    service = UserService(session=db)
    updated_user = service.update_user_profile(
        user_id=current_user.id, payload=payload
    )
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": _serialize_user_payload(updated_user),
    }


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change user password",
    description="Validate current password and update user to a new hashed password.",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Verify current password, hash new password, and save to database."""
    service = UserService(session=db)
    service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return {
        "success": True,
        "message": "Password updated successfully",
    }


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get the current user",
    description=(
        "Return the authenticated user profile for the active JWT bearer token."
    ),
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Return the authenticated user's public profile payload."""
    return {
        "success": True,
        "message": "Current user retrieved successfully",
        "data": _serialize_user_payload(current_user),
    }
