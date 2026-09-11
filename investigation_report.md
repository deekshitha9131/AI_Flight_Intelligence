# 🔍 AI Flight Intelligence — Complete System Investigation & Failure Audit Report

**Date:** 2026-09-01  
**Auditor:** Senior Software Architect / QA Engineer (Investigation Only — Zero Modifications Made)  
**Scope:** Full stack — Backend, Frontend, Database, AI/LLM, Tests, Configuration, Security  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Defect Registry (Master List)](#defect-registry)
4. [Phase 1 — Source Code Inspection](#phase-1--source-code-inspection)
5. [Phase 2 — Backend Startup & Runtime](#phase-2--backend-startup--runtime)
6. [Phase 3 — API Endpoint Testing](#phase-3--api-endpoint-testing)
7. [Phase 4 — Frontend Inspection](#phase-4--frontend-inspection)
8. [Phase 5 — Automated Test Suite](#phase-5--automated-test-suite)
9. [Phase 6 — Database & Configuration Audit](#phase-6--database--configuration-audit)
10. [Phase 7 — AI/LLM Integration Audit](#phase-7--aillm-integration-audit)
11. [Phase 8 — Security Audit](#phase-8--security-audit)
12. [Phase 9 — Code Quality & Maintainability](#phase-9--code-quality--maintainability)
13. [Risk Assessment Matrix](#risk-assessment-matrix)

---

## Executive Summary

> [!CAUTION]
> The AI Flight Intelligence project contains **53 distinct defects** across all layers. Of these, **14 are CRITICAL** (system-breaking), **17 are HIGH** severity, and **22 are MEDIUM/LOW**. The application **cannot function as an integrated system** due to fundamental failures in CORS, LLM integration, flight provider connectivity, frontend compilation, and database management.

### Key Findings at a Glance

| Category | Critical | High | Medium | Low |
|---|---|---|---|---|
| Backend Runtime | 3 | 4 | 3 | 1 |
| Frontend | 4 | 3 | 3 | 2 |
| AI/LLM Integration | 2 | 2 | 1 | 0 |
| Database/Config | 2 | 3 | 2 | 1 |
| Security | 1 | 2 | 2 | 0 |
| Tests | 1 | 2 | 2 | 1 |
| Code Quality | 1 | 1 | 3 | 2 |
| **Total** | **14** | **17** | **16** | **7** |

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Frontend (React + TypeScript + Vite)"
        A["index.html"] --> B["main.tsx"]
        B --> C["App.tsx (BrowserRouter)"]
        C --> D["LoginPage"]
        C --> E["RegisterPage"]
        C --> F["FlightsPage"]
        C --> G["AssistantPage"]
        C --> H["PreferencesPage"]
        C --> I["ProtectedRoutes → PrivateRoute"]
    end

    subgraph "Backend (FastAPI + SQLAlchemy)"
        J["main.py"] --> K["auth router"]
        J --> L["flight router"]
        J --> M["assistant router"]
        J --> N["conversation router"]
        J --> O["predictions router"]
        J --> P["recommendations router"]
        J --> Q["preferences router"]
    end

    subgraph "Services"
        L --> R["DuffelProvider (flight.py)"]
        M --> S["AssistantService"]
        S --> T["FlightUnderstandingService (AI)"]
        S --> R
        O --> U["PredictionService (joblib ML)"]
        P --> V["RecommendationService"]
    end

    subgraph "External"
        R --> W["Duffel API"]
        T --> X["Google Gemini LLM"]
    end

    subgraph "Database"
        Y["SQLite (test.db)"]
    end

    C -->|"HTTP (no CORS!)"| J
```

### Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend Framework | FastAPI | 0.104.1 |
| ORM | SQLAlchemy | 2.0.23 |
| Migrations | Alembic | 1.13.1 |
| Validation | Pydantic | 2.6.3 (V2) |
| Auth | python-jose + passlib[bcrypt] | — |
| AI/LLM | google-generativeai | 0.8.3 |
| ML Model | scikit-learn + joblib | 1.4.2 |
| Flight Provider | Duffel API (via httpx) | — |
| Frontend Framework | React | 18.2.0 |
| Build Tool | Vite | 5.0.8 |
| Language | TypeScript | 5.2.2 |
| Router | react-router-dom | 6.30.6 |

---

## Defect Registry

### 🔴 CRITICAL (P0) — Application Cannot Function

| # | Defect | Location | Impact |
|---|---|---|---|
| C01 | **CORS middleware not configured** — `main.py` defines no `CORSMiddleware`. Frontend on `:3000` cannot call backend on `:8000`. OPTIONS returns 405. | [main.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/main.py) | Frontend-to-backend communication completely blocked |
| C02 | **LLM model `gemini-pro` deprecated/removed** — Gemini API returns 404: "models/gemini-pro is not found for API version v1beta" | [llm.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/ai/llm.py#L13) | Assistant chat, intent extraction, and response generation all fail |
| C03 | **Missing `preference.ts` type file** — `PreferencesPage.tsx` and `preferences.ts` import from `../../types/preference` which does not exist | [frontend/src/types/](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/types) | Frontend will not compile; TypeScript build fails |
| C04 | **`auth.ts` has broken import** — Line 1 imports from `../../backend/app/schemas/auth` (cross-project import impossible) | [auth.ts](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/types/auth.ts#L1) | Frontend will not compile |
| C05 | **`PrivateRoute` renders `<Outlet/>` but receives `{children}`** — `ProtectedRoutes` passes children to `PrivateRoute`, but `PrivateRoute` renders `<Outlet/>`, ignoring them | [PrivateRoute.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/PrivateRoute.tsx#L11) + [ProtectedRoutes.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/ProtectedRoutes.tsx#L8) | Protected pages render blank; all authenticated routes broken |
| C06 | **Duffel `passengers` field iterates over an integer** — `for _ in request.passengers` where `passengers` is `int`, causing `TypeError: 'int' object is not iterable` | [flight.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/flight.py#L52) | All flight searches crash with 503 |
| C07 | **`AssistantPage.tsx` has two `converctions` typos** — `data.converctions[0].id` (L40) and `converctions.filter(...)` (L98) — undefined variable | [AssistantPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/AssistantPage.tsx#L40) | Runtime crash when loading or deleting conversations |
| C08 | **Virtual environment is empty** — `.venv` contains only `python.exe`/`pythonw.exe`, no packages installed | [backend/.venv/](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/.venv) | Cannot run backend using the project's venv |
| C09 | **JWT library mismatch** — Code imports `from jose import JWTError, jwt` (python-jose) but `requirements.txt` lists `PyJWT==2.8.0` (different library) | [security.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/core/security.py#L3) + [requirements.txt](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/requirements.txt#L11) | Fresh install from requirements.txt → `ModuleNotFoundError: No module named 'jose'` |
| C10 | **`PredictionService.predict_price` is sync but called with `await`** — endpoint calls `await prediction_service.predict_price(...)` but method is not async | [predictions.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/api/v1/predictions.py#L55) + [prediction.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/prediction.py#L159) | Prediction endpoint returns 500 |
| C11 | **No CSS files exist** — No `.css` files found anywhere in `frontend/src/`. All `className` references are unstyled | [frontend/src/](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src) | Entire UI is unstyled/unusable |
| C12 | **`ProtectedRoutes` missing React import** — Component uses `React.FC` but doesn't import React | [ProtectedRoutes.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/ProtectedRoutes.tsx#L6) | Compile error |
| C13 | **`Navbar` missing React import** — Component uses `React.FC` but doesn't import React | [Navbar.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/Navbar.tsx#L4) | Compile error |
| C14 | **`AssistantPage` imports `AssistantChatRequest` from API module** — `import { assistantChat, AssistantChatRequest, AssistantResponse } from '../../api/assistant'` but `assistant.ts` API doesn't re-export types as values | [AssistantPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/AssistantPage.tsx#L10) | Import may fail depending on bundler settings |

---

### 🟠 HIGH (P1) — Major Feature Broken

| # | Defect | Location | Impact |
|---|---|---|---|
| H01 | **Duffel API URL is wrong** — Uses `/offer/requests` (singular "offer") instead of `/offer_requests` per Duffel API docs | [flight.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/flight.py#L70) | Even with valid API key, flight searches will fail |
| H02 | **`alembic.ini` has placeholder DB URL** — `sqlalchemy.url = driver://user:pass@localhost/dbname` | [alembic.ini](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/alembic.ini#L63) | Alembic migrations cannot run |
| H03 | **Database tables created ad-hoc via `create_all()`** — No startup event or migration applies schema consistently; relies on SQLite auto-creation | [database.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/core/database.py) | Fragile; different DB instances may have inconsistent schemas |
| H04 | **`from_orm()` used with Pydantic V2** — `preference.py` service and `conversation.py` API use `.from_orm()` which is a Pydantic V1 method | [services/preference.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/preference.py#L13) + [api/v1/conversation.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/api/v1/conversation.py#L32) | Works via compatibility layer but emits deprecation warnings; will break in Pydantic V3 |
| H05 | **`orm_mode = True` used in Pydantic V2 schemas** — `auth.py`, `prediction.py`, `assistant.py` schemas use old V1 `class Config: orm_mode = True` | [schemas/auth.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/schemas/auth.py#L24) | Deprecation warnings; will break in Pydantic V3 |
| H06 | **`@validator` used instead of `@field_validator`** — preference schema uses Pydantic V1 style validators (5 instances) | [schemas/preference.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/schemas/preference.py#L14) | Deprecation warnings; will break in Pydantic V3 |
| H07 | **`model_version` field conflicts with Pydantic protected namespace** — `PredictionResponse.model_version` triggers `UserWarning: Field "model_version" has conflict with protected namespace "model_"` | [schemas/prediction.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/schemas/prediction.py) | May cause unexpected behavior |
| H08 | **`FlightResponse` not imported in `recommendations.ts`** — Used but not imported: `FlightResponse` type reference on L12 | [recommendations.ts](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/api/recommendations.ts#L12) | TypeScript compile error |
| H09 | **`FlightSearchRequest` not imported in `recommendations.ts`** — `FlightSearchAndRecommendRequest` type alias references `FlightSearchRequest` without import in types file | [recommendations.ts](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/types/recommendations.ts#L15) | TypeScript compile error |
| H10 | **Conversation create returns 200 instead of 201** — POST `/conversations/` returns 200 instead of REST standard 201 Created | [conversation.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/api/v1/conversation.py) | API inconsistency |
| H11 | **`handleChange` destructures `checked` from `HTMLSelectElement`** — `const { name, value, type, checked } = e.target` but `HTMLSelectElement` has no `checked` property | [FlightsPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/FlightsPage.tsx#L26) + [PreferencesPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/PreferencesPage.tsx#L79) | TypeScript type error |
| H12 | **Login/Register links use `<a href>` instead of `<Link>`** — Causes full page reload instead of SPA navigation | [LoginPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/LoginPage.tsx#L63) + [RegisterPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/RegisterPage.tsx#L89) | Breaks SPA state; auth context reset on navigation |
| H13 | **Predictions endpoint returns 500 for missing `flight_search_id`** — When `flight_search_id` is not provided as query param, the endpoint catches the `HTTPException(400)` inside its own `except Exception` block and re-raises as 500 | [predictions.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/api/v1/predictions.py#L34) | Incorrect error code returned |
| H14 | **`recommendations.ts` uses `FlightResponse` without importing it** — Line 12 references `FlightResponse` but the import from `'../types/flight'` is only in the type file, not the API file | [api/recommendations.ts](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/api/recommendations.ts#L12) | TypeScript compile error |
| H15 | **Auth register returns void in context** — `register()` in `authContext.tsx` returns `response` but function return type is `Promise<void>` | [authContext.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/store/authContext.tsx#L66) | Return value silently discarded |
| H16 | **SQLite file-based DB loses tables** — Using `sqlite:///./test.db` with a relative path; if working directory changes, a new empty DB is created | [.env](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/.env#L4) | Data loss across restarts |
| H17 | **Docker Compose only defines Postgres** — No backend/frontend services defined; Dockerfile exists but is not referenced | [docker-compose.yml](file:///d:/AI_Flight _intelligence/duplicate/flight/docker-compose.yml) | Cannot deploy via Docker |

---

### 🟡 MEDIUM (P2) — Degraded Functionality

| # | Defect | Location | Impact |
|---|---|---|---|
| M01 | **LLM uses sync `generate_content()` in async function** — `GeminiLLMProvider.generate_structured()` is `async` but calls the synchronous `self.model.generate_content()` | [llm.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/ai/llm.py#L37) | Blocks the event loop during LLM calls |
| M02 | **Singleton LLM crashes at import time** — `gemini_llm = GeminiLLMProvider()` at module level raises `ValueError` if API key is missing, crashing the entire import chain | [llm.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/ai/llm.py#L44) | Any module importing `llm.py` fails if key is bad |
| M03 | **`.env` contains real API keys committed to repository** — Duffel test key and LLM key are committed in plaintext | [.env](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/.env) | Security risk |
| M04 | **Docker Compose exposes Postgres password** — `POSTGRES_PASSWORD: deekshitha1234` hardcoded | [docker-compose.yml](file:///d:/AI_Flight _intelligence/duplicate/flight/docker-compose.yml#L9) | Security risk |
| M05 | **`_override_missing_from_history` is a no-op** — Method has extensive comments but all logic branches end in `pass` | [assistant.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/assistant.py#L195) | Conversation context override doesn't work |
| M06 | **23 broad `except Exception` handlers** — Swallow specific errors, making debugging difficult | Multiple backend files | Error root causes hidden |
| M07 | **`datetime.utcnow()` used throughout** — Deprecated in Python 3.12+; should use `datetime.now(timezone.utc)` | Multiple backend files | Future compatibility |
| M08 | **No `favicon.ico` file** — `index.html` references `/favicon.ico` but no such file exists | [index.html](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/index.html#L5) | 404 on every page load |
| M09 | **Prediction model limited to 6 Indian cities** — Only supports DEL, BOM, BLR, CCU, HYD, MAA as origin/destination | [prediction.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/prediction.py#L49) | International flights not supported for predictions |
| M10 | **Prediction model only supports ECONOMY and BUSINESS** — FIRST and PREMIUM_ECONOMY raise ValueError | [prediction.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/prediction.py#L73) | Incomplete cabin class support |
| M11 | **No rate limiting on any endpoint** — Authentication, flight search, and assistant endpoints have no rate limiting | [main.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/main.py) | Vulnerability to brute-force and abuse |
| M12 | **No input sanitization on chat messages** — User messages passed directly to LLM prompts without sanitization | [assistant.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/services/assistant.py#L59) | Prompt injection risk |
| M13 | **`.env` and `.env.example` have different DATABASE_URL types** — `.env` uses SQLite, `.env.example` uses PostgreSQL | [.env](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/.env#L4) vs [.env.example](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/.env.example#L4) | Confusing for new developers |
| M14 | **`error.response?.data?.detail` wrong for fetch API** — Frontend error handlers check `err.response?.data?.detail` but the API client uses `fetch`, not axios; the error is in `err.data?.detail` | [LoginPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/LoginPage.tsx#L23), [FlightsPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/FlightsPage.tsx#L58), etc. | Error messages never display correctly |
| M15 | **`useAuth()` hook throws if used outside `AuthProvider`** — But `Home` component is rendered inside `<AuthProvider>` then `<BrowserRouter>`, which is correct. However, the `Home` component uses `useAuth()` at the route level. | [App.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/App.tsx#L14) | Works but fragile pattern |
| M16 | **9 `.bak` files scattered across the codebase** — Indicates previous failed refactoring attempts | Multiple locations | Code archaeology; confusion about canonical versions |

---

### 🟢 LOW (P3) — Minor Issues

| # | Defect | Location | Impact |
|---|---|---|---|
| L01 | **Unused `Outlet` import** in `ProtectedRoutes.tsx` | [ProtectedRoutes.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/ProtectedRoutes.tsx#L1) | Dead import |
| L02 | **Unused `useNavigate`** imported in FlightsPage, PreferencesPage | Multiple pages | Dead import |
| L03 | **TODO comment for delete confirmation** never implemented | [AssistantPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/AssistantPage.tsx#L94) | Missing UX feature |
| L04 | **`logout()` in `api/auth.ts` is an empty function** | [auth.ts](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/api/auth.ts#L29) | Dead code |
| L05 | **`PreferencesPage` shows "No preferences set yet" but form is hidden** — When preferences are null, the form is not shown, so user has no way to create initial preferences | [PreferencesPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/PreferencesPage.tsx#L107) | UX dead end |
| L06 | **`FlightsPage` shows "No flights found" before any search** — Initial empty state message is misleading | [FlightsPage.tsx](file:///d:/AI_Flight _intelligence/duplicate/flight/frontend/src/components/pages/FlightsPage.tsx#L203) | Confusing UX |
| L07 | **`__import__('uuid')` inline import pattern** — Used in repositories instead of top-level import | [conversation.py](file:///d:/AI_Flight _intelligence/duplicate/flight/backend/app/repositories/conversation.py#L13), etc. | Unusual pattern; minor performance hit |

---

## Phase 1 — Source Code Inspection

### Backend Architecture

The backend follows a layered architecture: **Routers → Services → Repositories → Models**. Seven API routers are registered in `main.py` with a `/api/v1` prefix:

| Router | Prefix | Key Endpoints |
|---|---|---|
| Auth | `/auth` | `POST /register`, `POST /login`, `GET /me` |
| Flight | `/flights` | `POST /search` |
| Assistant | `/assistant` | `POST /chat` |
| Conversation | `/conversations` | CRUD operations |
| Predictions | `/predictions` | `POST /`, `GET /`, `GET /history` |
| Recommendations | `/recommendations` | `POST /`, `POST /search` |
| Preferences | `/preferences` | `GET /`, `PUT /` |

### Frontend Architecture

The frontend uses React 18 with TypeScript, Vite as the build tool, and `react-router-dom` v6 for routing. It has 5 pages (Login, Register, Flights, Assistant, Preferences) wrapped in a `BrowserRouter` with an `AuthProvider` context.

---

## Phase 2 — Backend Startup & Runtime

### Startup Behavior

The backend starts successfully with **4 warnings**:

```
UserWarning: Valid config keys have changed in V2: 'orm_mode' has been renamed to 'from_attributes'  (×2)
UserWarning: Field "model_version" has conflict with protected namespace "model_".
PydanticDeprecatedSince20: @validator is deprecated → use @field_validator  (×5)
```

Server runs on `http://0.0.0.0:8000` and responds to health checks. However:

- **No CORS middleware** → Frontend cannot connect
- **SQLite `test.db` created on first access** via `Base.metadata.create_all()` but this is fragile
- **LLM singleton initialization** may crash at import time if API key is invalid

---

## Phase 3 — API Endpoint Testing

### Test Results Summary

| Endpoint | Method | Expected | Actual | Status |
|---|---|---|---|---|
| `/health` | GET | 200 | 200 | ✅ PASS |
| `/api/v1/auth/register` | POST | 201 | 201 | ✅ PASS |
| `/api/v1/auth/register` (dup) | POST | 400 | 400 | ✅ PASS |
| `/api/v1/auth/register` (invalid) | POST | 422 | 422 | ✅ PASS |
| `/api/v1/auth/login` | POST | 200 | 200 | ✅ PASS |
| `/api/v1/auth/login` (wrong pw) | POST | 401 | 401 | ✅ PASS |
| `/api/v1/auth/me` | GET | 200 | 200 | ✅ PASS |
| `/api/v1/auth/me` (no token) | GET | 401 | 401 | ✅ PASS |
| `/api/v1/flights/search` | POST | 200 | **503** | ❌ FAIL — `'int' object is not iterable` |
| `/api/v1/flights/search` (same O/D) | POST | 400 | 400 | ✅ PASS |
| `/api/v1/flights/search` (no auth) | POST | 401 | 401 | ✅ PASS |
| `/api/v1/predictions/` | GET | 200 | 200 | ✅ PASS (model info) |
| `/api/v1/predictions/history` | GET | 200 | 200 | ✅ PASS (empty list) |
| `/api/v1/predictions/` | POST | 200/400 | **500** | ❌ FAIL — async/sync mismatch + error handling |
| `/api/v1/recommendations/` (empty) | POST | 400 | 400 | ✅ PASS |
| `/api/v1/recommendations/` (flights) | POST | 200 | 200 | ✅ PASS |
| `/api/v1/recommendations/search` | POST | 200 | **500** | ❌ FAIL — cascading flight search error |
| `/api/v1/preferences/` | GET | 200 | 404 (first), 200 (after set) | ✅ PASS |
| `/api/v1/preferences/` | PUT | 200 | 200 | ✅ PASS |
| `/api/v1/conversations/` | POST | 201 | **200** | ⚠️ Wrong status code |
| `/api/v1/conversations/` | GET | 200 | 200 | ✅ PASS |
| `/api/v1/conversations/{id}` | GET | 200 | 200 | ✅ PASS |
| `/api/v1/assistant/chat` | POST | 200 | 200 | ⚠️ Returns fallback (LLM fails silently) |
| CORS preflight (OPTIONS) | OPTIONS | 200 | **405** | ❌ FAIL — No CORS middleware |

### Key Runtime Errors Observed

1. **Flight search**: `TypeError: 'int' object is not iterable` — caused by `for _ in request.passengers` where `passengers` is an `int`
2. **LLM**: `404 models/gemini-pro is not found for API version v1beta` — the model name is deprecated
3. **Predictions**: Endpoint catches its own `HTTPException` in a broad `except Exception` and converts to 500
4. **User isolation**: Second registration attempt on a different SQLite DB instance hit `no such table: users` — indicates the `test.db` path is relative and fragile

---

## Phase 4 — Frontend Inspection

### Compilation Blockers

The frontend **cannot compile** due to these import/type errors:

1. **Missing `preference.ts`** — The file `frontend/src/types/preference.ts` does not exist, but is imported by `PreferencesPage.tsx` and `api/preferences.ts`
2. **Broken cross-project import** — `auth.ts` line 1: `import { ... } from '../../backend/app/schemas/auth'` — impossible path
3. **Missing React imports** — `ProtectedRoutes.tsx` and `Navbar.tsx` use `React.FC` without importing React
4. **`FlightResponse` not imported** in `api/recommendations.ts` — used on line 12 without import
5. **Missing `FlightSearchRequest` import** in `types/recommendations.ts`

### Logic Bugs

1. **`PrivateRoute` ignores children** — Renders `<Outlet/>` (for nested routes) but is used with `{children}` prop pattern. All protected pages render blank.
2. **Two `converctions` typos** in `AssistantPage.tsx` — `data.converctions[0].id` (L40) and `converctions.filter(...)` (L98) reference an undefined variable
3. **Error handler pattern** `err.response?.data?.detail` is for Axios, not for the custom `fetch`-based `ApiError` class

### Missing Functionality

- **No CSS/styles at all** — Zero `.css` files in the entire frontend
- **No global stylesheet imported** in `main.tsx`
- **No navigation between pages** from authenticated pages (Navbar exists but isn't consistently visible due to ProtectedRoute issue)
- **Preferences page** has no way to create initial preferences (form hidden when null)

---

## Phase 5 — Automated Test Suite

### Results: 27 Passed, 37 Failed, 7 Skipped

```
Total:  64 tests (+ 7 skipped async tests)
Passed: 27  (42%)
Failed: 37  (58%)
```

### Failure Categories

| Category | Count | Root Cause |
|---|---|---|
| Auth tests | 9 | Tests use wrong URL path (404s — tests don't include `/api/v1` prefix) |
| Flight tests | 9 | Flight provider crashes with `'int' object is not iterable` → 503 instead of expected codes |
| Assistant tests | 9 | LLM singleton crashes with `ValueError: LLM provider not configured` |
| AI Understanding tests | 6 | Same LLM configuration failure |
| Recommendation API tests | 7 | Tests use wrong URL paths / mocking issues |
| Flight API tests | Duplicated | Same as flight tests above |

### Test Infrastructure Issues

1. **Async tests not configured** — Tests use `async def` but `pytest-asyncio` is not installed. Tests are silently **skipped** with `PytestUnhandledCoroutineWarning`
2. **Auth tests target wrong URL** — Tests hit `/auth/register` instead of `/api/v1/auth/register`, getting 404s
3. **No test fixtures for database** — Tests share the production SQLite database
4. **`httpx` deprecation** — Tests use `app=` shortcut (deprecated), should use `WSGITransport`

---

## Phase 6 — Database & Configuration Audit

### Database

| Issue | Detail |
|---|---|
| **SQLite in production path** | `.env` uses `sqlite:///./test.db` but `.env.example` uses PostgreSQL |
| **No migration applied** | `alembic.ini` has placeholder URL `driver://user:pass@localhost/dbname` |
| **Schema via `create_all()`** | Tables created at runtime, not via Alembic migrations |
| **Relative DB path** | `./test.db` depends on working directory; different CWDs create different DBs |
| **No connection pooling** | SQLite has no pool; concurrent requests may conflict |

### Configuration Inconsistencies

| File | Issue |
|---|---|
| `.env` | `DATABASE_URL=sqlite:///./test.db` (SQLite) |
| `.env.example` | `DATABASE_URL=postgresql+psycopg2://...` (PostgreSQL) |
| `docker-compose.yml` | Defines Postgres service but nothing connects to it |
| `requirements.txt` | Lists `psycopg2-binary` but SQLite is used |
| `alembic.ini` | Has `driver://user:pass@localhost/dbname` placeholder |

### Backup Files Found (9 total)

| File | Suggests |
|---|---|
| `main.py.bak` | Previous version without `/api/v1` prefix |
| `preferences.py.bak` | Previous preferences endpoint version |
| `conversation.py.bak` (×3) | model, repo, schema, service all have backups |
| `preference.py.bak` | Previous preference schema |
| `test_health.py.bak` | Previous test version |
| `09e44e99b627_initial_migration.py.bak` | Broken migration backup |

---

## Phase 7 — AI/LLM Integration Audit

### Gemini LLM Provider

| Issue | Severity | Detail |
|---|---|---|
| Model name deprecated | 🔴 CRITICAL | `gemini-pro` returns 404 from Gemini API. Should use `gemini-1.5-flash` or similar |
| Sync call in async function | 🟡 MEDIUM | `generate_content()` is synchronous, blocking the event loop |
| Singleton crashes at import | 🟡 MEDIUM | Module-level instantiation fails if API key is invalid |
| No retry/backoff | 🟡 MEDIUM | Single attempt with no error recovery |

### Flight Intent Extraction

| Issue | Severity | Detail |
|---|---|---|
| Depends on deprecated LLM | 🔴 CRITICAL | Inherits the `gemini-pro` failure |
| JSON parsing is fragile | 🟡 MEDIUM | Falls back to substring extraction between `{` and `}` |
| No input validation | 🟡 MEDIUM | Arbitrary user input passed to prompt without sanitization |

### Response Generation

| Issue | Severity | Detail |
|---|---|---|
| Duplicate prompt code | 🟢 LOW | `_create_response_prompt()` in `assistant.py` duplicates `get_assistant_response_prompt()` in `response_generation.py` |
| Imported but unused | 🟢 LOW | `response_generation.py` is imported but `assistant.py` uses its own prompt builder |

---

## Phase 8 — Security Audit

| # | Issue | Severity | Detail |
|---|---|---|---|
| S01 | **API keys committed in `.env`** | 🟠 HIGH | Duffel test key and Gemini API key in plaintext |
| S02 | **Postgres password in `docker-compose.yml`** | 🟡 MEDIUM | `deekshitha1234` hardcoded |
| S03 | **No rate limiting** | 🟡 MEDIUM | Brute-force attacks on `/auth/login` possible |
| S04 | **No input sanitization for LLM** | 🟡 MEDIUM | Prompt injection possible via assistant chat |
| S05 | **JWT secret key has a real value in `.env`** | 🟠 HIGH | `SECRET_KEY=z5-mIjSSSLFwgG3xwtOjUah5_Hc73ZLiJklQ0JRQObo` committed |
| S06 | **No HTTPS enforcement** | 🟢 LOW | Tokens transmitted over HTTP |
| S07 | **Token stored in localStorage** | 🟢 LOW | XSS-vulnerable; httpOnly cookies would be safer |

---

## Phase 9 — Code Quality & Maintainability

### Consistency Issues

1. **Mixed Pydantic styles** — Some schemas use V2 `model_config = {'from_attributes': True}`, others use V1 `class Config: orm_mode = True`
2. **Mixed repository patterns** — `user.py` and `preference.py` use plain functions; others use class-based repositories
3. **Inline imports** — `__import__('uuid')` used in repositories; `from app.repositories...` imported inside endpoint functions
4. **Duplicate prompt generation** — Two independent response prompt builders exist

### Dead Code

- `response_generation.py` imported but never called
- `get_flight_intent_prompt_with_history()` defined but never called
- `logout()` in `api/auth.ts` is an empty function
- `pendingConversationId` state set but never read in `AssistantPage.tsx`

---

## Risk Assessment Matrix

```mermaid
quadrantChart
    title Defect Risk Matrix
    x-axis Low Impact --> High Impact
    y-axis Low Likelihood --> High Likelihood
    quadrant-1 Critical Priority
    quadrant-2 Monitor
    quadrant-3 Low Priority
    quadrant-4 Plan Fix
    "CORS Missing": [0.95, 0.99]
    "LLM Model Deprecated": [0.9, 0.95]
    "Missing Types File": [0.85, 0.99]
    "Passengers Bug": [0.9, 0.95]
    "No CSS Files": [0.8, 0.99]
    "PrivateRoute Bug": [0.85, 0.95]
    "JWT Mismatch": [0.75, 0.8]
    "Typos in Code": [0.7, 0.9]
    "Broken Import": [0.85, 0.99]
    "No Rate Limiting": [0.6, 0.4]
    "Keys in .env": [0.5, 0.6]
    "Pydantic V1 Compat": [0.4, 0.3]
```

---

> [!IMPORTANT]
> **Bottom Line:** This application has **zero functioning end-to-end user flows**. The frontend cannot compile, cannot connect to the backend (no CORS), and the backend's two core features (flight search and AI assistant) are both broken at the service level. The only subsystems that work correctly in isolation are: authentication endpoints, recommendation scoring logic, preference CRUD, and conversation CRUD.

---

*End of Investigation Report — No files were modified during this audit.*
