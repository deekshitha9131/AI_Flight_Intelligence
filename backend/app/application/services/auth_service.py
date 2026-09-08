import secrets
from datetime import UTC, datetime, timedelta

from app.domain.entities.user import User
from app.domain.exceptions.auth import (
    InvalidOAuthStateError,
    OAuthNotConfiguredError,
    OAuthExchangeError,
    SessionNotFoundError,
)
from app.infrastructure.cache.session_store import SessionStore
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.gmail.oauth_client import GoogleOAuthClient


class AuthService:
    def __init__(
        self,
        *,
        oauth_client: GoogleOAuthClient | None,
        user_repository: UserRepository,
        session_store: SessionStore,
    ) -> None:
        self._oauth_client = oauth_client
        self._user_repository = user_repository
        self._session_store = session_store

    def build_login_redirect(self) -> tuple[str, str]:
        """Build the Google authorization URL and a fresh CSRF state value.

        Returns (authorization_url, state) — the router sets `state` as
        the short-lived oauth_state cookie and redirects the browser to
        authorization_url. Generating the state here (not in the
        router) keeps "how a state value is generated" a service
        concern, even though where it's stored (a cookie) is the
        router's job.
        """
        if self._oauth_client is None or not getattr(self._oauth_client, "is_configured", True):
            raise OAuthNotConfiguredError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET in backend/.env."
            )
        state = secrets.token_urlsafe(32)
        authorization_url = self._oauth_client.build_authorization_url(state=state)
        return authorization_url, state

    async def handle_callback(
        self, *, code: str, state: str, state_cookie_value: str | None
    ) -> tuple[User, str]:
        if self._oauth_client is None:
            raise InvalidOAuthStateError("OAuth client is not configured.")
        if state_cookie_value is None or not secrets.compare_digest(state, state_cookie_value):
            raise InvalidOAuthStateError(
                "OAuth state mismatch — this can happen if the login attempt "
                "expired, or if the request didn't originate from our own "
                "login redirect."
            )

        token_response = await self._oauth_client.exchange_code_for_tokens(code=code)
        userinfo = await self._oauth_client.fetch_userinfo(access_token=token_response.access_token)

        user = await self._user_repository.get_by_google_sub_id(userinfo.sub)
        if user is None:
            user = await self._user_repository.create(
                email=userinfo.email,
                full_name=userinfo.name,
                google_sub_id=userinfo.sub,
            )

        refresh_token = token_response.refresh_token
        if refresh_token is None:
            existing_tokens = await self._user_repository.get_oauth_tokens(user.id)
            if existing_tokens is None:
                raise OAuthExchangeError(
                    "Google did not return a refresh token, and no previous "
                    "token is on file for this account. Please try logging "
                    "in again."
                )
            refresh_token = existing_tokens.refresh_token

        await self._user_repository.save_oauth_tokens(
            user.id,
            access_token=token_response.access_token,
            refresh_token=refresh_token,
            token_expiry=datetime.now(UTC) + timedelta(seconds=token_response.expires_in),
            granted_scopes=token_response.scope.split(),
        )

        session_id = await self._session_store.create_session(user.id)
        return user, session_id

    async def logout(self, session_id: str) -> None:
        await self._session_store.delete_session(session_id)

    async def get_current_user(self, session_id: str | None) -> User:
        if session_id is None:
            raise SessionNotFoundError("No active session.")

        user_id = await self._session_store.get_user_id(session_id)
        if user_id is None:
            raise SessionNotFoundError("No active session.")

        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise SessionNotFoundError("No active session.")

        return user
