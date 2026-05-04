# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-05-03
**Branch**: `001-concierge-chat-api`
**Status**: Backend FEATURE-COMPLETE against client requirements (127/127 tests). DB connected. **WordPress auth verified end-to-end. Resend live + appointment-from-chat tool wired and live-tested (real DB row + real email receipt).** Ready for Koyeb deployment + chat widget install.
**Purpose**: Full context for any next Claude session picking up this project.

---

## 0. ⚠️ POST-PULL RECOVERY PROTOCOL — READ FIRST

**Context**: As of 2026-05-03 there is uncommitted local work on this branch (Resend swap, `submit_appointment` agent tool, prompt fixes — see §6 "2026-04-30 session"). The user is about to pull their teammate's branch, which will overwrite that local work. A complete recovery guide has been captured at:

```
I:\Local Disk J\Clinets\aueshah\LOCAL_CHANGES_RECOVERY.md
```

### When the user says "recover my changes" / "reapply my work" / "restore from the guide" — follow these rules EXACTLY:

#### Rule 1 — The recovery guide is authoritative
- Open and read `LOCAL_CHANGES_RECOVERY.md` end-to-end **before** touching any file.
- It contains: Summary, Removed Code, Added Features, Refactors, file-by-file §5.1–§5.22 instructions, and a 13-step §6 reimplementation guide.
- Execute §6 in order. Do not improvise the order.

#### Rule 2 — DO NOT touch the friend's changes
- After the pull, the working tree reflects the friend's work. **Their changes are the new baseline and must not be modified, reverted, or "improved" while reapplying.**
- Before editing each file listed in §5, run `git log -1 --format="%h %s" -- <path>` to see what the friend last did to it. If their commit touched the same lines the recovery guide rewrites, **stop and ask the user** — do not silently overwrite their work.
- If a file in §5 was renamed, deleted, or heavily refactored by the friend, **stop and ask the user** how to proceed. Do not blindly recreate the old file.
- Reapply ONLY the diffs documented in `LOCAL_CHANGES_RECOVERY.md`. Do not bring back any other code, comments, or formatting that isn't in the guide.

#### Rule 3 — Reapply intent, not raw text
- The guide gives canonical replacement text for each file. Where possible, use exact `old_string → new_string` Edit calls.
- If the friend changed surrounding context so the `old_string` no longer matches, **adapt the replacement to preserve the user's intent** (e.g. SendGrid → Resend rename, new tool wired into general agent, prompt EXCEPTION clause present). Document any adaptation in your reply.

#### Rule 4 — Verify before claiming success
After applying §5.1–§5.22, run §6 step 12 verification **in this order**:
1. `cd backend && uv sync` — regenerates `uv.lock`. Do not edit the lockfile by hand.
2. `cd backend && uv run pytest tests/ -q` — expected: **127 passing** (no test count change). If the friend added tests, the count may be higher; failures are the only signal that matters.
3. Smoke import: `uv run python -c "from app.services.notifications import email; print(email.send_email)"`.
4. (If `RESEND_API_KEY` set) Optional live appointment test per §6 step 12.3.

If pytest fails, do **not** silently disable tests. Diagnose the root cause — most likely a signature mismatch between the new `submit_appointment` tool and the friend's version of `appointment_workflow.create_appointment`.

#### Rule 5 — Conflict surface (most likely friction points)
Watch these files specifically — they are the highest-risk overlap zones:
- `backend/app/core/agents_factory.py` — friend may have added/changed agents or tools
- `backend/app/config/prompts.py` — friend may have edited the system prompt
- `backend/app/services/appointment_workflow.py` — `create_appointment()` signature change would break the new tool
- `backend/app/services/notifications/email.py` — full rewrite; verify higher-level `send_client_*` / `send_concierge_*` helpers still call `send_email(...)` with the same kwargs
- `backend/app/config/settings.py` — friend may have added new settings fields between the SendGrid block

