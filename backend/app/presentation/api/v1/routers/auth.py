"""Auth router.

Implements the four auth endpoints from the frozen API design: login
(redirect to Google), callback (complete the handshake), logout, and
session (who am I). Every endpoint delegates to AuthService — this file
only translates between HTTP concerns (cookies, redirects, query
params) and service calls; no OAuth logic, no encryption, no session
storage detail lives here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.application.services.auth_service import AuthService
from app.core.constants import (
    OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    OpenAPITags,
)
from app.core.di_container import AppSettings, CurrentUser, get_auth_service
from app.presentation.api.v1.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=[OpenAPITags.AUTH])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.get(
    "/google/login",
    summary="Start Google OAuth login",
    description="Redirects the browser to Google's consent screen. "
    "Sets a short-lived oauth_state cookie used to verify the callback.",
    status_code=302,
)
async def google_login(auth_service: AuthServiceDep, settings: AppSettings) -> RedirectResponse:
    authorization_url, state = auth_service.build_login_redirect()

    response = RedirectResponse(url=authorization_url, status_code=302)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return response


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="Completes the login: validates CSRF state, exchanges the "
    "authorization code, resolves-or-creates the user, stores encrypted "
    "tokens, issues a session, and redirects to the frontend.",
    status_code=302,
)
async def google_callback(
    request: Request,
    auth_service: AuthServiceDep,
    settings: AppSettings,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    state_cookie_value = request.cookies.get(OAUTH_STATE_COOKIE_NAME)

    _user, session_id = await auth_service.handle_callback(
        code=code, state=state, state_cookie_value=state_cookie_value
    )

    response = RedirectResponse(url=settings.frontend_base_url, status_code=302)
    # The state cookie has done its job the moment the callback
    # validates it — clearing it here means a stale value can never be
    # replayed against a future login attempt.
    response.delete_cookie(OAUTH_STATE_COOKIE_NAME)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )
    return response


@router.post(
    "/logout",
    summary="Log out",
    description="Invalidates the current session server-side (Redis) and "
    "clears the session cookie.",
    status_code=204,
)
async def logout(request: Request, auth_service: AuthServiceDep, response: Response) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is not None:
        await auth_service.logout(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get(
    "/session",
    summary="Current session",
    description="Returns the authenticated user's profile, resolved from "
    "the session cookie. 401 if there is no valid session.",
    response_model=UserRead,
)
async def get_session(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
