# AI Email Assistant Platform — Final Engineering Blueprint (v1.0)

**MASTER REFERENCE DOCUMENT.** Builds on the frozen architecture (Doc 1) and system design (Doc 2). No decisions from those documents are revisited. This document is the implementation contract — every future coding prompt must conform to it.

---

## 1. FINAL FOLDER STRUCTURE

### 1.1 Repository Root

```
ai-email-assistant/
├── backend/              # FastAPI application, Clean Architecture layers
├── ai/                   # CrewAI agents, prompts, embedding/RAG logic
├── frontend/             # React SPA
├── database/             # Migrations, seed scripts, schema documentation
├── infra/                # Docker, docker-compose, reverse proxy, deployment configs
├── tests/                # Cross-cutting test suites (e2e, contract)
├── scripts/              # One-off operational and dev-utility scripts
├── docs/                 # Architecture docs (this series), ADRs, runbooks
├── .github/workflows/    # CI/CD pipelines
├── .env.example
└── README.md
```

**Rationale:** `ai/` is a top-level sibling to `backend/`, not nested inside it. CrewAI orchestration has a distinct dependency footprint (agent frameworks, prompt assets) and its own testing/versioning cadence — coupling it inside `backend/` would blur ownership boundaries as the AI layer evolves faster than the API layer.

---

### 1.2 `backend/` — Clean Architecture Layout

```
backend/
├── app/
│   ├── presentation/        # API layer — FastAPI routers, request/response schemas
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── routers/         # One router module per resource (threads, drafts, contacts, analytics, auth, settings)
│   │   │   │   └── schemas/         # Pydantic request/response models (DTOs) — never domain entities leaked directly
│   │   │   └── websocket/           # WS connection handler, channel management
│   │   └── middleware/              # Auth, logging, exception handling, request ID, rate limiting, CORS, security headers
│   │
│   ├── application/         # Use-case orchestration — the "what happens" layer
│   │   ├── services/                # Service classes (see §5) — orchestrate repositories + domain logic per use case
│   │   ├── dto/                     # Internal data-transfer objects between layers (not the same as API schemas)
│   │   └── interfaces/              # Abstract repository/service contracts (ports) — application depends on these, not on infrastructure
│   │
│   ├── domain/               # Pure business logic — zero framework dependencies
│   │   ├── entities/                 # Core domain objects (User, Thread, Draft, Contact, AgentRun...)
│   │   ├── value_objects/            # Immutable value types (EmailAddress, PriorityScore, TokenBudget)
│   │   ├── enums/                    # DraftStatus, SyncStatus, IntentType, etc.
│   │   └── exceptions/               # Domain-specific exceptions (DraftAlreadySentError, InvalidTransitionError)
│   │
│   ├── infrastructure/       # Concrete implementations of application/interfaces
│   │   ├── database/
│   │   │   ├── models/                # SQLAlchemy ORM models (mirror Doc 2 schema exactly)
│   │   │   ├── repositories/          # Concrete repository implementations (see §6)
│   │   │   └── unit_of_work.py        # Transaction boundary implementation
│   │   ├── cache/                     # Redis client wrapper, cache-aside helpers
│   │   ├── queue/                     # Celery app config, task registration
│   │   ├── gmail/                     # Gmail API client wrapper, OAuth handshake logic
│   │   ├── vector_store/              # ChromaDB client wrapper
│   │   └── external/                  # Any other third-party client adapters
│   │
│   ├── workers/               # Celery task definitions, segmented by pool
│   │   ├── sync_tasks/
│   │   ├── embedding_tasks/
│   │   ├── classification_tasks/
│   │   ├── agent_orchestration_tasks/
│   │   ├── send_tasks/
│   │   └── analytics_tasks/
│   │
│   ├── core/                  # Cross-cutting concerns
│   │   ├── config.py                  # Settings loader (see §8)
│   │   ├── di_container.py            # Dependency injection wiring
│   │   ├── security.py                # Token encryption, session handling helpers
│   │   └── logging_config.py          # Structured logging setup
│   │
│   └── main.py                # FastAPI app factory — assembles routers, middleware, DI container
│
├── alembic/                   # DB migration scripts (paired with database/ documentation)
├── pyproject.toml
└── Dockerfile
```

**Layer dependency rule (enforced, not optional):** `presentation → application → domain ← infrastructure`. Domain has zero inbound dependencies from any other layer. Infrastructure implements interfaces defined in `application/interfaces/` — it never gets imported directly by `domain/`.

