# Implementation Plan: AI Concierge Phase 2 — Persistence, WordPress Auth, Rate Limiting, Noor Allocation

**Branch**: `001-concierge-chat-api` | **Date**: 2026-04-16 | **Spec**: `specs/001-concierge-chat-api/spec.md`
**Input**: Phase 1 backend (complete + optimized) + Client Requirements Document (2026-04-16)

---

## Summary

Phase 1 delivered a stateless FastAPI concierge with hybrid skill routing, RAG grounding, and 1,958ms p95 latency. Phase 2 layers in **client-mandated production hardening**:

1. **Rate limiting + 15s timeout + crash prevention** (CRITICAL — prevents API abuse, cost explosion, server overload)
2. **Neon Serverless Postgres persistence** (users, chat history, appointments, noor_allocation_requests, activity log)
3. **WordPress-bridged authentication** (client site is WP; we trust WP-issued JWT and mirror users into Neon)
4. **Noor Allocation request workflow** (143-piece collection — formal request, concierge approval, cooldown)
5. **Personalization engine** (returning users greeted with profile + last-discussed context, recommendations grounded in saved preferences)
6. **Notification fan-out** (concierge email + Slack on appointment / Noor request, confirmation email to client)

**Approach**: Extend the existing `backend/app/` layout with `db/`, `auth/`, `middleware/`, and `services/notifications/` modules. Stateless API contract is preserved — server-side persistence is for memory/personalization/audit, not session state. Conversation context is still passed in the request body, but capped to 10–15 messages and merged with persisted summary on the server.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI (async), OpenAI Agents SDK + Responses API (`gpt-4.1`), Qdrant client, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic (migrations), `python-jose` (JWT verification), `httpx` (WP REST calls), `slowapi` or custom Redis-backed limiter, `redis.asyncio`, SendGrid SDK (or AWS SES), `slack_sdk` (async webhook).
**Storage**:
  - **Neon Serverless Postgres** (primary OLTP — users, chat_history, appointments, noor_allocation_requests, user_activity)
  - **Qdrant** (vector store, unchanged from Phase 1)
  - **Redis** (rate-limit counters, idempotency keys, optional short-term cache) — Upstash serverless if Neon-style serverless preferred
