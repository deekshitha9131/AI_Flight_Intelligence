"""Structured logging configuration.

Configures structlog to emit one consistent JSON schema across the API,
Celery workers, and (in later phases) the AI orchestration layer —
`timestamp`, `level`, `logger`, `event`, plus whatever context a caller
binds in (`request_id`, `user_id`, etc.). This uniformity is what makes
cross-service tracing possible later; it is set up once, here, rather
than each module configuring its own logger independently.
"""

import logging
import sys
from typing import cast

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structlog + stdlib logging for the current process.

    Called once at application startup (see app/main.py lifespan) and
    once per Celery worker process (see app/core/celery_app.py in a
    later phase) — anywhere a new Python process needs consistent logs.
    """
    settings = get_settings()

    # In development, render human-readable colored output for local
    # debugging. In every other environment, render strict JSON — log
    # aggregation tooling needs a stable machine-parseable shape, not
    # something optimized for a terminal.
    # Note: `format_exc_info` is deliberately omitted from this chain.
    # When structlog is wired into stdlib logging via ProcessorFormatter
    # (below), exception rendering is handled once, downstream, by the
    # renderer itself — including format_exc_info here as well would
    # double up on exception formatting and produce a runtime warning.
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.app_env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if settings.app_debug else logging.INFO)

    # Quiet noisy third-party loggers that would otherwise flood output
    # at INFO level without adding diagnostic value day-to-day.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.app_debug else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger.

    Thin wrapper so call sites do `get_logger(__name__)` instead of
    importing structlog directly everywhere — keeps the logging library
    choice swappable in one place if it ever needs to change.

    The cast is necessary because structlog.get_logger's own type stubs
    return `Any` — structlog's factory pattern means the concrete
    logger type isn't statically knowable, but we configure
    `wrapper_class=structlog.stdlib.BoundLogger` explicitly above, so
    asserting that type here is accurate, not a guess.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
