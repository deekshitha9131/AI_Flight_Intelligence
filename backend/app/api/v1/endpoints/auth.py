from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserCreate, UserRegistrationResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, password, and profile information.",
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
    description="Validate credentials and return a JWT access token for an active user.",
)
async def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and return a JWT access token."""
    service = AuthService(session=db)
    token_payload = service.login(payload=payload)
    return LoginResponse(
        success=True,
        message="Login successful",
        data={
            "access_token": token_payload["access_token"],
            "token_type": token_payload["token_type"],
            "expires_in": token_payload["expires_in"],
        },
    )
