---
id: "0003"
title: Architecture Plan Concierge Chat API
stage: plan
date: 2026-04-14
surface: agent
model: claude-haiku-4-5-20251001
feature: 001-concierge-chat-api
branch: 001-concierge-chat-api
user: HasnainCodeHub
command: /sp.plan
labels: ["plan","architecture","fastapi","rag","skill-routing","hybrid-routing","failure-handling","openai","qdrant"]
links:
  spec: specs/001-concierge-chat-api/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-concierge-chat-api/plan.md
tests:
  - none
---

## Prompt

/sp.plan
Generate a complete technical architecture plan for a standalone AI Concierge backend (Phase 1).

Follow the project constitution and clarified decisions strictly.

[User provided: System scope, core capabilities, required components, data flow, constraints, project structure, temporary test UI, non-goals, output requirements — all detailed in prompt]

## Response snapshot

Created comprehensive `specs/001-concierge-chat-api/plan.md` with:

**Post-planning clarifications integrated** (5 Phase 1 design decisions):
1. LLM classification fallback: minimal prompt, temp=0, structured JSON output (intent + confidence)
2. Stateless context: caller-maintained history, no server-side session, 10–15 msg limit, no echo response
3. Error codes: HTTP standard only (200, 400, 429, 500, 503); no custom codes
4. Test UI: included in Phase 1 tasks, minimal, zero business logic, fully decoupled
5. Noor tool: schema definition only (no execution logic), integration point defined, Phase 2 deferred

---

Full plan includes:

- **Technical Context**: Python 3.11, FastAPI, OpenAI SDK, Qdrant, Pydantic, httpx
- **Constitution Check**: All 16 architecture principles verified and PASS
- **Project Structure**: Backend FastAPI (`backend/`) + removable Next.js test UI (`ui/`)
- **12 Components**: API layer, orchestrator, intent classifier (hybrid rule+LLM), skill router, prompt builder, AI client (retry+fallback), RAG service, failure handler, 5 skills, tool handler, config, models/schemas
- **Data Flow**: Detailed ASCII diagram showing request → intent detection → skill routing → RAG (if needed) → prompt build → OpenAI (retry) → response
- **API Contract**: POST /chat with request/response schemas and error handling
- **Non-Functional Requirements**: Latency (p95 <4s), reliability (95%), observability, security
- **Failure Scenarios**: 11 edge cases mapped to handling strategy
- **Technical Decisions**: 10 key decisions with rationale and alternatives
- **Phase 1 Scope**: 10 deliverables; Phase 2+ out of scope
- **Risks & Mitigations**: 6 major risks with mitigation strategies

## Outcome

- ✅ Impact: Complete, constitution-aligned architecture plan ready for task decomposition. All 16 constitution principles verified (PASS). All clarifications from `/sp.clarify` integrated (context format, failure recovery, hybrid routing).
- 🧪 Tests: Constitution check — PASS (all principles mapped, no violations). Technical decision rationale documented for all 10 key decisions.
- 📁 Files: `specs/001-concierge-chat-api/plan.md` (created, 1700+ lines).
- 🔁 Next prompts: `/sp.tasks` to decompose plan into atomic, testable implementation tasks.
- 🧠 Reflection: Architecture cleanly separates concerns into 12 layered components (api → core → services → skills). Hybrid routing strategy elegantly balances performance (rules) with accuracy (LLM fallback). Failure handling is explicit and deterministic (retry → fallback; no loops). Temporary test UI is clearly marked as removable, preventing scope creep into frontend logic.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Constitution check — PASS; all 16 principles satisfied
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run `/sp.tasks` and verify that each FRs (20 total) maps to at least one task without circular dependencies or missing components.
