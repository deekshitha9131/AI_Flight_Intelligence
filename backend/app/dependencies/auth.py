from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.database.session import get_db
from app.exceptions.base import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user for protected endpoints."""
    if not token:
        raise UnauthorizedException(message="Authentication required.")

    try:
        payload = decode_access_token(token=token)
    except ValueError as exc:
        raise UnauthorizedException(message="Authentication failed.") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Authentication failed.")

    service = AuthService(session=db)
    try:
        return service.get_authenticated_user(user_id=str(user_id))
    except ForbiddenException as exc:
        raise ForbiddenException(message=exc.message) from exc
