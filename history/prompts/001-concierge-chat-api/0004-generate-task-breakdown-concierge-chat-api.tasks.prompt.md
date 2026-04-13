---
id: "0004"
title: Generate Task Breakdown Concierge Chat API
stage: tasks
date: 2026-04-14
surface: agent
model: claude-haiku-4-5-20251001
feature: 001-concierge-chat-api
branch: 001-concierge-chat-api
user: HasnainCodeHub
command: /sp.tasks
labels: ["tasks","breakdown","user-stories","phase-breakdown","atomic-tasks","p1-p2-p3"]
links:
  spec: specs/001-concierge-chat-api/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-concierge-chat-api/tasks.md
tests:
  - none
---

## Prompt

/sp.tasks

(Generate comprehensive task breakdown from plan.md and spec.md, organized by user story and phase.)

## Response snapshot

Generated `specs/001-concierge-chat-api/tasks.md` with:

- **Total Tasks**: ~87 atomic, executable tasks
- **Phases**: 7 phases (Setup → Foundational → 4 User Stories → Hardening)
- **User Stories**: 4 stories (P1, P2, P2, P3) with independent test criteria
- **Task Format**: Strict markdown checklist with Task ID, [P] parallelization flag, [Story] label (where applicable), file paths
- **MVP Scope**: Phase 1–5 (~45 tasks) delivers core chat + routing + RAG
- **Post-MVP**: Phase 6–7 (~20 tasks) adds context awareness + hardening

**Phase Breakdown**:
- Phase 1 (Setup): 6 tasks — project structure, dependencies, Docker, pytest
- Phase 2 (Foundational): 12 tasks — models, config, base classes, shared services
- Phase 3 (US1 Basic Chat): 13 tasks — API endpoint, orchestrator, prompt builder, AI client, general skill
- Phase 4 (US2 Skill Routing): 15 tasks — hybrid classifier, 5 skills, skill router, routing tests
- Phase 5 (US3 RAG): 12 tasks — RAG service, chunk retrieval, orchestrator integration, tests
- Phase 6 (US4 Context): 6 tasks — context validation, truncation, prompt integration, tests
- Phase 7 (Hardening): 21 tasks — retry+fallback, injection detection, logging, test UI (Next.js), comprehensive testing

**Parallel Opportunities**:
- Phase 4: 5 skill implementations (T037–T041) runnable in parallel
- Phase 3–7: Test writing parallelizable with implementation
- Phase 7: Test UI development (T075–T081) parallelizable with failure handling (T065–T074)

**Dependencies**:
- Phase 1 → Phase 2 (blocking)
- Phase 2 → Phase 3 (blocking)
- Phase 3 → Phase 4, 5, 6 (all depend on US1 API working)
- Phases 4, 5, 6 can proceed in parallel after Phase 3 complete

**Quality Gates**:
- Before US1 merge: 100% tests pass, POST /chat returns valid response
- Before US2 merge: Routing latency <100–200ms, all 5 skills callable
- Before US3 merge: RAG tested, zero hallucination
- Before release: All MVP tests pass, <4s p95 SLA met, no secrets leaked

## Outcome

- ✅ Impact: Executable task breakdown (87 tasks) organized by user story, priority, and dependency. Every task is atomic, testable, and references exact file paths. Enables concurrent implementation of phases and parallel work within phases.
- 🧪 Tests: Task format validation — 100% of tasks follow checklist format with ID, [P], [Story] label (where applicable), and file paths. All user stories have independent test criteria.
- 📁 Files: `specs/001-concierge-chat-api/tasks.md` (created).
- 🔁 Next prompts: `/sp.implement` (when ready) to execute task breakdown; or user can directly begin implementation using tasks.md as guide.
- 🧠 Reflection: Task breakdown cleanly separates setup/foundational work from user-story-driven implementation. MVP scope (Phases 1–5, ~45 tasks) is aggressive but achievable in 2–3 weeks with parallel effort. Post-MVP (Phases 6–7) adds context + hardening without blocking MVP release. Test UI is deliberately minimal (zero business logic) to remain removable and not distract from backend core.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Task format validation — PASS (all 87 tasks follow checklist format)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Pick Phase 3 (US1 Basic Chat) and implement first 3 tasks (T019–T021) in parallel; measure velocity to refine estimate for remaining phases.
