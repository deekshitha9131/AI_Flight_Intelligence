from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from app.ai.llm_provider import build_llm_provider
from app.ai.model_loader import ModelLoader
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.database.base import Base
from app.database.session import check_database_connection, engine
from app.exceptions.base import AppException
from app.exceptions.handlers import (
    app_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.integrations.amadeus.client import AmadeusClient
from app.middleware.process_time import ProcessTimeMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from fastapi import FastAPI
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

        # Create all database tables (Development Only)
        print("=" * 80)
        for table_name, table in Base.metadata.tables.items():
            print(f"\nTABLE: {table_name}")
            for idx in table.indexes:
                print(f"INDEX: {idx.name} -> {[c.name for c in idx.columns]}")
        print("=" * 80)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    else:
        logger.warning("Database connection check failed")

    amadeus_client = AmadeusClient.from_settings()
    app.state.amadeus = amadeus_client
    logger.info("AmadeusClient initialised (base_url=%s).", settings.amadeus_base_url)

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

    yield

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


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    """Return a simple welcome payload for the API root."""
    return {"message": "AI Flight Intelligence Platform API"}