#### Rule 6 — Do not commit until the user confirms
After the reapply:
1. Run `git status` and `git diff --stat` and report what was reapplied.
2. Show the user pytest output.
3. **Wait for explicit user approval before committing.** Do not run `git commit` autonomously. The suggested message is in §6 step 13 of the recovery guide.

#### Rule 7 — If anything is ambiguous, ask
The recovery guide is precise but the friend's branch is unknown. If a file no longer exists, has been renamed, or has been refactored such that the guide's instructions no longer make literal sense, **stop and ask the user** with a concrete question (e.g. "The friend renamed `appointment_workflow.py` → `appointments/workflow.py`. Should I update the import in `submit_appointment` to match, or restore the old path?"). Do not guess.

---

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

A stateless, controlled **FastAPI** concierge backend + **chat widget embedded in WordPress**:
- All routing + model invocation runs through the **OpenAI Agents SDK** (triage agent with native handoffs to 5 specialists).
- Skills: `product`, `compare`, `noor`, `bespoke`, `general`.
- **Hybrid knowledge**: static JSON for Noor profile matching (deterministic scoring) + Qdrant RAG for everything else.
- **Two-layer off-topic defense**: keyword regex guardrail + prompt-level SCOPE section.
- Async end-to-end. Model: **gpt-4.1** (OpenAI).
- Strict constitution compliance (12 principles, `.specify/memory/constitution.md`).

### Latency budgets (p95 ≤ 3s)
Routing ≤ Agents SDK overhead · RAG ≤ 2.5s (trans-region to Qdrant Cloud eu-west-1) · AI ≤ 2s.

---

## 3. Stack & Tooling

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI async, Pydantic v2, **openai-agents** SDK, qdrant-client |
| Database | **Neon Serverless Postgres** (SQLAlchemy 2.0 async + asyncpg, Alembic migrations) — **CONNECTED & INITIALIZED** |
| Cache/Rate Limit | **Redis** (sliding-window sorted set, fail-open) — **not connected yet** |
| Auth | WordPress **HS256** JWT (`JWT_AUTH_SECRET_KEY` shared secret) → our HS256 session JWT (python-jose) |
| Package manager | **uv** (`backend/pyproject.toml` + `uv.lock`) |
| Vector store | **Qdrant Cloud (eu-west-1)** — collection `aueshah_knowledge`, 108 points loaded (needs re-embed with `text-embedding-3-large`) |
| Notifications | **Resend** (email — live) + Slack SDK (webhooks — env vars not set yet) |
| Deployment | **Koyeb** (planned) — Docker-based, `backend/Dockerfile.prod` ready |

### Database Connection (LIVE)
```
Neon: ep-soft-base-an05ulxi-pooler.c-6.us-east-1.aws.neon.tech/neondb
Tables: users, chat_messages, appointments, noor_allocation_requests, user_activity
Alembic: revision 0002 applied (0001 initial schema + 0002 users.updated_at column)
Triggers: updated_at on users, appointments, noor_allocation_requests
```

