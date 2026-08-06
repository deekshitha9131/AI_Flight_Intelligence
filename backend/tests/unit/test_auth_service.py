"""Tests for app/application/services/auth_service.py.

Fakes every collaborator (oauth client, user repository, session
store) — this is a pure test of orchestration logic: does AuthService
call the right things in the right order and handle their results
correctly. Real integration of each collaborator is tested separately
(test_oauth_client.py, integration/test_user_repository.py).
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.services.auth_service import AuthService
from app.domain.entities.oauth_token import OAuthToken
from app.domain.entities.user import User
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.auth import (
    InvalidOAuthStateError,
    OAuthExchangeError,
    SessionNotFoundError,
)
from app.infrastructure.gmail.oauth_client import GoogleTokenResponse, GoogleUserInfo


class FakeOAuthClient:
    def __init__(self, *, token_response: GoogleTokenResponse, userinfo: GoogleUserInfo) -> None:
        self._token_response = token_response
        self._userinfo = userinfo
        self.exchange_calls: list[str] = []

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://accounts.google.com/fake-auth?state={state}"

    async def exchange_code_for_tokens(self, *, code: str) -> GoogleTokenResponse:
        self.exchange_calls.append(code)
        return self._token_response

    async def fetch_userinfo(self, *, access_token: str) -> GoogleUserInfo:
        return self._userinfo


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_sub: dict[str, User] = {}
        self.users_by_id: dict = {}
        self.saved_tokens: dict = {}

    async def get_by_google_sub_id(self, google_sub_id: str) -> User | None:
        return self.users_by_sub.get(google_sub_id)

    async def get_by_id(self, user_id) -> User | None:
        return self.users_by_id.get(user_id)

    async def create(self, *, email: str, full_name: str, google_sub_id: str) -> User:
        user = User(
            id=uuid4(),
            email=email,
            full_name=full_name,
            google_sub_id=google_sub_id,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.users_by_sub[google_sub_id] = user
        self.users_by_id[user.id] = user
        return user

    async def save_oauth_tokens(
        self, user_id, *, access_token, refresh_token, token_expiry, granted_scopes
    ) -> None:
        self.saved_tokens[user_id] = OAuthToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            granted_scopes=granted_scopes,
        )

    async def get_oauth_tokens(self, user_id) -> OAuthToken | None:
        return self.saved_tokens.get(user_id)


class FakeSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, object] = {}

    async def create_session(self, user_id) -> str:
        session_id = f"session-for-{user_id}"
        self.sessions[session_id] = user_id
        return session_id

    async def get_user_id(self, session_id: str):
        return self.sessions.get(session_id)

    async def delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)


def _make_service(*, oauth_client, user_repository=None, session_store=None) -> AuthService:
    return AuthService(
        oauth_client=oauth_client,
        user_repository=user_repository or FakeUserRepository(),
        session_store=session_store or FakeSessionStore(),
    )


def _default_token_response(**overrides) -> GoogleTokenResponse:
    defaults = dict(
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        expires_in=3600,
        scope="openid email",
        token_type="Bearer",
    )
    defaults.update(overrides)
    return GoogleTokenResponse(**defaults)


def _default_userinfo(**overrides) -> GoogleUserInfo:
    defaults = dict(
        sub="google-sub-123", email="user@example.com", name="Test User", email_verified=True
    )
    defaults.update(overrides)
    return GoogleUserInfo(**defaults)


def test_build_login_redirect_returns_url_and_state() -> None:
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        )
    )
    url, state = service.build_login_redirect()
    assert state in url
    assert len(state) > 20  # secrets.token_urlsafe(32) produces a long value


async def test_handle_callback_rejects_state_mismatch() -> None:
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        )
    )
    with pytest.raises(InvalidOAuthStateError):
        await service.handle_callback(
            code="irrelevant", state="expected", state_cookie_value="different"
        )


async def test_handle_callback_rejects_missing_state_cookie() -> None:
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        )
    )
    with pytest.raises(InvalidOAuthStateError):
        await service.handle_callback(code="irrelevant", state="expected", state_cookie_value=None)


async def test_handle_callback_creates_new_user_on_first_login() -> None:
    user_repo = FakeUserRepository()
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        ),
        user_repository=user_repo,
    )

    user, session_id = await service.handle_callback(
        code="auth-code", state="s", state_cookie_value="s"
    )

    assert user.email == "user@example.com"
    assert user.google_sub_id == "google-sub-123"
    assert session_id.startswith("session-for-")
    assert user_repo.saved_tokens[user.id].access_token == "fake-access-token"


async def test_handle_callback_reuses_existing_user_on_repeat_login() -> None:
    user_repo = FakeUserRepository()
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        ),
        user_repository=user_repo,
    )

    first_user, _ = await service.handle_callback(code="code-1", state="s", state_cookie_value="s")
    second_user, _ = await service.handle_callback(code="code-2", state="s", state_cookie_value="s")

    assert first_user.id == second_user.id
    assert len(user_repo.users_by_sub) == 1


async def test_handle_callback_preserves_existing_refresh_token_when_google_omits_it() -> None:
    user_repo = FakeUserRepository()
    oauth_client = FakeOAuthClient(
        token_response=_default_token_response(),  # has a refresh_token
        userinfo=_default_userinfo(),
    )
    service = _make_service(oauth_client=oauth_client, user_repository=user_repo)

    user, _ = await service.handle_callback(code="code-1", state="s", state_cookie_value="s")
    original_refresh_token = user_repo.saved_tokens[user.id].refresh_token

    # Simulate a repeat login where Google omits refresh_token this time.
    oauth_client._token_response = _default_token_response(refresh_token=None)
    await service.handle_callback(code="code-2", state="s", state_cookie_value="s")

    assert user_repo.saved_tokens[user.id].refresh_token == original_refresh_token


async def test_handle_callback_raises_when_no_refresh_token_available_at_all() -> None:
    """First-ever login where Google somehow omits refresh_token and there's
    nothing on file to fall back to — must fail loudly, not silently
    store an unusable empty token."""
    oauth_client = FakeOAuthClient(
        token_response=_default_token_response(refresh_token=None), userinfo=_default_userinfo()
    )
    service = _make_service(oauth_client=oauth_client)

    with pytest.raises(OAuthExchangeError):
        await service.handle_callback(code="code-1", state="s", state_cookie_value="s")


async def test_get_current_user_with_valid_session() -> None:
    user_repo = FakeUserRepository()
    session_store = FakeSessionStore()
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        ),
        user_repository=user_repo,
        session_store=session_store,
    )
    user, session_id = await service.handle_callback(code="c", state="s", state_cookie_value="s")

    resolved = await service.get_current_user(session_id)
    assert resolved.id == user.id


async def test_get_current_user_raises_for_missing_session() -> None:
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        )
    )
    with pytest.raises(SessionNotFoundError):
        await service.get_current_user(None)


async def test_get_current_user_raises_for_unknown_session() -> None:
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        )
    )
    with pytest.raises(SessionNotFoundError):
        await service.get_current_user("session-that-does-not-exist")


async def test_logout_deletes_the_session() -> None:
    user_repo = FakeUserRepository()
    session_store = FakeSessionStore()
    service = _make_service(
        oauth_client=FakeOAuthClient(
            token_response=_default_token_response(), userinfo=_default_userinfo()
        ),
        user_repository=user_repo,
        session_store=session_store,
    )
    _user, session_id = await service.handle_callback(code="c", state="s", state_cookie_value="s")

    await service.logout(session_id)

    with pytest.raises(SessionNotFoundError):
        await service.get_current_user(session_id)
