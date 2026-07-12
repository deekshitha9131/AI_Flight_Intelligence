from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base exception for application-defined errors."""

    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource cannot be found."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=404, details=details)


class ValidationException(AppException):
    """Raised when request data is invalid."""

    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=400, details=details)


class UnauthorizedException(AppException):
    """Raised when authentication is required or invalid."""

    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=401, details=details)


class ForbiddenException(AppException):
    """Raised when the requester is not allowed to perform an action."""

    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=403, details=details)


class ConflictException(AppException):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=409, details=details)


class DatabaseException(AppException):
    """Raised when a database operation fails."""

    def __init__(self, message: str = "Database operation failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=503, details=details)


class ExternalAPIException(AppException):
    """Raised when an external service call fails."""

    def __init__(self, message: str = "External service failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, status_code=502, details=details)