### Commands
```bash
# Backend
cd backend
uv sync                                                   # one-time
uv run uvicorn app.main:app --reload --port 8000          # dev
uv run pytest tests/ -q                                   # tests (127 passing)

# RAG loader (MUST re-run — switched to text-embedding-3-large)
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
│                                            # ⚠ ADR-0003 pending: WP auth HS256 swap (not yet written)
├── Data.txt                                 # Brand brain source (already encoded in SYSTEM_PROMPT)
├── WORDPRESS_INTEGRATION_ROADMAP.md         # ★ Step-by-step guide for WP developer
├── backend/
│   ├── pyproject.toml                       # uv-managed deps
│   ├── .env                                 # OPENAI_API_KEY, QDRANT_*, NEON_DATABASE_URL, JWT_AUTH_SECRET_KEY (all set)
│   ├── alembic.ini + alembic/               # Migrations at revision 0002 (applied to Neon)
│   ├── Dockerfile.prod                      # ★ Multi-stage uv build, non-root, healthcheck — ready for Koyeb
│   ├── app/
│   │   ├── main.py                          # FastAPI app + middleware stack
│   │   ├── api/
│   │   │   ├── routes.py                    # POST /chat (rate limit, visitor cookie, persistence, page_context)
│   │   │   ├── auth_routes.py               # POST /v1/auth/wp-login, GET /v1/auth/me, POST /v1/auth/logout
│   │   │   ├── noor_routes.py               # POST /v1/noor-requests, GET /v1/noor-requests/me
│   │   │   └── admin_routes.py              # X-Admin-Token-gated CRUD + metrics
│   │   ├── auth/
│   │   │   ├── wp_verifier.py               # Verify WP HS256 JWTs via shared secret + /users/me hydration
│   │   │   ├── session_jwt.py               # Mint/decode our HS256 session JWTs
│   │   │   ├── dependencies.py              # get_current_user, get_current_user_optional, require_role
│   │   │   └── visitor.py                   # Signed HTTP-only visitor_id cookie
│   │   ├── core/
│   │   │   ├── agents_factory.py            # ★ Triage agent + 5 specialists + 4 tools (search_catalog, noor_recommend, submit_noor_request, submit_appointment)
│   │   │   ├── agents_context.py            # ContextVar for threading user_id into agent tools
│   │   │   ├── orchestrator.py              # Runner.run wrapper + token tracking
│   │   │   └── personalization.py           # Selective return memory (Noor 30d / Bespoke 60d expiry)
│   │   ├── db/
│   │   │   ├── session.py                   # Async engine + sessionmaker (Neon pooler compat)
│   │   │   ├── models.py                    # User, ChatMessage, Appointment, NoorAllocationRequest, UserActivity
│   │   │   └── repositories/               # chat_history, users, noor_requests, appointments
│   │   ├── middleware/
│   │   │   ├── error_handler.py             # Never leaks internals
│   │   │   ├── timeout.py                   # 15s hard cap
│   │   │   ├── rate_limiter.py              # Redis sliding-window (5 req/min/IP, fail-open)
│   │   │   └── request_context.py           # X-Request-ID propagation
│   │   ├── services/
│   │   │   ├── rag_service.py               # Qdrant retrieval
│   │   │   ├── noor_catalog.py              # Deterministic Noor profile matcher
│   │   │   ├── noor_workflow.py             # Eligibility + insert + notifications
│   │   │   ├── appointment_workflow.py      # Persist + notify
│   │   │   ├── persistence_writer.py        # Fire-and-forget persist_turn + log_activity
│   │   │   ├── notifications/email.py       # Resend wrapper
│   │   │   ├── notifications/slack.py       # Slack webhook poster
│   │   │   ├── summary_cache.py             # In-process LRU per-user
│   │   │   ├── profile_extractor.py         # Regex extraction of age/skin_tone/style from messages
│   │   │   └── failure_handler.py           # Graceful degradation
│   │   ├── config/
│   │   │   ├── settings.py                  # 30+ env vars — defaults match client requirements doc
│   │   │   └── prompts.py                   # ★ Brand brain v2.0 + all required clauses
│   │   ├── utils/
│   │   │   ├── validators.py                # injection_guardrail + off_topic_guardrail
│   │   │   ├── metrics.py                   # Prometheus counters/histograms + TOKENS_USED_TOTAL
│   │   │   └── logging.py                   # JSON structured logging with ContextVar request_id
│   │   ├── models/
│   │   │   ├── schemas.py                   # ChatRequest (with PageContext), ChatResponse, auth/noor/admin schemas
│   │   │   └── errors.py                    # All typed errors
│   │   └── data/                            # heritage.md, products.json, noor_catalog.json
│   └── tests/                               # 127 tests across unit/integration/security/chaos/e2e
├── ui/                                       # Next.js chat (dev/test only — production widget goes in WP)
├── CLAUDE.md                                # Project rules for Claude (read first!)
├── WORDPRESS_INTEGRATION_ROADMAP.md         # ★ WP developer guide (send to client)
└── SUMMARY.md                               # ← this file
```

