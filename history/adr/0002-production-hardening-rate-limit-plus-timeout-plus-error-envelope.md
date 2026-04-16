# ADR-0002: Production Hardening — Redis Sliding-Window Rate Limit + 15s Timeout + Unified Error Envelope

- **Status:** Proposed
- **Date:** 2026-04-16
- **Feature:** 001-concierge-chat-api (Phase 2)
- **Context:** Phase 1 deferred rate limiting per the spec's scope boundary (constitution IX.3 was waived on the assumption that throttling would be added later). The client has now explicitly mandated: max 5 requests/minute per IP, 15-second hard timeout per request, graceful error handling with a standard fallback message, and conversation history capped at 10–15 messages server-side. Without these controls, a buggy client or targeted attacker could (a) exhaust the OpenAI API budget, (b) overload the single-instance Qdrant retriever, and (c) cause cascading request queue buildup that degrades legitimate users. This ADR captures the cluster of production-hardening decisions that restore constitution IX.3 compliance and enforce the client's stability contract.

## Decision

Adopt a three-part hardening cluster, all implemented as FastAPI middleware and applied to `/chat` (and selectively to other high-cost endpoints):

- **Rate limiter**: Upstash Redis (serverless, `rediss://`) backing a sliding-window log algorithm. Per-IP key `ratelimit:chat:{ip}`, sorted set of request timestamps, evict entries older than 60s before insert, count, enforce `count <= RATE_LIMIT_PER_MIN` (default 5). On violation, return `429` with `Retry-After: 60` header and the standard fallback envelope. **Fail-open on Redis unavailability**: log a warning, allow the request, emit a metric for ops alerting — availability > strict enforcement.
- **Timeout**: `asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)` wrapping the `/chat` handler only. Default 15s. On `TimeoutError`, return `408` with the standard fallback envelope. Not applied to fast endpoints (`/health`, `/v1/auth/me`) because the overhead is wasted and the timeout masks real latency problems on those paths.
- **Unified error envelope**: Every non-2xx response returns `{ "error": "<safe-text>", "code": <int>, "retry_after"?: <int> }`. The error string never contains stack traces, model names, API keys, internal paths, or system-prompt fragments (constitution V.5 / IX.5). For 429/408/503, the `error` field is the brand-safe fallback: *"There appears to be a temporary delay. Please try again shortly."* All errors pass through a single `error_handler.py` middleware that wraps exceptions at the outermost layer.
- **Request-context cap**: A small dependency (`cap_context`) trims caller-supplied `context` to the most recent 15 entries before the request reaches the orchestrator, regardless of what the client sent. This is not middleware — it's a Pydantic validator on `ChatRequest` — but it belongs to the same hardening cluster because it bounds token/latency blast radius from a misbehaving client.

**Rollout**: Gated behind `ENABLE_RATE_LIMIT=false` on initial deploy. Enable in staging, load-test, enable in production, monitor for 24h, then remove the flag.

## Consequences

### Positive

- **Cost protection**: At 5 req/min/IP, a single abusive IP is capped at 300 requests/hour — roughly $0.60 in OpenAI cost vs unbounded. Total OpenAI budget impact is now predictable.
- **Latency SLO preserved under stress**: Without a timeout, slow OpenAI responses could queue up and blow past the 3s p95. With a 15s hard cap, the worst-case user experience degrades to a clear fallback rather than an indefinite hang.
- **Constitution IX.3 compliance restored**: Previously deferred; now enforced.
- **Horizontally scalable**: Redis-backed counters are correct across multiple backend instances (in-process limiters like `slowapi` break on multi-instance deploys).
- **Fair**: Sliding-window log is exact at the enforcement boundary — no "burst through the edge" at window rollover like fixed-window limiters have.
- **Ops-friendly**: Fail-open on Redis outage means a Redis incident doesn't take down `/chat`; the warning log + metric gives ops time to fix without user-visible impact.
- **Safe error surface**: Unified envelope removes the class of bugs where a particular failure mode leaks internals (e.g., an uncaught `OpenAIError` printing the API key in its repr).

