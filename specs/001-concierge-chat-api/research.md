# Phase 0 Research — AI Concierge Phase 2

**Date**: 2026-04-16
**Feature**: `001-concierge-chat-api` (Phase 2 — persistence, WP auth, rate limiting, Noor allocation, personalization)

Purpose: resolve every NEEDS CLARIFICATION from `plan.md` so implementation can proceed without stalling on architectural ambiguity.

---

## §1. WordPress → Backend identity bridge

**Decision**: **WP JWT Authentication plugin** (`jwt-authentication-for-wp-rest-api` or the hardened fork `jwt-auth`) issuing **RS256** tokens, verified on our backend via **JWKS** fetched from the WP site and cached in-memory (TTL 10 minutes).

**Token flow**:
```
WP Login (WordPress UI)
   ↓
WP issues JWT (RS256, claims: sub=wp_user_id, email, display_name, exp, iat, iss=wp_site_url)
   ↓
Browser sends JWT → our POST /v1/auth/wp-login   (body: { wp_token })
   ↓
Backend: verify signature via cached JWKS; validate iss, exp, aud
   ↓
Backend: upsert user in Neon (match on wp_user_id; update email/display_name)
   ↓
Backend: mint OUR session JWT (HS256, 24h, claims: sub=internal_user_id, wp_user_id, role)
   ↓
Return { access_token } to browser; browser uses Bearer on subsequent calls
```

**Why RS256 + JWKS** (not HS256 shared-secret): WP and our backend are separate deployments; asymmetric keys mean a compromised backend cannot forge WP tokens.

**Why re-mint our own session JWT**: Decouples session lifetime from WP token TTL, lets us embed our `user_id` + role without pinging WP on every request, and lets us invalidate independently (revocation list in Redis).

**Anonymous → authenticated merge**: Browser gets an HTTP-only `visitor_id` cookie (uuid, signed) on first contact. On successful `/v1/auth/wp-login`, we rewrite `chat_messages.visitor_id = X` to carry `user_id = Y` for that row, preserving pre-login conversation context.

**Alternatives considered**:
- **WP Application Passwords (Basic auth)**: Works but leaks long-lived credentials; worse UX (user has to generate a password in WP admin); rejected.
- **Cookie + WP nonce via reverse proxy**: Requires both apps behind same domain; fragile across environments; rejected for a decoupled backend on Fly/Railway.
- **HS256 shared secret**: Symmetric key must be copied between WP server and backend; key rotation is painful; rejected.

**Implementation notes**:
- JWKS URL: `{WP_BASE_URL}/wp-json/jwt-auth/v1/.well-known/jwks.json` (plugin provides; if absent, fall back to configured public key PEM in env)
- Library: `python-jose[cryptography]` with `jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})` (set `iss` check manually)
- JWKS cache: in-memory dict keyed by `kid`, refreshed on cache miss or every 10 min; on fetch failure, fail-closed with structured error
- Clock skew tolerance: 30 seconds

---

## §2. Rate-limit + Redis provider

**Decision**: **Upstash Redis (serverless, REST + Redis protocol)** with a **sliding-window log** limiter implemented in-app (not `slowapi`, which uses in-process fixed windows and fails across instances).

**Why Upstash**:
- Serverless, pay-per-request (free tier covers 10k commands/day — far more than we need)
- REST endpoint works through HTTP (no long-lived TCP) — ideal for Fly/Render/Vercel runtimes with cold starts
- Native async client (`upstash-redis`) or standard `redis.asyncio` works too
- Matches "Neon serverless" posture for operational symmetry

**Why sliding window log** (not fixed window / token bucket):
- At 5 req/min, fixed window has a classic 2x burst problem at window boundaries (user can fire 5 at 00:00:59 and 5 at 00:01:00 = 10 in 1s)
- Sliding window log is exact: store timestamps in a Redis sorted set, drop entries older than 60s, count remaining, compare to limit
- Cost: ~5 Redis ops per request — acceptable for 5/min limit

**Algorithm** (pseudocode):
```python
key = f"ratelimit:chat:{client_ip}"
now = time.time()
pipe = redis.pipeline()
pipe.zremrangebyscore(key, 0, now - 60)      # evict old
pipe.zadd(key, {str(uuid4()): now})          # record this request
pipe.zcard(key)                              # current count
pipe.expire(key, 60)                         # auto-cleanup
_, _, count, _ = await pipe.execute()
if count > 5:
    raise RateLimited(retry_after=60)
```

