#!/usr/bin/env bash
# ==============================================================================
# Database initialization.
#
# Waits for the Postgres container to be ready to accept connections,
# then applies every migration up to head. Safe to run repeatedly:
# `alembic upgrade head` is a no-op if the database is already current,
# so this can be part of a routine `make db-init` after pulling new
# migrations, not just a first-time setup step.
#
# Usage:
#   ./scripts/dev/init_db.sh
# ==============================================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

MAX_WAIT_SECONDS=60
ELAPSED=0

echo "Waiting for postgres to be ready..."
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-ai_email_assistant}" > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: postgres did not become ready within ${MAX_WAIT_SECONDS}s." >&2
        echo "Is the stack running? Try: docker compose up -d postgres" >&2
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo "  ...still waiting (${ELAPSED}s elapsed)"
done

echo "postgres is ready. Applying migrations..."
docker compose exec -T api alembic upgrade head

echo "Database initialization complete."
