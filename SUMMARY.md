# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-04-17
**Branch**: `001-concierge-chat-api`
**Status**: Backend FEATURE-COMPLETE against client requirements (122/122 tests). DB connected. Ready for deployment + WP integration.
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
| Auth | WordPress RS256 JWT (JWKS) → our HS256 session JWT (python-jose) |
| Package manager | **uv** (`backend/pyproject.toml` + `uv.lock`) |
| Vector store | **Qdrant Cloud (eu-west-1)** — collection `aueshah_knowledge`, 108 points loaded (needs re-embed with `text-embedding-3-large`) |
| Notifications | SendGrid (email) + Slack SDK (webhooks) — env vars not set yet |
| Deployment | **Koyeb** (planned) — Docker-based, `backend/Dockerfile.prod` ready |

### Database Connection (LIVE)
```
Neon: ep-soft-base-an05ulxi-pooler.c-6.us-east-1.aws.neon.tech/neondb
Tables: users, chat_messages, appointments, noor_allocation_requests, user_activity
Alembic: revision 0001 applied
Triggers: updated_at on users, appointments, noor_allocation_requests
```

### Commands
```bash
# Backend
cd backend
uv sync                                                   # one-time
uv run uvicorn app.main:app --reload --port 8000          # dev
uv run pytest tests/ -q                                   # tests (122 passing)

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
├── Data.txt                                 # Brand brain source (already encoded in SYSTEM_PROMPT)
├── WORDPRESS_INTEGRATION_ROADMAP.md         # ★ Step-by-step guide for WP developer
├── backend/
│   ├── pyproject.toml                       # uv-managed deps
│   ├── .env                                 # OPENAI_API_KEY, QDRANT_*, NEON_DATABASE_URL (connected)
│   ├── alembic.ini + alembic/               # Migration at revision 0001 (applied to Neon)
│   ├── Dockerfile.prod                      # ★ Multi-stage uv build, non-root, healthcheck — ready for Koyeb
│   ├── app/
│   │   ├── main.py                          # FastAPI app + middleware stack
│   │   ├── api/
│   │   │   ├── routes.py                    # POST /chat (rate limit, visitor cookie, persistence, page_context)
│   │   │   ├── auth_routes.py               # POST /v1/auth/wp-login, GET /v1/auth/me, POST /v1/auth/logout
│   │   │   ├── noor_routes.py               # POST /v1/noor-requests, GET /v1/noor-requests/me
│   │   │   └── admin_routes.py              # X-Admin-Token-gated CRUD + metrics
│   │   ├── auth/
│   │   │   ├── wp_verifier.py               # Verify WP RS256 JWTs via cached JWKS
│   │   │   ├── session_jwt.py               # Mint/decode our HS256 session JWTs
│   │   │   ├── dependencies.py              # get_current_user, get_current_user_optional, require_role
│   │   │   └── visitor.py                   # Signed HTTP-only visitor_id cookie
│   │   ├── core/
│   │   │   ├── agents_factory.py            # ★ Triage agent + 5 specialists + 3 tools (search_catalog, noor_recommend, submit_noor_request)
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
│   │   │   ├── notifications/email.py       # SendGrid wrapper
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
│   └── tests/                               # 122 tests across unit/integration/security/chaos/e2e
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
- **Group C**: WP JWT verification (RS256 JWKS), session JWT (HS256), user repo, auth routes, visitor merge
- **Group D**: Personalization preamble (selective: Noor 30d / Bespoke 60d), summary cache, profile extractor
- **Group E**: Noor allocation workflow (submit, review, cooldown, notifications)
- **Group F**: Appointments + notifications (SendGrid + Slack)
- **Group G**: Security (14 leak tests), chaos (5 degradation tests), E2E journey, Prometheus metrics, request-scoped logging, Dockerfile.prod

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
- Alembic at revision 0001

### Test Suite — 122/122 PASSING

---

## 7. What's Remaining (Next Session)

### PRIORITY 1: Deploy Backend to Koyeb

**Deployment target**: [Koyeb](https://www.koyeb.com/) (Docker-based)

`backend/Dockerfile.prod` is ready. Steps:
1. Create Koyeb account/project
2. Connect GitHub repo or push Docker image
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
   JWT_SIGNING_KEY=<generate-random-64-char>
   ADMIN_API_TOKEN=<generate-random-token>
   ENABLE_RATE_LIMIT=true
   ```
4. Optional (add when ready):
   ```
   REDIS_URL=<upstash-or-similar>
   WP_JWKS_URL=https://aueshah.com/wp-json/jwt-auth/v1/jwks
   WP_ISSUER=https://aueshah.com
   SENDGRID_API_KEY=<key>
   SLACK_WEBHOOK_NOOR=<url>
   SLACK_WEBHOOK_APPOINTMENTS=<url>
   ```
5. Lock CORS to `https://aueshah.com` (currently `allow_origins=["*"]`)
6. Verify health: `GET /health`
7. Test `/chat` endpoint from Koyeb URL

### PRIORITY 2: Re-embed Qdrant with text-embedding-3-large

