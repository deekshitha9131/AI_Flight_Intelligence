# AI Email Assistant Platform — System Architecture (v1.0, FROZEN)

**Status:** Architecture baseline. No code, no schema, no API contracts — those are separate deliverables.

---

## 1. Product Vision

An AI-native email assistant that sits on top of Gmail and acts as a **cognitive layer** for a user's inbox — reading, understanding, prioritizing, and drafting replies to email, while keeping a human in the loop for every outbound action. The product is not "auto-reply." It is a **decision-support system for email work** that compounds in value as it learns a user's tone, priorities, and relationships over time.

Positioning: "Your inbox has a chief of staff."

---

## 2. Business Goals

- Reduce time-to-inbox-zero for knowledge workers (target: 60–70% reduction in manual triage/drafting time).
- Build a defensible moat via **personalization data** (tone, past replies, relationship graph) — this is the retention lever, not the LLM itself.
- Support a multi-tenant SaaS model: thousands of users, isolated data, usage-based cost control (LLM tokens are the dominant COGS).
- Land as a B2C/prosumer tool first; architect so a B2B (team/workspace) tier is a config change, not a rewrite.

---

## 3. User Personas

1. **Founder/Executive** — high email volume, low tolerance for wrong tone, needs triage + delegation-style drafts.
2. **Sales/CS professional** — repetitive email patterns, needs speed and consistency, cares about CRM-like context.
3. **Individual power user** — wants inbox organization + smart drafting, price-sensitive, self-serve onboarding.
4. **(Future) Team admin** — manages shared inboxes, needs audit trail and approval policies across a team.

Primary persona for v1: **Founder/Executive** and **Sales/CS professional** — highest willingness to pay, clearest ROI story.

---

## 4. Functional Requirements

- Google OAuth 2.0 login and consent (Gmail scopes only — least privilege).
- Initial full mailbox sync + ongoing incremental sync (near-real-time).
- Email understanding: classification (priority, category, intent), entity extraction, thread summarization.
- Multi-agent workflow (CrewAI) to triage → research context (RAG) → draft → self-critique → present.
- RAG over: past sent emails (tone/style), thread history, and optionally connected knowledge sources.
- Personalized draft generation matching the user's historical writing style.
- **Human-in-the-loop approval**: no email is sent without explicit user action (edit/approve/reject).
- Conversation memory: per-thread and per-contact memory so tone/context persists across sessions.
- Analytics dashboard: time saved, response rates, draft-acceptance rate, category breakdown.
- Notification layer for high-priority items requiring attention.

**Explicitly out of scope for v1:** autonomous sending without approval, calendar/meeting scheduling automation, multi-mailbox aggregation across providers other than Gmail.

---

## 5. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Availability | 99.9% for core sync + draft services |
| Latency | Draft generation P95 < 8s; UI interactions P95 < 300ms |
| Scalability | Horizontally scalable to 10K+ concurrent users, 100K+ mailboxes syncing |
| Security | OAuth token encryption at rest, scoped Gmail permissions, tenant data isolation |
| Data residency | Configurable per region (future); single-region v1 acceptable |
| Cost control | Hard per-user LLM token budgets; degrade gracefully, never silently overspend |
| Auditability | Every AI action (draft, classification) is logged and traceable to a decision trail |
| Compliance | GDPR-aligned data deletion; Google API user-data policy compliance (this is a hard gate for Gmail API approval) |

---

## 6. Complete User Workflow

1. User signs up → Google OAuth consent screen → scoped Gmail access granted.
2. Backend performs **initial sync** (bounded historical window, e.g., last 90 days, configurable) — user sees a progress indicator, not a blocked UI.
3. Dashboard populates incrementally as sync progresses (streamed, not blocking).
4. Emails are auto-classified into priority tiers; user sees a **triaged inbox view**, not raw Gmail order.
5. User opens a thread → sees AI-generated **summary** + a **suggested draft reply** + confidence/reasoning notes.
6. User edits or accepts the draft → clicks **Approve & Send** (this is the only path that sends mail).
7. Every accept/edit/reject is captured as a feedback signal, feeding personalization memory.
8. User checks Analytics tab periodically for time-saved and usage metrics.
9. Real-time updates: new mail triggers incremental sync → classification → (optionally) draft pre-generation, surfaced via websocket/notification.

