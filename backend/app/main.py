from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure the backend root directory is in sys.path for app module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from .ai.llm_provider import build_llm_provider
from .ai.model_loader import ModelLoader
from .api.v1.endpoints.health import router as health_router
from .api.v1.router import router as v1_router
from .core.config import get_settings
from .core.logging import setup_logging
from .database.base import Base
from .database.session import check_database_connection, engine
from .exceptions.base import AppException
from .exceptions.handlers import (
    app_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from .integrations.amadeus.client import AmadeusClient
from .middleware.process_time import ProcessTimeMiddleware
from .middleware.request_logging import RequestLoggingMiddleware

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Handle application startup and shutdown events."""
    setup_logging()
    logger.info("Starting application: %s", settings.app_name)

    if check_database_connection():
        logger.info("Database connection healthy")

        if settings.environment == "production":
            logger.info("Skipping automatic table creation in production")
        else:
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error("Failed to create database tables: %s", e)
    else:
        logger.warning("Database connection check failed")

    amadeus_client: AmadeusClient | None = None
    if settings.flight_provider.lower() == "amadeus":
        try:
            amadeus_client = AmadeusClient.from_settings()
            app.state.amadeus = amadeus_client
            logger.info("Amadeus Flight Provider Enabled")
        except Exception as err:
            logger.warning("Failed to initialize AmadeusClient (%s). Falling back to Mock Flight Provider.", err)
            logger.info("Mock Flight Provider Enabled")
    else:
        logger.info("Mock Flight Provider Enabled")

    model_loader = ModelLoader()
    model_loader.load()
    app.state.model_loader = model_loader
    logger.info(
        "ModelLoader initialised | version=%s fallback=%s",
        model_loader.model_version,
        model_loader.is_fallback,
    )

    llm_provider = build_llm_provider()
    app.state.llm_provider = llm_provider
    logger.info("LLMProvider initialised: %s", type(llm_provider).__name__)

    try:
        yield
    finally:
        if amadeus_client is not None:
            await amadeus_client.close()
        logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    description="Production-ready backend foundation for the AI Flight Intelligence Platform.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router)
app.include_router(v1_router)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    """Return a simple welcome payload for the API root."""
    return {"message": "AI Flight Intelligence Platform API"}


