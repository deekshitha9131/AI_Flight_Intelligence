"""Request ID middleware.

Assigns every request a unique ID — reusing one supplied by the caller
via the `X-Request-ID` header if present (so a request can be traced
across a browser, this API, and any upstream proxy that already set
one), otherwise generating a fresh one. The ID is:

1. Bound into `app.core.request_context` (a plain contextvar).
2. Bound into structlog's contextvars (so every log line emitted while
   handling this request includes it automatically — no call site has
   to pass it explicitly, see app/core/logging_config.py's
   `merge_contextvars` processor).
3. Echoed back on the response header, so a client or browser dev tools
   can correlate a specific HTTP response with server-side log lines.

This must be the outermost application middleware (registered last in
app/main.py, per Starlette's middleware-ordering semantics) so that the
request ID is available to every other middleware and to the exception
handlers, no matter where in the stack something fails.
"""

from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER
from app.core.request_context import generate_request_id, set_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming_id if incoming_id else generate_request_id()

        set_request_id(request_id)
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response = await call_next(request)
        finally:
            # Clear on the way out regardless of success/failure, so a
            # future request handled by a reused worker/task never
            # inherits a stale request_id from a prior request.
            structlog.contextvars.clear_contextvars()

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
