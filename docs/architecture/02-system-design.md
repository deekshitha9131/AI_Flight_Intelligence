# AI Email Assistant Platform — System Design (v1.0)

**Builds on the frozen architecture (Prompt 1). No architectural decisions are revisited here.**
Consistency anchors carried forward: Postgres = single source of truth · ChromaDB = derived/rebuildable · Redis = cache/broker/pubsub (never authoritative) · Celery = segmented worker pools · CrewAI = gated, not run on every email · No AI-initiated send bypasses human approval · FastAPI = stateless.

---

## PART A — DATABASE DESIGN (PostgreSQL)

Design principles applied throughout:
- Every table has a surrogate `UUID` primary key (safe for distributed generation, doesn't leak sequential info).
- `created_at` / `updated_at` on every table (audit hygiene, cheap to add now, expensive to retrofit).
- Soft-delete (`deleted_at`) on user-facing entities where recoverability matters; hard-delete only on ephemeral/derived data.
- Foreign keys always indexed (Postgres does not auto-index FK columns).
- Multi-tenant isolation via `user_id` scoping on every tenant-owned table, never inferred from a join.

---

### 1. `users`
**Purpose:** Core account record — one per human, the tenant boundary for the entire system.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| google_sub_id | VARCHAR(255) | UNIQUE, NOT NULL (Google's stable subject identifier) |
| account_status | ENUM('active','suspended','deleted') | NOT NULL, DEFAULT 'active' |
| plan_tier | ENUM('free','pro','team') | NOT NULL, DEFAULT 'free' |
| llm_token_budget_daily | INTEGER | NOT NULL, DEFAULT (plan default) |
| onboarding_completed_at | TIMESTAMPTZ | NULLABLE |
| created_at / updated_at / deleted_at | TIMESTAMPTZ | created_at NOT NULL |

**Indexes:** UNIQUE(email), UNIQUE(google_sub_id), INDEX(account_status) for admin queries.
**Relationships:** parent to nearly every other table via `user_id`.

---

### 2. `oauth_tokens`
**Purpose:** Encrypted Gmail OAuth credentials. Kept separate from `users` so token rotation/compromise never touches core identity rows.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| access_token_encrypted | BYTEA | NOT NULL |
| refresh_token_encrypted | BYTEA | NOT NULL |
| token_expiry | TIMESTAMPTZ | NOT NULL |
| granted_scopes | TEXT[] | NOT NULL |
| revoked_at | TIMESTAMPTZ | NULLABLE |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(user_id) UNIQUE (one active token set per user in v1 — single mailbox).
**Relationships:** 1:1 with `users` (v1); becomes 1:N once multi-mailbox ships (future extensibility, not built now).

---

### 3. `mailboxes`
**Purpose:** Represents the connected Gmail account itself, decoupled from `users` so the future multi-mailbox/team tier doesn't require a redesign.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| gmail_address | VARCHAR(255) | NOT NULL |
| history_id | VARCHAR(64) | NULLABLE (Gmail's sync cursor) |
| sync_status | ENUM('pending','syncing','active','error') | NOT NULL, DEFAULT 'pending' |
| last_synced_at | TIMESTAMPTZ | NULLABLE |
| sync_window_days | INTEGER | NOT NULL, DEFAULT 90 |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(user_id), INDEX(sync_status) (workers poll by status).
**Relationships:** N:1 to users; 1:N to threads, emails.

---

### 4. `threads`
**Purpose:** Normalized email thread — the unit the UI is organized around.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| mailbox_id | UUID | FK → mailboxes.id, NOT NULL |
| gmail_thread_id | VARCHAR(64) | NOT NULL |
| subject | TEXT | NULLABLE |
| priority_tier | ENUM('urgent','normal','low','fyi') | NULLABLE (set by classifier) |
| category | VARCHAR(64) | NULLABLE |
| last_message_at | TIMESTAMPTZ | NOT NULL |
| needs_reply | BOOLEAN | NOT NULL, DEFAULT FALSE |
| is_archived | BOOLEAN | NOT NULL, DEFAULT FALSE |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(mailbox_id, gmail_thread_id), INDEX(mailbox_id, last_message_at DESC) — this is the primary inbox-list query, INDEX(mailbox_id, needs_reply) for the triage view.
**Relationships:** N:1 mailboxes; 1:N emails; 1:1 memory_thread; 1:N drafts.

---

### 5. `emails`
**Purpose:** Individual message record, normalized from Gmail MIME payload.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| thread_id | UUID | FK → threads.id, NOT NULL |
| gmail_message_id | VARCHAR(64) | NOT NULL |
| sender_email | VARCHAR(255) | NOT NULL |
| recipient_emails | TEXT[] | NOT NULL |
| cc_emails | TEXT[] | NULLABLE |
| subject | TEXT | NULLABLE |
| body_text | TEXT | NULLABLE (plain-text extraction) |
| body_html_ref | TEXT | NULLABLE (pointer to object storage if retained, not inline) |
| direction | ENUM('inbound','outbound') | NOT NULL |
| sent_at | TIMESTAMPTZ | NOT NULL |
| has_attachments | BOOLEAN | NOT NULL, DEFAULT FALSE |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(thread_id, gmail_message_id), INDEX(sender_email) (contact-history lookups), INDEX(thread_id, sent_at) (thread reconstruction order).
**Relationships:** N:1 threads; referenced by `embeddings_index` for RAG.

**Note:** `body_text` is the largest-volume column in the schema — flagged explicitly in §15 (Database Optimization).

---

### 6. `contacts`
**Purpose:** Aggregated view of people the user corresponds with — backbone of per-contact personalization and memory.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| email_address | VARCHAR(255) | NOT NULL |
| display_name | VARCHAR(255) | NULLABLE |
| relationship_tag | VARCHAR(64) | NULLABLE (e.g., "client", "internal", "vendor" — user-editable) |
| total_thread_count | INTEGER | NOT NULL, DEFAULT 0 |
| last_interaction_at | TIMESTAMPTZ | NULLABLE |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(user_id, email_address).
**Relationships:** N:1 users; 1:1 memory_contact.

---

### 7. `classifications`
**Purpose:** Output of the cheap gating classifier — decoupled from `threads`/`emails` so re-classification never requires mutating source records.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| email_id | UUID | FK → emails.id, NOT NULL |
| priority_score | NUMERIC(3,2) | NOT NULL (0.00–1.00) |
| category | VARCHAR(64) | NOT NULL |
| intent | ENUM('needs_reply','fyi','action_item','spam_like') | NOT NULL |
| model_version | VARCHAR(32) | NOT NULL |
| classified_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(email_id), INDEX(intent) (feeds the agent-gating query directly).
**Relationships:** N:1 emails (1:N in practice — re-classification creates new rows, latest wins; append-only for auditability).

---

### 8. `agent_runs`
**Purpose:** Records every CrewAI orchestration execution — the audit trail for "what did the AI do and why."

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| thread_id | UUID | FK → threads.id, NOT NULL |
| triggered_by | ENUM('auto_classifier','user_manual','retry') | NOT NULL |
| status | ENUM('queued','running','completed','failed') | NOT NULL, DEFAULT 'queued' |
| triage_output | JSONB | NULLABLE |
| retrieval_output | JSONB | NULLABLE (references to chroma doc IDs used, not the content itself) |
| critic_notes | JSONB | NULLABLE |
| confidence_score | NUMERIC(3,2) | NULLABLE |
| token_cost | INTEGER | NULLABLE |
| started_at / completed_at | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(thread_id), INDEX(status) (worker polling), INDEX(created_at) (cost analytics).
**Relationships:** N:1 threads; 1:N drafts (a run produces one primary draft, but retries create new runs).

---

### 9. `drafts`
**Purpose:** The AI-generated reply awaiting human action. This table is the hinge of the entire product.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| thread_id | UUID | FK → threads.id, NOT NULL |
| agent_run_id | UUID | FK → agent_runs.id, NOT NULL |
| body_text | TEXT | NOT NULL |
| status | ENUM('pending','approved','edited','rejected','sent') | NOT NULL, DEFAULT 'pending' |
| confidence_score | NUMERIC(3,2) | NULLABLE |
| created_at / updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(thread_id, status), INDEX(status) (approval-queue query — this is a hot path).
**Relationships:** N:1 threads, N:1 agent_runs; 1:N draft_versions; 1:1 send_log (on send).

---

### 10. `draft_versions`
**Purpose:** Immutable edit history — required for both product analytics (edit-distance = personalization signal) and audit compliance.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| draft_id | UUID | FK → drafts.id, NOT NULL |
| version_number | INTEGER | NOT NULL |
| body_text | TEXT | NOT NULL |
| edited_by | ENUM('ai','user') | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(draft_id, version_number), INDEX(draft_id).
**Relationships:** N:1 drafts. Append-only, never updated or deleted.

---

### 11. `approvals`
**Purpose:** The explicit human-in-the-loop action record — the single most safety-critical table in the schema.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| draft_id | UUID | FK → drafts.id, NOT NULL |
| user_id | UUID | FK → users.id, NOT NULL |
| action | ENUM('approved','edited','rejected') | NOT NULL |
| final_body_text | TEXT | NULLABLE (snapshot at approval time) |
| action_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(draft_id), INDEX(user_id, action_at DESC) (analytics: approval-rate over time).
**Relationships:** N:1 drafts, N:1 users. Append-only.

---

### 12. `send_log`
**Purpose:** Confirms actual Gmail-side delivery — kept distinct from `drafts.status` because send confirmation is a separate, riskier system boundary (see Failure Recovery, Prompt 1 §16).

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| draft_id | UUID | FK → drafts.id, NOT NULL, UNIQUE |
| gmail_message_id | VARCHAR(64) | NULLABLE (populated on confirmed send) |
| send_status | ENUM('pending','confirmed','failed','ambiguous') | NOT NULL, DEFAULT 'pending' |
| attempted_at | TIMESTAMPTZ | NOT NULL |
| confirmed_at | TIMESTAMPTZ | NULLABLE |
| error_detail | TEXT | NULLABLE |

**Indexes:** UNIQUE(draft_id), INDEX(send_status) (ops dashboard queries ambiguous/failed sends).
**Relationships:** 1:1 drafts.

---

### 13. `memory_contact`
**Purpose:** Persistent, evolving per-contact memory — tone notes, prior commitments, relationship summary — injected as agent context.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| contact_id | UUID | FK → contacts.id, NOT NULL, UNIQUE |
| tone_summary | TEXT | NULLABLE |
| open_commitments | JSONB | NULLABLE |
| relationship_summary | TEXT | NULLABLE |
| last_refreshed_at | TIMESTAMPTZ | NULLABLE |

**Indexes:** UNIQUE(contact_id).
**Relationships:** 1:1 contacts. Mutable, refreshed by the feedback-loop job (not append-only — this is a compact working-memory object, not an audit log).

---

### 14. `memory_thread`
**Purpose:** Per-thread rolling summary so a long thread doesn't require re-reading full history on every agent run.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| thread_id | UUID | FK → threads.id, NOT NULL, UNIQUE |
| summary | TEXT | NOT NULL |
| key_facts | JSONB | NULLABLE |
| last_refreshed_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(thread_id).
**Relationships:** 1:1 threads.

---

### 15. `embeddings_index`
**Purpose:** Pointer table mapping Postgres records to ChromaDB vector IDs — since ChromaDB is derived/rebuildable, this table is what makes rebuilding possible without guesswork.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| source_type | ENUM('email','thread_summary') | NOT NULL |
| source_id | UUID | NOT NULL (polymorphic — points to emails.id or memory_thread.id) |
| chroma_collection | VARCHAR(128) | NOT NULL (per-tenant namespace) |
| chroma_vector_id | VARCHAR(128) | NOT NULL |
| embedded_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** UNIQUE(source_type, source_id), INDEX(chroma_collection).
**Relationships:** Polymorphic — no FK enforced at DB level (deliberate: source_type discriminates the target table; enforced at application layer).

---

### 16. `notifications`
**Purpose:** In-app/real-time alert queue driving the websocket layer.

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| type | ENUM('high_priority_mail','draft_ready','sync_complete','send_failed') | NOT NULL |
| payload | JSONB | NOT NULL |
| read_at | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(user_id, read_at) (unread-count query, hot path).
**Relationships:** N:1 users.

---

### 17. `analytics_daily_aggregates`
**Purpose:** Pre-computed rollups so the dashboard never runs raw event queries live (Prompt 1 §18 constraint).

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| date | DATE | NOT NULL |
| emails_processed | INTEGER | NOT NULL, DEFAULT 0 |
| drafts_generated | INTEGER | NOT NULL, DEFAULT 0 |
| drafts_approved | INTEGER | NOT NULL, DEFAULT 0 |
| drafts_edited | INTEGER | NOT NULL, DEFAULT 0 |
| drafts_rejected | INTEGER | NOT NULL, DEFAULT 0 |
| estimated_minutes_saved | INTEGER | NOT NULL, DEFAULT 0 |
| llm_tokens_used | INTEGER | NOT NULL, DEFAULT 0 |

**Indexes:** UNIQUE(user_id, date).
**Relationships:** N:1 users. Built by a nightly Celery beat job from `approvals` + `agent_runs`.

---

### 18. `audit_log`
**Purpose:** Immutable, append-only record of every AI decision and human action — compliance and debugging backbone (Prompt 1 §14, §19).

| Field | Type | Constraints |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id, NOT NULL |
| actor | ENUM('system','ai_agent','user') | NOT NULL |
| action_type | VARCHAR(64) | NOT NULL |
| entity_type | VARCHAR(64) | NOT NULL |
| entity_id | UUID | NOT NULL |
| metadata | JSONB | NULLABLE |
| occurred_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** INDEX(user_id, occurred_at DESC), INDEX(entity_type, entity_id).
**Relationships:** N:1 users. Never updated or deleted; retention policy handled at the storage-tiering level, not by row deletion.

---

### 19. `user_settings`
**Purpose:** Tone preferences, sync scope, notification thresholds — first-class user controls (Prompt 1 §8).

| Field | Type | Constraints |
|---|---|---|
| user_id | UUID | PK, FK → users.id |
| tone_preference | VARCHAR(64) | NULLABLE |
| notification_priority_threshold | NUMERIC(3,2) | NOT NULL, DEFAULT 0.70 |
| auto_draft_enabled | BOOLEAN | NOT NULL, DEFAULT TRUE |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** PK doubles as the only lookup index needed.
**Relationships:** 1:1 users.

---

## PART B — ER DIAGRAM (Text Representation)

```
users ──1:1── oauth_tokens
users ──1:1── user_settings
users ──1:N── mailboxes
users ──1:N── contacts
users ──1:N── notifications
users ──1:N── analytics_daily_aggregates
users ──1:N── audit_log
users ──1:N── approvals

mailboxes ──1:N── threads

threads ──1:N── emails
threads ──1:1── memory_thread
threads ──1:N── agent_runs
threads ──1:N── drafts

contacts ──1:1── memory_contact

agent_runs ──1:N── drafts

drafts ──1:N── draft_versions
drafts ──1:N── approvals
drafts ──1:1── send_log

emails ──(polymorphic)── embeddings_index
memory_thread ──(polymorphic)── embeddings_index
```

**Key structural notes:**
- `contacts` is derived from `emails.sender_email` / `recipient_emails` via an async job — no direct FK from emails to contacts to avoid write-time contention on every ingested message.
- `embeddings_index` is intentionally polymorphic and unenforced at the DB level — trades referential integrity for flexibility, compensated by application-layer validation (documented trade-off, consistent with Prompt 1's rebuildable-ChromaDB principle).

---

## PART C — DATA LIFECYCLE

1. **Ingestion:** Gmail → `emails` (raw normalized) → async job populates `contacts` aggregate → async job creates `embeddings_index` row + Chroma vector.
2. **Classification:** `emails` → `classifications` (append-only, latest row wins by `classified_at`).
3. **Agent processing:** qualifying `emails`/`threads` → `agent_runs` → `drafts`.
4. **Human action:** `drafts` → `draft_versions` (on edit) + `approvals` (on any terminal action).
5. **Send:** approved `drafts` → `send_log` → Gmail API → confirmation updates `send_log.send_status` and `drafts.status`.
6. **Memory refresh:** `approvals` feed a nightly job that updates `memory_contact` / `memory_thread` — memory is a compacted, mutable projection, not raw history.
7. **Analytics:** nightly Celery beat job aggregates `approvals` + `agent_runs` → `analytics_daily_aggregates`.
8. **Retention/deletion:** on user deletion request — `users.deleted_at` set immediately (access revoked), hard-delete of `emails.body_text`, `draft_versions`, and Chroma vectors within the GDPR-mandated window; `audit_log` retained per compliance policy with user_id pseudonymized, not deleted (audit integrity vs. right-to-erasure trade-off — standard practice, must be disclosed in privacy policy).

---

## PART D — REST API DESIGN

**Convention:** all endpoints under `/api/v1/`, JSON in/out, Bearer session token unless noted. Full CRUD surface not exhaustively listed — representative complete set per resource.

### Auth
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/auth/google/login` | GET | No | — | 302 redirect to Google consent | 302 |
| `/auth/google/callback` | GET | No | `code`, `state` (query) | Sets session cookie, redirects to app | 302, 400 |
| `/auth/logout` | POST | Yes | — | `{}` | 204 |
| `/auth/session` | GET | Yes | — | `{ user_id, email, plan_tier }` | 200, 401 |

### Mailbox / Sync
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/mailbox` | GET | Yes | — | `{ sync_status, last_synced_at, gmail_address }` | 200 |
| `/mailbox/sync/trigger` | POST | Yes | — | `{ job_id }` | 202, 429 |

### Threads / Inbox
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/threads` | GET | Yes | Query: `priority_tier, category, cursor, limit` | `{ threads: [...], next_cursor }` | 200 |
| `/threads/{thread_id}` | GET | Yes | — | Full thread + emails + memory_thread summary | 200, 404 |
| `/threads/{thread_id}/archive` | POST | Yes | — | `{}` | 204, 404 |

### Drafts / Approval (the core safety-critical surface)
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/threads/{thread_id}/draft` | GET | Yes | — | Latest pending draft + confidence + reasoning | 200, 404 |
| `/drafts/{draft_id}` | PATCH | Yes | `{ body_text }` | Updated draft, creates new `draft_versions` row | 200, 404, 409 (already sent) |
| `/drafts/{draft_id}/approve` | POST | Yes | `{ final_body_text? }` | `{ status: 'approved', send_job_id }` | 202, 404, 409 |
| `/drafts/{draft_id}/reject` | POST | Yes | `{ reason? }` | `{ status: 'rejected' }` | 200, 404, 409 |

### Contacts / Memory
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/contacts` | GET | Yes | Query: `cursor, limit` | `{ contacts: [...] }` | 200 |
| `/contacts/{contact_id}` | GET | Yes | — | Contact + memory_contact summary | 200, 404 |
| `/contacts/{contact_id}` | PATCH | Yes | `{ relationship_tag }` | Updated contact | 200, 404 |

### Analytics
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/analytics/summary` | GET | Yes | Query: `range=7d\|30d\|90d` | `{ minutes_saved, approval_rate, drafts_by_category }` | 200 |
| `/analytics/timeseries` | GET | Yes | Query: `metric, range` | `{ points: [{date, value}] }` | 200 |

### Settings / Notifications
| Endpoint | Method | Auth | Request | Response | Status |
|---|---|---|---|---|---|
| `/settings` | GET | Yes | — | Full `user_settings` object | 200 |
| `/settings` | PATCH | Yes | Partial settings object | Updated settings | 200, 400 |
| `/notifications` | GET | Yes | Query: `unread_only` | `{ notifications: [...] }` | 200 |
| `/notifications/{id}/read` | POST | Yes | — | `{}` | 204, 404 |

### Realtime
| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/ws/updates` | WS | Yes (token on connect) | Pushes: sync progress, draft-ready, high-priority-mail events |

**Standard status code contract across all endpoints:** 200 (OK), 201 (created), 202 (accepted/async), 204 (no content), 400 (validation), 401 (unauthenticated), 403 (unauthorized — wrong tenant), 404 (not found), 409 (state conflict — e.g., approving an already-sent draft), 429 (rate limited), 500 (server error), 503 (dependency unavailable, e.g., Gmail API down).

---

## PART E — CORE FLOWS

### 1. Authentication Flow
1. Client hits `/auth/google/login` → redirected to Google consent (scopes: `gmail.readonly`, `gmail.send`, `userinfo.email`).
2. Google redirects to `/auth/google/callback` with `code`.
3. Backend exchanges `code` for access + refresh tokens → encrypts and writes to `oauth_tokens`.
4. Backend creates/updates `users` row (matched on `google_sub_id`), creates `mailboxes` row if new.
5. Backend issues an httpOnly session cookie (opaque session ID, session state in Redis — not a JWT holding Gmail scopes client-side).
6. Client redirected to app; `/auth/session` confirms identity on load.
7. Token refresh: a Celery beat job proactively refreshes tokens nearing expiry; API-layer also handles reactive refresh on a 401 from Gmail.

### 2. Gmail Synchronization Flow
1. **Initial sync:** on mailbox creation, enqueue a bounded historical sync job (`sync_window_days`) — paginated `messages.list` calls, each page enqueues a parse+store sub-task (fan-out, not one giant sequential job).
2. Each message → parsed → upserted into `emails`/`threads` → `mailboxes.history_id` updated to the latest seen.
3. **Incremental sync:** Gmail Pub/Sub push notification → lightweight webhook receiver → enqueues a `history.list(startHistoryId=...)` job → diffs and applies changes.
4. Fallback: a periodic poll (e.g., every 5 min) as a safety net if a push notification is missed — idempotent by design (dedup on `gmail_message_id`).
5. Sync completion/progress → `notifications` row → pushed over websocket.

### 3. AI Processing Flow (Classification Gate)
1. New/updated `emails` row → enqueue classification job (separate worker pool from sync).
2. Classifier runs a lightweight, cheap pass → writes `classifications` row.
3. If `intent = 'needs_reply'` and priority above threshold → enqueue `agent_runs` job. Otherwise, thread is tagged and surfaced in the triaged inbox with **no LLM agent cost incurred**.

### 4. CrewAI Flow
1. `agent_runs` row created (`status='queued'`).
2. Worker picks up job → Triage Agent confirms intent/urgency using thread + classification data.
3. Context Retrieval Agent queries `embeddings_index` → ChromaDB (per-tenant collection) for relevant past emails/contact history.
4. Drafting Agent generates reply using retrieved context + `memory_contact`/`memory_thread`.
5. Critic Agent reviews for tone consistency and unsupported claims → attaches `critic_notes` + `confidence_score`.
6. `agent_runs` marked `completed` → `drafts` row created (`status='pending'`) → `notifications` row (`draft_ready`) → websocket push.
7. On any agent failure: `agent_runs.status='failed'`, retry with backoff up to a cap, then surfaced to user as "draft unavailable, view thread manually."

### 5. RAG Flow
1. Retrieval query built from: current thread's subject/participants + contact identity.
2. Query embedding generated → similarity search against the user's ChromaDB collection, metadata-filtered by `contact_id`/date range to keep results relevant and cheap.
3. Top-k results resolved back to source rows via `embeddings_index` (vector ID → Postgres record) — Chroma never holds display content as the source of truth, only vectors + minimal metadata.
4. Retrieved content injected as context into the Drafting Agent's prompt.

### 6. Background Job Flow (Celery)
- **Queues (segmented pools, per Prompt 1 §13):** `sync`, `embedding`, `classification`, `agent_orchestration`, `send`, `analytics`.
- Each queue has independent concurrency limits — `agent_orchestration` deliberately capped per-user to enforce the cost-control invariant.
- Redis is the broker; result backend also Redis (short-TTL, since results are persisted to Postgres by the task itself, not read back from Redis).
- Celery beat drives scheduled jobs: token refresh sweep, memory refresh, nightly analytics aggregation, dead-letter queue review alerts.

### 7. Draft Generation Flow
Covered in CrewAI Flow (§4) — restated as the product-critical path: **classification → gate → agent crew → draft → approval queue.** No step in this chain writes directly to Gmail; `drafts` is always an intermediate, reversible state.

### 8. Analytics Flow
1. Every `approvals` write and `agent_runs` completion is a raw event.
2. Nightly Celery beat job aggregates the day's events per user into `analytics_daily_aggregates`.
3. `/analytics/*` endpoints read **only** from the aggregate table — never scan `approvals`/`agent_runs` live, keeping dashboard latency flat regardless of account age.
4. `estimated_minutes_saved` computed via a fixed heuristic (e.g., avg. manual reply time − avg. review time) — documented as an estimate, not a precise measurement, in the UI copy.

---

## PART F — CROSS-CUTTING STRATEGIES

### Redis Usage
- **Cache DB (logical DB 0):** hot reads — thread list pages, session lookups, user settings. TTL-based invalidation, explicit invalidation on writes to `threads`/`drafts`.
- **Celery broker (logical DB 1):** task queues, one per worker pool.
- **Pub/Sub (logical DB 2):** websocket fan-out channel per `user_id`.
- **Rate limiting counters (logical DB 3):** sliding-window counters per user/endpoint.

### Caching Strategy
- Cache-aside pattern: API reads check Redis first, fall back to Postgres, populate cache on miss.
- Write-through invalidation: any mutation to `threads`, `drafts`, `notifications` invalidates the relevant cache keys synchronously before the API response returns — avoids stale-read races on the approval-critical path.
- Analytics aggregates cached with a longer TTL (data is already a daily rollup, staleness tolerance is naturally higher).

### Transaction Strategy
- Single-row-family writes (e.g., draft edit → new `draft_versions` row) wrapped in a DB transaction with the parent `drafts.updated_at` bump — atomic, no partial states.
- Approval action is the highest-stakes transaction: `approvals` insert + `drafts.status` update happen in one transaction; the actual Gmail send is **deliberately outside** that transaction (async, via `send_log`) — because an external API call must never hold a DB transaction open.
- Sync ingestion uses `INSERT ... ON CONFLICT DO UPDATE` (upsert) keyed on `gmail_message_id` for idempotency, avoiding read-then-write races across concurrent sync workers.

### Database Optimization Strategy
- `emails.body_text` is the largest column by volume — candidate for TOAST-aware access patterns; large historical bodies can be moved to object storage with a reference column if table bloat becomes an issue at scale (documented as a v2 lever, not built now).
- Composite indexes matched to actual hot queries: `(mailbox_id, last_message_at DESC)` for inbox list, `(status)` on `drafts` for the approval queue, `(user_id, occurred_at DESC)` on `audit_log`.
- Read replicas for `analytics_daily_aggregates` and `audit_log` queries — keeps reporting load off the primary that serves the approval-critical write path.
- Partitioning candidate: `audit_log` and `emails` by month, once volume justifies it (not needed at initial scale — noted for the growth path).

### API Versioning Strategy
- URL-path versioning (`/api/v1/...`) — explicit and cache-friendly, avoids header-based versioning ambiguity for a public-facing SaaS API.
- Breaking changes require a new version prefix; additive changes (new optional fields) ship within `v1`.

### Rate Limiting Strategy
- Per-user, per-endpoint sliding-window limits enforced at the API gateway layer via Redis counters.
- Separate, stricter budget for LLM-cost-bearing actions (`/mailbox/sync/trigger`, manual agent re-runs) vs. read endpoints.
- `429` responses include a `Retry-After` header; client-side backoff is a UI requirement, not just a backend courtesy.

### Error Response Standards
Uniform error envelope across all endpoints:
```
{ "error": { "code": "DRAFT_ALREADY_SENT", "message": "...", "request_id": "..." } }
```
- Machine-readable `code` for client branching, human-readable `message` for logs/support, `request_id` ties directly to the structured log trace ID (Prompt 1 §19).

### Audit Logging Strategy
- Every write to `drafts`, `approvals`, `send_log`, and `oauth_tokens` emits a corresponding `audit_log` row within the same request lifecycle (not best-effort/async for these specific tables — audit integrity on safety-critical actions is non-negotiable).
- `audit_log` is queried by support/ops tooling only — never exposed directly through a general-purpose user-facing endpoint beyond the user's own action history.

---

## PART G — FINAL DATABASE DECISIONS (Frozen for this project)

1. **19 core tables**, UUID PKs throughout, `user_id`-scoped tenant isolation enforced at the schema level wherever applicable.
2. **`drafts` and `approvals` are the safety-critical spine of the schema** — every other table exists to feed context into a draft or record what happened after.
3. **`embeddings_index` is the only polymorphic, DB-unenforced relationship** — a deliberate, documented trade-off consistent with ChromaDB being a rebuildable derived store.
4. **Append-only tables** (`classifications`, `draft_versions`, `approvals`, `audit_log`) are never updated or hard-deleted — history is preserved by design, not by discipline.
5. **Analytics never reads live event tables** — aggregation is precomputed nightly, full stop.
6. **The Gmail send call sits outside the approval database transaction** — external API calls and DB transactions are never mixed, to prevent long-held locks and to make send-failure handling explicit (`send_log.send_status='ambiguous'`) rather than silently retried.

This document is now frozen as the system-design baseline, consistent with the Prompt 1 architecture. Folder structure and implementation-level API contracts (full request/response schemas, validation rules) are the next, separate deliverable.
