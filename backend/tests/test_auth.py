"""
test_auth.py
------------
HTTP-layer integration tests for all authentication endpoints.

Covers:
  POST /api/v1/auth/login
    - Successful login returns access_token + refresh_token
    - Wrong password returns 401
    - Unknown email returns 401

  GET /api/v1/auth/me  (protected route)
    - No token returns 401
    - Invalid token string returns 401
    - Expired token returns 401
    - Valid token returns the authenticated user profile

  POST /api/v1/auth/refresh
    - Valid refresh token returns a new token pair
    - Old refresh token is rejected after rotation (401)
    - Expired refresh token returns 401
    - Malformed / garbage token returns 401
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import get_settings

settings = get_settings()

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_expired_access_token(user_id: str, email: str, role: str) -> str:
    """Build a syntactically valid but already-expired access token."""
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),  # still in the past
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _make_expired_refresh_token(user_id: str) -> str:
    """Build a syntactically valid but already-expired refresh token."""
    now = datetime.now(timezone.utc) - timedelta(days=10)
    payload = {
        "sub": user_id,
        "jti": "test-jti",
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),  # still in the past
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, Any]:
    """Perform a login and return the parsed response JSON."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_successful_login_returns_token_pair(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        payload = user_payload()
        response = await _login(client, payload["email"], payload["password"])

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Login successful"

        data = body["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        payload = user_payload()
        response = await _login(client, payload["email"], "WrongPass@999")

        assert response.status_code == 401
        assert response.json()["success"] is False

    async def test_unknown_email_returns_401(self, client: AsyncClient) -> None:
        response = await _login(client, "nobody@example.com", "Secure@123")

        assert response.status_code == 401
        assert response.json()["success"] is False

    async def test_login_does_not_leak_credentials_in_error(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        """Error message must not reveal whether email or password was wrong."""
        payload = user_payload()
        response = await _login(client, payload["email"], "BadPass@1")

        message = response.json()["message"]
        assert "email" not in message.lower() or "password" not in message.lower()
        # Both cases return the same generic message
        assert "Invalid email or password" in message


# ---------------------------------------------------------------------------
# Protected route tests
# ---------------------------------------------------------------------------


class TestProtectedRoutes:
    async def test_no_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_invalid_token_string_returns_401(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert response.status_code == 401

    async def test_expired_token_returns_401(
        self, client: AsyncClient, registered_user
    ) -> None:
        expired_token = _make_expired_access_token(
            user_id=str(registered_user["id"]),
            email=registered_user["email"],
            role="USER",
        )
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    async def test_valid_token_returns_200(
        self, client: AsyncClient, auth_headers
    ) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Current user endpoint tests
# ---------------------------------------------------------------------------


class TestCurrentUser:
    async def test_me_returns_correct_user_profile(
        self,
        client: AsyncClient,
        user_payload,
        registered_user,
        auth_headers,
    ) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Current user retrieved successfully"

        data = body["data"]
        payload = user_payload()
        assert data["email"] == payload["email"]
        assert data["first_name"] == payload["first_name"]
        assert data["last_name"] == payload["last_name"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    async def test_me_does_not_expose_password_hash(
        self, client: AsyncClient, auth_headers
    ) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        body_text = response.text
        assert "password" not in body_text
        assert "hash" not in body_text


# ---------------------------------------------------------------------------
# Refresh token tests
# ---------------------------------------------------------------------------


class TestRefreshToken:
    async def _get_tokens(
        self, client: AsyncClient, user_payload, registered_user
    ) -> tuple[str, str]:
        """Log in and return (access_token, refresh_token)."""
        payload = user_payload()
        response = await _login(client, payload["email"], payload["password"])
        assert response.status_code == 200
        data = response.json()["data"]
        return data["access_token"], data["refresh_token"]

    async def test_valid_refresh_returns_new_token_pair(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        _, refresh_token = await self._get_tokens(client, user_payload, registered_user)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Token refreshed successfully"

        data = body["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_new_tokens_are_different_from_old_tokens(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        old_access, old_refresh = await self._get_tokens(
            client, user_payload, registered_user
        )

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert response.status_code == 200
        data = response.json()["data"]

        assert data["access_token"] != old_access
        assert data["refresh_token"] != old_refresh

    async def test_old_refresh_token_is_rejected_after_rotation(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        """Token rotation: the consumed refresh token must be revoked."""
        _, old_refresh = await self._get_tokens(client, user_payload, registered_user)

        # First use — succeeds and rotates
        first = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert first.status_code == 200

        # Second use of the same token — must be rejected
        second = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert second.status_code == 401
        assert second.json()["success"] is False

    async def test_rotated_refresh_token_is_usable(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        """The newly issued refresh token from a rotation must itself be valid."""
        _, old_refresh = await self._get_tokens(client, user_payload, registered_user)

        first = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert first.status_code == 200
        new_refresh = first.json()["data"]["refresh_token"]

        second = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh},
        )
        assert second.status_code == 200

    async def test_expired_refresh_token_returns_401(
        self, client: AsyncClient, registered_user
    ) -> None:
        expired = _make_expired_refresh_token(user_id=str(registered_user["id"]))

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired},
        )
        assert response.status_code == 401
        assert response.json()["success"] is False

    async def test_malformed_refresh_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not.a.real.token"},
        )
        assert response.status_code == 401

    async def test_garbage_string_refresh_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "garbage"},
        )
        assert response.status_code == 401

    async def test_new_access_token_grants_access_to_protected_route(
        self, client: AsyncClient, user_payload, registered_user
    ) -> None:
        """Access token obtained via refresh must work on protected endpoints."""
        _, old_refresh = await self._get_tokens(client, user_payload, registered_user)

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert refresh_response.status_code == 200
        new_access = refresh_response.json()["data"]["access_token"]

        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert me_response.status_code == 200