### Negative

- **New runtime dependency (Redis)**: Adds a failure mode to monitor. Mitigated by fail-open design.
- **~5ms added latency per chat request**: Sliding-window log uses 4 Redis ops per request (zremrangebyscore, zadd, zcard, expire) pipelined. Measured ~3–5ms on Upstash's US-East-2 region. Within budget.
- **Sliding-window log cost at scale**: Each sorted set entry is ~50 bytes; at 5 req/min/IP this is negligible, but if we ever raise the limit to 100 req/min for authed users, memory per key grows. Revisit if rate limit policy changes.
- **Timeout can mask real problems**: A 15s cap means latency regressions >15s look like "timeouts" in logs rather than slow responses. Mitigation: emit latency histogram before the timeout wrapper so we still see the real tail.
- **Fallback message deduplication**: Every brand-safe error string is now a single constant. If we ever want per-endpoint fallbacks, that requires a change here. For now, uniform is correct.
- **Flag debt**: `ENABLE_RATE_LIMIT` feature flag should be removed after rollout to keep config surface small.

## Alternatives Considered

**Alternative A — `slowapi` library (in-process rate limiter)**
- Drop-in FastAPI integration, minimal code.
- Rejected: in-process counters break under multi-instance deploy. We will be multi-instance in production.

**Alternative B — Fixed window rate limiter (per-minute bucket)**
- Trivial to implement (`INCR` + `EXPIRE`).
- Rejected: classic 2x burst at window boundary. At 5/min limit, a user can hit 10 req in 1 second across the boundary — exactly the abuse pattern we need to prevent.

**Alternative C — Token bucket**
- Great for burst smoothing with refill rate.
- Rejected: extra parameter surface (bucket size vs refill rate vs max burst) and overkill for a flat 5/min limit. Sliding window is the simpler, exact-enforcement choice here.

**Alternative D — Fly Redis / Render Redis / self-hosted**
- Fewer vendors.
- Rejected: persistent TCP, higher baseline cost, doesn't match the serverless posture of Neon + Qdrant. Upstash REST is cheaper and simpler at our scale.

**Alternative E — Cloudflare / API Gateway rate limit (edge-enforced)**
- No code required; enforcement at the edge.
- Rejected for v1: requires a specific deployment topology we haven't committed to, and we still need application-level limits because the backend may be called from the same origin (no IP to discriminate). Revisit if we add a CDN/WAF layer.

**Alternative F — No timeout, rely on OpenAI's internal timeout**
- Simpler code path.
- Rejected: OpenAI's default timeout is 10min. During an OpenAI degradation, our `/chat` would hang for minutes, exhausting worker slots. An explicit 15s cap is non-negotiable for client-facing SLA.

**Alternative G — Per-endpoint custom error formats**
- More flexibility.
- Rejected: duplicated error-shaping logic invites inconsistencies and leaks. A single envelope is a small constraint that pays off in safety and tooling (one error parser on the client, one log schema on ops).

## References

- Feature Spec: `specs/001-concierge-chat-api/spec.md` (FR-009, FR-015, FR-016, SC-007, SC-008)
- Implementation Plan: `specs/001-concierge-chat-api/plan.md` (Phase 2 Group A)
- Research Notes: `specs/001-concierge-chat-api/research.md` (§2 rate limit, §7 rollout)
- Client Requirements: `CLIENT_REQUIREMENTS_ANALYSIS.md`
- Related ADRs: ADR-0001 (Persistence & Identity — shares Redis as cache for JWKS + session revocation)
- Constitution sections affected: IX.3 (restored compliance), IX.5 (safe error surface), X.1 (p95 SLO), X.3 (graceful degradation)
- Evaluator Evidence: `history/prompts/001-concierge-chat-api/0006-plan-phase-2-persistence-wp-auth.plan.prompt.md`
