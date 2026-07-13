from __future__ import annotations

from typing import Any


class AmadeusException(Exception):
    """Base exception for all Amadeus API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, message={self.message!r})"


class AmadeusAuthException(AmadeusException):
    """Raised when OAuth2 token acquisition or refresh fails (HTTP 401)."""

    def __init__(
        self,
        message: str = "Amadeus authentication failed.",
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=401, response_body=response_body)


class AmadeusPermissionException(AmadeusException):
    """Raised when the API key lacks permission for the requested resource (HTTP 403)."""

    def __init__(
        self,
        message: str = "Access to this Amadeus resource is forbidden.",
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=403, response_body=response_body)


class AmadeusNotFoundException(AmadeusException):
    """Raised when the requested Amadeus resource does not exist (HTTP 404)."""

    def __init__(
        self,
        message: str = "Amadeus resource not found.",
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=404, response_body=response_body)


class AmadeusRateLimitException(AmadeusException):
    """Raised when the Amadeus rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Amadeus API rate limit exceeded. Please retry later.",
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status_code=429, response_body=response_body)


class AmadeusServerException(AmadeusException):
    """Raised when Amadeus returns a 5xx server error (HTTP 500+)."""

    def __init__(
        self,
        message: str = "Amadeus API server error.",
        status_code: int = 500,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message, status_code=status_code, response_body=response_body
        )


class AmadeusTimeoutException(AmadeusException):
    """Raised when a request to the Amadeus API times out."""

    def __init__(self, message: str = "Amadeus API request timed out.") -> None:
        super().__init__(message=message, status_code=None)


class AmadeusConnectionException(AmadeusException):
    """Raised when a network-level connection to the Amadeus API fails."""

    def __init__(self, message: str = "Failed to connect to the Amadeus API.") -> None:
        super().__init__(message=message, status_code=None)
