# ADR-0001: Persistence & Identity — WordPress JWT Auth + Neon Serverless Postgres + Persisted Chat History

- **Status:** Proposed
- **Date:** 2026-04-16
- **Feature:** 001-concierge-chat-api (Phase 2)
- **Context:** The Phase 1 concierge is stateless with no user model. The client's product is a WordPress site and the client has mandated (a) personalization based on saved profile data, (b) cross-session memory of past conversations, (c) a formal Noor allocation request system tied to user identity, and (d) an appointment flow tied to user identity. These requirements cannot be satisfied without a durable user record, a persistent chat store, and an identity bridge to the WordPress user base that already exists.

## Decision

Adopt a single cohesive persistence & identity cluster:

- **Identity bridge**: WordPress is the source of truth for user accounts. The `jwt-authentication-for-wp-rest-api` plugin on the client's WP site issues RS256 JWTs. Our backend verifies these via the WP site's JWKS endpoint (cached in-memory, TTL 10 min), then upserts the user into our Neon database keyed on `wp_user_id`. We re-mint our own HS256 session JWT (24h TTL) so subsequent API calls do not require round-trips to WP.
- **Anonymous→authenticated merge**: Browsers receive a signed HTTP-only `visitor_id` cookie on first contact. On successful WP login, we rewrite `chat_messages.user_id` where `visitor_id` matches, so pre-login conversation context survives the login transition.
- **Primary OLTP store**: **Neon Serverless Postgres** via `asyncpg` + SQLAlchemy 2.0 async, with Alembic migrations. Five tables: `users`, `chat_messages`, `appointments`, `noor_allocation_requests`, `user_activity`. Pooled connection string, `ssl=require`.
- **Chat history persistence**: Every user message and assistant reply is persisted to `chat_messages` with intent, skill, routing source, and RAG chunk IDs used for grounding. Persistence happens on a background task (`asyncio.create_task`) and never blocks the client response.
- **Prompt-context cap preserved**: The caller still supplies `context` on each `/chat` request; the server caps it at 15 entries server-side before invoking the LLM. Persisted history is used *only* to derive a compact personalization preamble (last-N summary + profile fields), never replayed verbatim into the prompt.

**Constitutional deviations** (explicitly justified):
- **VI.1** (visitor_id primary key): Identity anchor becomes `wp_user_id` (mapped to internal `user_id`). `visitor_id` is retained for anonymous sessions and merged on login. Justification: client product runs on WP; a parallel visitor-first identity creates double-accounts and breaks "remember me across sessions."
- **VI.2** (store summaries, not transcripts): Full messages persisted. Justification: client explicitly required warm re-engagement ("remember my recent activities"), which distillation erases. Mitigation: prompt context is still capped at 15 (VI.3 preserved); prompt tokens are bounded; retention policy archives rows >12 months.

## Consequences

### Positive

- **Client requirements met**: Personalization, cross-session memory, Noor request identity, appointment tracking all unblocked.
- **Single source of truth for identity**: WP remains the user management UI; we never store WP password hashes, reducing our security surface.
- **Serverless symmetry with Qdrant/OpenAI**: Neon scales to zero, no idle database cost, matches the existing stateless-ish posture of the backend.
- **Auditability**: Full chat history + `user_activity` log enables the concierge team to context-switch into a conversation, review past decisions, and justify Noor approvals.
- **Merge-on-login preserves UX**: Users who chat anonymously then log in don't lose their pre-login conversation.
- **Async persistence does not impact p95**: Writes happen on background tasks; the `/chat` latency budget (3s) is unaffected.

### Negative

- **New operational dependency**: Neon outages now impact persistence (but *not* chat — we fail-open by logging a warning and serving the request without history).
- **Schema evolution cost**: Alembic migrations introduce a deploy step that didn't exist in Phase 1.
- **Privacy surface expands**: We now store PII (email, display_name, optional phone) and free-text user messages. Requires a retention policy, data-subject-access pathway, and secure backup handling.
- **Token-budget ceiling lower**: Injecting personalization preamble (profile + summary) consumes ~300–500 tokens per request. Compensated by the 68% system-prompt reduction completed in Phase 1 optimization.
- **Constitutional non-standard**: Deviates from VI.1 and VI.2. Requires this ADR to remain accepted; future auditors must reference this document.
- **WP coupling**: Backend availability is gated on WP issuing valid JWTs. Mitigation: cached JWKS means brief WP outages do not break existing sessions (only new logins).

## Alternatives Considered

**Alternative A — Visitor-only identity, no WP integration, summaries only**
- Retain constitution VI.1 and VI.2 strictly.
- Rejected: cannot satisfy "remember me across sessions across devices" without a stable cross-device identity key. Users on WP already have accounts — forcing them to re-profile every session is a worse UX.

**Alternative B — WP Application Passwords (Basic Auth) instead of JWT plugin**
- Simpler to implement; no JWKS fetch, no token minting.
- Rejected: leaks long-lived credentials, worse UX (user must generate a password in WP admin), and doesn't compose with future mobile/native clients. RS256 + JWKS is the industry-standard approach.

**Alternative C — Cookie + WP nonce via shared reverse proxy**
- Elegant if backend and WP share a domain.
- Rejected: couples deployment topology; fragile across environments; doesn't survive moving the backend to a different region.

**Alternative D — Self-hosted Postgres (Fly / Railway / RDS) instead of Neon**
- More control, familiar ops.
- Rejected: introduces idle cost, scaling friction, and backup/restore toil. Neon's branch-per-environment model also simplifies dev/staging isolation.

**Alternative E — MongoDB or DynamoDB for flexible chat history**
- Document stores handle variable-shape conversation data well.
- Rejected: relational constraints are load-bearing for this domain (FK from `noor_allocation_requests.user_id` to `users.id` enforces "Noor requests require auth"; unique constraints on `reference_id` are critical). Postgres with JSONB for `user_activity.details` gets us document flexibility where we actually need it.

**Alternative F — Persist summaries only (constitution-pure VI.2)**
- Distill each conversation turn into a compact summary; never store raw messages.
- Rejected: summaries lose the recency signal needed for warm re-engagement ("You were asking about the Noor Collection last Tuesday — want to pick up there?"). Also removes audit trail; concierge can't review what actually happened in a conversation to justify decisions.

## References

- Feature Spec: `specs/001-concierge-chat-api/spec.md`
- Implementation Plan: `specs/001-concierge-chat-api/plan.md`
- Research Notes: `specs/001-concierge-chat-api/research.md` (§1 WP auth, §6 statelessness preservation)
- Data Model: `specs/001-concierge-chat-api/data-model.md`
- Related ADRs: ADR-0002 (Production Hardening — rate limit + timeout)
- Constitution sections affected: II.2, II.3, VI.1, VI.2, VI.3, VI.4
- Evaluator Evidence: `history/prompts/001-concierge-chat-api/0006-plan-phase-2-persistence-wp-auth.plan.prompt.md`
