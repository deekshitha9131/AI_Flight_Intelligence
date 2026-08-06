# ==============================================================================
# Makefile — thin wrappers around docker compose, alembic, and the
# backend/frontend tooling (pytest, ruff, black, mypy, eslint, prettier,
# vitest).
#
# Migration and quality commands run *inside* the api/frontend
# containers (via `docker compose exec ...`) rather than requiring a
# local Python/Node environment — the only hard requirement to run any
# of this is Docker. This is also exactly what CI runs (see
# .github/workflows/ci.yml), just against containers instead of GitHub
# Actions' hosted runners — "works with make test" and "works in CI"
# are meant to be the same claim.
# ==============================================================================

.PHONY: help up down logs db-init migrate migrate-create migrate-down migrate-history migrate-current \
        test test-unit test-integration lint format typecheck check \
        frontend-lint frontend-format frontend-typecheck frontend-test

help:
	@echo "Stack:"
	@echo "  make up                        Start the full stack (detached)"
	@echo "  make down                      Stop the full stack"
	@echo "  make logs                      Follow logs from every container"
	@echo ""
	@echo "Database:"
	@echo "  make db-init                   Wait for Postgres, then apply all migrations"
	@echo "  make migrate                   Apply all pending migrations (alembic upgrade head)"
	@echo "  make migrate-create name=\"...\" Autogenerate a new migration from model changes"
	@echo "  make migrate-down              Roll back the most recent migration"
	@echo "  make migrate-history           Show the full migration history"
	@echo "  make migrate-current           Show the currently applied migration"
	@echo ""
	@echo "Backend quality:"
	@echo "  make test                      Run the full backend test suite (unit + integration)"
	@echo "  make test-unit                 Run only fast, infra-free unit tests"
	@echo "  make test-integration          Run only integration tests (requires live Postgres/Redis)"
	@echo "  make lint                      Run ruff against the backend"
	@echo "  make format                    Apply black formatting to the backend"
	@echo "  make typecheck                 Run mypy against the backend"
	@echo "  make check                     Run lint + typecheck + test together (mirrors CI)"
	@echo ""
	@echo "Frontend quality:"
	@echo "  make frontend-lint             Run eslint against the frontend"
	@echo "  make frontend-format           Apply prettier formatting to the frontend"
	@echo "  make frontend-typecheck        Run tsc --noEmit against the frontend"
	@echo "  make frontend-test             Run the frontend test suite (vitest)"

# ------------------------------------------------------------------
# Stack
# ------------------------------------------------------------------

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------

db-init:
	./scripts/dev/init_db.sh

migrate:
	docker compose exec api alembic upgrade head

migrate-create:
	@if [ -z "$(name)" ]; then \
		echo "ERROR: usage: make migrate-create name=\"add drafts table\"" >&2; \
		exit 1; \
	fi
	docker compose exec api alembic revision --autogenerate -m "$(name)"

migrate-down:
	docker compose exec api alembic downgrade -1

migrate-history:
	docker compose exec api alembic history --verbose

migrate-current:
	docker compose exec api alembic current --verbose

# ------------------------------------------------------------------
# Backend quality
# ------------------------------------------------------------------

test:
	docker compose exec api pytest -v

test-unit:
	docker compose exec api pytest tests/unit -v

test-integration:
	docker compose exec api pytest tests/integration -v -m integration

lint:
	docker compose exec api ruff check app tests

format:
	docker compose exec api black app tests

typecheck:
	docker compose exec api mypy app

check: lint typecheck test

# ------------------------------------------------------------------
# Frontend quality
# ------------------------------------------------------------------

frontend-lint:
	docker compose exec frontend npm run lint

frontend-format:
	docker compose exec frontend npm run format

frontend-typecheck:
	docker compose exec frontend npm run typecheck

frontend-test:
	docker compose exec frontend npm run test
