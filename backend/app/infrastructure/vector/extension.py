"""pgvector extension bootstrap.

The `pgvector/pgvector` Docker image (see docker-compose.yml) ships the
extension's files on disk, but PostgreSQL still requires `CREATE
EXTENSION vector` to be run once per database before the `vector` type
or any similarity operators are usable. This is idempotent
(`IF NOT EXISTS`) and cheap, so it's run once at application startup
(see app/main.py's lifespan) rather than requiring a manual operational
step — the same guarantee a migration would give, without needing
Alembic wired up before this phase.

Once Alembic migrations exist (a later phase), the very first migration
should also issue this statement, so a fresh database created purely
via `alembic upgrade head` (no application startup involved, e.g. in
CI) ends up in the same state. The two are complementary, not
redundant: this covers "app started against a database that hasn't run
migrations yet" during early development; the migration covers
production/CI provisioning.
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


async def ensure_pgvector_extension(session: AsyncSession) -> None:
    """Create the pgvector extension if it doesn't already exist, then commit."""
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await session.commit()
    logger.info("pgvector_extension_ready")
