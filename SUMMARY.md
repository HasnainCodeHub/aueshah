# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-04-16
**Branch**: `001-concierge-chat-api`
**Status**: Phase 2 IN PROGRESS — Groups A, B, C COMPLETE (45/45 tests passing)
**Purpose**: Full context for any next Claude session picking up this project.

---

## 1. The Client

**Aueshah** — luxury fine jewelry house (https://aueshah.com/).
- 30+ years heritage (founded 1987 as Al-Syed Jewellers by Syed Rashid Ali Shah; Aueshah launched 2018).
- Brand meaning: **Au** (gold, elemental symbol) + **esha** (desire) + **Shah** (family lineage).
- Philosophy: *"Not crafted to impress. Crafted to be felt."*
- Ethical sourcing, lifetime warranty, blockchain-backed authenticity (NFT on Ethereum).

### Offerings
- **Categories**: rings, bracelets, earrings, pendants, necklaces, tiaras, waist adornments.
- **Collections**: **Noor** (limited 143-piece edition), **Empire Allegiance**, **Velvet Line**, **Luxura Series**.
- **Bespoke service**: custom design led by a private concierge and atelier.
- **Support**: repairs, virtual appointments, size guide (US/EU/UK PDFs), warranty.

### Catalog size
- 60 non-Noor pieces scraped with full detail (EUR 1,818 – EUR 2,913,410).
- 5 Noor pieces (ring, bracelet, earrings, necklace, tiara) — all 925 sterling silver + 18k gold plating, Mughal jali design.

---

## 2. What We're Building

A stateless, controlled **FastAPI** concierge backend + **Next.js** chat UI:
- All routing + model invocation now runs through the **OpenAI Agents SDK** (triage agent with native handoffs to 5 specialists).
- Skills: `product`, `compare`, `noor`, `bespoke`, `general`.
- **Hybrid knowledge**: static JSON for Noor profile matching (deterministic scoring) + Qdrant RAG for everything else.
- **Two-layer off-topic defense**: keyword regex guardrail + prompt-level SCOPE section → warm 200 OK redirect (no error bubble in UI).
- Async end-to-end. Model: **gpt-4.1** (OpenAI).
- Strict constitution compliance (12 principles, `.specify/memory/constitution.md`).

### Latency budgets (p95 ≤ 3s)
Routing ≤ Agents SDK overhead · RAG ≤ 2.5s (trans-region to Qdrant Cloud eu-west-1) · AI ≤ 2s.

---

## 3. Stack & Tooling

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI async, Pydantic v2, **openai-agents** SDK, qdrant-client |
| Database | **Neon Serverless Postgres** (SQLAlchemy 2.0 async + asyncpg, Alembic migrations) |
| Cache/Rate Limit | **Redis** (sliding-window sorted set, fail-open) |
| Auth | WordPress RS256 JWT (JWKS) → our HS256 session JWT (python-jose) |
| Package manager | **uv** (`backend/pyproject.toml` + `uv.lock`) |
| UI | Next.js 14 (Pages Router), React 18, TypeScript |
| Vector store | **Qdrant Cloud (eu-west-1)** — collection `aueshah_knowledge`, 108 points loaded |
| Notifications (planned) | SendGrid (email) + Slack SDK (webhooks) |
| Deploy (planned) | Docker Compose (`docker-compose.yml` present) |

### Commands
```bash
# Backend
cd backend
uv sync                                                   # one-time
uv run uvicorn app.main:app --reload --port 8000          # dev
uv run pytest tests/integration/ -v                       # tests

# UI
cd ui
npm install
npm run dev                                               # http://localhost:3000

# RAG loader (re-run whenever heritage.md / products.json changes)
cd backend
python -m scripts.load_rag
python -m scripts.smoke_rag                               # sanity-check retrieval
```

Backend runs on http://localhost:8000 (health: `GET /health`).

---

## 4. Project Structure (important files only)

```
aueshah/
├── .specify/memory/constitution.md          # 12 non-negotiable principles
├── specs/001-concierge-chat-api/            # spec.md / plan.md / tasks.md / research.md / data-model.md
│   └── contracts/openapi.yaml               # Phase 2 API contracts (auth, noor, admin)
├── history/adr/                             # ADR-0001 (persistence+identity), ADR-0002 (hardening)
├── Data.txt                                 # Brand brain source (already encoded in SYSTEM_PROMPT)
├── backend/
│   ├── pyproject.toml                       # uv-managed deps (openai-agents added)
│   ├── requirements.txt                     # Phase 2 deps: sqlalchemy, asyncpg, alembic, redis, python-jose, sendgrid, slack_sdk
│   ├── .env                                 # OPENAI_API_KEY, QDRANT_*, NEON_DATABASE_URL, REDIS_URL, WP_*, JWT_*
│   ├── alembic.ini                          # Alembic config → NEON_DATABASE_URL
│   ├── alembic/
│   │   ├── env.py                           # Async engine for migrations
│   │   └── versions/0001_initial_schema.py  # 5 tables: users, chat_messages, appointments, noor_allocation_requests, user_activity
│   ├── app/
│   │   ├── main.py                          # FastAPI app + middleware stack + auth_router wired
│   │   ├── api/
│   │   │   ├── routes.py                    # POST /chat (+ rate limit, visitor cookie, persistence)
│   │   │   └── auth_routes.py               # ★ POST /v1/auth/wp-login, GET /v1/auth/me, POST /v1/auth/logout
│   │   ├── auth/
│   │   │   ├── wp_verifier.py               # ★ Verify WP RS256 JWTs via cached JWKS
│   │   │   ├── session_jwt.py               # ★ Mint/decode our HS256 session JWTs
│   │   │   ├── dependencies.py              # ★ get_current_user, get_current_user_optional, require_role
│   │   │   └── visitor.py                   # Signed HTTP-only visitor_id cookie (HMAC-SHA256)
│   │   ├── core/
│   │   │   ├── agents_factory.py            # ★ Triage agent + 5 specialists + tools
│   │   │   └── orchestrator.py              # Thin Runner.run wrapper
│   │   ├── db/
│   │   │   ├── session.py                   # Async engine + sessionmaker (Neon pooler compat)
│   │   │   ├── models.py                    # SQLAlchemy 2.0: User, ChatMessage, Appointment, NoorAllocationRequest, UserActivity
│   │   │   └── repositories/
│   │   │       ├── chat_history.py          # insert_message, get_recent, merge_visitor_to_user
│   │   │       └── users.py                 # ★ upsert_from_wp_claims, get_by_id, update_last_seen
│   │   ├── middleware/
│   │   │   ├── error_handler.py             # Unified error envelope (never leaks internals)
│   │   │   ├── timeout.py                   # 15s hard cap on /chat (asyncio.wait_for)
│   │   │   └── rate_limiter.py              # Redis sliding-window (5 req/min/IP, fail-open)
│   │   ├── services/
│   │   │   ├── rag_service.py               # Qdrant query_points — real retrieval
│   │   │   ├── noor_catalog.py              # Deterministic Noor profile matcher
│   │   │   ├── persistence_writer.py        # Fire-and-forget persist_turn + log_activity
│   │   │   └── failure_handler.py           # Graceful degradation
│   │   ├── data/                            # heritage.md, products.json, noor_catalog.json
│   │   ├── config/
│   │   │   ├── settings.py                  # 30+ env vars (Phase 1 + Phase 2)
│   │   │   └── prompts.py                   # ★ Brand brain + OFF_TOPIC_RESPONSE + FALLBACK_MESSAGE
│   │   ├── utils/validators.py              # injection_guardrail + off_topic_guardrail
│   │   ├── models/
│   │   │   ├── schemas.py                   # ChatRequest/Response + WPLoginRequest, AuthResponse, UserPublic, Noor*, Admin*
│   │   │   └── errors.py                    # AuthFailure, RateLimited, CooldownActive, NoorPendingConflict, DatabaseUnavailable
│   │   └── scripts/wp_mock.py               # ★ Tiny WP JWKS mock for offline dev/testing
│   ├── scripts/
│   │   ├── load_rag.py                      # Embed + upsert to Qdrant
│   │   └── smoke_rag.py                     # 5-query sanity check
│   └── tests/
│       ├── unit/
│       │   ├── test_history_cap.py          # 7 tests — context capping
│       │   ├── test_visitor_cookie.py       # 6 tests — signed cookie issuance
│       │   ├── test_session_jwt.py          # 5 tests — HS256 mint/decode
│       │   ├── test_wp_verifier.py          # 5 tests — WP RS256 verification
│       │   └── test_auth_dependencies.py    # 8 tests — FastAPI auth deps
│       └── integration/
│           ├── test_api_endpoint.py          # 6 tests — /chat happy + error paths
│           ├── test_rate_limiter.py          # 4 tests — 429, fail-open, disabled
│           ├── test_timeout.py              # 2 tests — 408, health bypass
│           ├── test_chat_persistence.py     # 4 tests — persist_turn, log_activity
│           └── test_auth_routes.py          # 4 tests — wp-login, /me, logout
├── ui/                                       # Next.js chat (dark theme, gradient, typing dots)
├── CLAUDE.md                                # Project rules for Claude (read first!)
└── SUMMARY.md                               # ← this file
```

---

## 5. Prompt System (Critical)

### `backend/app/config/prompts.py` — Aueshah Concierge Intelligence **v2.0 Supreme Edition**

- 7-layer intelligence (client analysis → emotional intent → aesthetic mapping → recommendation → conversational behavior → subtle upsell → brand signature).
- **SCOPE & GRACEFUL REDIRECTION** section — soft acknowledgement → gentle bridge → warm invitation for off-topic messages that slip past the keyword guardrail.
- **PROFILING GATE** in product skill — must collect age + skin_tone + style_preference before calling `noor_recommend`.
- `OFF_TOPIC_RESPONSE` constant used by both the fast-path in `routes.py` and the `OffTopic` handler.

### 5 Specialist agents (in `agents_factory.py`)
- **product**: one piece (+ optional statement) via `search_catalog` tool.
- **compare**: A/B essences using `search_catalog`.
- **noor**: profile → `noor_recommend` tool (deterministic scoring in `noor_catalog.py`) → private concierge invite.
- **bespoke**: warm atelier handoff.
- **general**: heritage / appointments / warranty / policies / sizing; default fallback.

Triage agent has `input_guardrails=[injection_guardrail, off_topic_guardrail]`.

---

## 6. Current Runtime State

### ✅ PHASE 1 — FULLY OPERATIONAL & OPTIMIZED
- OpenAI Agents SDK deployed — triage agent with 5 specialist handoffs working perfectly.
- Qdrant collection `aueshah_knowledge` loaded with **108 points**.
- Off-topic guardrail returns 200 OK with warm redirect ✓
- Injection guardrail returns 400 ✓
- **Latency performance**: 1,958ms avg (well under 3s budget) ✓
- Token efficiency: **68% reduction** vs v1 (prompt optimization)

### ✅ PHASE 2 — GROUPS A, B, C COMPLETE (2026-04-16)

**Group A — Foundation Hardening** (complete, 13 tests):
- Redis sliding-window rate limiter (5 req/min/IP, fail-open on Redis down)
- 15s timeout middleware on /chat (asyncio.wait_for)
- Unified error envelope (ErrorHandlerMiddleware — never leaks internals)
- Context cap (hard 15-message limit via Pydantic validator + defense-in-depth)
- Neon DB session factory (async engine, Neon pooler `statement_cache_size=0`)
- Alembic migration: 5 tables with indexes, triggers, check constraints

**Group B — Chat Persistence** (complete, 10 tests):
- Signed visitor_id cookie (HMAC-SHA256, HTTP-only, 1-year TTL)
- Fire-and-forget `persist_turn()` + `log_activity()` (never blocks response)
- Chat history repository (insert, get_recent, merge_visitor_to_user)
- /chat route wired: rate limit → validate → visitor → orchestrate → persist → cookie

**Group C — WordPress Authentication** (complete, 22 tests):
- WP JWT verification via JWKS (RS256, cached by kid, 10-min TTL, stale fallback)
- Our HS256 session JWT (mint/decode, 24h expiry, 30s clock leeway)
- User repository (upsert_from_wp_claims, get_by_id, update_last_seen)
- FastAPI auth dependencies (get_current_user, get_current_user_optional, require_role)
- Auth routes: POST `/v1/auth/wp-login`, GET `/v1/auth/me`, POST `/v1/auth/logout`
- Anonymous→authenticated merge on login (UPDATE chat_messages SET user_id WHERE visitor_id)
- WP JWKS mock server for offline dev (`app/scripts/wp_mock.py`)

**Test Suite**: 45/45 passing (0 failures)

---

## 7. Architectural Decisions Made This Session

| Decision | Rationale |
|---|---|
| **OpenAI Agents SDK over custom orchestrator** | Native handoffs, guardrails, tools — replaces intent_classifier + prompt_builder + ai_client. Deletes ~1,000 LOC of scaffolding. |
| **Hybrid storage (not pure RAG, not pure JSON)** | Noor: deterministic profile scoring (metal_tone × style × age_tier × occasion) needs exact control — stays as JSON. Heritage + 60-piece catalog + narratives embed well — Qdrant. |
| **Off-topic → 200 OK, not 400** | UI renders as normal assistant message (no error bubble). `OffTopic` exception has `code=200`. |
| **RAG timeout 2.5s** | Trans-region TLS to Qdrant Cloud eu-west-1 from Pakistan needs more than 0.5s. Still inside 3s p95 budget. |

Worth formalizing as ADRs (`/sp.adr <title>`):
- ADR: Migration to OpenAI Agents SDK.
- ADR: Hybrid storage — structured Noor JSON + Qdrant RAG.
- ADR: Off-topic as warm 200 redirect via input guardrail.

---

## 8. .env Secrets (DO NOT COMMIT — verified in `.gitignore`)

`backend/.env` currently holds (real values, not placeholders):
```
OPENAI_API_KEY=sk-svcacct-...
OPENAI_MODEL=gpt-4.1
QDRANT_URL=https://871454ad-...eu-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGci...
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=2.5            # bumped from 0.5 for trans-region TLS
ROUTING_TIMEOUT_MS=200
LOG_LEVEL=INFO
EMBEDDING_MODEL=text-embedding-3-small
```

`ui/.env`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## 9. UI State (unchanged from v1)

Modern dark-theme chat UI: `_app.tsx` globals, gradient background, avatar bubbles (U / Au), 3-dot typing indicator, auto-growing textarea, mobile-responsive <640px, error message variant, empty-state hero with 4 suggestion chips.

---

## 10. What's Done vs Pending

### ✅ PHASE 1 COMPLETE + OPTIMIZED
- Constitution + spec / plan / tasks ✓
- OpenAI Agents SDK migration (triage + 5 specialists + guardrails + tools) ✓
- Aueshah v2.0 brand-brain prompt (optimized, 68% smaller) ✓
- Full catalog scrape (60 non-Noor + 5 Noor pieces + heritage) ✓
- Qdrant RAG (108 points indexed, all verified) ✓
- Real `rag_service.retrieve()` via `query_points` ✓
- Two-layer off-topic defense (regex guardrail + prompt SCOPE) ✓
- **Profiling flow verified** (age → tone → style) ✓
- **Live chat testing** (greeting, FAQs, Noor, off-topic all working) ✓
- **Professional audit** (14/14 tests passing) ✓
- **Latency optimized** (1,958ms avg < 3,000ms budget) ✓
- UI polished ✓
- `.env` properly gitignored ✓

### ⏳ Phase 2 — Remaining Groups (D through G)

**Group D (T160-T169) — Personalization** (next up, depends on B+C):
- Returning-user context injection (last intent, recent history summary)
- Profile-aware prompt enrichment (age_range, skin_tone, style_preference)
- User preferences update endpoint

**Group E (T170-T185) — Noor Allocation Workflow** (depends on C for auth):
- POST `/v1/noor-requests` — submit allocation request (auth required)
- 90-day cooldown enforcement, pending-request conflict check
- Admin endpoints: GET list, PATCH approve/decline
- NOR-XXXXXXXX reference ID generation

**Group F (T190-T197) — Appointments + Notifications**:
- Persist appointments to DB (currently in-memory only)
- SendGrid email notifications (new request → concierge team)
- Slack webhook notifications (Noor + appointment channels)

**Group G (T200-T211) — Test & Harden**:
- End-to-end auth flow tests with real DB
- Performance regression tests (p95 ≤ 3s with persistence overhead)
- Security audit (no key leaks, no SQL injection, no XSS in responses)
- Production deployment readiness (Docker Compose, health checks, graceful shutdown)

---

## 11. PHR / ADR Discipline

Per `CLAUDE.md`:
- Every user prompt → create a **PHR** under `history/prompts/<route>/`.
- Routes: `constitution/`, `001-concierge-chat-api/`, `general/`.
- Significant architecture decisions → **suggest** (never auto-create) an ADR via `/sp.adr <title>`.

---

## 12. Where We Left Off & How to Continue

### Last completed: Group C — WordPress Authentication (T140-T152)
- All 13 Group C tasks done. 45/45 tests passing.
- Auth routes wired into `main.py`. WP mock server ready for offline dev.

### Resume from: Group D — Personalization (T160-T169)
This is the next group to implement. It requires:
1. A returning-user detection flow (check if session JWT present → load user profile + recent history)
2. Context injection into the prompt builder (last intent, profile fields)
3. A PATCH `/v1/users/me/preferences` endpoint for updating profile fields (age_range, skin_tone, style_preference, etc.)

Group D depends on Groups B (chat history) and C (auth) — both complete.

After D, proceed to Group E (Noor Allocation), then F (Appointments + Notifications), then G (Test & Harden).

See `specs/001-concierge-chat-api/tasks.md` for the full 78-task breakdown (T100-T211).

---

## 13. Quick Orientation Checklist for New Claude Session

Before any work:
1. Read `CLAUDE.md` (operational rules).
2. Read `.specify/memory/constitution.md` (12 principles).
3. Read this file (`SUMMARY.md`).
4. Scan `backend/app/core/agents_factory.py` — that's the whole runtime.
5. Scan `backend/app/config/prompts.py` — that's the brand brain.
6. Scan `backend/app/auth/` — the full auth stack (wp_verifier, session_jwt, dependencies, visitor).
7. Check `git status` and current branch before editing.

**Non-negotiables**:
- Factual detail lives in Qdrant (`aueshah_knowledge`) and JSON files under `app/data/` — **never** the system prompt (except brand voice).
- Never hallucinate pieces, prices, stock, materials. Always prefer uncertainty.
- API keys never leave server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- Re-run `python -m scripts.load_rag` whenever `heritage.md` / `products.json` / `noor_catalog.json` changes.
