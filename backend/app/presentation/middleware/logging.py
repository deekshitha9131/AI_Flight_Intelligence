import time
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_method = logger.warning if response.status_code >= 500 else logger.info
        log_method(
            "http_request",
            method=request.method,
            path=request.url.path,
            query=request.url.query or None,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