---

## 7. Complete Backend Workflow

1. **Auth Service** handles OAuth handshake, token exchange, encrypted token storage, refresh-token rotation.
2. **Sync Service** (Celery workers) — uses Gmail push notifications (Pub/Sub) for incremental sync + polling fallback; writes normalized email records to PostgreSQL.
3. **Ingestion pipeline** — on new/updated email: enqueue an async job → clean/parse MIME → extract text/attachments metadata → embed relevant content → upsert into ChromaDB.
4. **Classification Service** — lightweight model/pass to tag priority/category/intent; cheap and fast, runs on every email (cost-conscious — not every email needs a full agent run).
5. **Orchestration Layer (CrewAI)** — triggered selectively (e.g., emails needing a reply): a multi-agent crew runs triage → context retrieval (RAG) → draft generation → self-review → hands off to approval queue.
6. **Memory Service** — maintains per-contact and per-thread memory objects (summaries, tone notes, prior commitments) used as agent context; updated after user feedback.
7. **Approval Queue** — drafts sit in a pending state; user action (approve/edit/reject) is the only trigger for the **Send Service**, which calls Gmail's send API.
8. **Feedback loop** — approve/edit/reject events are captured and used to periodically refresh personalization embeddings/memory (not live fine-tuning — retrieval-based personalization, not model training, for v1).
9. **Analytics pipeline** — async aggregation jobs (Celery beat) compute usage metrics into read-optimized aggregates.
10. Redis is the backbone for: Celery broker/result backend, caching hot reads (inbox view, user session), rate limiting, and pub/sub for real-time UI updates.

---

## 8. Complete Frontend Workflow

1. React SPA — auth state managed via secure httpOnly session cookies (not localStorage tokens).
2. Inbox view: virtualized list (thousands of emails must not choke the DOM), backed by paginated/streamed API + websocket delta updates.
3. Thread detail view: renders summary, draft, confidence indicators, and an inline edit surface for the draft (edit-in-place, not a separate "compose" modal — reduces friction).
4. Approval action bar: Approve / Edit / Reject / Snooze — always visible, always the final gate.
5. Real-time layer: websocket (or SSE) subscription per user session for sync progress, new high-priority mail, and draft-ready notifications.
6. Analytics dashboard: client-rendered charts against pre-aggregated backend endpoints (never raw event queries from the client).
7. Settings: tone preferences, per-contact rules, sync scope, notification thresholds — all first-class controls, not buried.

---

## 9. AI Workflow (Multi-Agent, CrewAI)

**Design principle:** not every email deserves a full agent crew run — cost and latency must be gated by a cheap pre-classifier.

Crew composition per qualifying email/thread:
1. **Triage Agent** — determines intent (needs reply / FYI / action item / spam-like) and urgency.
2. **Context Retrieval Agent** — queries ChromaDB (RAG) for: relevant past emails with this contact, prior commitments, relevant knowledge docs.
3. **Drafting Agent** — generates a reply grounded in retrieved context and the user's stylistic profile (derived from embeddings of their historical sent mail).
4. **Critic/Reviewer Agent** — checks draft against tone consistency, factual grounding (no hallucinated commitments), and flags low-confidence sections for human attention.
5. **Presentation layer** — final draft + reasoning trace + confidence score handed to the Approval Queue.

Memory is injected as context at the Context Retrieval and Drafting stages — not baked into a fine-tuned model. This keeps the system provider-agnostic and cheap to update.

RAG store (ChromaDB) is partitioned per-user (tenant isolation) with metadata filters (contact, thread, date) to keep retrieval precise and cheap.

---

## 10. Data Flow

```
Gmail (Push/Poll) → Sync Worker → Postgres (source of truth, normalized email + thread state)
                                 → Embedding Worker → ChromaDB (vector store, per-tenant namespace)
Postgres change → Classification Worker → priority/category tags → Postgres
Qualifying thread → CrewAI Orchestrator → (reads Postgres + ChromaDB) → Draft → Approval Queue (Postgres)
User action (approve) → Send Worker → Gmail Send API → Postgres (status update) → Analytics aggregator
All async transitions → Redis (broker/cache/pubsub) → Frontend (websocket) 
```

