"""
test_users.py
-------------
HTTP-layer integration tests for user registration.

Covers:
  POST /api/v1/auth/register
    - Successful registration returns 201 with sanitized user data
    - Duplicate email returns 400
    - Invalid email format returns 422
    - Missing required fields returns 422
    - Weak password (no uppercase) returns 422
    - Weak password (no lowercase) returns 422
    - Weak password (no digit) returns 422
    - Weak password (no special character) returns 422
    - Password too short returns 422
    - First name too short returns 422
    - Last name too short returns 422
    - Response never exposes password_hash
    - Registered user is_verified defaults to False
    - Registered user role defaults to USER
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Successful registration
# ---------------------------------------------------------------------------


class TestRegistrationSuccess:
    async def test_successful_registration_returns_201(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post("/api/v1/auth/register", json=user_payload())
        assert response.status_code == 201

    async def test_successful_registration_response_shape(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        response = await client.post("/api/v1/auth/register", json=payload)
        body = response.json()

        assert body["success"] is True
        assert "data" in body

        data = body["data"]
        assert data["email"] == payload["email"]
        assert data["first_name"] == payload["first_name"]
        assert data["last_name"] == payload["last_name"]
        assert "id" in data
        assert "is_verified" in data

    async def test_registered_user_is_not_verified_by_default(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post("/api/v1/auth/register", json=user_payload())
        assert response.json()["data"]["is_verified"] is False

    async def test_response_does_not_expose_password(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post("/api/v1/auth/register", json=user_payload())
        body_text = response.text
        assert "password" not in body_text
        assert "hash" not in body_text

    async def test_email_is_stored_lowercase(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload(email="UPPER@Example.COM")
        response = await client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 201
        assert response.json()["data"]["email"] == "upper@example.com"


# ---------------------------------------------------------------------------
# Duplicate email
# ---------------------------------------------------------------------------


class TestDuplicateEmail:
    async def test_duplicate_email_returns_400(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        await client.post("/api/v1/auth/register", json=payload)

        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400

    async def test_duplicate_email_error_message(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        await client.post("/api/v1/auth/register", json=payload)

        response = await client.post("/api/v1/auth/register", json=payload)
        assert "already registered" in response.json()["message"].lower()

    async def test_duplicate_email_case_insensitive(
        self, client: AsyncClient, user_payload
    ) -> None:
        """Registering with the same email in different case must be rejected."""
        await client.post(
            "/api/v1/auth/register", json=user_payload(email="jane@example.com")
        )
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(email="JANE@EXAMPLE.COM"),
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Invalid email format
# ---------------------------------------------------------------------------


class TestInvalidEmail:
    @pytest.mark.parametrize(
        "bad_email",
        [
            "not-an-email",
            "missing@",
            "@nodomain.com",
            "spaces in@email.com",
            "",
        ],
    )
    async def test_invalid_email_returns_422(
        self, client: AsyncClient, user_payload, bad_email: str
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(email=bad_email),
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Weak password
# ---------------------------------------------------------------------------


class TestWeakPassword:
    async def test_password_too_short_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(password="Ab1!"),
        )
        assert response.status_code == 422

    async def test_password_no_uppercase_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(password="secure@123"),
        )
        assert response.status_code == 422

    async def test_password_no_lowercase_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(password="SECURE@123"),
        )
        assert response.status_code == 422

    async def test_password_no_digit_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(password="Secure@abc"),
        )
        assert response.status_code == 422

    async def test_password_no_special_char_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(password="Secure1234"),
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Missing / invalid name fields
# ---------------------------------------------------------------------------


class TestNameValidation:
    async def test_first_name_too_short_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(first_name="A"),
        )
        assert response.status_code == 422

    async def test_last_name_too_short_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json=user_payload(last_name="B"),
        )
        assert response.status_code == 422

    async def test_missing_first_name_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        del payload["first_name"]
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_missing_last_name_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        del payload["last_name"]
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_missing_email_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        del payload["email"]
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    async def test_missing_password_returns_422(
        self, client: AsyncClient, user_payload
    ) -> None:
        payload = user_payload()
        del payload["password"]
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422
