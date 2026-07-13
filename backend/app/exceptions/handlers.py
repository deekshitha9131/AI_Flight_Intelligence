from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.base import AppException

logger = logging.getLogger(__name__)


def build_error_response(
    *,
    message: str,
    error: str,
    status_code: int,
    request: Request,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Construct a standardized error payload for API responses."""
    payload: dict[str, Any] = {
        "success": False,
        "message": message,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
    }
    if details:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application-defined exceptions."""
    logger.warning("Application exception: %s", exc.message, exc_info=False)
    return build_error_response(
        message=exc.message,
        error=exc.__class__.__name__,
        status_code=exc.status_code,
        request=request,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.warning("HTTP exception: %s", exc, exc_info=False)
    return build_error_response(
        message="Request failed",
        error="HTTPException",
        status_code=getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR),
        request=request,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request validation failures."""

    errors = []

    for err in exc.errors():
        clean = dict(err)

        if "ctx" in clean:
            clean["ctx"] = {k: str(v) for k, v in clean["ctx"].items()}

        errors.append(clean)

    logger.warning("Validation error: %s", errors)

    return build_error_response(
        message="Validation failed",
        error="ValidationError",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request=request,
        details={"errors": errors},
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database failures raised by SQLAlchemy."""
    logger.exception("SQLAlchemy error: %s", exc)
    return build_error_response(
        message="Database operation failed",
        error="DatabaseException",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        request=request,
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle uncaught exceptions as a last line of defense."""
    logger.exception("Unexpected exception: %s", exc)
    return build_error_response(
        message="Internal server error",
        error="InternalServerError",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=request,
    )
