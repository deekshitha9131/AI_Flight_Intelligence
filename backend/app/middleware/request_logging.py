import logging
import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request metadata and response status for each HTTP interaction."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            "method=%s path=%s status=%s client_ip=%s process_time=%.4fs",
            request.method,
            request.url.path,
            response.status_code,
            client_ip,
            process_time,
        )
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response