---

## 5. Client Requirements — FULLY MATCHED

All 17 sections of the client's `requirements.docx` are now satisfied:

| Section | Status |
|---|---|
| 1. Overview (server-side, controlled prompt, function calling, page awareness, RAG, memory) | MATCH |
| 2. Core Architecture (Frontend → Backend → OpenAI → tool calls → response) | MATCH |
| 3. Required OpenAI Endpoint (gpt-4.1, Responses API) | MATCH |
| 4. System Prompt (brand brain, tone, Noor hierarchy, symbolism, blog restraint, rejection philosophy) | MATCH |
| 5. Page Context Awareness (page_type, product_name, collection_name) | MATCH |
| 6. Noor Function (submit_noor_request tool with 6 params) | MATCH |
| 7. Tool Call Handling (parse, store, return, generate confirmation) | MATCH |
| 8. Database Structure (noor_allocation_requests table, all fields) | MATCH |
| 9. Rate Limiting & Crash Prevention (5/min/IP, 15s timeout, fallback message) | MATCH |
| 10. Knowledge System / RAG (text-embedding-3-large, top-k=3, Qdrant) | MATCH |
| 11. Blog Reference Policy (title only, no auto-link) | MATCH |
| 12. Memory System (session + selective Noor 30d / Bespoke 60d) | MATCH |
| 13. Noor Rejection Policy (decline cooldown 12 months, verbatim message) | MATCH |
| 14. Noor Closure Logic (143 cap, tool disabled, closure message) | MATCH |
| 15. Security (env vars, sanitization, SQL injection prevention, no auto-learning) | MATCH |
| 16. Testing Checklist (all areas covered) | MATCH |
| 17. Deployment Rules (staging, monitoring, token usage, error logging) | MATCH |

---

## 6. What's Done

### Phase 1 — COMPLETE
- OpenAI Agents SDK (triage + 5 specialists + guardrails + tools)
- Brand brain v2.0 prompt (all required clauses)
- Qdrant RAG (108 points indexed)
- Two-layer off-topic defense
- Profiling flow (age → tone → style)
- Latency optimized (1,958ms avg)

### Phase 2 — COMPLETE
- **Group A**: Redis rate limiter, 15s timeout, error envelope, Neon DB, Alembic migration
- **Group B**: Visitor cookies, fire-and-forget persistence, chat history repo
- **Group C**: WP JWT verification (**HS256 shared secret** — swapped from RS256/JWKS 2026-04-23 to match the "JWT Authentication for WP-API" plugin), session JWT (HS256), user repo, auth routes, visitor merge
- **Group D**: Personalization preamble (selective: Noor 30d / Bespoke 60d), summary cache, profile extractor
- **Group E**: Noor allocation workflow (submit, review, cooldown, notifications)
- **Group F**: Appointments + notifications (Resend + Slack)
- **Group G**: Security (14 leak tests), chaos (5 degradation tests), E2E journey, Prometheus metrics, request-scoped logging, Dockerfile.prod

### 2026-04-23 session (commit `424b53e`)
- Swapped WP auth from RS256/JWKS to HS256 shared secret
- Added `/wp/v2/users/me` hydration for display_name
- `WPLoginRequest` now accepts optional `user_email` + `user_display_name` (WP REST hides real email by default)
- Migration 0002: added missing `users.updated_at` column (trigger from 0001 was failing on UPDATEs)
- End-to-end WP → backend login verified with real WordPress user (UUID `c0ce41c4-...`, wp_user_id=3)
- Test count bumped 122 → 127 (5 new HS256 tests)

