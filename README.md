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

## Running the Project with External Services

To fully demonstrate the AI capabilities, you'll need to obtain API keys for the external services:

1. **Google OAuth Credentials**: 
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable the Gmail API
   - Create OAuth 2.0 Client ID credentials (Desktop app)
   - Add `http://localhost:8000/api/v1/auth/google/callback` as an authorized redirect URI
   - Copy the Client ID and Client Secret to `backend/.env`

2. **Anthropic API Key** (for AI analysis and draft generation):
   - Sign up at [Anthropic Console](https://console.anthropic.com/)
   - Create an API key
   - Add it to `backend/.env` as `ANTHROPIC_API_KEY`

3. **OpenAI API Key** (for email embeddings in RAG):
   - Sign up at [OpenAI Platform](https://platform.openai.com/)
   - Create an API key
   - Add it to `backend/.env` as `OPENAI_API_KEY`

Once you have these credentials:
1. Copy environment templates:
   ```
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
2. Edit `backend/.env` to add your actual API keys (replace the placeholder values)
3. Start the stack:
   ```
   docker compose up --build
   ```
4. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## AI/RAG Flow Demonstration

To see the complete AI pipeline in action:

1. Log in with your Google account via the frontend
2. Wait for or trigger email synchronization (emails will appear in your inbox)
3. Click on any email to view its details
4. Click "Generate Draft" to trigger:
   - AI analysis of the email content (classification, intent, sentiment, etc.)
   - RAG retrieval of similar emails from your history
   - Context-aware draft generation using Claude
   - Display of the generated draft in the editor
5. Edit the draft as needed, then click "Approve" to finalize it

Note: The system implements a strict human-approval gate - no AI-generated draft is ever sent without explicit user approval.

## Project Status

**Implementation Complete: Core AI Email Pipeline Functional**
The following features are fully implemented and tested:

- ✅ User Authentication (Google OAuth)
- ✅ Email Storage & Retrieval (PostgreSQL)
- ✅ AI Email Analysis (Classification, Intent, Urgency, Sentiment, Entities, Summary)
- ✅ RAG Pipeline (Chunking, Embedding Storage, Similarity Search)
- ✅ AI-Powered Draft Generation with Human Approval Workflow
- ✅ Email Listing, Search, and Thread Views
- ✅ Draft Editing, Saving, and Approval
- ✅ Comprehensive Unit Test Coverage
- ✅ Dockerized Development Environment

Subsequent phases (refinement, performance optimization, additional features) are in progress but the core AI email assistant pipeline is fully functional.
