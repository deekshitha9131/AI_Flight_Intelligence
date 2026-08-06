"""Alembic migration environment.

Two things make this different from Alembic's stock generated env.py:

1. The database URL is never duplicated into alembic.ini. It's read
   from the same `Settings` object the running application uses
   (app/core/config.py) — one source of truth for "which database,"
   whether that's local dev, CI, staging, or production.
2. The project's engine is async (asyncpg), so `alembic upgrade head`
   has to run migrations through an async connection. Alembic's
   migration execution itself is synchronous internally; the standard
   pattern (used here) is to open an async connection and use
   `connection.run_sync(...)` to bridge into Alembic's sync migration
   runner for the duration of one connection.

Autogenerate support (`alembic revision --autogenerate`) depends on
`target_metadata` reflecting every model that exists — which is why
every ORM model must be imported (directly or transitively) via
app/infrastructure/database/models before this file builds
`target_metadata`. A model that exists but was never imported here is
invisible to autogenerate: it will silently be treated as "not part of
the schema" and diffed for deletion.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.infrastructure.database.base import Base

# Import every ORM model so Base.metadata is fully populated before
# autogenerate compares it against the live database schema. Models
# themselves live in app/infrastructure/database/models/ (added in a
# later implementation phase) and must be imported here — directly or
# via that package's __init__.py re-exporting them — or autogenerate
# will not see them at all.
from app.infrastructure.database import models  # noqa: F401,E402

# Alembic Config object, providing access to values within alembic.ini.
config = context.config

# Interpret alembic.ini's logging configuration (console formatting,
# per-logger levels) — this is what makes `alembic upgrade head` output
# readable instead of silent or overwhelming.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what autogenerate diffs the live database against. Because
# Base.metadata was built with an explicit naming convention (see
# app/infrastructure/database/base.py), every constraint Alembic
# generates gets a deterministic name — not a dialect-assigned one that
# would make future diffs noisy.
target_metadata = Base.metadata

# Source the connection URL from the application's own settings rather
# than alembic.ini, so migrations always target whatever database the
# app itself would connect to in the current environment.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live DB connection.

    Used by `alembic upgrade head --sql`, e.g. to generate a SQL script
    for a DBA to review and apply manually, rather than letting Alembic
    connect and apply it directly.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic against an already-open synchronous-facing connection.

    `compare_type=True` and `compare_server_default=True` matter
    specifically for this project's column types: without them,
    autogenerate would miss a change from `VARCHAR(255)` to
    `VARCHAR(500)`, or a change to a `server_default=func.now()`
    timestamp default, and silently produce an incomplete migration.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open an async engine, bridge into Alembic's sync migration runner.

    `poolclass=pool.NullPool` — migrations are a single short-lived
    connection, not a long-running pooled workload; pooling here would
    only add overhead and a connection that outlives the migration run
    for no benefit.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — the default, connecting to a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
