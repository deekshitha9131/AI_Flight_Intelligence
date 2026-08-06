# AI Email Assistant Platform — Simplified Architecture (v2.0, FROZEN)

**Supersedes the folder structure, repository count, service count, CrewAI trigger logic, and vector store choice from the previous blueprint. All other principles (human approval gate, append-only audit tables, send-outside-transaction, classification-gates-agents) are preserved unchanged — this is a scope reduction, not a philosophy change.**

---

## 1. AI Package Moves Inside Backend

**New layout:**
```
backend/
└── app/
    ├── ai/              # was a top-level sibling — now lives here
    ├── presentation/
    ├── application/
    ├── domain/
    ├── infrastructure/
    ├── workers/
    └── core/
```

**Why this is the right call for this project, not just a simplification:**

- **One dependency tree, one lockfile, one virtual environment.** A separate top-level `ai/` package implied a second Python project with its own `pyproject.toml` — that only pays off when a different team owns it and ships on a different cadence. Here, it's one person. A second dependency tree is pure overhead: two places to update a package version, two places for version drift to cause a bug that only shows up at integration time.
- **One deployment artifact.** The AI logic doesn't call the backend over a network — it's called *by* the backend, in-process. Splitting it into a separate top-level folder invites (even if not required) eventually deploying it separately, which adds a network hop, a service to monitor, and a failure mode (AI service unreachable) that a solo student project has no operational capacity to handle well.
- **Import clarity, not import distance.** `app/ai/agents/drafting_agent.py` importing `app/domain/entities/draft.py` is an obvious same-codebase import. A top-level `ai/` importing from `backend/app/domain/` was already an architectural smell — it meant the "separate" AI package was never really separate, just organized to look that way.
- **This still preserves the separation that matters.** `app/ai/` remains its own subtree with its own internal structure (agents, prompts, rag, memory) — nothing about "AI logic is isolated and swappable" is lost. What's removed is the *pretense* that it's a separately deployable service, which it was never actually going to be at this scale.

---

## 2. Simplified Repository Structure

**Rule going forward: one repository per aggregate root that the application actually queries/mutates as a unit. Not one per table.**

Previous design had 18 repositories, largely because Doc 2's schema had 19 tables. Most of those tables are either (a) child records naturally accessed through their parent, or (b) simple enough to not need a repository abstraction at all — direct ORM access inside the owning service is fine and is what a solo-developer, single-codebase project should do.

**Reduced to 6 repositories:**

| Repository | Owns / Absorbs | Rationale |
|---|---|---|
| `UserRepository` | `users`, `oauth_tokens`, `user_settings` | These three tables are always accessed in the context of "this user" — one repository exposing `get_user`, `get_tokens`, `get_settings`, `update_settings` is simpler than three, and they share a lifecycle. |
| `MailboxRepository` | `mailboxes` | Kept separate — sync status/cursor logic is distinct enough from user identity to warrant its own boundary, and workers poll this independently of user-facing requests. |
| `ThreadRepository` | `threads`, `emails`, `classifications`, `memory_thread` | A thread is never meaningfully retrieved without its emails, and classification/memory are thread-scoped derived data. One repository, several methods (`get_thread_with_emails`, `get_latest_classification`, `get_thread_memory`). |
| `ContactRepository` | `contacts`, `memory_contact` | Same logic — contact memory has no independent existence from the contact. |
| `DraftRepository` | `drafts`, `draft_versions`, `approvals`, `send_log`, `agent_runs` | This is the safety-critical cluster. Keeping it as one repository (not five) means the Unit of Work boundary around "approve a draft" touches exactly one repository's transactional methods — simpler to reason about, harder to accidentally split a transaction across repository boundaries. |
| `NotificationRepository` | `notifications`, `analytics_daily_aggregates` | Both are write-mostly, read-by-user-and-date-range patterns; grouping them avoids a repository that exists for one query type. |

**Dropped entirely as a repository concern:** `embeddings_index` / `audit_log` — these are handled as thin, direct data-access calls inside the services that own them (`RAGService` and `AuditService` respectively), not full repository classes. They have exactly one or two access patterns each; a repository abstraction adds a file and an interface for no real flexibility gained.

**What's preserved from the original rule:** repositories still don't leak raw ORM objects past their boundary into services carelessly, and services still don't hand-write ad hoc queries outside a repository for the six aggregates above. The simplification is in *count*, not in discipline.

---

## 3. Simplified Service Structure

**Reduced from 15 services to 7.** Each remaining service now owns a coherent slice of the product, not a single use case.

