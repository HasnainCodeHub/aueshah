# Aueshah AI Concierge — Backend

Stateless FastAPI concierge for [aueshah.com](https://aueshah.com/). Routes visitor
messages through the **OpenAI Agents SDK** (triage agent + 5 specialists),
grounds answers with **Qdrant RAG**, persists identity and chat history in
**Neon Postgres**, and rate-limits via **Upstash Redis**.

**Status**: feature-complete against client requirements. All 17 sections of
the spec are satisfied. 122/122 tests passing.

---

## Stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.11+, FastAPI async |
| Validation | Pydantic v2 |
| AI | OpenAI `gpt-4.1` via **openai-agents** SDK |
| Embeddings | `text-embedding-3-large` (3072d) |
| Vector store | Qdrant Cloud (eu-west-1) |
| Database | Neon Serverless Postgres (SQLAlchemy 2.0 async + asyncpg) |
| Migrations | Alembic |
| Cache / rate limit | Redis (Upstash) — sliding-window, fail-open |
| Auth | WordPress RS256 JWT (JWKS) → our HS256 session JWT |
| Package manager | `uv` |
| Notifications | Resend (email) |
| Observability | Prometheus metrics, JSON structured logging with request IDs |
| Deployment | Docker (`Dockerfile.prod`), targets Koyeb |

---

## Quick start

```bash
# 1. Install deps (one-time)
uv sync

# 2. Configure
cp .env.example .env
# → paste your OPENAI_API_KEY, QDRANT_*, NEON_DATABASE_URL, REDIS_URL

# 3. Apply DB migrations
uv run alembic upgrade head

# 4. Load RAG knowledge base
uv run python -m scripts.load_rag
uv run python -m scripts.smoke_rag   # sanity-check retrieval

# 5. Run the dev server
uv run uvicorn app.main:app --reload --port 8000
```

API is live at `http://localhost:8000`. Health check: `GET /health`.

### Docker

```bash
# Local (dev)
docker build -t aueshah-concierge backend
docker run --env-file backend/.env -p 8000:8000 aueshah-concierge

# Production (multi-stage, non-root, healthcheck)
docker build -f backend/Dockerfile.prod -t aueshah-concierge:prod backend
```

---

## Environment variables

Required:

| Var | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI — LLM + embeddings |
| `OPENAI_MODEL` | default `gpt-4.1` |
| `EMBEDDING_MODEL` | default `text-embedding-3-large` |
| `QDRANT_URL` / `QDRANT_API_KEY` | vector store |
| `NEON_DATABASE_URL` | `postgresql+asyncpg://…?ssl=require` |

Recommended for production:

| Var | Purpose |
|---|---|
| `REDIS_URL` | Upstash `rediss://…` — rate limiting (always on when set; unset to disable) |
| `JWT_SIGNING_KEY` | HS256 session JWT signing (`python -c "import secrets; print(secrets.token_urlsafe(64))"`) |
| `ADMIN_API_TOKEN` | shared secret for `X-Admin-Token` gated routes |
| `WP_JWKS_URL` / `WP_ISSUER` | WordPress JWT verification |
| `RESEND_API_KEY` | email notifications (Resend) |

Full list with defaults: `app/config/settings.py`.

---

## API

### Public

| Method | Path | Notes |
|---|---|---|
| `POST` | `/chat` | Main chat endpoint. Accepts message + optional `session_id` + `page_context`. |
| `GET`  | `/health` | Liveness probe. |
| `POST` | `/v1/auth/wp-login` | Exchange WP RS256 JWT → our session JWT. Merges visitor cookie. |
| `GET`  | `/v1/auth/me` | Current user profile (Bearer token). |
| `POST` | `/v1/auth/logout` | Clear session. |
| `POST` | `/v1/noor-requests` | Submit Noor allocation request. |
| `GET`  | `/v1/noor-requests/me` | Current user's requests. |

### Admin (`X-Admin-Token` header)

| Method | Path | Notes |
|---|---|---|
| `GET`    | `/v1/admin/noor-requests` | List, filter by status. |
| `GET`    | `/v1/admin/noor-requests/{id}` | Fetch one. |
| `PATCH`  | `/v1/admin/noor-requests/{id}` | Approve / decline + notify client. |
| `DELETE` | `/v1/admin/users/{user_id}` | GDPR right-to-erasure (wipes PII across all tables). |
| `GET`    | `/v1/admin/metrics` | Prometheus scrape endpoint. |

### POST /chat example

```json
{
  "message": "Tell me about the Noor Collection",
  "session_id": "9f7a…",
  "page_context": {
    "page_type": "collection",
    "collection_name": "Noor"
  }
}
```

Response:
```json
{
  "reply": "The Noor Collection…",
  "metadata": {
    "skill": "noor",
    "latency_ms": 1850
  }
}
```

---

## Project layout

```
backend/
├── alembic/                        # Migrations (at revision 0001)
├── app/
│   ├── main.py                     # FastAPI app + middleware stack
│   ├── api/
│   │   ├── routes.py               # POST /chat
│   │   ├── auth_routes.py          # /v1/auth/*
│   │   ├── noor_routes.py          # /v1/noor-requests
│   │   └── admin_routes.py         # /v1/admin/*
│   ├── auth/                       # WP verifier, session JWT, visitor cookie
│   ├── core/
│   │   ├── agents_factory.py       # Triage agent + 5 specialists + 3 tools
│   │   ├── orchestrator.py         # Runner wrapper + token tracking
│   │   └── personalization.py      # Selective return memory (Noor 30d / Bespoke 60d)
│   ├── db/
│   │   ├── models.py               # User, ChatMessage, Appointment, NoorAllocationRequest, UserActivity
│   │   ├── session.py              # Async engine + sessionmaker
│   │   └── repositories/           # chat_history, users, noor_requests, appointments
│   ├── middleware/                 # error_handler, timeout, rate_limiter, request_context
│   ├── services/
│   │   ├── rag_service.py          # Qdrant retrieval
│   │   ├── noor_catalog.py         # Deterministic Noor profile matcher
│   │   ├── noor_workflow.py        # Eligibility + persistence + notifications
│   │   ├── appointment_workflow.py
│   │   ├── persistence_writer.py   # Fire-and-forget chat persistence
│   │   ├── notifications/          # email (Resend)
│   │   ├── summary_cache.py        # In-process LRU per-user
│   │   ├── profile_extractor.py
│   │   └── failure_handler.py
│   ├── config/
│   │   ├── settings.py             # All env vars
│   │   └── prompts.py              # Brand brain v2.0 + skill prompts
│   ├── utils/                      # validators, metrics, logging
│   ├── models/                     # Pydantic schemas, typed errors
│   └── data/                       # heritage.md, products.json, noor_catalog.json
├── scripts/
│   ├── load_rag.py                 # Embed + upsert knowledge into Qdrant
│   └── smoke_rag.py                # Retrieval sanity check
├── tests/
│   ├── unit/ integration/ security/ chaos/ e2e/
│   └── load/locustfile.py          # Post-deploy load test
├── Dockerfile                      # Dev
├── Dockerfile.prod                 # Multi-stage, non-root, healthcheck
├── pyproject.toml                  # uv-managed
└── alembic.ini
```

---

## Testing

```bash
uv run pytest tests/ -q                     # full suite
uv run pytest tests/integration/ -v         # integration only
uv run pytest tests/security/ -v            # leak + injection tests
uv run pytest tests/chaos/ -v               # degraded-mode tests
```

See `tests/load/README.md` for Locust load testing against a deployed URL.

---

## Architecture notes

- **Backend-first, stateless.** All logic in FastAPI. Context comes in the
  request body; persistence is a side effect, never authoritative for the
  current turn.
- **Agents SDK owns routing.** A triage agent hands off to one of five
  specialists (`product`, `compare`, `noor`, `bespoke`, `general`). Tools
  (`search_catalog`, `noor_recommend`, `submit_noor_request`) are explicit and
  validated.
- **No hallucination.** Factual detail lives in Qdrant + JSON, never the
  system prompt. The agent defers to uncertainty over invention.
- **Two-layer off-topic defense.** Regex keyword guardrail + prompt-level
  SCOPE section.
- **Fail-open degradation.** Redis down → rate limit skipped (logged).
  Qdrant down → agent answers without RAG. OpenAI timeout → graceful fallback.
- **12-principle constitution** governs all changes — see
  `/.specify/memory/constitution.md`.

---

## Deployment

Production image: `backend/Dockerfile.prod` (multi-stage `uv` build, non-root,
healthcheck). Deploys to Koyeb / Render / Fly / any Docker-capable platform.

At deploy time:
1. Set all env vars in the platform dashboard — **not** baked into the image.
2. Lock CORS: change `allow_origins=["*"]` in `app/main.py` to your domain.
3. Apply migrations: `alembic upgrade head` (can run as a release job).
4. Reload the RAG index if embedding model changed: `python -m scripts.load_rag`.
5. Verify `GET /health` returns 200 before switching traffic.

See the repo root `SUMMARY.md` for full session-level deployment context.
