# Phase 2 Quickstart — Local Dev Setup

**Date**: 2026-04-16
**Audience**: Backend engineers setting up the concierge locally with Neon + Redis + WP integration

---

## Prerequisites

- Python 3.11+
- Docker (for local Qdrant; optional if using managed Qdrant)
- A Neon account (free tier — https://neon.tech)
- An Upstash account for Redis (free tier — https://upstash.com)
- A Resend account (free tier, 3,000 emails/month — https://resend.com)
- A Slack workspace with permission to create incoming webhooks
- A WordPress sandbox with the `jwt-authentication-for-wp-rest-api` plugin installed (or use the local mock shipped in `app/scripts/wp_mock.py`)

---

## 1. Clone and install

```bash
git clone <repo>
cd aueshah/backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

New dependencies introduced in Phase 2 (already in `requirements.txt` after merge):

```
sqlalchemy[asyncio]==2.0.*
asyncpg==0.29.*
alembic==1.13.*
redis==5.*
python-jose[cryptography]==3.3.*
httpx==0.27.*
resend>=2.0.0
slack_sdk==3.*
```

---

## 2. Provision Neon

1. Sign in at https://console.neon.tech
2. Create a new project: `aueshah-concierge` (region: closest to your deploy region)
3. Copy the **pooled** connection string (the one with `-pooler` in the host) — it's the one your app should use.
4. Create a second branch `dev` for local development (so prod data stays clean).

Example DSN:
```
postgresql+asyncpg://user:pass@ep-cool-host-pooler.us-east-2.aws.neon.tech/aueshah?ssl=require
```

Note the `+asyncpg` driver prefix — SQLAlchemy needs this explicitly.

---

## 3. Provision Upstash Redis

1. Create a Redis database at https://console.upstash.com
2. Copy the **Redis URL** (starts with `rediss://`)
3. Keep the REST URL + token handy too (useful for admin inspection in the browser)

Example:
```
rediss://default:password@us1-frog-12345.upstash.io:12345
```

---

## 4. Configure `.env`

Copy the example and fill in:

```bash
cp .env.example .env
```

Required values:

```bash
# Core (Phase 1, unchanged)
OPENAI_API_KEY=sk-...
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=aueshah_catalog

# Neon (Phase 2)
NEON_DATABASE_URL=postgresql+asyncpg://user:pass@...-pooler.../aueshah?ssl=require

# Redis (Phase 2)
REDIS_URL=rediss://default:password@...upstash.io:12345

# Rate limit / timeout (Phase 2)
RATE_LIMIT_PER_MIN=5
REQUEST_TIMEOUT_SECONDS=15
ENABLE_RATE_LIMIT=true

# WordPress auth (Phase 2)
WP_BASE_URL=https://aueshah.com
WP_JWKS_URL=https://aueshah.com/wp-json/jwt-auth/v1/.well-known/jwks.json
WP_ISSUER=https://aueshah.com
WP_JWKS_CACHE_TTL=600

# Our session JWT (Phase 2)
JWT_SIGNING_KEY=<generate with: openssl rand -hex 32>
JWT_EXPIRES_SECONDS=86400

# Admin API (Phase 2)
ADMIN_API_TOKEN=<generate with: openssl rand -hex 24>

# Notifications (Phase 2)
RESEND_API_KEY=re_...
# Until aueshah.com is verified in Resend, use the sandbox sender below.
RESEND_FROM_EMAIL=Aueshah Concierge <onboarding@resend.dev>
CONCIERGE_ALERT_EMAIL=husnainxebad@gmail.com
SLACK_WEBHOOK_NOOR=https://hooks.slack.com/services/...
SLACK_WEBHOOK_APPOINTMENTS=https://hooks.slack.com/services/...

# Business logic (Phase 2)
NOOR_COOLDOWN_DAYS=90
MAX_CONTEXT_MESSAGES=15
```

---

## 5. Run migrations

```bash
alembic upgrade head
```

Verifies by connecting to Neon and running migration `0001_initial` which creates:
- `users`, `chat_messages`, `appointments`, `noor_allocation_requests`, `user_activity`
- Required extensions (`citext`, `pgcrypto`)
- `set_updated_at()` trigger function and associated triggers

Rollback (if needed):
```bash
alembic downgrade -1
```

---

## 6. Seed Qdrant (Phase 1, unchanged)

Start Qdrant locally:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

Load the catalog:
```bash
python -m app.scripts.seed_rag
```

(Expected: ~108 chunks in collection `aueshah_catalog`.)

---

## 7. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Smoke test:

```bash
# Liveness
curl http://localhost:8000/health
# → {"status":"ok"}

# Anonymous chat
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Tell me about the Noor Collection"}'

# Rate-limit test (run 6 times rapidly)
for i in {1..6}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"hi"}'
done
# Expected: 200, 200, 200, 200, 200, 429
```

---

## 8. Optional — WordPress local mock

If you don't have a WP sandbox, use the local mock:

```bash
python -m app.scripts.wp_mock --port 8080 &
```

Then in `.env`:
```
WP_BASE_URL=http://localhost:8080
WP_JWKS_URL=http://localhost:8080/.well-known/jwks.json
WP_ISSUER=http://localhost:8080
```

Mint a test WP token:
```bash
curl -X POST http://localhost:8080/issue-token \
  -d '{"wp_user_id":1,"email":"test@aueshah.com","display_name":"Test User"}'
# → {"wp_token":"eyJhbGciOiJSUzI1NiIs..."}
```

Exchange for our session JWT:
```bash
curl -X POST http://localhost:8000/v1/auth/wp-login \
  -H 'Content-Type: application/json' \
  -d '{"wp_token":"eyJhbGciOiJSUzI1NiIs..."}'
# → {"access_token":"...","user":{...}}
```

Use the access token for authed calls:
```bash
curl http://localhost:8000/v1/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

---

## 9. Run the tests

```bash
pytest tests/                                        # all
pytest tests/integration/test_rate_limiter.py -v     # rate limit slice
pytest tests/integration/test_noor_workflow.py -v    # Noor flow
pytest tests/integration/test_auth_flow.py -v        # WP auth
```

Integration tests use `testcontainers-postgres` and a disposable Redis via `fakeredis.aioredis` — no cloud credentials required for local runs.

---

## 10. Docker compose (optional all-in-one)

For running everything locally without cloud dependencies:

```bash
docker-compose up
```

Services:
- `backend` (port 8000)
- `postgres` (port 5432) — substitutes Neon locally
- `redis` (port 6379) — substitutes Upstash
- `qdrant` (port 6333)
- `wp_mock` (port 8080)

Point `.env` at these local services (see `.env.local` template).

---

## Troubleshooting

**`alembic upgrade head` fails with "extension citext does not exist"**
→ Your Neon user lacks `CREATE EXTENSION` privilege. On Neon free tier this should work; on other Postgres hosts, run as superuser:
```sql
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

**Rate limit returns 429 even on the first request**
→ Redis has stale keys. Flush: `redis-cli FLUSHDB` or in Upstash console → Data Browser → delete `ratelimit:*`.

**WP token verification fails with "invalid signature"**
→ JWKS is cached; the WP site may have rotated keys. Restart the backend or lower `WP_JWKS_CACHE_TTL` temporarily.

**`/chat` times out at 15s**
→ Expected behavior under slow OpenAI conditions. Client receives fallback message per constitution X.3. Check OpenAI status page; consider bumping `REQUEST_TIMEOUT_SECONDS` temporarily (not recommended for production).

---

## What to build next

After this quickstart works end-to-end, proceed to `/sp.tasks` to generate the atomic task list for implementation. Anticipated groups:

- Group A — Foundation (rate limit, timeout, history cap)
- Group B — Persistence (Neon models, repositories)
- Group C — WP auth (JWKS verifier, /v1/auth/*)
- Group D — Personalization (load profile + summary, inject into prompt)
- Group E — Noor allocation (workflow, cooldown, admin)
- Group F — Appointments + notifications
- Group G — Test & harden