| Service | Responsibility (merged from previous services) |
|---|---|
| `AuthService` | Google OAuth handshake, session issuance/validation, token refresh. *(unchanged — this was already correctly scoped)* |
| `MailboxSyncService` | Initial + incremental Gmail sync, cursor management, **and** contact aggregation (absorbs the old `ContactService`) — contacts are a byproduct of sync, not a separate domain concern worth its own service. |
| `EmailProcessingService` | Classification **and** memory refresh (absorbs old `ClassificationService` + `MemoryService`) — both are "what do we know about this email/thread/contact now that it's arrived," triggered from the same point in the pipeline. |
| `AIOrchestrationService` | Everything AI-related: the classification-gate decision (simple vs. CrewAI, see §4), single-LLM-call path, **and** full CrewAI Flow invocation (absorbs old `AgentOrchestrationService` + `RAGService`) — RAG retrieval only ever happens in service of generating a draft, so it doesn't need to be a separate service from the thing that uses it. |
| `DraftService` | Draft creation, edit versioning, approve/reject state transitions, **and** send dispatch (absorbs old `ApprovalService` + `SendService`) — this is still the safety-critical spine, and keeping approval + send in one service (with send still explicitly dispatched *after* commit, outside the transaction — see §7 invariant) is simpler to audit than tracing a call across two services. |
| `NotificationService` | Notification creation/delivery **and** analytics aggregation (absorbs old `AnalyticsService`) — both are "compute something after the fact and make it visible to the user," on a similar nightly/event-driven cadence. |
| `SettingsService` | User settings read/update. *(unchanged — genuinely simple, no merge candidate)* |

**What was cut, not just merged:** the standalone `AuditService` is demoted from a service to a small shared utility function (`log_audit_event(...)`) called directly by `DraftService` and `AuthService` at the points that need it. A full service class for "insert one row" was over-engineering at this scale — a utility achieves the same non-negotiable invariant (every safety-critical write gets an audit row) without the ceremony of a DI-injected service for a single-method concern.

---

## 4. Simplified CrewAI Usage

**Workflow (as specified):**
```
Incoming Email
      ↓
Lightweight Classification
      ↓
 ┌────┴────┐
 │         │
Simple   Complex
 │         │
Single    CrewAI
LLM call  Flow
```

**Classification decides the branch. Concretely, an email routes to the single-LLM-call path when it meets simple criteria, and to the CrewAI Flow otherwise:**

**→ Single LLM call (the default, most emails):**
- Short, low-ambiguity threads (e.g., a scheduling confirmation, a one-line question, a routine status update).
- No open commitments or prior unresolved context attached to the thread (`memory_thread` is empty or trivial).
- Classifier confidence on intent is high (e.g., clearly "needs a short acknowledgment/reply").
- **What happens:** one prompt, combining a compact version of the thread + a lightweight style hint, produces a draft directly. No retrieval step, no critique step. This covers the large majority of email volume in practice and is what keeps LLM cost and latency low as the default case.

**→ Full CrewAI Flow (the exception, reserved for cases that actually need multi-step reasoning):**
- Thread has real complexity: multiple open questions, a negotiation, or a reply that depends on facts scattered across earlier messages in the thread.
- The contact has meaningful history (`memory_contact` is non-trivial) where tone/relationship context materially changes what a good reply looks like.
- Classifier flags ambiguity or low confidence on intent — when the cheap classifier itself isn't sure, that's exactly the signal that shallow generation is likely to produce a bad draft.
- The user has manually requested a "regenerate with more context" action on a draft they weren't satisfied with.

**Why this matters beyond cost:** this isn't just a cost-saving shortcut — it's the correct product decision. Most email replies genuinely don't need a 4-agent pipeline; forcing every email through triage→retrieval→drafting→critique for a one-line "sounds good, see you then" reply is wasted latency the user feels as slowness, not as thoroughness. Reserving CrewAI for genuinely complex threads means the AI system does more work exactly where more work produces a better draft.

---

## 5. Vector Database Decision

| Criterion | PostgreSQL + pgvector | PostgreSQL + ChromaDB |
|---|---|---|
| **Simplicity** | One database to run, back up, and reason about. Vector columns live in the same tables/transactions as everything else. | A second database process, a second client library, a second thing to keep in sync with Postgres (via the `embeddings_index` pointer table). |
| **Deployment** | One more entry in `docker-compose.yml` is avoided entirely — it's the same Postgres container already required. | Requires its own container, its own volume, its own health check, its own backup story. |
| **Learning value** | Forces understanding of how vector similarity search actually works *inside* a relational engine (indexes, distance operators, query planning) — a skill that's directly SQL-transferable. | Learning value is more "how to use a vector-DB SDK," which is narrower and less transferable to a generic data-analyst/engineering interview context. |
| **Production readiness** | pgvector is genuinely used in production at real companies for exactly this "RAG at moderate scale" use case — not a toy choice. | Also production-viable, but its advantage (purpose-built vector engine, better at very large-scale/high-QPS vector search) only matters at a scale this project will never reach. |
| **Portfolio value** | "I implemented RAG retrieval using pgvector inside our primary relational database, including similarity search and metadata filtering in SQL" is a strong, specific, interview-ready sentence — and it directly reinforces your SQL skills, which matters more for a Data Analyst-track portfolio than a second NoSQL-adjacent tool would. | "I used ChromaDB" is a weaker, more generic sentence — it doesn't demonstrate anything about your database/SQL depth, which is the skill you specifically need to showcase. |