---

### 1.3 `ai/` — AI System Layout

```
ai/
├── agents/
│   ├── triage_agent.py             # Definition, role, goal, backstory for the Triage Agent
│   ├── retrieval_agent.py          # Context Retrieval Agent
│   ├── drafting_agent.py           # Drafting Agent
│   ├── critic_agent.py             # Critic/Reviewer Agent
│   └── crew_definitions.py         # CrewAI Crew assembly — wires agents + task sequence
│
├── prompts/
│   ├── templates/                  # Versioned prompt templates per agent (plain text/YAML, not embedded in code)
│   └── prompt_registry.py          # Loads/versions templates, exposes them to agents
│
├── embeddings/
│   ├── embedding_client.py         # Wraps the embedding model call
│   └── chunking_strategy.py        # Email/thread chunking rules before embedding
│
├── rag/
│   ├── retriever.py                # Query construction, metadata filtering, top-k resolution
│   └── context_builder.py          # Assembles retrieved content + memory into agent-ready context
│
├── memory/
│   ├── contact_memory_service.py   # Reads/refreshes memory_contact
│   └── thread_memory_service.py    # Reads/refreshes memory_thread
│
├── style_learning/
│   └── style_profile_builder.py    # Derives tone/style signal from historical sent mail + edit deltas
│
└── evaluation/
    └── draft_quality_checks.py     # Programmatic checks run alongside the Critic Agent (grounding, length, tone drift)
```

**Rationale:** Prompts live as versioned template assets, not inline strings in agent code — this is what makes prompt iteration a content change, not a code deploy, and it's the only way prompt A/B testing stays sane later.

---

### 1.4 `frontend/`

```
frontend/
├── src/
│   ├── pages/                  # Route-level components (Inbox, ThreadDetail, Analytics, Settings)
│   ├── components/             # Reusable UI components (ThreadListItem, DraftEditor, ApprovalBar, ConfidenceBadge)
│   ├── features/               # Feature-scoped logic (inbox/, drafts/, analytics/, auth/) — hooks + local state per feature
│   ├── api/                    # Typed API client layer (one module per backend resource, matches Doc 2 endpoint list)
│   ├── ws/                     # Websocket connection manager, event dispatch
│   ├── store/                  # Global client state (session, notifications)
│   ├── styles/
│   └── App.tsx
├── public/
├── tests/
├── package.json
└── Dockerfile
```

---

### 1.5 `database/`

```
database/
├── migrations/          # Alembic migration files (source of truth for schema evolution)
├── seed/                 # Dev/staging seed data scripts
└── schema_docs/          # Human-readable schema documentation, kept in sync with Doc 2
```

---

### 1.6 `infra/`

```
infra/
├── docker/
│   ├── docker-compose.yml          # Local dev orchestration — all services
│   ├── docker-compose.prod.yml     # Production overrides
│   └── nginx/                       # Reverse proxy config
├── env/
│   ├── .env.staging.example
│   └── .env.production.example
└── deployment/
    └── runbooks/                    # Deployment/rollback procedures
```

---

### 1.7 `tests/`, `scripts/`, `docs/`

```
tests/
├── e2e/                  # Full user-journey tests (Playwright/Cypress-class, tool TBD)
└── contract/             # API contract tests validating responses against Doc 2 schemas

scripts/
├── ops/                   # DB backup, manual reprocessing, dead-letter-queue replay
└── dev/                    # Local environment bootstrap helpers

docs/
├── architecture/          # This document series (frozen)
├── adr/                   # Architecture Decision Records for any post-freeze deviation (see §15)
└── runbooks/               # Incident response, on-call procedures
```

---

## 2. CLEAN ARCHITECTURE DESIGN

**Presentation Layer** — FastAPI routers and Pydantic schemas only. No business logic. Its sole job: validate input shape, call the appropriate application service, serialize the output. Never talks to repositories or the database directly.

**Application Layer** — Services here implement use cases ("approve a draft," "trigger a sync"). They orchestrate one or more repositories and domain entities, enforce use-case-level rules (e.g., "cannot approve a draft not in `pending` status"), and define the abstract interfaces that infrastructure must implement. This layer knows *what* needs to happen, not *how* it's persisted.

**Domain Layer** — Framework-agnostic. Entities carry their own invariants (e.g., a `Draft` entity refuses an illegal state transition internally, not via an external `if` check scattered in a service). No SQLAlchemy, no Pydantic, no FastAPI imports here — this is what makes the domain layer unit-testable with zero infrastructure.

