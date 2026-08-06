"""Application factory and entrypoint.

`create_app()` assembles the FastAPI application from its constituent
parts (settings, lifespan, middleware, exception handlers, routers).
Everything else in this codebase plugs into the app built here; nothing
downstream constructs its own FastAPI instance.

Run directly for local (non-Docker) development:
    python -m app.main
In every other context (Docker, production), uvicorn is invoked against
`app.main:app` directly by the container CMD (see backend/Dockerfile),
which does not execute this file's `__main__` block at all.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.constants import (
    API_V1_PREFIX,
    HEALTH_STATUS_OK,
    OPENAPI_TAGS_METADATA,
    PROJECT_DESCRIPTION,
    PROJECT_NAME,
    PROJECT_VERSION,
    OpenAPITags,
)
from app.core.logging_config import configure_logging
from app.domain.exceptions import DomainError
from app.infrastructure.cache.redis_client import close_redis_client, create_redis_client
from app.infrastructure.database.engine import create_db_engine, dispose_engine
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.vector.extension import ensure_pgvector_extension
from app.presentation.api.v1.router import api_router
from app.presentation.exception_handlers import (
    domain_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.presentation.middleware.logging import RequestLoggingMiddleware
from app.presentation.middleware.request_id import RequestIDMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown, as a single lifespan context manager.

    FastAPI's `lifespan` replaces the older `@app.on_event("startup")` /
    `@app.on_event("shutdown")` decorators (deprecated) — startup is
    everything before `yield`, shutdown is everything after it. Both
    live in one function so the resources acquired at startup and
    released at shutdown are visibly paired, rather than split across
    two separately-registered callbacks that a future edit could let
    drift out of sync.
    """
    settings = get_settings()
    configure_logging()

    logger.info("startup_begin", app_env=settings.app_env)

    # --- Startup ---
    # Build the database engine + session factory once per process and
    # attach them to app.state — the DI container's provider functions
    # (app/core/di_container.py) read from app.state, never construct
    # these directly.
    engine = create_db_engine(settings)
    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)

    # Ensure pgvector's extension is installed before anything else
    # touches the database — see infrastructure/vector/extension.py for
    # why this is idempotent and safe to run on every startup.
    async with app.state.db_session_factory() as bootstrap_session:
        await ensure_pgvector_extension(bootstrap_session)

    redis_client = create_redis_client(settings)
    app.state.redis_client = redis_client

    # One shared httpx client for the whole process, for outbound calls
    # to external services (currently: Google's OAuth endpoints — see
    # app/infrastructure/gmail/oauth_client.py). Reusing one client
    # keeps its connection pool warm across requests, the same reason
    # the DB engine and Redis client are built once here rather than
    # per-request.
    http_client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = http_client

    logger.info("startup_complete", app_env=settings.app_env)

    yield

    # --- Shutdown ---
    # Release resources in the reverse order they were acquired, so
    # nothing is left holding a connection to an already-torn-down
    # dependency.
    logger.info("shutdown_begin")

    await http_client.aclose()
    await close_redis_client(redis_client)
    await dispose_engine(engine)

    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=PROJECT_NAME,
        description=PROJECT_DESCRIPTION,
        version=PROJECT_VERSION,
        openapi_tags=OPENAPI_TAGS_METADATA,
        # Docs are useful in every environment except production, where
        # exposing the full schema/interactive explorer publicly is an
        # unnecessary information-disclosure surface for no real benefit.
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # --- CORS ---
    # Restricted to the explicit origin list from settings — never "*"
    # once credentials (the session cookie, added in a later phase) are
    # involved, since browsers reject wildcard origins on credentialed
    # requests anyway.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request logging + request ID ---
    # Starlette wraps middleware in reverse of the order added — the
    # LAST call to add_middleware ends up OUTERMOST (its code runs
    # first on the way in, last on the way out). RequestIDMiddleware is
    # added last so it wraps RequestLoggingMiddleware: the request ID
    # is bound into structlog's context before the logging middleware's
    # dispatch ever runs, so every log line it emits already carries it
    # via the `merge_contextvars` processor — the logging middleware
    # itself never has to know a request ID exists.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # --- Exception handlers ---
    # Order doesn't matter to FastAPI here (it dispatches by exception
    # type specificity), but registering the most specific handlers
    # first keeps this list readable as a hierarchy.
    #
    # The `type: ignore[arg-type]` on each line below is a known,
    # widely-hit mypy/FastAPI interaction: Starlette's stub for
    # add_exception_handler types the handler parameter contravariantly
    # against the base `Exception`, so a handler typed against a
    # specific subclass (DomainError, RequestValidationError,
    # HTTPException) technically fails variance checking — even though
    # this is the exact registration pattern shown in FastAPI's own
    # documentation and works correctly at runtime.
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # --- Routers ---
    app.include_router(api_router, prefix=API_V1_PREFIX)

    # --- Root liveness endpoint ---
    # Deliberately NOT versioned and NOT under api_router: this is what
    # container orchestration (see backend/Dockerfile HEALTHCHECK and
    # docker-compose.yml) polls to decide "is this process alive at
    # all." It must answer instantly with no dependency checks — that's
    # what /api/v1/health/ready is for (see routers/health.py).
    @app.get("/health", tags=[OpenAPITags.HEALTH], summary="Liveness check")
    async def liveness_check() -> dict[str, Any]:
        return {"status": HEALTH_STATUS_OK}

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug,
    )
