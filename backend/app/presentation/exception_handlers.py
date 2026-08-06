"""Exception handlers.

Maps every exception type the API can raise onto the single error
envelope defined by the frozen system design:

    { "error": { "code": "...", "message": "...", "request_id": "..." } }

Registered once, in app/main.py's application factory — no router or
service ever formats an error response by hand.
"""

from typing import Any

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id
from app.domain.exceptions import DomainError

logger = structlog.get_logger(__name__)


def _error_envelope(code: str, message: str, request_id: str) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handle every business-rule violation raised by the domain layer.

    Each DomainError subclass carries its own `http_status` and `code`
    (see app/domain/exceptions/base.py) — this handler is generic across
    all of them, so a new domain exception type never needs a new
    handler registered, only a new subclass.
    """
    request_id = get_request_id()
    logger.warning(
        "domain_error",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_error_envelope(exc.code, exc.message, request_id),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request-shape validation failures (malformed body/query/path params).

    Distinct from BusinessValidationError — this fires before a request
    ever reaches a route handler, for input that doesn't match the
    declared Pydantic schema at all (wrong type, missing required field).
    """
    request_id = get_request_id()
    field_errors = [
        {"field": ".".join(str(loc) for loc in err["loc"] if loc != "body"), "issue": err["msg"]}
        for err in exc.errors()
    ]
    logger.info(
        "validation_error",
        path=request.url.path,
        errors=field_errors,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request could not be validated.",
                "request_id": request_id,
                "fields": field_errors,
            }
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle explicit HTTPException raises (e.g. `raise HTTPException(404, ...)`).

    Wraps Starlette's default plain-text/JSON shape into the same
    envelope every other error path uses, so a client never has to
    branch on which handler produced a given error.
    """
    request_id = get_request_id()
    logger.info(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_envelope("HTTP_ERROR", str(exc.detail), request_id),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything not already handled above.

    Logs the full exception server-side with a stack trace, but returns
    only a generic message to the client — internal detail (stack
    traces, exception class names, file paths) must never leak into an
    API response.
    """
    request_id = get_request_id()
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        request_id=request_id,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_envelope(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred. Please try again.",
            request_id,
        ),
    )