**Decision: PostgreSQL + pgvector.**

**Justification:** every criterion points the same direction at this project's scale. Running a second database (ChromaDB) for a solo project that will hold, realistically, a few thousand to low tens-of-thousands of embedded emails is unjustified infrastructure — pgvector handles that volume comfortably with a standard IVFFlat or HNSW index. It also removes an entire architectural component: the `embeddings_index` polymorphic pointer table from Doc 2 is no longer needed as a separate consistency-tracking mechanism, because the embedding vector can live as a column directly on `emails`/`memory_thread` rows — one less place for data to drift out of sync, one less "is Chroma consistent with Postgres" background job to build. Given your stated goal (Data Analyst-track, SQL-heavy skill demonstration), this choice also does double duty as a stronger interview story than a generic vector-DB integration would.

---

## 6. Final Technology Stack (Confirmed)

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| Database | PostgreSQL |
| Vector search | pgvector (extension on the same PostgreSQL instance) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Task queue | Celery |
| Cache / broker | Redis |
| AI orchestration | CrewAI |
| LLM provider | Claude (Anthropic API) / OpenAI-compatible interface |
| Frontend framework | React |
| Frontend build tool | Vite |
| Frontend language | TypeScript |
| Frontend styling | TailwindCSS |
| Containerization | Docker |
| Local/deployment orchestration | Docker Compose |

No component from the original stack is dropped except ChromaDB, which is replaced by pgvector per §5. Everything else (FastAPI, Postgres, SQLAlchemy, Alembic, Celery, Redis, CrewAI, React) is unchanged from the original architecture — the simplification is in structure and count, not in the core technology choices, which were already appropriately scoped.

---

## 7. FINAL SIMPLIFIED ARCHITECTURE (Frozen)

### Folder Structure
```
ai-email-assistant/
├── backend/
│   ├── app/
│   │   ├── ai/                  # agents, prompts, rag, memory — lives inside backend now
│   │   ├── presentation/        # FastAPI routers + schemas + middleware
│   │   ├── application/         # services + interfaces
│   │   ├── domain/               # entities, value objects, exceptions
│   │   ├── infrastructure/       # repositories, gmail client, pgvector queries, redis, celery config
│   │   ├── workers/              # celery tasks (sync, classification, ai, send, notifications)
│   │   └── core/                 # config, DI container, logging
│   ├── alembic/
│   └── Dockerfile
├── frontend/                    # React + Vite + TypeScript + Tailwind
├── infra/
│   └── docker-compose.yml       # api, workers, postgres (with pgvector), redis, nginx, frontend
├── docs/                        # this document series
└── README.md
```

### Repositories (6)
`UserRepository` · `MailboxRepository` · `ThreadRepository` · `ContactRepository` · `DraftRepository` · `NotificationRepository`

### Services (7)
`AuthService` · `MailboxSyncService` · `EmailProcessingService` · `AIOrchestrationService` · `DraftService` · `NotificationService` · `SettingsService`

### AI Routing (unchanged from §4)
Classification → simple (single LLM call) or complex (CrewAI Flow) → draft → human approval → send.

### Vector Store
pgvector inside the primary PostgreSQL instance — no second database.

### Invariants Preserved from the Original Architecture (non-negotiable, unaffected by this simplification)
1. No AI-generated reply is ever sent without explicit human approval.
2. The Gmail send call happens outside any database transaction.
3. Every draft/approval/send/token action is audit-logged.
4. Classification always gates AI generation cost — nothing runs a full pipeline on every email by default.
5. Append-only tables (`draft_versions`, `approvals`, `audit_log`, `classifications`) are never updated or deleted in place.

**This is now the frozen architecture for implementation.** It is one person's project: 6 repositories, 7 services, one database, one AI routing decision point, and a folder structure that reads top-to-bottom in under a minute. Nothing here should need to grow before v1 ships — if a future prompt is tempted to add a repository or service back, that's a signal to check whether it's solving a real problem at this scale or re-introducing complexity this document deliberately removed.