Postgres is the single source of truth for state; ChromaDB is a derived index (rebuildable); Redis is ephemeral (nothing there is authoritative).

---

## 11. External Services

- **Google OAuth 2.0 / Gmail API** — auth + mail read/send (requires Google API verification/audit for production scopes — plan for this lead time).
- **Google Pub/Sub** — Gmail push notifications for near-real-time sync.
- **LLM Provider (Anthropic API)** — classification, drafting, critique agents.
- **ChromaDB** — vector store for RAG (self-hosted or managed).
- **Object storage (S3-compatible)** — attachment storage, if retained.
- **Email delivery is Gmail itself** — no separate SMTP provider needed since sending is via Gmail API on behalf of the user.
- **Observability stack** (see §18) — external or self-hosted (Prometheus/Grafana, Sentry).

---

## 12. High-Level System Architecture

```
                        ┌─────────────┐
                        │   React SPA │
                        └──────┬──────┘
                               │ HTTPS / WSS
                        ┌──────▼──────┐
                        │  FastAPI    │  (stateless, horizontally scaled)
                        │  API Layer  │
                        └──────┬──────┘
                 ┌─────────────┼──────────────┐
                 │             │              │
          ┌──────▼─────┐ ┌─────▼─────┐  ┌─────▼─────┐
          │  Postgres  │ │   Redis   │  │ ChromaDB  │
          │ (state)    │ │(cache/MQ) │  │ (vectors) │
          └────────────┘ └─────┬─────┘  └───────────┘
                                │
                         ┌──────▼──────┐
                         │   Celery    │  (workers, separate pools)
                         │   Workers   │──── Sync / Embedding / Classification
                         └──────┬──────┘     Send / Analytics
                                │
                         ┌──────▼──────┐
                         │  CrewAI     │  (invoked as a specialized worker task)
                         │ Orchestrator│──── calls Anthropic API
                         └─────────────┘
```

All components containerized (Docker), each service independently deployable and scalable. FastAPI layer never talks to Gmail/LLM synchronously for anything expensive — it enqueues and returns; results stream back via websocket.

---

## 13. Scalability Strategy

- **Stateless API tier** — FastAPI instances horizontally scaled behind a load balancer; no sticky sessions.
- **Worker pools segmented by workload type** (sync, embedding, classification, agent-orchestration, send) — so a spike in agent latency doesn't starve sync workers. Each pool scales independently.
- **Postgres**: read replicas for analytics/reporting queries; connection pooling (PgBouncer) to survive worker fan-out.
- **Redis**: separate logical DBs/instances for cache vs. Celery broker vs. pub/sub, to avoid noisy-neighbor contention.
- **ChromaDB**: per-tenant namespace/collection sharding as data grows; horizontal scaling via managed deployment.
- **Agent orchestration is the most expensive path** — gate it behind the cheap classifier, cap concurrent crew runs per user, and queue-throttle globally to control LLM spend.

---

## 14. Security Strategy

- OAuth tokens encrypted at rest (envelope encryption), never logged, refreshed via short-lived access tokens.
- Principle of least privilege on Gmail scopes — request only what's needed (readonly + send, not full mailbox modify unless required).
- Tenant isolation enforced at every data layer: Postgres row-level scoping, ChromaDB per-tenant collections, Redis key-namespacing.
- All inter-service traffic within a private network; only the API gateway is internet-facing.
- Human approval gate is itself a security control — it's the last line against AI-generated content causing real-world harm (wrong commitment, leaked info, wrong recipient).
- Secrets management via a dedicated vault (not env files in production).
- Audit log: immutable record of every AI decision + every human approval/edit/reject, tied to user and timestamp.

---

## 15. Performance Strategy

- Cheap classifier gates expensive agent runs — this is the single biggest cost/latency lever in the whole system.
- Aggressive caching (Redis) of inbox views and frequently-read thread summaries.
- Streaming UI updates instead of polling — reduces perceived latency and backend load.
- Embedding generation batched, not per-email synchronous calls.
- Draft generation is async end-to-end — user never blocks on an LLM call in the request/response cycle.

---

## 16. Failure Recovery Strategy

