"""Request logging middleware.

Logs one structured line per request: method, path, status code, and
latency in milliseconds. Deliberately does NOT log request or response
bodies — email content must never land in general application logs
(per the frozen logging design); that belongs in the access-restricted
audit log, written by services at the point of a safety-critical action,
not sniffed out of HTTP traffic here.

Must run *inside* RequestIDMiddleware (registered before it in
app/main.py) so that by the time this middleware logs, structlog's
contextvars already carry the request_id — this middleware never
handles request IDs itself, it relies entirely on that binding.
"""

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
