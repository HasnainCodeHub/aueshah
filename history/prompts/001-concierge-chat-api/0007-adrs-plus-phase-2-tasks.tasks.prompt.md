---
id: "0007"
title: ADRs + Phase 2 Tasks
stage: tasks
date: 2026-04-16
surface: agent
model: claude-opus-4-6
feature: 001-concierge-chat-api
branch: 001-concierge-chat-api
user: HasnainCodeHub
command: /sp.plan (continuation)
labels: [adr, tasks, phase-2, wp-auth, neon, rate-limit, noor-allocation]
links:
  spec: specs/001-concierge-chat-api/spec.md
  ticket: null
  adr: history/adr/0001-persistence-and-identity-wordpress-jwt-auth-plus-neon-serverless-postgres-with-chat-history.md, history/adr/0002-production-hardening-rate-limit-plus-timeout-plus-error-envelope.md
  pr: null
files:
  - history/adr/0001-persistence-and-identity-wordpress-jwt-auth-plus-neon-serverless-postgres-with-chat-history.md
  - history/adr/0002-production-hardening-rate-limit-plus-timeout-plus-error-envelope.md
  - specs/001-concierge-chat-api/tasks.md
tests:
  - (design phase — 78 test tasks defined in tasks.md, none executed yet)
---

## Prompt

okay execute what is best i just want best of the best

## Response snapshot

User approved autonomous execution of the "best" path after plan completion. Executed three follow-on artifacts:

1. **ADR-0001** (Persistence & Identity cluster): WordPress JWT auth + Neon Serverless Postgres + persisted chat history. Documents 2 deliberate deviations from constitution (VI.1 `wp_user_id` replaces `visitor_id`-only; VI.2 full messages persisted). 6 alternatives considered and rejected with reasons.

2. **ADR-0002** (Production Hardening cluster): Redis sliding-window rate limiter (5 req/min/IP) + 15s timeout + unified error envelope. Restores constitution IX.3 compliance. 7 alternatives considered.

3. **tasks.md Phase 2 extension**: 78 atomic tasks across Phase 2-Setup, Phase 2-Foundational, and Groups A–G, each ≤4 hours, labeled with task ID, parallel marker, and group. Dependency graph makes A a hard blocker (must deploy first) and allows B+C to parallelize after A. Each Group is an independently deployable slice with its own checkpoint.

Clustered 4 originally-proposed ADRs into 2 per template guidance ("document decision clusters, not individual technology choices"). Did not begin implementation — user's prior directive "don't commit anything until I say" still in effect.

## Outcome

- ✅ Impact: Phase 2 is now fully specified end-to-end: plan.md + research.md + data-model.md + contracts/ + quickstart.md + tasks.md + 2 ADRs. Ready to start implementation on user's green light.
- 🧪 Tests: None executed. 78 tasks defined in tasks.md include explicit test tasks at each group (TDD-friendly).
- 📁 Files: 3 new artifacts created; tasks.md extended (Phase 1 section preserved intact).
- 🔁 Next prompts:
  1. User review of ADRs — set Status from `Proposed` to `Accepted` or request revisions
  2. User provisions cloud accounts (Neon, Upstash, SendGrid, Slack) per quickstart.md §2–§4
  3. Begin implementation: "Start Group A" → execute T100–T128 (Phase 2-Setup + Foundational + Group A) in ~1–2 working days
- 🧠 Reflection: User gave high-autonomy prompt ("best of the best") but prior context clearly restricted commits. The right interpretation was to push design artifacts to completion, stop at the implementation boundary. Resisted urge to start coding Group A — implementation needs user-provisioned cloud credentials (Neon DSN, Upstash URL) before it can be tested, so starting would have blocked on a dependency.

## Evaluation notes (flywheel)

- Failure modes observed: None in this batch. Template for ADR required manual `Read` + `Write` (placeholder token `{{ID}}` in freshly-created file trips Edit safety).
- Graders run and results (PASS/FAIL): N/A (design artifacts).
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): First implementation slice (Group A) should be executed and measured — rate limiter overhead prediction was ~3–5ms; validate that empirically on Upstash US-East-2.