**Infrastructure Layer** — Concrete repository implementations (SQLAlchemy), the Gmail client, ChromaDB client, Redis client. Implements the interfaces application defines. This is the only layer allowed to know about Postgres, Gmail's SDK shape, or ChromaDB's API.

**Dependency Injection** — A central DI container (`core/di_container.py`) wires concrete infrastructure implementations to application interfaces at startup. Services and routers receive dependencies via FastAPI's `Depends()`, resolved through the container — nothing is manually instantiated deep in a function body. This is what makes swapping, say, the embedding provider a one-line change.

**Repository Pattern** — Every aggregate root (User, Thread, Draft, Contact, AgentRun) gets exactly one repository. Repositories expose domain-meaningful methods (`get_pending_draft_for_thread`, not `select * where status = 'pending'`) — SQL/ORM specifics never leak past the repository boundary.

**Service Layer** — Application services are the only callers of repositories. A service method maps 1:1 to a use case, not 1:1 to an API endpoint (some endpoints may call multiple services; some services back multiple endpoints).

**Unit of Work** — Wraps a repository set in a single transaction boundary (`infrastructure/database/unit_of_work.py`). Any use case touching multiple tables (e.g., approve draft → insert `approvals` + update `drafts.status`) goes through one Unit of Work instance, committed once. This is the mechanism enforcing the transaction rule from Doc 2 (§ Transaction Strategy) — Gmail send explicitly happens **outside** a Unit of Work scope, dispatched as a separate async task after commit.

**Middleware** — Cross-cutting request-level concerns (see §7), applied at the presentation layer boundary, never duplicated inside services.

**Background Workers** — Celery tasks live in `app/workers/`, organized by pool. A worker task is a thin adapter: it resolves dependencies via the same DI container, calls the relevant application service, and handles retry/failure semantics. Workers never contain business logic that isn't also reachable through the service layer — this guarantees the same rules apply whether a draft is approved via API or reprocessed via a retry job.

---

## 3. COMPLETE MODULE BREAKDOWN

| Module | Objective | Dependencies | Files (approx.) | Complexity | Testing Strategy | Validation Strategy |
|---|---|---|---|---|---|---|
| **Auth & Session** | Google OAuth handshake, session issuance, token refresh | Gmail OAuth, Redis (session store) | 10–12 | Medium | Unit (token encryption, session logic) + integration (mocked Google OAuth flow) | Schema validation on callback params; token expiry invariants tested explicitly |
| **Mailbox & Sync** | Initial + incremental Gmail sync, history cursor management | Gmail API client, Celery sync pool | 14–16 | High | Unit (diff/parsing logic) + integration (mocked Gmail responses, idempotency replay tests) | Idempotency test: replaying the same push notification must not duplicate records |
| **Thread & Email Domain** | Normalize, store, and serve thread/email data | Mailbox module, Postgres | 12 | Medium | Unit (entity invariants) + repository integration tests | Pagination cursor correctness; ordering guarantees under concurrent writes |
| **Classification** | Cheap gating classifier, priority/intent tagging | Thread/Email module, LLM client (lightweight call) | 6–8 | Low–Medium | Unit (threshold logic) + golden-set accuracy tests | Confidence-threshold regression tests against a fixed labeled sample set |
| **Contacts & Memory** | Contact aggregation, `memory_contact`/`memory_thread` refresh | Thread/Email module, feedback events | 10 | Medium | Unit (aggregation logic) + integration (refresh job correctness) | Memory refresh must be idempotent and bounded in size (no unbounded JSONB growth) |
| **CrewAI Orchestration** | Multi-agent triage → retrieval → draft → critique pipeline | `ai/` package, RAG module, Memory module | 16–20 | High | Unit (per-agent prompt/response contract tests, mocked LLM) + integration (full crew run against a fixed fixture set) | Critic Agent output schema strictly validated before a draft is ever persisted |
| **RAG / Vector Retrieval** | Embedding generation, ChromaDB indexing and query | `ai/embeddings`, ChromaDB client | 8–10 | Medium–High | Unit (chunking logic) + integration (retrieval relevance smoke tests) | Embedding/index consistency check job (compares `embeddings_index` row count vs. Chroma collection count) |
| **Draft & Approval** | Draft lifecycle, human-in-the-loop state machine | CrewAI module, Postgres, Unit of Work | 12 | High (safety-critical) | Unit (state machine transition tests — exhaustive) + integration (approval → send_log flow) | Illegal state transitions must raise a domain exception, never silently no-op |
| **Send Service** | Confirmed Gmail send, ambiguous-state handling | Gmail client, Draft module | 6 | Medium (high-risk) | Integration (mocked Gmail send failures, timeout, ambiguous response) | Explicit test matrix: success / hard-fail / timeout-ambiguous, each mapped to correct `send_log.send_status` |
| **Notifications & Realtime** | Websocket push, notification persistence | Redis pub/sub | 8 | Medium | Unit (event payload shape) + integration (WS connection lifecycle) | Message delivery-at-least-once verified under reconnect scenarios |
| **Analytics** | Nightly aggregation, dashboard read endpoints | Approvals/AgentRuns data, Celery beat | 8 | Low–Medium | Unit (aggregation math) + integration (beat job idempotency on re-run) | Aggregate re-run must be idempotent (upsert by `user_id, date`, never double-count) |
| **Settings & Notifications Prefs** | User-configurable tone/sync/notification settings | User module | 4 | Low | Unit only | Schema validation on all settings fields |
| **Audit Logging** | Immutable action trail | Cross-cutting, hooked into Draft/Approval/Send/OAuth modules | 4 | Low | Unit (log entry shape) + integration (verify every safety-critical write emits a log row in the same transaction) | Test asserts audit row count matches action count 1:1 for critical tables |
| **Middleware & Core** | Auth guard, logging, rate limiting, error handling, CORS | Cross-cutting | 10 | Medium | Unit (each middleware in isolation) + integration (full request pipeline test) | Rate-limit boundary tests (exactly-at-limit, one-over-limit) |

