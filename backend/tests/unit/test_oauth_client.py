"""Tests for app/infrastructure/gmail/oauth_client.py.

Uses httpx.MockTransport (built into httpx — no extra dependency) to
simulate Google's token and userinfo endpoints. This is a real test of
GoogleOAuthClient's request construction and response parsing, not a
mock of the client itself — the only thing faked is what's on the other
end of the HTTP call.
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core.constants import GOOGLE_TOKEN_ENDPOINT, GOOGLE_USERINFO_ENDPOINT
from app.domain.exceptions.auth import OAuthExchangeError
from app.infrastructure.gmail.oauth_client import GoogleOAuthClient


def _client(transport: httpx.MockTransport) -> GoogleOAuthClient:
    http_client = httpx.AsyncClient(transport=transport)
    return GoogleOAuthClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/api/v1/auth/google/callback",
        http_client=http_client,
    )


def test_build_authorization_url_includes_required_params() -> None:
    client = _client(httpx.MockTransport(lambda request: httpx.Response(200)))

    url = client.build_authorization_url(state="test-state-value")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == ["http://localhost:8000/api/v1/auth/google/callback"]
    assert params["response_type"] == ["code"]
    assert params["state"] == ["test-state-value"]
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert "gmail.readonly" in params["scope"][0]
    assert "gmail.send" in params["scope"][0]


async def test_exchange_code_for_tokens_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == GOOGLE_TOKEN_ENDPOINT
        body = parse_qs(request.content.decode())
        assert body["code"] == ["test-code"]
        assert body["grant_type"] == ["authorization_code"]
        return httpx.Response(
            200,
            json={
                "access_token": "fake-access-token",
                "refresh_token": "fake-refresh-token",
                "expires_in": 3599,
                "scope": "openid email",
                "token_type": "Bearer",
            },
        )

    client = _client(httpx.MockTransport(handler))
    result = await client.exchange_code_for_tokens(code="test-code")

    assert result.access_token == "fake-access-token"
    assert result.refresh_token == "fake-refresh-token"
    assert result.expires_in == 3599


async def test_exchange_code_for_tokens_missing_refresh_token() -> None:
    """Simulates a repeat-consent login where Google omits refresh_token —
    AuthService is responsible for handling this, but the client itself
    must parse it correctly as None, not crash on the missing key."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "fake-access-token",
                "expires_in": 3599,
                "scope": "openid email",
                "token_type": "Bearer",
            },
        )

    client = _client(httpx.MockTransport(handler))
    result = await client.exchange_code_for_tokens(code="test-code")

    assert result.refresh_token is None


async def test_exchange_code_for_tokens_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = _client(httpx.MockTransport(handler))

    with pytest.raises(OAuthExchangeError):
        await client.exchange_code_for_tokens(code="expired-or-reused-code")


async def test_fetch_userinfo_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == GOOGLE_USERINFO_ENDPOINT
        assert request.headers["Authorization"] == "Bearer fake-access-token"
        return httpx.Response(
            200,
            json={
                "sub": "1234567890",
                "email": "user@example.com",
                "name": "Test User",
                "email_verified": True,
            },
        )

    client = _client(httpx.MockTransport(handler))
    result = await client.fetch_userinfo(access_token="fake-access-token")

    assert result.sub == "1234567890"
    assert result.email == "user@example.com"
    assert result.name == "Test User"
    assert result.email_verified is True


async def test_fetch_userinfo_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_token"})

    client = _client(httpx.MockTransport(handler))

    with pytest.raises(OAuthExchangeError):
        await client.fetch_userinfo(access_token="revoked-token")