- Every Celery task idempotent and retry-safe (sync, embedding, classification, send) — critical since email operations must never double-send or duplicate-process.
- Dead-letter queues for tasks exceeding retry budget, surfaced to an ops dashboard, not silently dropped.
- Gmail API failures (rate limit, token expiry) trigger backoff + token refresh flow, not user-facing crashes.
- ChromaDB is a derived store — if lost/corrupted, it is fully rebuildable from Postgres + re-embedding, so it never holds unique data.
- Send operations are the highest-risk failure point: send status is confirmed via Gmail API response before marking "sent" in Postgres; ambiguous states are flagged for user review rather than silently retried (to avoid duplicate sends).

---

## 17. Deployment Strategy

- Fully containerized (Docker) — API, workers (per pool), CrewAI orchestrator, and frontend build as separate images.
- Environment separation: dev / staging / production, with staging as a mandatory gate before any Gmail-scope-touching change ships (Google API changes carry review risk).
- Rolling deployments for API/worker tiers to avoid downtime; migrations run as a separate gated step before app deploy.
- Infrastructure-as-code for reproducibility (exact tool TBD in later prompt — out of scope here).

---

## 18. Monitoring Strategy

- Service-level metrics: API latency/error rates, Celery queue depth per pool, worker task success/failure rates.
- Business-level metrics: drafts generated vs. approved vs. rejected (this ratio is the core product health signal), sync lag per user, LLM cost per user/day.
- Alerting thresholds on: queue depth spikes, Gmail API error rate, LLM cost anomalies, approval-rate drops (signals quality regression in drafting).

---

## 19. Logging Strategy

- Structured logging (JSON) across all services, correlated by a request/trace ID that follows an email from ingestion through agent processing to send.
- Separate log streams for: application logs, audit logs (AI decisions + human actions — retained longer, access-restricted), and infra logs.
- No PII/email-content in generic application logs — content-bearing logs go to the access-restricted audit stream only.

---

## 20. Architectural Trade-offs

| Decision | Trade-off accepted |
|---|---|
| Human-approval-gated sending | Slower "time to value" per email, but essential for trust and safety in v1 — no autonomous send |
| RAG + retrieval-based personalization instead of per-user fine-tuning | Less "deeply personalized" than fine-tuning, but far cheaper, faster to update, and provider-agnostic |
| Cheap classifier gating expensive agent runs | Some emails get shallower treatment than a full crew run would give, but this is the only way to keep LLM cost bounded at scale |
| Postgres as single source of truth, ChromaDB as derived/rebuildable | Slight duplication of effort on rebuild, but massively simplifies backup/consistency story |
| Gmail-only in v1 (no multi-provider) | Narrower TAM initially, but avoids a fragmented sync/abstraction layer before product-market fit is proven |

---

## 21. Future Extensibility

- Multi-provider support (Outlook/Exchange) via an abstracted mail-provider interface — deferred, not designed in v1 to avoid premature abstraction.
- Team/workspace tier: shared inbox approval workflows, role-based access, admin audit views.
- Autonomous send for low-risk, high-confidence categories (e.g., "confirmed meeting acknowledgments") — opt-in, gated by trust score built from historical approval-rate data.
- Calendar integration for scheduling-aware drafting.
- Fine-tuned per-organization models once usage data volume justifies the cost (B2B tier only).

---

## 22. Final Engineering Decisions (Frozen for this project)

1. **PostgreSQL** is the single source of truth; all other stores are caches or derived indexes.
2. **Redis** serves three distinct roles (cache, Celery broker, pub/sub) — logically separated even if co-located initially.
3. **Celery** workers are segmented by workload type from day one — no single generic worker pool.
4. **CrewAI orchestration is gated**, never runs on every email — cost control is a first-class architectural concern, not an afterthought.
5. **No AI-initiated send ever bypasses human approval** in this version — this is a product and safety invariant, not just a feature flag.
6. **ChromaDB is rebuildable, never authoritative** — protects data integrity guarantees.
7. **FastAPI is stateless and never performs long-running work synchronously** — everything expensive is async via Celery.
8. **Frontend is real-time via websocket/SSE, not polling**, for both UX and backend load reasons.

This document is now frozen as the architectural baseline. Database schema, API contracts, and folder structure are separate, subsequent deliverables and must remain consistent with the decisions above.
