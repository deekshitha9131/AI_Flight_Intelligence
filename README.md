# AI Email Assistant Platform

An AI-native assistant that triages, understands, and drafts replies to Gmail email — with a human-approval gate on every outbound message. Built as a production-inspired, single-developer portfolio project.

## Architecture

This repository implements the architecture frozen across three design documents (see `docs/architecture/`):

1. **Product & System Architecture** — vision, requirements, high-level design.
2. **System Design** — database schema, REST API contracts, core flows.
3. **Simplified Engineering Blueprint** — Clean Architecture layout, reduced service/repository count, CrewAI routing logic, final technology stack.

Core invariants that no implementation may violate:
- No AI-generated reply is ever sent without explicit human approval.
- The Gmail send call always happens outside any database transaction.
- Every draft/approval/send/token action is audit-logged.
- Classification always gates AI generation cost — most emails are handled by a single LLM call; only complex threads trigger a full CrewAI Flow.
- Append-only tables (`draft_versions`, `approvals`, `audit_log`, `classifications`) are never updated or deleted in place.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | PostgreSQL + pgvector |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Task Queue | Celery |
| Cache / Broker | Redis |
| AI Orchestration | CrewAI |
| LLM Provider | Claude (Anthropic API) |
| Frontend | React + Vite + TypeScript + TailwindCSS |
| Containerization | Docker + Docker Compose |

## Repository Structure

```
ai-email-assistant/
├── backend/          # FastAPI service — Clean Architecture (presentation, application, domain, infrastructure, ai, workers)
├── frontend/          # React + Vite + TypeScript SPA
├── database/           # Migration docs, seed data, schema documentation
├── infra/               # Docker Compose overrides, nginx reverse proxy, environment templates
├── tests/                 # Cross-cutting end-to-end and API contract tests
├── scripts/               # Operational and local dev utility scripts
├── docs/                   # Architecture documents, ADRs, runbooks
└── .github/workflows/      # CI/CD pipelines
```

See `backend/README.md` (added in a later phase) for backend-specific layer documentation, and `docs/architecture/` for the full frozen design.

## Local Development Setup

**Prerequisites:** Docker and Docker Compose installed.

1. Copy environment templates:
   ```
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
2. Fill in `backend/.env` with your Google OAuth client credentials and Anthropic API key.
3. Start the stack:
   ```
   docker compose up --build
   ```
4. Backend API available at `http://localhost:8000`, frontend at `http://localhost:5173`.

Database migrations, seed scripts, and application logic are introduced in subsequent implementation phases — this repository currently contains only the project scaffold, configuration, and tooling.

## Development Workflow

- Install pre-commit hooks: `pre-commit install` (run once per clone).
- Backend: dependencies managed via `backend/pyproject.toml`; install with `pip install -e ".[dev]"` inside a virtual environment for local (non-Docker) development.
- Frontend: dependencies managed via `frontend/package.json`; install with `npm install`.

## Project Status

**Phase 1 — Repository & Project Structure: complete.**
Subsequent phases (domain layer, infrastructure layer, API layer, AI layer, frontend implementation) proceed strictly within the boundaries defined in `docs/architecture/`.