**Fail-open policy**: If Redis is unreachable, log a warning and allow the request (availability > strict enforcement). Also emit a metric for ops alerting.

**Timeout middleware (separate from rate limit)**: `asyncio.wait_for(call_next(request), timeout=15)` wrapping the whole handler. On `TimeoutError`, return 408 with standard fallback message. Applied only to `/chat` (other endpoints are fast).

**Alternatives considered**:
- **`slowapi`**: Per-process memory, breaks under multi-instance deploy; rejected.
- **Fly Redis / Render Redis**: Persistent TCP connection; higher baseline cost; rejected in favor of serverless symmetry.
- **Token bucket**: Better for burst smoothing but overkill at 5/min; rejected for simplicity.

---

## §3. Notification provider

**Decision**: **SendGrid** for email + **Slack Incoming Webhooks** for team alerts.

**Email — SendGrid**:
- Free tier: 100 emails/day, sufficient for current volume (expected <10 appointments/day + <5 Noor requests/day at launch)
- Python SDK: `sendgrid` package, works with `httpx.AsyncClient` wrapper for true async
- Templates stored as dynamic templates in SendGrid UI (concierge team can edit copy without code deploy)
- Two templates required:
  1. `client-confirmation` — sent to client after appointment/Noor request (variables: `name`, `reference_id`, `request_type`)
  2. `concierge-alert` — sent to `concierge@aueshah.com` with full request payload (variables: `user_profile_json`, `request_details`, `admin_link`)

**Slack — Incoming Webhooks**:
- Two channels: `#noor-requests` (critical — every Noor request) and `#appointments` (every appointment)
- Webhook URLs stored in env: `SLACK_WEBHOOK_NOOR`, `SLACK_WEBHOOK_APPOINTMENTS`
- Library: `slack_sdk.webhook.async_client.AsyncWebhookClient`
- Message format: Block Kit with approve/decline buttons (v2) — MVP ships with plain text + link to admin panel

**Alternatives considered**:
- **AWS SES**: Cheaper at scale (~$0.10/1k emails), but setup overhead (domain verification, DKIM, sandbox exit review) slows v1; revisit at 10k+ emails/month.
- **Postmark**: Best deliverability reputation, but paid from day 1 (~$15/month); overkill for launch volume.
- **Resend**: Good DX, free tier (3k/month) but relatively new; keep as fallback option.

**Failure mode**: Notifications are fire-and-forget via `asyncio.create_task()` — they never block the client response. Failed sends are logged and written to a `notification_failures` table (deferred to Phase 3 if volume warrants) or surfaced via Sentry.

---

## §4. Noor cooldown policy

**Decision**: **90-day cooldown post-approval**, **immediate block on pending**, **no cooldown on decline** (client may re-apply with better context).

**Logic**:
```
Before creating a new Noor request for user_id:
  1. If user has status='pending' request → block: "You already have an active Noor request."
  2. If user has status='approved' request with cooldown_until > now() → block:
     "You have an approved Noor allocation. New requests unlock on {cooldown_until:%b %d, %Y}."
  3. If user has status='declined' request → allow (no cooldown)
  4. Otherwise → allow

On approval:
  SET cooldown_until = now() + INTERVAL '90 days'
  SET status = 'approved'
  SET reviewed_at = now()
  SET reviewed_by = <concierge_id>
```

**Why 90 days**: Aueshah Noor pieces are heirloom-level purchases; the typical purchase cycle runs 30–60 days from approval to delivery, plus buffer. Shorter cooldowns risk repeat requesters gaming the waitlist; longer feels punitive.

**Override path**: Concierge can manually clear a user's cooldown via `PATCH /v1/admin/users/{id}` with reason logged to `user_activity`.

**Configurable via env**: `NOOR_COOLDOWN_DAYS=90` (changeable without redeploy via hot-reload settings if added later).

---

## §5. Concierge admin surface

**Decision (MVP)**: **Token-protected JSON endpoints** (`/v1/admin/*`) accessible via **Postman collection** + a **minimal Next.js admin page** bundled with the existing test UI at `ui/pages/admin/`. Protected by `ADMIN_API_TOKEN` (rotated quarterly).

