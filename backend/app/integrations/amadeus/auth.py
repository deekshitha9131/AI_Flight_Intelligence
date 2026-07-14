from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from app.integrations.amadeus.exceptions import (
    AmadeusAuthException,
    AmadeusConnectionException,
    AmadeusTimeoutException,
)

logger = logging.getLogger(__name__)

# Refresh the token this many seconds before it actually expires to avoid
# race conditions between the expiry check and the outgoing request.
_EXPIRY_BUFFER_SECONDS: int = 30

_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"


class AmadeusTokenManager:
    """
    Manages OAuth2 client-credentials tokens for the Amadeus API.

    Responsibilities:
    - Fetch a new token on first use.
    - Cache the token in memory.
    - Transparently refresh it before expiry.
    - Never log the API secret or the raw access token value.

    Thread / task safety:
    - An asyncio.Lock prevents concurrent token-fetch requests when multiple
      coroutines call get_access_token() simultaneously on a cold or expired cache.
    """

    def __init__(self, api_key: str, api_secret: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout

        self._access_token: str | None = None
        self._expires_at: float = 0.0  # Unix timestamp
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_access_token(self) -> str:
        """Return a valid access token, fetching or refreshing as needed."""
        if self._is_token_valid():
            return self._access_token  # type: ignore[return-value]

        async with self._lock:
            # Re-check inside the lock — another coroutine may have refreshed
            # the token while this one was waiting to acquire the lock.
            if self._is_token_valid():
                return self._access_token  # type: ignore[return-value]

            await self._fetch_token()
            return self._access_token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_token_valid(self) -> bool:
        """Return True when a cached token exists and has not yet expired."""
        return (
            self._access_token is not None
            and time.monotonic() < self._expires_at - _EXPIRY_BUFFER_SECONDS
        )

    async def _fetch_token(self) -> None:
        """Perform the OAuth2 client-credentials grant and cache the result."""
        logger.info("Fetching new Amadeus access token.")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                response = await http.post(
                    _TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._api_key,
                        "client_secret": self._api_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.TimeoutException as exc:
            logger.error("Timeout while fetching Amadeus access token.")
            raise AmadeusTimeoutException() from exc
        except httpx.ConnectError as exc:
            logger.error("Connection error while fetching Amadeus access token.")
            raise AmadeusConnectionException() from exc

        if response.status_code != 200:
            logger.error(
                "Amadeus token endpoint returned HTTP %d.", response.status_code
            )
            _raise_auth_error(response)

        body: dict[str, Any] = response.json()
        self._access_token = body["access_token"]
        expires_in: int = int(body.get("expires_in", 1799))
        self._expires_at = time.monotonic() + expires_in

        logger.info(
            "Amadeus access token obtained successfully. Expires in %d seconds.",
            expires_in,
        )


def _raise_auth_error(response: httpx.Response) -> None:
    """Parse the error body and raise AmadeusAuthException."""
    try:
        body: dict[str, Any] = response.json()
    except Exception:
        body = {}
    raise AmadeusAuthException(
        message=body.get("error_description", "Amadeus authentication failed."),
        response_body=body,
    )
