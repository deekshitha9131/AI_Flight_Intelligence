import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Attach an X-Process-Time header to the response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response
