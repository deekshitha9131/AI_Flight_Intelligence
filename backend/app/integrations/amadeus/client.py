from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from app.integrations.amadeus.auth import AmadeusTokenManager
from app.integrations.amadeus.exceptions import (
    AmadeusAuthException,
    AmadeusConnectionException,
    AmadeusException,
    AmadeusNotFoundException,
    AmadeusPermissionException,
    AmadeusRateLimitException,
    AmadeusServerException,
    AmadeusTimeoutException,
)

logger = logging.getLogger(__name__)

# HTTP status codes that are safe to retry (transient server-side failures).
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({500, 502, 503, 504})

# Default retry configuration.
_DEFAULT_MAX_RETRIES: int = 3
_DEFAULT_RETRY_BACKOFF_SECONDS: float = 0.5


class AmadeusClient:
    """
    Async HTTP client for the Amadeus Self-Service API.

    Responsibilities:
    - Automatically attach a valid Bearer token to every request.
    - Retry transient failures with exponential back-off.
    - Map HTTP error codes to typed AmadeusException subclasses.
    - Log endpoint, status, duration, and errors — never secrets or tokens.

    Lifecycle:
    - Call `await client.close()` when the application shuts down, or use the
      client as an async context manager.

    Usage (dependency injection)::

        client = AmadeusClient.from_settings()
        data = await client.request("GET", "/v2/shopping/flight-offers", params={...})
        await client.close()
    """

    def __init__(
        self,
        token_manager: AmadeusTokenManager,
        base_url: str,
        timeout: float,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._token_manager = token_manager
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(cls) -> AmadeusClient:
        """Construct an AmadeusClient from the application settings."""
        from app.core.config import get_settings

        settings = get_settings()
        token_manager = AmadeusTokenManager(
            api_key=settings.amadeus_api_key,
            api_secret=settings.amadeus_api_secret,
            timeout=settings.amadeus_timeout_seconds,
        )
        return cls(
            token_manager=token_manager,
            base_url=settings.amadeus_base_url,
            timeout=settings.amadeus_timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_access_token(self) -> str:
        """Return a valid Amadeus access token (fetched or refreshed automatically)."""
        return await self._token_manager.get_access_token()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an authenticated HTTP request against the Amadeus API.

        Automatically:
        - Attaches a valid Bearer token.
        - Retries on transient 5xx errors with exponential back-off.
        - Raises a typed AmadeusException on non-retryable failures.

        Args:
            method:  HTTP verb (GET, POST, …).
            path:    API path relative to the base URL (e.g. "/v2/shopping/flight-offers").
            params:  Query string parameters.
            json:    Request body serialised as JSON.
            headers: Additional request headers (merged with auth header).

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            AmadeusAuthException:       401 — invalid or expired credentials.
            AmadeusPermissionException: 403 — insufficient API permissions.
            AmadeusNotFoundException:   404 — resource not found.
            AmadeusRateLimitException:  429 — rate limit exceeded.
            AmadeusServerException:     5xx — Amadeus server error.
            AmadeusTimeoutException:    Request timed out.
            AmadeusConnectionException: Network-level connection failure.
        """
        last_exception: AmadeusException | None = None

        for attempt in range(1, self._max_retries + 1):
            token = await self._token_manager.get_access_token()
            merged_headers = _build_headers(token, headers)
            start = time.monotonic()

            try:
                response = await self._http.request(
                    method=method.upper(),
                    url=path,
                    params=params,
                    json=json,
                    headers=merged_headers,
                )
            except httpx.TimeoutException as exc:
                elapsed = time.monotonic() - start
                logger.error(
                    "Amadeus request timed out | method=%s path=%s attempt=%d/%d elapsed=%.3fs",
                    method.upper(),
                    path,
                    attempt,
                    self._max_retries,
                    elapsed,
                )
                last_exception = AmadeusTimeoutException()
                if attempt < self._max_retries:
                    await _backoff(attempt)
                continue
            except httpx.ConnectError as exc:
                elapsed = time.monotonic() - start
                logger.error(
                    "Amadeus connection error | method=%s path=%s attempt=%d/%d elapsed=%.3fs",
                    method.upper(),
                    path,
                    attempt,
                    self._max_retries,
                    elapsed,
                )
                last_exception = AmadeusConnectionException()
                if attempt < self._max_retries:
                    await _backoff(attempt)
                continue

            elapsed = time.monotonic() - start
            logger.info(
                "Amadeus response | method=%s path=%s status=%d attempt=%d/%d elapsed=%.3fs",
                method.upper(),
                path,
                response.status_code,
                attempt,
                self._max_retries,
                elapsed,
            )

            if response.is_success:
                return response.json()

            # Map the error status to a typed exception.
            exc = _map_error(response)

            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < self._max_retries
            ):
                logger.warning(
                    "Amadeus transient error %d — retrying (attempt %d/%d).",
                    response.status_code,
                    attempt,
                    self._max_retries,
                )
                last_exception = exc
                await _backoff(attempt)
                continue

            raise exc

        raise last_exception  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx connection pool."""
        await self._http.aclose()
        logger.info("AmadeusClient HTTP connection pool closed.")

    async def __aenter__(self) -> AmadeusClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_headers(token: str, extra: dict[str, str] | None) -> dict[str, str]:
    """Merge the Bearer auth header with any caller-supplied headers."""
    headers = {"Authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    return headers


def _map_error(response: httpx.Response) -> AmadeusException:
    """Map an unsuccessful HTTP response to the appropriate AmadeusException."""
    try:
        body: dict[str, Any] = response.json()
    except Exception:
        body = {}

    status = response.status_code
    detail = _extract_error_detail(body)

    logger.error(
        "Amadeus API error | status=%d detail=%r",
        status,
        detail,
    )

    if status == 401:
        return AmadeusAuthException(message=detail, response_body=body)
    if status == 403:
        return AmadeusPermissionException(message=detail, response_body=body)
    if status == 404:
        return AmadeusNotFoundException(message=detail, response_body=body)
    if status == 429:
        return AmadeusRateLimitException(message=detail, response_body=body)
    if status >= 500:
        return AmadeusServerException(
            message=detail, status_code=status, response_body=body
        )

    # Catch-all for any other non-success status.
    return AmadeusException(message=detail, status_code=status, response_body=body)


def _extract_error_detail(body: dict[str, Any]) -> str:
    """Pull the most descriptive error string from an Amadeus error payload."""
    # Amadeus error envelopes vary by endpoint; try the most common shapes.
    if "errors" in body and isinstance(body["errors"], list) and body["errors"]:
        first = body["errors"][0]
        return first.get("detail") or first.get("title") or str(first)
    if "error_description" in body:
        return str(body["error_description"])
    if "error" in body:
        return str(body["error"])
    return "An unexpected Amadeus API error occurred."


async def _backoff(attempt: int) -> None:
    """Exponential back-off: 0.5s, 1.0s, 2.0s, …"""
    import asyncio

    delay = _DEFAULT_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
    logger.debug(
        "Amadeus retry back-off: sleeping %.2fs before attempt %d.", delay, attempt + 1
    )
    await asyncio.sleep(delay)
