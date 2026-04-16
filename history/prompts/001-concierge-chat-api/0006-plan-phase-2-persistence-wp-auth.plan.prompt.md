---
id: "0006"
title: Plan Phase 2 — Persistence, WP Auth, Rate Limiting
stage: plan
date: 2026-04-16
surface: agent
model: claude-opus-4-6
feature: 001-concierge-chat-api
branch: 001-concierge-chat-api
user: HasnainCodeHub
command: /sp.plan
labels: [plan, neon, wordpress-auth, rate-limiting, noor-allocation, personalization]
links:
  spec: specs/001-concierge-chat-api/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-concierge-chat-api/plan.md
  - specs/001-concierge-chat-api/research.md
  - specs/001-concierge-chat-api/data-model.md
  - specs/001-concierge-chat-api/contracts/openapi.yaml
  - specs/001-concierge-chat-api/quickstart.md
  - CLAUDE.md
tests:
  - (none — design phase)
---

## Prompt

noe make a plan according to our whole conversation and implement the best approach according to the client wants and i want to use neon serveless database also remember the client wesite is on wordpress so the user authentication is coming from wordpress site we have to develop our authentication system according to it

## Response snapshot

Produced Phase 2 implementation plan extending existing backend with:

1. **Rate limiting + 15s timeout** (Redis sliding-window log, 5 req/min/IP, fail-open)
2. **Neon Serverless Postgres** (5 tables: users, chat_messages, appointments, noor_allocation_requests, user_activity)
3. **WordPress-bridged auth** (RS256 WP JWT → verify via JWKS → upsert user → mint our HS256 session JWT)
4. **Noor allocation workflow** (formal request, 90d cooldown, concierge approve/decline, notifications)
5. **Personalization** (profile + last-N summary injected into system prompt; caller context still capped to 15)
6. **Notifications** (SendGrid email + Slack webhooks, fire-and-forget)

Delivered artifacts: plan.md (with Technical Context, Constitution Check, Project Structure, Complexity Tracking), research.md (7 topics resolved), data-model.md (5 tables with state machines, indexes, Alembic plan), contracts/openapi.yaml (OpenAPI 3.1, all new endpoints), quickstart.md (local dev including WP mock).

Identified 3 constitutional deviations requiring ADRs:
- ADR-002: `wp_user_id` as identity anchor (vs visitor_id only — VI.1)
- ADR-003: Persist full chat messages (vs summary-only — VI.2)
- ADR-004: Redis sliding-window rate limiter (restores IX.3)
- ADR-005: Neon Serverless Postgres as primary OLTP

## Outcome

- ✅ Impact: Phase 2 design complete. All NEEDS CLARIFICATION resolved in research.md. Ready for `/sp.tasks` to generate atomic task list.
- 🧪 Tests: None in this phase (design only). Test plan documented in plan.md §Phase 2 Group G.
- 📁 Files: 5 spec artifacts created; CLAUDE.md updated with new tech stack markers.
- 🔁 Next prompts:
  1. `/sp.adr wp-identity-anchor` (ADR-002)
  2. `/sp.adr persist-full-chat-messages` (ADR-003)
  3. `/sp.adr redis-sliding-window-rate-limit` (ADR-004)
  4. `/sp.adr neon-serverless-postgres` (ADR-005)
  5. `/sp.tasks` to generate implementation task list
- 🧠 Reflection: User provided WordPress + Neon constraints late in the conversation, which changed the identity architecture significantly. Good that we captured this before starting implementation — would have been costly to rip out a visitor_id-first design later.

## Evaluation notes (flywheel)

- Failure modes observed: Initial plan template lacked a "integration with existing deployment" section; improvised by adding explicit deploy-slice strategy in research.md §7.
- Graders run and results (PASS/FAIL): N/A — design artifact only.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): After `/sp.tasks`, verify each task group can be independently deployed behind a feature flag (research.md §7 claim).