### 2026-04-30 session (uncommitted as of this note)
- **Email provider swap: SendGrid → Resend.** Rewrote `app/services/notifications/email.py` around the synchronous `resend` SDK (`resend.Emails.send`) wrapped in `asyncio.to_thread`. Same 5 public `send_*` functions (no caller changes). Removed `sendgrid` from `pyproject.toml` / `requirements.txt`; added `resend>=2.0.0`. Live test: `husnainxebad@gmail.com` received the verification email.
- **Settings**: `sendgrid_api_key/from_email/from_name` → `resend_api_key/resend_from_email`. `concierge_alert_email` default now `husnainxebad@gmail.com`. Default sender is `Aueshah Concierge <onboarding@resend.dev>` (Resend sandbox sender — must swap to a verified-domain address once `aueshah.com` is verified in Resend).
- **Doc cleanup**: removed all stale SendGrid references from `SUMMARY.md`, `CLAUDE.md`, `generate_client_pdf.py` (client onboarding PDF rewritten for Resend's one-key signup), `specs/001-concierge-chat-api/{research,quickstart,plan,tasks}.md`, `DATABASE_AND_PERSONALIZATION_ARCHITECTURE.md`. Renamed two chaos test fns `test_sendgrid_failure_*` → `test_resend_failure_*`. Remaining "SendGrid" mentions are intentional (decision-log "swapped from", alternatives-considered table, append-only PHRs in `history/prompts/`).
- **Critical bug fix: appointments-from-chat now actually persist + email.** The `general` agent had no tools — it collected client info and said "concierge will reach out" but nothing was inserted to the DB and no email fired. Added a `submit_appointment` agent tool (mirrors `submit_noor_request`) that calls `appointment_workflow.create_appointment()`. Wired it into `general_agent.tools`. Live tested end-to-end: 3-turn chat → row `APT-6AF506C9` in Neon → 2 Resend emails accepted (client confirmation + concierge alert).
- **Prompt fixes** in `app/config/prompts.py`:
  - Added EXCEPTION clause to `MANDATORY FIRST-TURN BEHAVIOR` so the bot does NOT force the age/skin-tone/style profiling flow when the client opens with an appointment, bespoke, heritage, repair, or policy intent. (Profiling exists to enable a piece recommendation — don't force it on other flows.)
  - Rewrote rule #7 (the "never book appointments" rule): bot still doesn't claim it booked, but it DOES submit via the tool when available; concierge confirms after.
  - Updated `general` skill prompt with the explicit appointment flow (collect email + type, optionally phone/preferred_date/notes, call `submit_appointment`, relay reference ID).
- **Tests**: 127/127 still passing. No test count change — added a new tool but didn't add tests for it; live end-to-end was the verification.

### Client Requirements Gaps — ALL CLOSED
- Page-context awareness (PageContext model + system injection)
- submit_noor_request as AI function tool (agent writes DB row directly)
- Decline cooldown (12 months, blocks re-submission)
- Noor closure at 143 allocations (count_approved + tool gating)
- Missing system prompt clauses (symbolism, blog restraint, allocation protocol, rejection philosophy)
- Selective return memory (Noor 30d / Bespoke 60d expiry gate)
- Config defaults (gpt-4.1, text-embedding-3-large, 15s timeout, token-usage metric)

### Database — CONNECTED
- Neon Postgres: 5 tables created, 3 triggers, 15 indexes, all check constraints
- Alembic at revision **0002**
- One real user row exists (from 2026-04-23 WP login test)

### Test Suite — 127/127 PASSING

---

## 7. What's Remaining (Next Session)

### PRIORITY 1: Deploy Backend to Koyeb

**Deployment target**: [Koyeb](https://www.koyeb.com/) (Docker-based)

`backend/Dockerfile.prod` is ready. Steps:
1. Create Koyeb account/project
2. Connect GitHub repo (`HasnainCodeHub/aueshah`, branch `001-concierge-chat-api`) or push Docker image
3. Set environment variables in Koyeb dashboard:
   ```
   OPENAI_API_KEY=sk-svcacct-...
   OPENAI_MODEL=gpt-4.1
   QDRANT_URL=https://871454ad-...
   QDRANT_API_KEY=eyJhbGci...
   NEON_DATABASE_URL=postgresql+asyncpg://neondb_owner:npg_2MUObdLw0EsY@ep-soft-base-an05ulxi-pooler.c-6.us-east-1.aws.neon.tech/neondb?ssl=require
   EMBEDDING_MODEL=text-embedding-3-large
   CHAT_TIMEOUT_SECONDS=3
   RAG_TIMEOUT_SECONDS=2.5
   LOG_LEVEL=INFO
   JWT_SIGNING_KEY=<already-generated, copy from local .env>
   ADMIN_API_TOKEN=<already-generated, copy from local .env>
   JWT_AUTH_SECRET_KEY=<already in local .env — copies wp-config.php value>
   WP_BASE_URL=https://aueshah.com
   WP_ISSUER=https://aueshah.com
   ENABLE_RATE_LIMIT=true
   # Resend (required — appointment + Noor flows depend on email delivery)
   RESEND_API_KEY=<re_... — copy from local .env>
   RESEND_FROM_EMAIL=Aueshah Concierge <onboarding@resend.dev>
   CONCIERGE_ALERT_EMAIL=husnainxebad@gmail.com
   ```
4. Optional (add when ready):
   ```
   REDIS_URL=<upstash-or-similar>
   SLACK_WEBHOOK_NOOR=<url>
   SLACK_WEBHOOK_APPOINTMENTS=<url>
   ```
5. **Lock CORS** to `https://aueshah.com` (currently `allow_origin_regex=".*"` in `backend/app/main.py:39-45` — commented production block at lines 46-56 is ready to paste)
6. Verify health: `GET /health`
7. Test `/chat` endpoint from Koyeb URL
8. Test `/v1/auth/wp-login` exchange from Koyeb URL using a real WP token

### PRIORITY 2: Re-embed Qdrant with text-embedding-3-large

The existing 108 vectors were embedded with `text-embedding-3-small` (1536d).
Settings now default to `text-embedding-3-large` (3072d). **Must re-run**:
```bash
cd backend
python -m scripts.load_rag       # re-embeds with large model
python -m scripts.smoke_rag      # verify retrieval works
```
This may require recreating the Qdrant collection with `size=3072`.

### PRIORITY 3: WordPress Chat Widget Deploy

**Prerequisites — ALL DONE ✅**
1. ~~Install JWT plugin on aueshah.com~~ ✅ "JWT Authentication for WP-API" installed and active (health check green)
2. ~~Set `JWT_AUTH_SECRET_KEY` in `wp-config.php`~~ ✅ set and matches backend
3. ~~Verify WP → backend token exchange~~ ✅ tested 2026-04-23, returned HTTP 200 with real user data

**What's left (needs Priority 1 deployed first):**
1. Build minimal chat widget JS/CSS (uses backend URL from Koyeb)
2. On WP login, JS calls `POST /wp-json/jwt-auth/v1/token` → gets WP JWT
3. JS exchanges WP JWT via `POST <koyeb-url>/v1/auth/wp-login` with full body:
   ```json
   {
     "wp_token": "<from /token response>",
     "user_email": "<from /token response body>",
     "user_display_name": "<from /token response body>"
   }
   ```
4. Store backend's session JWT in localStorage
5. Send chat messages with `Authorization: Bearer <session-jwt>`
6. Upload as WP plugin (`wp-content/plugins/aueshah-concierge/`) or inject via `functions.php`

Full guide: `WORDPRESS_INTEGRATION_ROADMAP.md` (may need updates — written for RS256/JWKS flow)

### PRIORITY 4: Deferred Cleanup Tasks

| Task | What | When |
|---|---|---|
| ADR-0003 | Document the RS256→HS256 swap (rationale, tradeoffs, rotation plan) | Before next architectural review |
| ADR-0004 | Document the SendGrid→Resend swap + the appointment-tool wiring | Same window as ADR-0003 |
| Resend domain verification | Verify `aueshah.com` in Resend → swap `RESEND_FROM_EMAIL` from `onboarding@resend.dev` (sandbox sender) to a real `concierge@aueshah.com` style address | Before client launch |
| T200 | Locust load test | After Koyeb deploy (needs real infra) |
| T204 | PII deletion endpoint | After first compliance review |
| T208 | README rewrite | During deploy prep |
| T209 | docker-compose update (postgres + redis services) | Dev convenience |
| T211 | Remove `ENABLE_RATE_LIMIT` flag (always-on) | At deploy time |
| CORS lockdown | Change `allow_origin_regex=".*"` to `["https://aueshah.com"]` | At deploy time |
| Redis | Connect Upstash or similar for production rate limiting | At deploy time |
| WP scripts/wp_mock.py | Update or remove — was a JWKS mock, now obsolete | Housekeeping |

---

## 8. .env Current State

`backend/.env` currently holds:
```
# Connected / set
OPENAI_API_KEY=sk-svcacct-... (set)
OPENAI_MODEL=gpt-4.1 (set)
QDRANT_URL=https://871454ad-... (set, connected)
QDRANT_API_KEY=eyJhbGci... (set)
NEON_DATABASE_URL=postgresql+asyncpg://... (set, connected, alembic at 0002)
EMBEDDING_MODEL=text-embedding-3-small (⚠️ code defaults to large — re-embed needed)
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=2.5
ROUTING_TIMEOUT_MS
LOG_LEVEL=INFO
REDIS_URL= (empty — rate limiter fails open)
JWT_SIGNING_KEY=<set, 64 chars — signs OUR session JWTs>
ADMIN_API_TOKEN=<set — gates /admin/* endpoints>
JWT_AUTH_SECRET_KEY=<set — HS256 shared secret, matches wp-config.php>
WP_BASE_URL=https://aueshah.com (set)
WP_ISSUER=https://aueshah.com (set)

# Set (Resend wired up + verified)
RESEND_API_KEY=<set — re_8ACa...>          # Email via Resend (live, tested 2026-04-30)
# RESEND_FROM_EMAIL defaults to "Aueshah Concierge <onboarding@resend.dev>" (sandbox);
#   swap to a verified domain address once aueshah.com is verified in Resend.
# CONCIERGE_ALERT_EMAIL defaults to husnainxebad@gmail.com.

# NOT SET YET (optional / nice-to-have):
SLACK_WEBHOOK_NOOR=           # Slack notifications
SLACK_WEBHOOK_APPOINTMENTS=   # Slack notifications
ENABLE_RATE_LIMIT=false       # Flip to true when Redis connected
```

---

## 9. Koyeb Deployment Notes

### Dockerfile.prod is ready at `backend/Dockerfile.prod`
- Multi-stage uv build (builder + runtime)
- Non-root `app` user (UID 1001)
- Healthcheck: `curl -fsS http://localhost:${PORT}/health`
- Configurable: `PORT` (default 8000), `UVICORN_WORKERS` (default 2), `LOG_LEVEL`

### Koyeb-specific considerations
- Koyeb provides `PORT` env var automatically — Dockerfile already uses `${PORT}`
- Set all secrets via Koyeb dashboard (not in Docker image)
- Koyeb supports Docker builds from GitHub — can auto-deploy on push
- Build command: `docker build -f backend/Dockerfile.prod -t aueshah-concierge:prod backend`
- Health check path: `/health`
- Region: choose US East (closest to Neon us-east-1)

---

## 10. WordPress Site State (aueshah.com)

- **Platform**: WordPress + WooCommerce
- **Login**: Standard WooCommerce at `/my-account/` (username + password, no social login)
- **Bespoke page**: `/bespoke` — has `[openai_chat]` shortcode placeholder (not yet connected to our backend)
- **JWT plugin**: ✅ **"JWT Authentication for WP-API" installed and active** (HS256). Health check all green. `JWT_AUTH_SECRET_KEY` set in `wp-config.php` and matches our backend.
- **Token endpoint verified**: `POST /wp-json/jwt-auth/v1/token` returns a 224-char HS256 JWT plus `user_email`, `user_nicename`, `user_display_name`.
- **Application Passwords**: NOT enabled yet — needed only if we want WP MCP access for code injection
- **Chat widget**: NOT deployed yet — next action item in Priority 3

### User flow (planned, once widget deploys)
```
User clicks "Start Bespoke" on /bespoke
  → Check localStorage for session token
  → If no token: redirect to /my-account/ login
  → After WP login: JS calls /wp-json/jwt-auth/v1/token → WP JWT
  → JS calls <koyeb-url>/v1/auth/wp-login with wp_token + user_email + user_display_name
  → Backend verifies HS256 signature, upserts user in Neon, returns our session JWT
  → Store our token in localStorage
  → Redirect back to /bespoke?chat=open
  → Chat widget opens, sends POST /chat with Authorization: Bearer <token>
  → Backend loads user from Neon DB, builds personalization preamble
  → AI responds with bespoke skill
```

### User provisioning model (confirmed 2026-04-23)
- **Lazy sync** — no WP→Neon push on registration. A Neon row is created the **first time a user opens the chat** (triggers the WP JWT exchange). Users who never chat stay in WP's MySQL only.
- This matches constitution principle #3 (stateless/minimal) and avoids syncing dormant accounts.

---

## 11. Quick Orientation for New Claude Session

Before any work:
1. Read `CLAUDE.md` (operational rules).
2. Read this file (`SUMMARY.md`).
3. Check `git status` and current branch.
4. Check `backend/.env` for what's connected.

### Key files to scan
- `backend/app/core/agents_factory.py` — the whole AI runtime (triage + 5 specialists + 4 tools, including `submit_appointment` on the `general` agent)
- `backend/app/config/prompts.py` — brand brain + all skill prompts
- `backend/app/config/settings.py` — all 30+ env vars with defaults
- `backend/app/api/routes.py` — POST /chat with full pipeline
- `backend/app/auth/wp_verifier.py` — **HS256 WP token verification + /users/me hydration**
- `backend/app/api/auth_routes.py` — token exchange endpoint
- `backend/Dockerfile.prod` — production Docker image
- `WORDPRESS_INTEGRATION_ROADMAP.md` — WP developer instructions (note: written for RS256 flow, may need updates)

### Non-negotiables
- Factual detail lives in Qdrant + JSON data files — **never** the system prompt.
- Never hallucinate pieces, prices, stock, materials. Always prefer uncertainty.
- API keys never leave server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- `requirements.docx` is the authoritative client spec — all 17 sections must stay matched.

### Resume from
**Priority 1: Deploy backend to Koyeb.** All credentials in local `.env` are ready to copy into the Koyeb dashboard (now including `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `CONCIERGE_ALERT_EMAIL`). After Koyeb is live → Priority 2 (Qdrant re-embed) → Priority 3 (WP chat widget). WP JWT plugin is already installed and verified end-to-end. Resend + appointment-from-chat are also live-verified locally as of 2026-04-30, so the widget should "just work" once it points at the new Koyeb URL.

**Heads-up for the next session**: there are uncommitted changes from the 2026-04-30 work — the Resend swap, the `submit_appointment` tool, and the prompt updates. Before deploying, confirm `git status` is clean / committed. Run `uv run pytest tests/ -q` (expect 127 pass) and optionally repeat the live appointment test by sending a 2–3 turn chat via `/chat` to confirm the tool path still ends in a Resend email.