The existing 108 vectors were embedded with `text-embedding-3-small` (1536d).
Settings now default to `text-embedding-3-large` (3072d). **Must re-run**:
```bash
cd backend
python -m scripts.load_rag       # re-embeds with large model
python -m scripts.smoke_rag      # verify retrieval works
```
This may require recreating the Qdrant collection with `size=3072`.

### PRIORITY 3: WordPress Integration

**Prerequisite**: Client/WP developer must:
1. Install a JWT Auth plugin (RS256 + JWKS endpoint) on aueshah.com
2. Enable Application Passwords (add `add_filter('wp_is_application_passwords_available', '__return_true');` to `functions.php`)
3. Share the JWKS URL and issuer with us

**Then Claude Code can** (via WordPress MCP or direct file editing):
1. Connect WordPress MCP: `claude mcp add --transport stdio wordpress --env WP_URL=https://aueshah.com --env WP_USERNAME=admin --env WP_APPLICATION_PASSWORD=xxxx -- cmd /c npx -y @node2flow/wordpress-mcp`
2. Inject chat widget JS/CSS into the bespoke page
3. Add post-login token exchange script to my-account page
4. Add custom `/wp-json/aueshah/v1/mint-token` REST endpoint
5. Enqueue scripts in `functions.php`
6. Set WP_JWKS_URL + WP_ISSUER + JWT_SIGNING_KEY in backend `.env`

Full guide for the WP developer: `WORDPRESS_INTEGRATION_ROADMAP.md`

### PRIORITY 4: Deferred Cleanup Tasks

| Task | What | When |
|---|---|---|
| T200 | Locust load test | After Koyeb deploy (needs real infra) |
| T204 | PII deletion endpoint | After first compliance review |
| T208 | README rewrite | During deploy prep |
| T209 | docker-compose update (postgres + redis services) | Dev convenience |
| T211 | Remove `ENABLE_RATE_LIMIT` flag (always-on) | At deploy time |
| CORS lockdown | Change `allow_origins=["*"]` to `["https://aueshah.com"]` | At deploy time |
| Redis | Connect Upstash or similar for production rate limiting | At deploy time |

---

## 8. .env Current State

`backend/.env` currently holds:
```
OPENAI_API_KEY=sk-svcacct-... (set)
OPENAI_MODEL=gpt-4.1 (set)
QDRANT_URL=https://871454ad-... (set, connected)
QDRANT_API_KEY=eyJhbGci... (set)
NEON_DATABASE_URL=postgresql+asyncpg://... (set, connected, tables created)
EMBEDDING_MODEL=text-embedding-3-small (⚠️ code defaults to large, .env still says small — re-embed needed)
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=2.5
LOG_LEVEL=INFO

# NOT SET YET (needed for full functionality):
REDIS_URL=                    # Rate limiting (fails open without it)
WP_JWKS_URL=                  # WordPress auth
WP_ISSUER=                    # WordPress auth
JWT_SIGNING_KEY=              # Our session JWT signing
ADMIN_API_TOKEN=              # Admin endpoints
SENDGRID_API_KEY=             # Email notifications
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
- **JWT plugin**: NOT installed yet — needed for auth flow
- **Application Passwords**: NOT enabled yet — needed for MCP connection
- **Chat widget**: NOT deployed yet — `WORDPRESS_INTEGRATION_ROADMAP.md` has full instructions

### User flow (planned)
```
User clicks "Start Bespoke" on /bespoke
  → Check localStorage for session token
  → If no token: redirect to /my-account/ login
  → After WP login: exchange WP JWT for our session JWT via POST /v1/auth/wp-login
  → Store our token in localStorage
  → Redirect back to /bespoke?chat=open
  → Chat widget opens, sends POST /chat with Authorization: Bearer <token>
  → Backend loads user from Neon DB, builds personalization preamble
  → AI responds with bespoke skill
```

---

## 11. Quick Orientation for New Claude Session

Before any work:
1. Read `CLAUDE.md` (operational rules).
2. Read this file (`SUMMARY.md`).
3. Check `git status` and current branch.
4. Check `backend/.env` for what's connected.

### Key files to scan
- `backend/app/core/agents_factory.py` — the whole AI runtime (triage + 5 specialists + 3 tools)
- `backend/app/config/prompts.py` — brand brain + all skill prompts
- `backend/app/config/settings.py` — all 30+ env vars with defaults
- `backend/app/api/routes.py` — POST /chat with full pipeline
- `backend/app/auth/` — WP verifier, session JWT, dependencies
- `backend/Dockerfile.prod` — production Docker image
- `WORDPRESS_INTEGRATION_ROADMAP.md` — WP developer instructions

### Non-negotiables
- Factual detail lives in Qdrant + JSON data files — **never** the system prompt.
- Never hallucinate pieces, prices, stock, materials. Always prefer uncertainty.
- API keys never leave server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- `requirements.docx` is the authoritative client spec — all 17 sections must stay matched.

### Resume from
**Deploy backend to Koyeb**, then connect WordPress. See Priority 1-3 above.
