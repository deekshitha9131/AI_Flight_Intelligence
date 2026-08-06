"""Request-scoped context variables.

A `contextvars.ContextVar` is isolated per asyncio task, which is exactly
the lifetime of a single request under Starlette/FastAPI — this is what
lets `RequestIDMiddleware` bind a request ID once, and have it show up
automatically in every structlog line and every error response produced
while handling that request, without threading it through every
function signature in between.

This module only defines the context variable and thin accessors.
Binding it into structlog's own context (so log processors pick it up)
is the middleware's job (app/presentation/middleware/request_id.py) —
kept separate so this module has no dependency on structlog at all.
"""

import contextvars
import uuid

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def generate_request_id() -> str:
    """Generate a new request ID. Exposed separately from `set_request_id`
    so callers (middleware, tests) can generate first and log/inspect
    the value before binding it."""
    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    """Bind a request ID to the current task's context."""
    _request_id_var.set(request_id)


def get_request_id() -> str:
    """Return the current request's ID, generating a fallback if none was bound.

    The fallback path matters for code that raises outside the normal
    middleware-wrapped request cycle (e.g. a startup-time error) — it
    must never crash trying to report an error just because there's no
    request ID yet.
    """
    return _request_id_var.get() or generate_request_id()