---

## 4. AI SYSTEM DESIGN

**LLM** — Anthropic API (per the platform's Claude-in-Claude / API integration pattern established in Doc 1). Used at three distinct cost tiers: (1) cheap classification pass — smallest/fastest model tier; (2) drafting — mid/high-capability model; (3) critique — same tier as drafting, since catching hallucinated commitments requires real reasoning, not a cheaper pass.

**Embedding Model** — A dedicated embedding endpoint (separate from the generative LLM call) used to vectorize email bodies and thread summaries at ingestion time, and to vectorize retrieval queries at draft-generation time. Chunking strategy: email bodies chunked by logical paragraph boundaries with a max-token cap per chunk, never split mid-sentence.

**Vector Database** — ChromaDB, per-tenant collection (namespace = `user_id`), consistent with Doc 1/2's tenant-isolation and rebuildable-derived-store principles. Metadata on every vector: `contact_id`, `thread_id`, `sent_at` — enables filtered retrieval, not just pure similarity search.

**Prompt Management** — Prompts are versioned template files in `ai/prompts/templates/`, loaded through a `prompt_registry` that resolves the active version per agent. Never hardcoded inline in agent classes — this is a hard rule (§14).

**Conversation Memory** — Two tiers, matching Doc 2's schema: `memory_thread` (rolling summary of a specific thread, refreshed after each new message) and `memory_contact` (durable, cross-thread relationship/tone memory, refreshed nightly from approval/edit feedback). Memory is retrieval context, never fine-tuning data.

**Writing Style Learning** — Derived, not trained. The `style_profile_builder` computes a style signal from (a) embeddings of the user's own historically sent mail and (b) the delta between AI-drafted and user-edited final text (`draft_versions`). This signal is injected into the Drafting Agent's prompt as retrieved exemplars — style personalization lives entirely in the retrieval/prompt layer, keeping the system model-agnostic.

**Knowledge Base** — v1 scope is limited to the user's own mailbox history (emails + threads). The `rag/` module is deliberately built provider-agnostic so an external knowledge source (docs, CRM data) can be added later as just another embedded, filterable collection — no redesign needed (ties to Doc 1 §21 Future Extensibility).

**Multi-Agent Collaboration** — Sequential crew: Triage → Retrieval → Drafting → Critic, as fixed in Doc 1 §9. Agents communicate via structured, schema-validated handoffs (JSON), not free-text — this is what makes `agent_runs.triage_output` / `retrieval_output` / `critic_notes` reliably queryable and testable.

**CrewAI Flows** — One Flow per qualifying thread/email, instantiated by the `agent_orchestration` worker pool. Flow state is persisted at each stage boundary into `agent_runs` — a failed Flow can resume from the last completed stage rather than restarting from scratch, bounding both cost and latency on retries.

**Prompt Templates** — Each agent has a versioned template with clearly delimited sections: role/goal, constraints (e.g., "never invent commitments"), input schema, output schema. Output schema is strict JSON, validated on receipt before the next agent stage or persistence proceeds.

**Context Management** — Context assembled by `rag/context_builder.py` in a fixed priority order: (1) current thread's unread messages, (2) `memory_thread` summary, (3) top-k retrieved similar past emails from RAG, (4) `memory_contact` tone/relationship notes. A hard token budget caps total injected context per agent call — enforced in code, not left to prompt-length hope, directly protecting the per-user LLM cost invariant from Doc 1.

---

## 5. SERVICE DESIGN

| Service | Responsibility | Key Dependencies |
|---|---|---|
| `AuthService` | OAuth handshake orchestration, session issuance/validation, token refresh scheduling | `OAuthTokenRepository`, Gmail client, Redis session store |
| `MailboxSyncService` | Coordinates initial and incremental sync, cursor management | `MailboxRepository`, `ThreadRepository`, `EmailRepository`, Gmail client |
| `ThreadService` | Thread listing, filtering, archive actions, thread detail assembly | `ThreadRepository`, `EmailRepository`, `MemoryThreadRepository` |
| `ClassificationService` | Runs the gating classifier, persists results, decides agent-run eligibility | `ClassificationRepository`, LLM client (lightweight) |
| `ContactService` | Contact aggregation from email traffic, relationship-tag updates | `ContactRepository`, `EmailRepository` |
| `MemoryService` | Reads/refreshes `memory_thread`/`memory_contact` objects | `MemoryThreadRepository`, `MemoryContactRepository`, feedback event data |
| `AgentOrchestrationService` | Invokes CrewAI Flow, persists `agent_runs` state at each stage | `AgentRunRepository`, `ai/` package (Crew definitions) |
| `RAGService` | Query construction, retrieval execution, context assembly hand-off to orchestration | `EmbeddingsIndexRepository`, ChromaDB client |
| `DraftService` | Draft creation, edit versioning, status-transition enforcement | `DraftRepository`, `DraftVersionRepository`, Unit of Work |
| `ApprovalService` | Executes the approve/edit/reject use case, writes `approvals`, triggers send dispatch | `DraftRepository`, `ApprovalRepository`, Unit of Work, `SendService` (async dispatch, not direct call) |
| `SendService` | Confirmed Gmail send execution, ambiguous/failure state handling | `SendLogRepository`, Gmail client |
| `NotificationService` | Creates notification records, publishes to Redis pub/sub for WS delivery | `NotificationRepository`, Redis pub/sub |
| `AnalyticsService` | Nightly aggregation job logic, read-path for dashboard endpoints | `AnalyticsAggregateRepository`, `ApprovalRepository`, `AgentRunRepository` |
| `SettingsService` | Read/update user settings and preferences | `UserSettingsRepository` |
| `AuditService` | Emits audit log entries within the same transaction as the triggering action | `AuditLogRepository` — injected into every safety-critical service above, not called ad hoc |

**Dependency direction:** every service depends only on repository interfaces (application layer) and other services where a use case genuinely spans domains (e.g., `ApprovalService` dispatching to `SendService` asynchronously). Services never depend on presentation-layer schemas or infrastructure concrete classes directly.

---

## 6. REPOSITORY DESIGN

| Repository | Responsibility |
|---|---|
| `UserRepository` | CRUD + lookup by `google_sub_id`/`email` for `users` |
| `OAuthTokenRepository` | Encrypted token storage/retrieval, expiry queries for the refresh sweep |
| `MailboxRepository` | Mailbox record CRUD, sync-status queries |
| `ThreadRepository` | Thread CRUD, filtered/paginated listing queries, `needs_reply` queries |
| `EmailRepository` | Email CRUD, idempotent upsert by `gmail_message_id`, sender/thread lookups |
| `ContactRepository` | Contact CRUD, upsert-on-interaction logic |
| `ClassificationRepository` | Append-only insert, latest-classification-per-email lookup |
| `AgentRunRepository` | Agent run CRUD, status-filtered polling queries |
| `DraftRepository` | Draft CRUD, status-filtered approval-queue queries |
| `DraftVersionRepository` | Append-only version insert, version history retrieval |
| `ApprovalRepository` | Append-only insert, approval-rate aggregation source queries |
| `SendLogRepository` | Send record CRUD, ambiguous/failed-status queries for ops |
| `MemoryThreadRepository` | `memory_thread` read/upsert |
| `MemoryContactRepository` | `memory_contact` read/upsert |
| `EmbeddingsIndexRepository` | Pointer-table CRUD, consistency-check queries against Chroma |
| `NotificationRepository` | Notification CRUD, unread-count queries |
| `AnalyticsAggregateRepository` | Upsert-by-date aggregation writes, range-query reads |
| `AuditLogRepository` | Append-only insert only — no update/delete methods exposed, enforced at the interface level |
| `UserSettingsRepository` | Single-row read/update per user |

**Rule:** every repository interface is defined in `application/interfaces/`, implemented once in `infrastructure/database/repositories/`. No service ever imports a concrete repository class — only the interface, resolved via DI.

---

## 7. MIDDLEWARE DESIGN

- **Authentication Middleware** — validates session cookie against Redis session store, attaches `user_id` to request context; rejects with 401 before any route handler executes.
- **Request ID Middleware** — generates/propagates a `request_id` (or accepts an inbound trace header), attaches to logging context and response headers — this is the thread that ties an API call to worker-task logs to audit rows.
- **Logging Middleware** — structured request/response logging (method, path, status, latency, `request_id`, `user_id`) — never logs request/response bodies containing email content (Doc 1 §19 constraint).
- **Exception Handling Middleware** — catches domain exceptions and maps them to the standard error envelope (Doc 2 §Error Response Standards); unhandled exceptions logged with full context and returned as a generic 500 without internal detail leakage.
- **Rate Limiting Middleware** — checks Redis sliding-window counters per user/endpoint before handler execution; attaches `Retry-After` on 429.
- **Security Headers Middleware** — standard hardening headers (CSP, X-Content-Type-Options, etc.) on every response.
- **CORS Middleware** — restricts allowed origins to the known frontend domain(s) per environment; credentials-aware for the session cookie.

**Ordering (outermost to innermost):** Security Headers → CORS → Request ID → Logging → Rate Limiting → Authentication → Exception Handling boundary → route handler. Exception handling wraps the innermost call so it can catch anything raised by the handler or the services it invokes.

---

## 8. CONFIGURATION DESIGN

- **Environment Variables** — all config sourced from environment, loaded once at startup through `core/config.py` (a typed settings object, validated on boot — the app must fail fast on missing/malformed config, never at first use).
- **Secrets** — Gmail OAuth client secret, token-encryption key, database credentials, LLM API key — never in `.env` files committed to the repo; production secrets sourced from a dedicated secrets manager (mechanism TBD at deployment-provider selection, out of scope here), injected as environment variables into containers at runtime.
- **Settings** — non-secret operational config (sync window default, classifier priority threshold default, rate-limit thresholds) — also environment-sourced, with sane defaults in `.env.example` for local dev.
- **Feature Flags** — a minimal flag set (e.g., `auto_draft_enabled` globally, `agent_orchestration_enabled` as a kill switch) sourced from environment at v1, with a documented upgrade path to a dynamic flag service if the flag count grows — no flag service built prematurely.
- **AI Configuration** — model identifiers per tier (classification/drafting/critique), token budget caps, embedding model identifier, retrieval `top_k` default — grouped in a dedicated `AIConfig` sub-section of settings, since these change independently of infra config.
- **Database Configuration** — connection string, pool size, statement timeout — environment-sourced, with distinct values per environment (dev/staging/prod) via the `infra/env/` files.

---

## 9. LOGGING DESIGN

- **Structured Logging** — JSON logs everywhere, one schema (`timestamp`, `level`, `request_id`, `user_id`, `service`, `message`, `context`) across API, workers, and CrewAI orchestration — this uniformity is what makes cross-service tracing possible (Doc 1 §19).
- **Audit Logging** — handled exclusively through `AuditService` writing to `audit_log`, not through general application logs — audit is a data concern (queryable, retained, compliance-bound), not a log-stream concern.
- **Error Logging** — full stack trace + context captured server-side; client-facing responses never include stack traces (Exception Middleware, §7).
- **AI Logging** — every agent stage logs: model/version used, token counts, latency, and a truncated/redacted content summary (never full email bodies in generic logs — routed to `agent_runs`/`audit_log` instead, which are access-restricted per Doc 1 §19).
- **Performance Logging** — latency captured per request (API) and per task (Celery), tagged by endpoint/task name, feeding the monitoring dashboards from Doc 1 §18 — not a separate ad hoc mechanism.

---

## 10. ERROR HANDLING STRATEGY

| Error Class | Handling |
|---|---|
| **Validation Errors** | Caught at the presentation layer (Pydantic), returned as 400 with field-level detail in the error envelope. Never reach the service layer. |
| **Business Errors** | Raised as domain exceptions (e.g., `DraftAlreadySentError`) inside `domain/exceptions/`, caught by Exception Middleware, mapped to 409/422 as appropriate. |
| **External API Errors (Gmail)** | Wrapped at the infrastructure client boundary; transient errors (rate limit, 5xx) trigger retry-with-backoff in the calling worker task; persistent errors surface as `send_log.send_status='failed'` or `mailboxes.sync_status='error'`, never a raw exception bubbling to the user. |
| **AI Errors** | LLM timeout/malformed-output errors caught in `AgentOrchestrationService`; malformed critic output specifically blocks draft persistence rather than saving an unvalidated draft — a hard invariant, not a soft warning. |
| **Database Errors** | Connection/constraint errors caught at the repository boundary, logged with full context, re-raised as a generic infrastructure exception the service layer can handle uniformly (never a raw `SQLAlchemyError` escaping past infrastructure). |
| **Background Job Errors** | Celery task-level retry policy (bounded, exponential backoff) per queue; tasks exceeding retry budget route to a dead-letter queue with an ops alert (Doc 1 §16), never silently dropped. |

---

## 11. TESTING STRATEGY

- **Unit Tests** — domain entities (state-transition invariants), individual service methods (mocked repositories), individual middleware components, prompt/response schema validators. Fast, no I/O, run on every commit.
- **Integration Tests** — repository implementations against a real (containerized) test Postgres instance; Celery tasks against a test Redis broker; Gmail client against recorded/mocked API fixtures (never live Gmail in CI).
- **API Tests** — full request/response cycle per endpoint against the running FastAPI app (test client), validated against the Doc 2 contract (status codes, response shape).
- **AI Tests** — per-agent prompt/output contract tests against a fixed fixture set (mocked LLM responses for determinism); a smaller, slower "golden set" suite that runs against the real LLM API periodically (not on every commit) to catch prompt-drift regressions.
- **Frontend Tests** — component-level tests (rendering, interaction) and typed API-client contract tests against the same Doc 2 schemas backend tests validate.
- **End-to-End Tests** — full user journeys (login → sync → view draft → approve → confirm send) run against a fully containerized stack in a dedicated CI stage, gating deploys to staging.

---

## 12. CI/CD STRATEGY

- **GitHub Actions**, triggered on PR (lint + unit + integration) and on merge to main (full suite + build + deploy-to-staging).
- **Linting** — enforced as a required check (type checking, formatting, import-order) — no PR merges with lint failures.
- **Testing** — unit + integration on every PR; full E2E suite runs on merge to main, gating the staging deploy specifically (not every PR, to keep PR feedback fast).
- **Docker Build** — each service (`backend`, `ai` if deployed separately, `frontend`, workers) builds its own image, tagged by commit SHA, pushed to a container registry.
- **Deployment Pipeline** — staging deploy is automatic on main-branch merge passing all gates; production deploy is a manual-approval gate after staging verification — consistent with Doc 1 §17's mandatory staging gate for anything touching Gmail scopes.

---

## 13. PRODUCTION DEPLOYMENT ARCHITECTURE

- **Docker Compose** (or equivalent orchestration at chosen scale) — services: `api` (FastAPI, horizontally scaled), `worker-sync`, `worker-embedding`, `worker-classification`, `worker-agent`, `worker-send`, `worker-analytics` (each a separate container/replica group per Doc 1's segmented-pool principle), `celery-beat` (single instance — scheduling must not run concurrently), `postgres`, `redis`, `chromadb`, `nginx` (reverse proxy), `frontend` (static build served via nginx or CDN).
- **Networking** — private internal network for all backend services; only `nginx` exposed publicly, terminating TLS and routing to `api`/`frontend`.
- **Reverse Proxy** — `nginx` handles TLS termination, static asset serving for the frontend build, and routing `/api/*` to the FastAPI service; also the websocket upgrade path for `/ws/*`.
- **Persistent Storage** — named volumes for `postgres` data and `chromadb` data; object storage (external, not a container volume) for any retained attachments.
- **Secrets** — injected as environment variables at container start from the deployment platform's secrets mechanism, never baked into images.
- **Scaling Strategy** — `api` and each `worker-*` service scale independently by replica count based on queue depth (workers) or request load (api); `postgres`/`redis`/`chromadb` scale vertically first, with read-replica/sharding strategies (Doc 2 §Database Optimization) as documented next steps, not built at v1.
- **Health Checks** — each service exposes a lightweight liveness/readiness endpoint; `api` readiness includes a DB connectivity check; workers report liveness via a Celery heartbeat monitored by the orchestrator; failed health checks trigger automatic container restart before paging.

---

## 14. CODING STANDARDS

- **Naming Convention** — `snake_case` for Python modules/functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants; React components `PascalCase`, hooks `camelCase` prefixed `use`.
- **Folder Convention** — one concern per folder as laid out in §1; no cross-layer imports that violate the dependency rule in §2 (enforced via lint rule / architecture test, not just convention).
- **SOLID** — Single Responsibility enforced at the service/repository granularity defined in §5/§6 (one repository per aggregate root, not per query); Dependency Inversion enforced via the interface/DI pattern in §2 — services depend on abstractions, never concrete infrastructure.
- **Clean Code** — functions do one thing; service methods map to one use case; no service method exceeding a reasonable cognitive scope — if a method needs a "and also" in its docstring, it's two methods.
- **Type Hints** — mandatory on every function signature (Python) and every exported function/component (TypeScript) — no implicit `Any`.
- **Docstrings** — mandatory on every service method and repository method, describing the use case/responsibility, not restating the signature.
- **Import Style** — absolute imports within `backend/app/`, grouped stdlib → third-party → local, no wildcard imports.
- **Error Handling Rules** — never catch a bare exception without re-raising or explicitly logging + converting to a domain/infrastructure exception per §10's table; no silent `except: pass`.
- **Dependency Injection Rules** — nothing outside `core/di_container.py` and FastAPI route signatures constructs a repository or service directly; everything else receives dependencies through the container.
- **Repository Rules** — repositories never contain business logic, only data access; no repository method returns a raw ORM model past the infrastructure boundary — always mapped to a domain entity.
- **Service Rules** — services never construct SQL/ORM queries directly; services never call another module's repository directly, only through that module's service or a shared interface.

---

## 15. FINAL ENGINEERING RULES (Mandatory — Prevents Architectural Drift)

1. **No implementation prompt may alter the frozen decisions in Doc 1 or Doc 2.** Any genuine need to deviate requires an ADR (`docs/adr/`) explaining why, before code is written — not a silent divergence.
2. **The domain layer never imports from application, infrastructure, or presentation.** This is checked, not assumed.
3. **No AI-initiated send bypasses `ApprovalService`.** This invariant from Doc 1 is enforced structurally: `SendService` is only ever invoked from `ApprovalService`'s post-commit dispatch, never called directly from a worker task or router.
4. **The Gmail send call never occurs inside a Unit of Work transaction.** No exceptions.
5. **Every write to `drafts`, `approvals`, `send_log`, or `oauth_tokens` emits a same-transaction `audit_log` row.** Enforced via `AuditService` injection into those specific services, not left to individual developer discipline.
6. **CrewAI orchestration is only ever triggered through the classification gate or an explicit user-manual re-run action** — never on every ingested email, preserving the cost-control invariant from Doc 1.
7. **Prompts are never hardcoded inline.** All agent prompts live in `ai/prompts/templates/` and are loaded through the prompt registry.
8. **Append-only tables (`classifications`, `draft_versions`, `approvals`, `audit_log`) have no `UPDATE`/`DELETE` repository methods exposed, at all** — not even for admin tooling; corrections happen via new rows.
9. **Analytics endpoints read only from `analytics_daily_aggregates`**, never from live event tables — no exceptions for "just this one dashboard widget."
10. **Every repository interface lives in `application/interfaces/`; every concrete implementation lives in `infrastructure/`.** A service importing a concrete infrastructure class directly is a defect, not a style preference.
11. **No service method may exceed one use case.** If an implementation prompt produces a service method doing two distinct things, it must be split before merge.
12. **All config and secrets are environment-sourced; nothing environment-specific is ever committed to the repository.**
13. **Every new external integration (beyond Gmail/Anthropic/ChromaDB) requires a corresponding infrastructure adapter behind an application-layer interface** — never a direct SDK call from a service.
14. **This document, together with Doc 1 and Doc 2, is the sole source of architectural truth for the remainder of the project.** Implementation prompts that follow must reference these documents rather than re-deriving decisions.

---

**This is the final frozen blueprint.** All subsequent prompts are implementation prompts operating strictly within the boundaries defined across this three-document series.