**Testing**: pytest + pytest-asyncio + httpx AsyncClient; testcontainers-postgres for integration; respx for OpenAI/WordPress HTTP mocking
**Target Platform**: Linux container (Docker) on Fly.io / Railway / Render; Neon as managed Postgres
**Project Type**: Web (backend-only — UI is the client's WordPress site + existing Next.js test harness)
**Performance Goals**:
  - p95 chat latency ≤ 3s (unchanged)
  - Auth verification ≤ 150ms (cached JWKS)
  - DB writes (chat persistence) ≤ 50ms async (non-blocking on response path)
  - Rate-limit check ≤ 5ms
**Constraints**:
  - Max 5 requests/min/IP on `/chat`
  - 15s hard request timeout
  - Conversation context capped at 15 messages server-side regardless of payload
  - WP is source of truth for identity; we never store WP password hashes
  - All AI-side keys server-side only (constitution IV)
**Scale/Scope**: Single tenant (Aueshah), expected <1k DAU initially, ~143 Noor pieces total, low-volume appointment requests (<100/month at launch)

### NEEDS CLARIFICATION (resolved in Phase 0 research.md)

- WP auth mechanism (JWT plugin vs Application Passwords vs Cookie-shared) → see research.md §1
- Notification provider (SendGrid vs AWS SES vs Postmark) → see research.md §3
- Redis provider (Upstash serverless vs self-hosted) → see research.md §2
- Cooldown duration default for Noor re-requests → see research.md §4
- Concierge admin surface (separate Next.js admin vs WP admin plugin) → see research.md §5

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| § | Principle | Phase 2 Compliance |
|---|-----------|-------------------|
| I | Controlled concierge | ✅ Personalization stays within brand rails; no generic-assistant drift |
| II.1 | Backend-first | ✅ All auth/db/rate-limit logic in FastAPI; WP only issues identity token |
| II.2 | Separation of concerns | ✅ New layers stay in their lanes: `db/` only DB, `auth/` only identity, `middleware/` only cross-cutting |
| II.3 | Stateless API | ✅ Request still self-contained (token + context in headers/body); persistence is for memory, not session |
| II.4 | Server-side AI calls | ✅ Unchanged |
| II.5 | Async-first | ✅ asyncpg + SQLAlchemy 2.0 async + httpx async + redis.asyncio |
| III | AI behavior rules | ✅ Personalization grounds in retrieved profile, not invention; uncertainty preserved |
| IV | Skills routing | ✅ New `noor_request` flow is part of existing `noor` skill — no new skill class added without registry |
| V | RAG standards | ✅ Unchanged — Qdrant only, top-k=3, 500–800 token chunks |
| VI.1 | `visitor_id` primary key | ⚠️ Identity now anchored on `wp_user_id` (mapped to internal `user_id`); `visitor_id` retained for anonymous pre-login messages, merged on first login. **Justified**: WP is product source of truth; ADR required. |
| VI.2 | Store summaries, not transcripts | ⚠️ Client explicitly requires chat history persistence. **Justified**: store full messages but cap *prompt context* to 15. ADR required. |
| VI.3 | Active context bounded ≤15 | ✅ Enforced in middleware before AI call |
| VI.4 | Privacy by default | ✅ Profile fields are user-provided (profiling Q&A), not inferred |
| VII | Tooling rules | ✅ Notification + DB writes are explicit, validated, logged |
| VIII | API contract stability | ✅ `/chat` shape preserved; new endpoints under `/v1/auth/*`, `/v1/appointments`, `/v1/noor-requests` |
| IX.3 | Rate limiting mandatory | ✅ Now enforced — was the gap |
| X.1 | p95 ≤ 3s | ✅ Persistence on background task; reads cached |
| X.3 | Graceful degradation | ✅ DB-down → log warning, serve chat without history; Redis-down → fail-open with logged warning |
| XI | SDD cycle | ✅ This plan precedes implementation |
| XII | Non-goals | ✅ No new generic-assistant capabilities |

**Constitution Violations Requiring ADR**:
1. **VI.1** — `wp_user_id` becomes the primary identity anchor (vs `visitor_id`-only) → ADR-002
2. **VI.2** — Full chat messages persisted (not only summaries) → ADR-003
3. **IX.3** — Phase 1 deferred rate limiting; now formally added → tracked as compliance restoration, ADR-004 documents the limiter design

These are tracked in **Complexity Tracking** below and will be raised as ADR suggestions to the user before code lands.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-concierge-chat-api/
├── plan.md              # THIS FILE
├── research.md          # Phase 0 — WP auth, Redis, notifications, cooldown, admin surface
├── data-model.md        # Phase 1 — 5 Neon tables + relationships
├── quickstart.md        # Phase 1 — local dev setup (Neon + Redis + WP test mode)
├── contracts/
│   └── openapi.yaml     # Phase 1 — extended API (auth, appointments, noor-requests, admin)
└── tasks.md             # Phase 2 — generated by /sp.tasks (NOT by this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes.py                  # /chat (extended), /health (existing)
│   │   ├── auth_routes.py             # NEW — /v1/auth/wp-login, /v1/auth/me, /v1/auth/logout
│   │   ├── appointment_routes.py      # NEW — /v1/appointments (POST/GET status)
│   │   ├── noor_routes.py             # NEW — /v1/noor-requests (POST/GET status)
│   │   └── admin_routes.py            # NEW — /v1/admin/noor-requests (concierge approve/decline)
│   ├── auth/                          # NEW
│   │   ├── wp_verifier.py             # Verify WP-issued JWT (JWKS fetch + cache)
│   │   ├── dependencies.py            # FastAPI Depends(get_current_user)
│   │   └── visitor.py                 # Anonymous visitor_id cookie issuance + merge-on-login
│   ├── core/                          # Existing — orchestrator, intent_classifier, prompt_builder, tool_handler
│   │   └── personalization.py         # NEW — load profile + last-N summary, inject into prompt
│   ├── db/                            # NEW
│   │   ├── session.py                 # Async engine + sessionmaker (Neon DSN)
│   │   ├── models.py                  # SQLAlchemy 2.0 declarative — User, ChatMessage, Appointment, NoorAllocationRequest, UserActivity
│   │   └── repositories/
│   │       ├── users.py
│   │       ├── chat_history.py
│   │       ├── appointments.py
│   │       └── noor_requests.py
│   ├── middleware/                    # NEW
│   │   ├── rate_limiter.py            # Redis-backed sliding-window, 5/min/IP, fail-open
│   │   ├── timeout.py                 # 15s hard cap via asyncio.wait_for
│   │   └── error_handler.py           # Unified fallback message envelope
│   ├── services/                      # Existing + new
│   │   ├── ai_client.py               # Existing
│   │   ├── rag_service.py             # Existing
│   │   ├── failure_handler.py         # Existing
│   │   ├── embedding_client.py        # Existing
│   │   ├── notifications/             # NEW
│   │   │   ├── email.py               # SendGrid wrapper (concierge alert + client confirmation)
│   │   │   └── slack.py               # Async webhook → #noor-requests / #appointments
│   │   ├── noor_workflow.py           # NEW — create_request, check_cooldown, approve, decline
│   │   └── appointment_workflow.py    # NEW — create + notify (replaces inline /appointment-request)
│   ├── skills/                        # Existing — base, product, compare, noor, bespoke, general
│   ├── models/
│   │   ├── schemas.py                 # Extended — add WPLoginRequest, NoorAllocationRequest schemas, AppointmentRequest already exists
│   │   └── errors.py                  # Existing + AuthFailure, RateLimited, CooldownActive
│   ├── config/
│   │   ├── settings.py                # + NEON_DATABASE_URL, REDIS_URL, WP_BASE_URL, WP_JWKS_URL, SENDGRID_API_KEY, SLACK_WEBHOOK_*
│   │   ├── prompts.py                 # Existing (already optimized)
│   │   └── routing_rules.yaml         # Existing
│   └── main.py                        # Existing — register new middleware + routers
├── alembic/                           # NEW — migrations
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py            # Creates all 5 tables + indexes
├── tests/
│   ├── integration/
│   │   ├── test_api_endpoint.py       # Existing
│   │   ├── test_auth_flow.py          # NEW
│   │   ├── test_rate_limiter.py       # NEW
│   │   ├── test_noor_workflow.py      # NEW
│   │   └── test_appointment_workflow.py # NEW
│   └── unit/
│       ├── test_personalization.py    # NEW
│       └── test_history_capping.py    # NEW
├── requirements.txt                   # + sqlalchemy[asyncio], asyncpg, alembic, redis, python-jose, httpx, sendgrid, slack_sdk
├── alembic.ini                        # NEW
└── .env.example                       # Updated with new vars
```

**Structure Decision**: Extend existing `backend/app/` layout with four new top-level modules (`auth/`, `db/`, `middleware/`, `services/notifications/`). No new top-level project. Frontend is unchanged — the existing test UI continues to work, and the production UI is the client's WordPress site (out of scope for this repo).

---

## Phase 0: Research Topics

To be resolved in `research.md`:

1. **WordPress → Backend identity bridge**
   - Options: (a) WP JWT Authentication plugin (RS256 JWKS), (b) WP Application Passwords (Basic auth → exchange for our JWT), (c) WP cookie + nonce shared via reverse proxy
   - Decide: signing algorithm, JWKS caching TTL, claim mapping (`sub` → `wp_user_id`, `email`, `display_name`)

2. **Rate-limit + Redis provider**
   - Upstash serverless (REST + Redis protocol, free tier) vs Fly Redis vs Render Redis
   - Sliding window vs fixed window vs token bucket — pick sliding window log for fairness at low limits (5/min)

3. **Notification provider**
   - SendGrid (free 100/day) vs AWS SES (cheaper at scale, more setup) vs Postmark (best deliverability, paid)
   - Slack: incoming webhook URL per channel (#noor-requests, #appointments)

4. **Noor cooldown policy**
   - Default 90 days post-approval; configurable per-user override; pending requests block new submissions immediately

5. **Concierge admin surface**
   - MVP: minimal token-protected endpoints + curl/Postman; v2: lightweight Next.js admin page or WP plugin embedding our admin API

6. **Stateless contract preservation**
   - How to merge persisted history with caller-supplied context without breaking statelessness — answer: caller still passes context; server treats it as ephemeral display state, while persisted history feeds personalization separately

---

## Phase 1: Design Artifacts (to be produced)

### data-model.md (entities)

5 tables in Neon:

1. **users** — `id` (uuid pk), `wp_user_id` (int unique), `email` (citext unique), `display_name`, `phone`, `age_range`, `skin_tone`, `style_preference`, `preferred_collection`, `favorite_metals` (text[]), `favorite_styles` (text[]), `status`, `created_at`, `last_seen_at`
2. **chat_messages** — `id`, `user_id` fk (nullable for anon), `visitor_id`, `session_id`, `role` ('user'|'assistant'), `content`, `intent`, `skill`, `latency_ms`, `created_at` — partitioned by month if volume warrants
3. **appointments** — `id`, `reference_id` (APT-XXXXXXXX unique), `user_id` fk, `appointment_type`, `preferred_date`, `notes`, `status` ('pending'|'confirmed'|'completed'|'cancelled'), `confirmed_by`, `scheduled_at`, `meeting_link`, `created_at`, `updated_at`
4. **noor_allocation_requests** — `id`, `user_id` fk, `full_name`, `purpose`, `timeline`, `delivery_location`, `contact_method`, `contact_details`, `status` ('pending'|'approved'|'declined'), `cooldown_until`, `submitted_at`, `reviewed_at`, `reviewed_by`, `internal_notes`, `source` default 'AI Concierge', `created_at`, `updated_at`
5. **user_activity** — `id`, `user_id` fk, `activity_type`, `details` (jsonb), `created_at`

Indexes: `users(email)`, `users(wp_user_id)`, `chat_messages(user_id, created_at desc)`, `noor_allocation_requests(user_id, status)`, `appointments(user_id, status)`.

### contracts/openapi.yaml (extended API)

New / changed endpoints:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/auth/wp-login` | WP token in body | Verify WP JWT, mint our session JWT, upsert user |
| GET | `/v1/auth/me` | Bearer | Return current user profile |
| POST | `/v1/auth/logout` | Bearer | Invalidate session |
| POST | `/chat` | Optional Bearer | Existing — now persists + personalizes if authed |
| POST | `/v1/appointments` | Optional Bearer | Create appointment, notify concierge |
| GET | `/v1/appointments/{ref_id}` | Bearer | Status check |
| POST | `/v1/noor-requests` | Bearer required | Create Noor allocation request (cooldown enforced) |
| GET | `/v1/noor-requests/me` | Bearer | List own requests + status |
| GET | `/v1/admin/noor-requests` | Admin token | List all pending |
| PATCH | `/v1/admin/noor-requests/{id}` | Admin token | Approve / decline + notes |
| GET | `/health` | None | Existing |

All responses follow stable error envelope: `{ "error": "string", "code": int }`.

### quickstart.md (local dev)

```bash
# 1. Provision Neon (free tier) → copy connection string
cp backend/.env.example backend/.env
# Set NEON_DATABASE_URL, REDIS_URL (Upstash), WP_BASE_URL, WP_JWKS_URL,
#     SENDGRID_API_KEY, SLACK_WEBHOOK_NOOR, SLACK_WEBHOOK_APPOINTMENTS,
#     ADMIN_API_TOKEN, JWT_SIGNING_KEY

# 2. Run migrations
cd backend && alembic upgrade head

# 3. Seed Qdrant (existing script, unchanged)
python -m app.scripts.seed_rag

# 4. Start dev server
uvicorn app.main:app --reload --port 8000

# 5. Local WP mock (for offline dev)
python -m app.scripts.wp_mock --port 8080
```

### Agent context update

Run `.specify/scripts/bash/update-agent-context.sh claude` to add new tech (Neon, asyncpg, SQLAlchemy 2.0 async, Alembic, Redis, python-jose, SendGrid, slack_sdk) to `CLAUDE.md` between markers — preserving manual additions.

---

## Phase 2 (NOT this command): Tasks

Will be produced by `/sp.tasks`. Anticipated grouping (for forward visibility only):

- **Group A — Foundation (Days 1–2)**: Redis + rate-limit middleware, 15s timeout, error envelope, conversation history capping middleware, integration tests
- **Group B — Persistence (Days 3–4)**: Neon setup, Alembic migration 0001, SQLAlchemy models, repositories, async session wiring
- **Group C — WP Auth (Days 5–6)**: JWKS verifier, `/v1/auth/wp-login`, `Depends(get_current_user)`, anonymous visitor cookie + merge-on-login, ADR-002
- **Group D — Personalization (Days 7–8)**: `core/personalization.py`, profile-aware system prompt block, persisted-history retrieval (last N), `/chat` extension, ADR-003
- **Group E — Noor Allocation (Days 9–10)**: `noor_workflow.py`, `/v1/noor-requests` POST/GET, cooldown enforcement, admin endpoints, notifications wiring
- **Group F — Appointments (Day 11)**: Migrate inline `/appointment-request` into `appointment_workflow.py`, add notifications, status endpoint
- **Group G — Test & Harden (Days 12–13)**: Load test rate limit, timeout chaos test, end-to-end flow tests, deploy to staging

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution VI.1 — `wp_user_id` as identity anchor (was: `visitor_id` only) | Client product runs on WordPress; users already have WP accounts. Forcing a parallel `visitor_id`-first identity creates double accounts and breaks "remember me across sessions" requirement. | Visitor-only identity rejected: cannot satisfy "personalization based on saved profile" because we'd have no stable cross-device key. ADR-002 will document. |
| Constitution VI.2 — Persist full chat messages (not only summaries) | Client explicitly requires "AI bot will remember the user by his recent activities" — distillation loses the recency signal needed for warm re-engagement greetings. | Summary-only rejected: cannot reconstruct "last discussed Noor Collection" without raw messages. Mitigated by capping *prompt context* to 15 (constitution VI.3 still satisfied). ADR-003 will document. |
| New top-level modules `auth/`, `db/`, `middleware/`, `services/notifications/` | Each is a distinct concern with its own test surface and dependency footprint. Folding them into existing modules would violate II.2 separation of concerns. | Single `services/` dump rejected: would create a 20+ file mega-module and entangle JWT logic with OpenAI logic. |

ADR suggestions to be raised after this plan is approved:
- **ADR-002**: WordPress JWT as primary identity anchor for personalization
- **ADR-003**: Persist full chat messages with prompt-context cap (vs summary-only)
- **ADR-004**: Sliding-window Redis rate limiter (5 req/min/IP) + 15s timeout middleware
- **ADR-005**: Neon Serverless Postgres as primary OLTP store