**v1 endpoints**:
- `GET /v1/admin/noor-requests?status=pending` — list
- `GET /v1/admin/noor-requests/{id}` — detail (with user profile)
- `PATCH /v1/admin/noor-requests/{id}` — approve/decline + internal_notes + reviewed_by
- `GET /v1/admin/appointments?status=pending` — list
- `PATCH /v1/admin/appointments/{ref_id}` — confirm + scheduled_at + meeting_link

**v2 (post-launch)**: Either a standalone admin SPA or a WordPress admin plugin that iframes our admin UI under the existing WP admin shell (client's team is already familiar with WP admin UX).

**Why token + minimal UI over full admin SPA**:
- Scope — admin surface needs to exist for Noor workflow to function, but it isn't the product focus
- Speed — concierge is a small team (<5 people); Postman + 1-page UI is sufficient until volume demands more
- Iteration cost — every hour spent on admin UX in v1 is an hour not spent on the core concierge experience

**Alternatives considered**:
- **WP admin plugin from day 1**: Would be elegant (single UX for concierge team) but requires WP dev pipeline (PHP, WP hooks, plugin submission) we don't own; defer to v2.
- **Retool / Metabase**: Good for quick admin UIs but introduces third-party dependency + per-user licensing cost; rejected for MVP.

---

## §6. Stateless contract preservation with persisted history

**Decision**: Keep `/chat` contract (`{ message, context }`) exactly as-is. On the server:

1. If request is authenticated (`Authorization: Bearer`), load **last N=5 summarized interactions** from `chat_messages` (distilled via a cheap summarization pass, cached per user for 10 min) and inject into the **system-prompt preamble** — not into the `context` array.
2. The caller-supplied `context` is treated as **ephemeral display state** — it's the client's responsibility to maintain, and we cap it to 15 entries on receipt regardless of what's sent.
3. Anonymous requests get no history injection, just the caller's `context` capped to 15.

**Why this preserves statelessness**: The server does not hold a session — each request is still self-contained from a protocol standpoint. The "memory" is *derived on demand* from persisted data keyed to the authenticated user, not from server RAM.

**Why cap on receipt**: Client could send a 200-message context (accidentally or maliciously). Hard cap at 15 protects token budget (constitution X.2) and latency SLO.

**Capping function**:
```python
def cap_context(context: list[ContextMessage], max_n: int = 15) -> list[ContextMessage]:
    if not context or len(context) <= max_n:
        return context or []
    return context[-max_n:]   # keep most recent
```

Applied in `middleware/` before the request reaches `orchestrator.handle_chat()`.

---

## §7. Migration & rollout strategy

**Decision**: Ship Phase 2 in **five separately-deployable slices** to avoid a big-bang cutover:

1. **Slice 1 (zero-risk)**: Rate limiter + timeout middleware behind feature flag `ENABLE_RATE_LIMIT=false` → deploy → enable → monitor → commit.
2. **Slice 2**: Neon setup + migrations + DB connection health check (no writes yet).
3. **Slice 3**: Persist chat messages (writes only, reads still from request context).
4. **Slice 4**: WP auth + personalization reads (authed users get history injection).
5. **Slice 5**: Noor allocation + appointments + notifications.

Each slice is independently revertable. No slice blocks the existing `/chat` endpoint from serving unauthenticated traffic.

---

## Summary of Decisions

| Topic | Decision | Primary reason |
|-------|----------|----------------|
| WP auth | WP JWT plugin (RS256) + JWKS verify + re-mint our JWT | Decoupled identity, safe key handling |
| Rate limit | Upstash Redis + sliding-window log, 5/min/IP | Exact enforcement, serverless symmetry |
| Timeout | `asyncio.wait_for(15s)` on /chat only | Simple, proven, matches client spec |
| Notifications | SendGrid (email) + Slack webhooks | Free tier sufficient, async-friendly |
| Noor cooldown | 90 days post-approval, immediate block on pending | Matches heirloom purchase cycle |
| Admin surface | Token-protected endpoints + 1-page Next.js UI | MVP scope discipline |
| Stateless + history | Caller context (capped 15) + server-side summary injection | Preserves stateless contract |
| Rollout | 5 deploy slices behind feature flags | Risk containment |

All NEEDS CLARIFICATION resolved. Ready for Phase 1 design.
