# Tasks: AI Concierge Backend — Chat Intelligence

**Branch**: `001-concierge-chat-api` | **Date**: 2026-04-14 | **Plan**: [plan.md](plan.md)  
**Total Tasks**: ~65 | **Estimated Duration**: Phase 1 (2–3 weeks)

---

## Implementation Strategy

**MVP Scope (Phase 3–5)**: User Stories 1, 2, 3 (P1 + P2) — delivers basic chat with skill routing and RAG grounding. ~45 tasks.

**Post-MVP (Phase 6–7)**: User Story 4 (P3), Polish, Tests — adds context awareness and production hardening. ~20 tasks.

**Phase 1–2 (Setup + Foundational)**: All stories depend on these; complete first. ~5–8 tasks.

---

## Phase 1: Setup & Project Initialization

Initialize project structure, dependencies, and core configuration files.

- [ ] T001 Create project directory structure per implementation plan (`backend/`, `ui/`, `tests/`, `app/` subdirs)
- [ ] T002 Create Python virtual environment and initialize `requirements.txt` with dependencies (FastAPI, OpenAI SDK, Qdrant, Pydantic, httpx, pytest)
- [ ] T003 Create `.env.example` with required environment variables (OPENAI_API_KEY, QDRANT_URL, LOG_LEVEL, CHAT_TIMEOUT_SECONDS)
- [ ] T004 Set up FastAPI application entry point (`backend/app/main.py`) with CORS, logging, exception handlers
- [ ] T005 Initialize Docker setup (`Dockerfile`, `docker-compose.yml`) for local development
- [ ] T006 Create pytest configuration (`conftest.py`, fixtures for async FastAPI testing)

**Phase 1 Acceptance**: All imports resolve, `python -m pytest` discovers tests, `docker-compose up` starts backend on localhost:8000

---

## Phase 2: Foundational Components & Shared Infrastructure

Build reusable base classes, shared models, and configuration infrastructure required by all user stories.

### Models & Schemas

- [ ] T007 Create Pydantic models in `backend/app/models/schemas.py`: ChatRequest, ChatResponse, ErrorResponse
  - ChatRequest: message (string, max 5000), context (optional list, max 15)
  - ChatResponse: reply (string), metadata (optional: intent, skill, latency_ms, routing_source)
  - ErrorResponse: error (string), code (int)
- [ ] T008 Create error entity models in `backend/app/models/errors.py`: ValidationError, RAGUnavailable, AITimeout, ToolError

### Configuration & Prompts

- [ ] T009 Create settings loader in `backend/app/config/settings.py`: load env vars, validate required keys, provide defaults
- [ ] T010 Create system prompt and skill templates in `backend/app/config/prompts.py`: system_prompt, skill_prompts (dict), fallback_response
- [ ] T011 Create routing rules configuration in `backend/app/config/routing_rules.yaml`: keyword patterns for product, compare, noor, bespoke, general
- [ ] T012 Create skill registry in `backend/app/config/skills_registry.py`: Skill dataclass with name, prompt, use_rag, allow_tool, output_schema

### Base Classes & Interfaces

- [ ] T013 Create Skill base class in `backend/app/skills/base.py`: name, prompt_template, use_rag, allow_tool, output_schema
- [ ] T014 Create logging utilities in `backend/app/utils/logging.py`: structured JSON logging, request_id tracing, component-level logging

### Services: Clients & Utilities

- [ ] T015 Create embedding client wrapper in `backend/app/services/embedding_client.py`: OpenAI embeddings API call, caching optional
- [ ] T016 Create Qdrant client wrapper in `backend/app/services/rag_service.py`: connection mgmt, search method (not retrieval logic yet)
- [ ] T017 Create input validators in `backend/app/utils/validators.py`: sanitize_input(), detect_prompt_injection(), validate_context()
- [ ] T018 Create failure handler skeleton in `backend/app/services/failure_handler.py`: exception classification, retry logic placeholders

**Phase 2 Acceptance**: All models instantiate correctly, config loads from env, routing rules parse from YAML, logging outputs JSON, no import errors

---

## Phase 3: User Story 1 — Basic Chat Interaction (P1)

Deliver the core chat loop: accept message, return reply. Fulfills FR-001, FR-002, FR-004, FR-007, FR-010, FR-011, FR-012, FR-014.

### API Endpoint

- [ ] T019 [US1] Create POST `/chat` endpoint in `backend/app/api/routes.py`: accept ChatRequest, validate, call orchestrator, return ChatResponse
- [ ] T020 [US1] Implement request validation middleware in `/chat`: call validators.sanitize_input(), check message not empty/too long, validate context array format
- [ ] T021 [US1] Implement error response transformation in `/chat`: catch exceptions, map to ErrorResponse (400, 500, 503), ensure no stack traces leaked

### Core Orchestration

- [ ] T022 [US1] Create orchestrator in `backend/app/core/orchestrator.py`: main chat handler, receives validated ChatRequest, delegates to downstream components
- [ ] T023 [US1] Implement basic prompt builder in `backend/app/core/prompt_builder.py`: assemble system_prompt + generic skill prompt + user message, no RAG yet
- [ ] T024 [US1] Create AI client wrapper in `backend/app/services/ai_client.py`: async call to OpenAI Responses API (gpt-4.1), extract reply, basic error handling
- [ ] T025 [US1] Implement request timeout in orchestrator: enforce 4-second total latency via async timeout context manager

### Skill Layer (Minimal for US1)

- [ ] T026 [US1] Create general skill in `backend/app/skills/general.py`: fallback skill, use_rag=False, minimal prompt
- [ ] T027 [US1] Create skill selector logic in orchestrator: hardcode general skill selection for US1 (routing comes in US2)

### Integration & Testing

- [ ] T028 [P] [US1] Create unit test file `backend/tests/unit/test_orchestrator.py`: test basic request → response flow
- [ ] T029 [P] [US1] Create integration test `backend/tests/integration/test_api_endpoint.py`: POST /chat with valid message, verify 200 + reply in response
- [ ] T030 [US1] Create contract test `backend/tests/contracts/test_api_schema.py`: validate response matches ChatResponse schema
- [ ] T031 [US1] Manual test with curl: `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"hello"}'`

**US1 Acceptance Criteria**:
- ✅ POST /chat accepts valid message, returns reply within 3 seconds (SC-001, SC-002)
- ✅ Empty message returns 400 error (FR-002)
- ✅ Valid message returns 200 + well-formed JSON reply (FR-001)
- ✅ No API keys or stack traces in response (FR-011)
- ✅ Async I/O throughout (FR-014)

**US1 Independent Test**: `POST /chat {"message":"hello"}` → `{"reply":"..."} 200` within 3s

---

## Phase 4: User Story 2 — Skill-Based Response Routing (P2)

Implement hybrid rule-based + LLM fallback routing. Fulfills FR-003, FR-003a, FR-018, FR-019, FR-020.

### Intent Classifier (Hybrid)

- [ ] T032 [US2] Create rule-based classifier in `backend/app/core/intent_classifier.py`: load routing_rules.yaml, check message keywords/patterns in order (product → compare → noor → bespoke → general)
- [ ] T033 [US2] Implement LLM fallback in intent_classifier: if no rule match, call OpenAI with minimal prompt `"Classify intent into: product, compare, noor, bespoke, general. Return JSON: {intent:..., confidence:...}"`, temp=0
- [ ] T034 [US2] Add routing decision logging in intent_classifier: log (source: "rule"|"llm", intent, confidence, latency_ms)
- [ ] T035 [US2] Implement latency enforcement in intent_classifier: ensure total routing time <100–200ms (timeout on LLM after 200ms)

### Skill Router & Skill Implementations

- [ ] T036 [US2] Create skill router in `backend/app/core/orchestrator.py` (or separate module): receive (intent, confidence) from classifier, select skill from registry, verify skill exists
- [ ] T037 [P] [US2] Create product skill in `backend/app/skills/product.py`: name="product", use_rag=True, prompt template for product inquiries
- [ ] T038 [P] [US2] Create compare skill in `backend/app/skills/compare.py`: name="compare", use_rag=True, prompt template for comparisons
- [ ] T039 [P] [US2] Create noor skill in `backend/app/skills/noor.py`: name="noor", use_rag=False, intent-only stub, acknowledgment reply
- [ ] T040 [P] [US2] Create bespoke skill in `backend/app/skills/bespoke.py`: name="bespoke", use_rag=True, flexible prompt template for custom requests
- [ ] T041 [US2] Update general skill in `backend/app/skills/general.py`: verify as fallback, use_rag=False, generic prompt

### Prompt Builder Update

- [ ] T042 [US2] Update prompt builder in `backend/app/core/prompt_builder.py`: accept skill context (name, prompt_template, use_rag), assemble system + skill + user message

### Integration & Testing

- [ ] T043 [P] [US2] Create unit test `backend/tests/unit/test_intent_classifier.py`: test rule-based routing for each skill, test LLM fallback, test latency
- [ ] T044 [P] [US2] Create unit test `backend/tests/unit/test_skills.py`: instantiate each skill, verify prompts are populated
- [ ] T045 [US2] Create integration test `backend/tests/integration/test_skill_routing.py`: send messages targeting each skill intent, verify correct skill selected
- [ ] T046 [US2] Manual test: send message "compare X and Y" → verify compare skill invoked, send "tell me about noor" → verify noor skill invoked

**US2 Acceptance Criteria**:
- ✅ Rule-based routing: message with keyword → correct skill (SC-003: 90% accuracy target)
- ✅ LLM fallback: ambiguous message → LLM classifier invoked, returns structured JSON
- ✅ Routing decision logged (source + intent) for observability (FR-019)
- ✅ Total routing latency <100–200ms (FR-020)
- ✅ All 5 skills callable without error

**US2 Independent Test**: Send 5 intent-distinct messages (product, compare, noor, bespoke, general) → verify each routes to correct skill (via logs)

---

## Phase 5: User Story 3 — RAG-Grounded Responses (P2)

Integrate vector store retrieval. Fulfills FR-005, FR-006, FR-008, FR-009.

### RAG Service Implementation

- [ ] T047 [US3] Implement full RAG retrieval in `backend/app/services/rag_service.py`: query method (message → embedding → Qdrant search top_k=3)
- [ ] T048 [US3] Add timeout to RAG retrieval: enforce 500ms timeout; on timeout, return empty list (graceful degradation)
- [ ] T049 [US3] Create RAGChunk model in `backend/app/models/schemas.py`: content, source, relevance_score
- [ ] T050 [US3] Implement RAG failure handling in failure_handler: if RAG times out/fails, orchestrator continues without RAG chunks (FR-009)

### Prompt Builder Update for RAG

- [ ] T051 [US3] Update prompt builder: if skill.use_rag and chunks available, inject top_k=3 chunks into prompt context with preamble "Based on the following context: [chunks]..."
- [ ] T052 [US3] Implement RAG bypass: if no chunks found or RAG disabled, continue without RAG (safe fallback per FR-008)

### Orchestrator Integration

- [ ] T053 [US3] Update orchestrator: after skill selection, if skill.use_rag, call RAG service with current message
- [ ] T054 [US3] Pass RAG chunks to prompt builder along with skill context

### Integration & Testing

- [ ] T055 [P] [US3] Create unit test `backend/tests/unit/test_rag_service.py`: mock Qdrant, test search logic, test timeout behavior
- [ ] T056 [US3] Create integration test `backend/tests/integration/test_rag_integration.py`: real Qdrant instance (docker), verify retrieval works
- [ ] T057 [US3] Create integration test `backend/tests/integration/test_orchestrator_full.py`: end-to-end request with RAG enabled
- [ ] T058 [US3] Manual test: send factual query → verify reply includes references to RAG chunks

**US3 Acceptance Criteria**:
- ✅ Factual query → retrieves up to 3 chunks (FR-005)
- ✅ Reply grounded in retrieved chunks (FR-006, SC-004)
- ✅ No fabricated claims when chunks available (SC-004: zero hallucinations)
- ✅ No chunks found → acknowledge uncertainty (FR-008, SC-004)
- ✅ RAG timeout → graceful continuation without RAG (FR-009, SC-008)

**US3 Independent Test**: Query with known answer in vector store → reply cites retrieved chunks, zero invented facts

---

## Phase 6: User Story 4 — Short-Term Conversation Context (P3)

Implement conversation context handling. Fulfills FR-007, SC-006.

### Context Management

- [ ] T059 [US4] Implement context validation in orchestrator: verify context array format, max 15 messages, ordered chronologically
- [ ] T060 [US4] Implement context truncation in orchestrator: if context > 15 messages, keep only last 15, log truncation
- [ ] T061 [US4] Update prompt builder: include full conversation context (last 10–15 messages) in prompt, after skill prompt, before current message

### Integration & Testing

- [ ] T062 [US4] Create unit test `backend/tests/unit/test_context_handling.py`: test validation, truncation, ordering
- [ ] T063 [US4] Create integration test `backend/tests/integration/test_conversation_flow.py`: send 3-message sequence, verify context awareness
- [ ] T064 [US4] Manual test: multi-turn conversation → final message answered coherently relative to prior messages

**US4 Acceptance Criteria**:
- ✅ Up to 15 messages in context respected (FR-007, SC-006)
- ✅ >15 messages → oldest truncated (FR-007)
- ✅ First message → fresh context, no stale assumptions (no prior context needed)

**US4 Independent Test**: Send 3-message conversation → final reply coherent with context

---

## Phase 7: Failure Handling, Logging & Hardening

Implement robust failure handling, retry logic, and observability infrastructure.

### Retry & Fallback Logic

- [ ] T065 [P] Create retry logic in ai_client: on OpenAI timeout/error, retry 1–2 times with backoff (200ms, 500ms) (FR-015)
- [ ] T066 [P] Implement fallback response in failure_handler: if retries exhausted, return safe fallback `"I'm temporarily unable to provide a detailed response. Please try again."` (FR-016)
- [ ] T067 Create retry+fallback logging in failure_handler: log each attempt (service, attempt count, error, latency) (FR-017)

### Prompt Injection Detection

- [ ] T068 [P] Implement injection detection in validators.detect_prompt_injection(): heuristic checks (e.g., "ignore previous", "system prompt", "instructions"), log suspicious patterns
- [ ] T069 Integrate injection detection into API endpoint: sanitize input if injection detected, log incident

### Observability & Logging

- [ ] T070 [P] Configure structured JSON logging in logging.py: all components log at INFO level, include request_id, component name, intent, skill, latency_ms
- [ ] T071 Add request_id tracing: generate UUID per request, pass through all components, include in logs and error responses
- [ ] T072 Create log aggregation config (optional): output to stdout for docker, support file rotation

### Error Response Completeness

- [ ] T073 [P] Ensure all error paths return proper ErrorResponse: 400 (validation), 429 (rate limit stub), 500 (internal), 503 (unavailable)
- [ ] T074 Verify no sensitive info in error responses: test error cases, confirm no API keys, prompts, or stack traces leak

### Test UI (Next.js)

- [ ] T075 [P] Initialize Next.js project in `ui/`: package.json, tsconfig, next.config.js
- [ ] T076 [P] Create ChatWindow component in `ui/src/components/ChatWindow.tsx`: display messages (user + assistant), scroll to latest
- [ ] T077 [P] Create ChatInput component in `ui/src/components/ChatInput.tsx`: text input + send button, disable while awaiting
- [ ] T078 [P] Create API service in `ui/src/services/api.ts`: POST /chat wrapper, handle errors
- [ ] T079 [P] Create main page in `ui/src/pages/index.tsx`: render ChatWindow + ChatInput, manage conversation state (in-memory array)
- [ ] T080 Create optional JsonDebugger in `ui/src/components/JsonDebugger.tsx`: show raw response JSON
- [ ] T081 Set up `.env.example` in `ui/`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

### Comprehensive Testing

- [ ] T082 [P] Create end-to-end test suite: successful chat, malformed JSON, empty message, injection attempt, AI timeout, RAG unavailable, context truncation
- [ ] T083 [P] Create performance test: measure p95/p99 latencies, verify ≤3s p95 SLA under simulated load
- [ ] T084 Create contract test: validate all responses match OpenAPI schema

### Documentation & Setup

- [ ] T085 Create `backend/README.md`: setup instructions (venv, pip install, .env, docker-compose up, pytest)
- [ ] T086 Create `ui/README.md`: Next.js setup, dev server, build instructions
- [ ] T087 Create deployment guide (optional for Phase 1): Docker push, cloud hosting notes

**Phase 7 Acceptance**:
- ✅ All error paths return proper responses (400/429/500/503)
- ✅ No sensitive data in responses
- ✅ Structured JSON logging to stdout
- ✅ Request tracing via request_id
- ✅ Test UI runs on localhost:3000, communicates with backend:8000
- ✅ All tests pass (unit, integration, contract, e2e)

---

## Task Dependencies & Parallel Execution

### Dependency Graph

```
Phase 1 (Setup) → Phase 2 (Foundational)
                  ↓
        Phase 3 (US1: Basic Chat) ← Blocking for all
        ↓          ↓
     Phase 4    Phase 4 (US2: Routing) ← Can start after US1
     (US2)      Phase 5 (US3: RAG) ← Can start after US1
     ↓           Phase 6 (US4: Context) ← Can start after US1
  Phase 5
  (US3)
     ↓
  Phase 7 (Hardening)
```

### Parallel Opportunities

**Within Phase 3 (US1)**:
- T028, T029, T030, T031: Tests can run in parallel during T019–T027 implementation

**Within Phase 4 (US2)**:
- T037–T041 (5 skills): Can be implemented in parallel
- T043–T046 (tests): Can start once T032–T034 complete

**Within Phase 5 (US3)**:
- T055–T058: RAG unit tests can start once T047 complete

**Within Phase 7 (Hardening)**:
- T075–T081 (Test UI): Can be developed in parallel with T065–T074 (failure handling)
- T068–T069, T070–T072: Logging can develop in parallel

---

## MVP Scope Summary

**Minimum Viable Product (Phase 1–5)**: ~45 tasks

Delivers:
- ✅ POST /chat endpoint (US1)
- ✅ Skill-based routing with hybrid rule+LLM (US2)
- ✅ RAG integration (US3)
- ✅ Basic failure handling (retry + fallback)
- ✅ Test UI for manual validation

**Does NOT include**:
- ❌ Conversation context (US4) — deferred to post-MVP
- ❌ Advanced logging/tracing — basic logging only
- ❌ Rate limiting — deferred to Phase 2+ infrastructure
- ❌ Production deployment — Docker setup only

---

## Post-MVP Work (Phase 6–7): ~20 tasks

- Phase 6: Conversation context (US4)
- Phase 7: Hardening (error handling, logging, tests, test UI)

---

## Quality Gates

### Before US1 Merge
- ✅ T019–T031 complete
- ✅ 100% tests pass
- ✅ POST /chat returns valid response within 3s
- ✅ No secrets leaked

### Before US2 Merge
- ✅ T032–T046 complete
- ✅ Skill routing tested for all 5 skills
- ✅ Routing latency <100–200ms

### Before US3 Merge
- ✅ T047–T058 complete
- ✅ RAG retrieval tested against real/mocked Qdrant
- ✅ No hallucination in RAG-grounded responses

### Before Release (Phase 1)
- ✅ All Phase 1–5 tasks complete (MVP)
- ✅ All tests pass (unit, integration, contract, e2e)
- ✅ Manual testing with curl + test UI successful
- ✅ Performance benchmarks meet ≤3s p95 SLA
- ✅ No secrets, stack traces, or PII in any response

---
---

# Phase 2: Persistence, WP Auth, Rate Limiting, Noor Allocation

**Date added**: 2026-04-16 | **Plan reference**: plan.md (Phase 2) | **ADRs**: ADR-0001, ADR-0002
**Total Phase 2 tasks**: 78 | **Estimated duration**: 13 working days (can parallelize to ~8 with 2 devs)

**Rollout model**: 5 deploy slices behind feature flags (see research.md §7). Each Group below is an independently deployable slice.

---

## Phase 2-Setup: New Dependencies & Infrastructure

**Goal**: Add all new packages and external service credentials before any Group begins.

- [ ] T100 Update `backend/requirements.txt` with Phase 2 deps: `sqlalchemy[asyncio]==2.0.*`, `asyncpg==0.29.*`, `alembic==1.13.*`, `redis==5.*`, `python-jose[cryptography]==3.3.*`, `resend>=2.0.0`, `slack_sdk==3.*`, `fakeredis[aioredis]` (dev)
- [ ] T101 [P] Extend `backend/.env.example` with all Phase 2 variables per quickstart.md §4 (NEON_DATABASE_URL, REDIS_URL, WP_*, JWT_*, RESEND_API_KEY, RESEND_FROM_EMAIL, CONCIERGE_ALERT_EMAIL, SLACK_WEBHOOK_*, NOOR_COOLDOWN_DAYS, RATE_LIMIT_PER_MIN, REQUEST_TIMEOUT_SECONDS, ENABLE_RATE_LIMIT)
- [ ] T102 [P] Extend `backend/app/config/settings.py` with new Pydantic settings fields, with safe defaults and `ENABLE_RATE_LIMIT=False` default
- [ ] T103 [P] Create `backend/alembic.ini` and `backend/alembic/env.py` wired to `NEON_DATABASE_URL` via async engine
- [ ] T104 Provision Neon project + copy pooled DSN into local `.env`; provision Upstash Redis + copy `rediss://` URL into local `.env`; verify both via `python -c "import asyncio; from app.db.session import engine; asyncio.run(engine.connect())"` and a Redis PING

**Phase 2-Setup Acceptance**: `alembic current` runs without error; `redis.asyncio.Redis.from_url(REDIS_URL).ping()` returns True; env vars validate via Pydantic.

---

## Phase 2-Foundational: Cross-Cutting Infrastructure

**Purpose**: Database session, error envelope, and request context cap — required by every Group below.
**⚠️ BLOCKS**: All Phase 2 Groups.

- [ ] T110 Create `backend/app/db/session.py` — async SQLAlchemy engine + `async_sessionmaker` + `get_session()` FastAPI dependency; pool size 5, statement_cache_size 0 (asyncpg requirement for PgBouncer/pooler compat)
- [ ] T111 [P] Create `backend/app/db/models.py` — SQLAlchemy 2.0 declarative models for all 5 tables per `data-model.md` (User, ChatMessage, Appointment, NoorAllocationRequest, UserActivity). Use `Mapped[...]` typing; `__table_args__` for indexes; CITEXT + UUID types.
- [ ] T112 [P] Create Alembic migration `backend/alembic/versions/0001_initial_schema.py` — `CREATE EXTENSION citext, pgcrypto`, all 5 tables, all indexes, `set_updated_at()` function + triggers per data-model.md §Alembic migration plan
- [ ] T113 Run `alembic upgrade head` against Neon dev branch; verify all 5 tables exist with `\d <table>` via psql
- [ ] T114 [P] Create `backend/app/middleware/error_handler.py` — unified `Error` envelope: catch-all middleware mapping exceptions to `{error, code, retry_after?}`; never leaks stack traces / API keys / prompt text (constitution IX.5)
- [ ] T115 [P] Extend `backend/app/models/schemas.py` — add `cap_context()` Pydantic validator on `ChatRequest.context` enforcing `max_items=15` server-side (truncate to last 15); add new schemas: `WPLoginRequest`, `AuthResponse`, `UserPublic`, `NoorRequestCreate`, `NoorRequestResponse`, `NoorRequest`, `NoorRequestAdmin`, `AdminNoorDecision`
- [ ] T116 [P] Extend `backend/app/models/errors.py` with: `AuthFailure`, `RateLimited`, `CooldownActive`, `NoorPendingConflict`, `DatabaseUnavailable`

**Foundational Acceptance**: `pytest tests/unit/test_schemas.py -k context_cap` passes (caps 20 → 15); `pytest tests/unit/test_error_handler.py` passes (stack traces suppressed); `SELECT 1 FROM users, chat_messages, appointments, noor_allocation_requests, user_activity LIMIT 0` returns 0 rows without error.

**Checkpoint**: Foundational complete — Groups A–G can now proceed (A must complete first; B–F can parallelize after A).

---

## Group A — Foundation Hardening (Slice 1, ~1 day) 🎯 Deploy first

**Goal**: Rate limiter + 15s timeout + history cap live on `/chat`. Restores constitution IX.3 compliance.

**Independent Test**: Fire 6 `/chat` requests in 10s → 6th returns 429 with `Retry-After: 60`. Send a 100-message `context` → server caps to 15 before invoking LLM. Simulate OpenAI 20s delay → server returns 408 with fallback message at 15s mark.

### Tests for Group A

- [ ] T120 [P] [A] Contract test `tests/integration/test_rate_limiter.py::test_429_after_5_requests` — use fakeredis fixture, fire 6, assert 200×5 + 429×1, assert `Retry-After` header
- [ ] T121 [P] [A] Contract test `test_rate_limiter.py::test_redis_down_fail_open` — patch Redis to raise, assert request succeeds with warning logged
- [ ] T122 [P] [A] Contract test `tests/integration/test_timeout.py::test_408_on_slow_openai` — mock orchestrator to sleep 20s, assert 408 at 15s with brand-safe fallback
- [ ] T123 [P] [A] Unit test `tests/unit/test_history_cap.py::test_cap_to_15` — pass 50 messages, assert returned 15 (last 15)

### Implementation for Group A

- [ ] T124 [A] Create `backend/app/middleware/rate_limiter.py` — Redis sliding-window log, `RATE_LIMIT_PER_MIN` (default 5), per-IP key `ratelimit:chat:{ip}`, fail-open on Redis error, gated by `ENABLE_RATE_LIMIT` flag
- [ ] T125 [A] Create `backend/app/middleware/timeout.py` — `asyncio.wait_for` wrapper, 15s, applied to `/chat` only via route decorator (not global middleware)
- [ ] T126 [A] Wire rate_limiter + timeout + error_handler into `backend/app/main.py` in correct order (error_handler outermost, rate_limiter before timeout, timeout wraps handler)
- [ ] T127 [A] Add `FALLBACK_MESSAGE = "There appears to be a temporary delay. Please try again shortly."` constant to `app/config/prompts.py`; use in 429/408/503 responses
- [ ] T128 [A] Extend `backend/app/api/routes.py::chat` to apply `cap_context()` validator explicitly (defense in depth even though schema enforces it)

**Group A Checkpoint**: Enable `ENABLE_RATE_LIMIT=true` in staging, run 10-min load test (100 req/min from single IP), assert: (a) first 5 pass, rest 429, (b) p95 unchanged on passing requests, (c) Redis memory flat under 1MB.

---

## Group B — Persistence Layer (Slice 2, ~1.5 days)

**Goal**: Chat writes persist to Neon (writes only; reads wired in Group D). No user-visible change yet.

**Independent Test**: POST `/chat` as anonymous → 200 reply + row in `chat_messages` with `user_id=NULL`, `visitor_id=<cookie>`, `intent`, `skill`, `routing_source`, `latency_ms`, `rag_chunk_ids` populated.

### Tests for Group B

- [ ] T130 [P] [B] Integration test `tests/integration/test_chat_persistence.py::test_anon_chat_persists` — send 1 message, assert 1 row in `chat_messages` with expected fields
- [ ] T131 [P] [B] Integration test `test_chat_persistence.py::test_db_down_fails_open` — patch session to raise, assert chat still returns 200 with warning logged (persistence is best-effort)
- [ ] T132 [P] [B] Unit test `tests/unit/test_visitor_cookie.py::test_issued_on_first_contact` — no cookie → sets one; has cookie → reuses

### Implementation for Group B

- [ ] T133 [P] [B] Create `backend/app/auth/visitor.py` — signed HTTP-only `visitor_id` cookie (uuid4), `get_or_issue_visitor_id()` FastAPI dependency
- [ ] T134 [P] [B] Create `backend/app/db/repositories/chat_history.py` — `insert_message(session, user_id, visitor_id, session_id, role, content, metadata)`, `get_recent(user_id, n=5)`, `get_last_intent(user_id)`
- [ ] T135 [B] Extend `backend/app/api/routes.py::chat` — after orchestrator returns, schedule `asyncio.create_task(persist_turn(...))` writing both the user message and the assistant reply; never awaited on the response path
- [ ] T136 [B] Create `backend/app/services/persistence_writer.py` — `persist_turn()` helper wrapping DB session + fail-open try/except + structured logging
- [ ] T137 [B] Add `user_activity` write on every turn: `activity_type='chat_message'`, `details={intent, skill, latency_ms}` (async task)

**Group B Checkpoint**: Deploy, send 50 real chat requests, verify 50 × 2 rows in `chat_messages` (user + assistant), zero added latency on `/chat` response path (measure before/after task scheduling).

---

## Group C — WordPress Authentication (Slice 3, ~2 days)

**Goal**: `/v1/auth/wp-login` exchanges WP JWT for our session JWT; `Depends(get_current_user)` available; anonymous→authed merge works.

**Independent Test**: POST `/v1/auth/wp-login` with valid WP token → receive our JWT + user profile; upsert idempotent (same user_id on second call); GET `/v1/auth/me` with Bearer returns profile; expired token → 401. After login, all prior `chat_messages` with matching `visitor_id` have `user_id` filled.

### Tests for Group C

- [ ] T140 [P] [C] Integration test `tests/integration/test_auth_flow.py::test_wp_login_mints_our_jwt` — use `wp_mock`, exchange token, assert our JWT valid + user row created
- [ ] T141 [P] [C] Integration test `test_auth_flow.py::test_idempotent_upsert` — call twice, assert single row, fields updated on 2nd call
- [ ] T142 [P] [C] Integration test `test_auth_flow.py::test_visitor_merge_on_login` — chat anonymously (3 messages), login, assert all 3 rows now have `user_id=<new>`
- [ ] T143 [P] [C] Unit test `tests/unit/test_wp_verifier.py::test_jwks_cache_hit` — first call fetches, second uses cache; TTL expiry forces refetch
- [ ] T144 [P] [C] Unit test `test_wp_verifier.py::test_rejects_invalid_signature` — flipped bit in token → `AuthFailure`

### Implementation for Group C

- [ ] T145 [P] [C] Create `backend/app/auth/wp_verifier.py` — async JWKS fetcher with 10-min in-memory cache, `verify_wp_token(token) -> WPClaims`, validates `iss`, `exp`, signature, tolerates 30s clock skew
- [ ] T146 [P] [C] Create `backend/app/auth/session_jwt.py` — `mint_session_jwt(user_id, wp_user_id, role)` (HS256, 24h exp), `decode_session_jwt(token) -> SessionClaims`
- [ ] T147 [P] [C] Create `backend/app/db/repositories/users.py` — `upsert_from_wp_claims(session, claims)`, `get_by_id(session, user_id)`, `update_last_seen(session, user_id)`
- [ ] T148 [C] Create `backend/app/auth/dependencies.py` — `get_current_user()` FastAPI Depends (required), `get_current_user_optional()` (returns None if no Bearer), `require_role(role)`
- [ ] T149 [C] Create `backend/app/api/auth_routes.py` — POST `/v1/auth/wp-login` (exchange), GET `/v1/auth/me` (profile), POST `/v1/auth/logout` (revoke via Redis blocklist)
- [ ] T150 [C] Implement anonymous→authed merge in `/v1/auth/wp-login`: `UPDATE chat_messages SET user_id=:uid WHERE visitor_id=:vid AND user_id IS NULL` in same transaction as upsert
- [ ] T151 [C] Register `auth_routes` router in `backend/app/main.py`
- [ ] T152 [P] [C] Create `backend/app/scripts/wp_mock.py` — tiny FastAPI mock issuing valid RS256 WP tokens (for offline dev + tests)

**Group C Checkpoint**: Enable in staging with real WP sandbox, confirm login round-trip <300ms p95, JWKS cache hit ratio >99%.

---

## Group D — Personalization (Slice 4, ~1.5 days)

**Goal**: Authenticated `/chat` requests get personalized greeting + last-discussed context injected into system prompt (not into `context` array). Anonymous flow unchanged.

**Independent Test**: Two-session test — session 1 (authed): discuss Noor Collection. Session 2 (same user, new `session_id`): send "hi" → reply references Noor interest naturally ("Welcome back — last time we looked at the Noor Collection. Pick up there, or something new?").

### Tests for Group D

- [ ] T160 [P] [D] Integration test `tests/integration/test_personalization.py::test_returning_user_greeted_with_context` — seed user + 3 prior Noor messages, new session, assert reply references Noor
- [ ] T161 [P] [D] Integration test `test_personalization.py::test_profile_injected_when_available` — user with `skin_tone=cool, style=heritage`, ask "show me something", assert retrieval biased or prompt mentions cool-tone heritage
- [ ] T162 [P] [D] Integration test `test_personalization.py::test_anonymous_unchanged` — anon request, assert no personalization block in prompt
- [ ] T163 [P] [D] Unit test `tests/unit/test_summary_builder.py::test_summarizes_last_n` — 10 messages → compact ≤200-token summary

### Implementation for Group D

- [ ] T164 [P] [D] Create `backend/app/core/personalization.py` — `build_preamble(user, recent_messages) -> str` producing a compact prompt block with: known profile fields, last-discussed intent, any open Noor/appointment request status
- [ ] T165 [P] [D] Create `backend/app/services/summary_cache.py` — per-user LRU cache (in-process, TTL 10min) keyed by `user_id` to avoid re-summarizing on every request
- [ ] T166 [D] Extend `backend/app/core/prompt_builder.py` to accept optional `personalization_preamble` and insert it **between system prompt and RAG context** (never duplicating system prompt content)
- [ ] T167 [D] Extend `backend/app/api/routes.py::chat` to: (1) resolve user via `get_current_user_optional`, (2) if user, fetch profile + recent messages, (3) build preamble, (4) pass to orchestrator
- [ ] T168 [D] Update `backend/app/core/orchestrator.py` to thread `personalization_preamble` through to `prompt_builder`
- [ ] T169 [D] Add profile-update capture in chat: when assistant extracts `age_range` / `skin_tone` / `style_preference` from user messages, call `users.update_profile(user_id, **fields)` async

**Group D Checkpoint**: p95 latency after personalization ≤3.2s (200ms budget for preamble assembly); personalization preamble avg ≤400 tokens.

---

## Group E — Noor Allocation (Slice 5a, ~2 days) 🔴 Client-critical

**Goal**: Full Noor workflow: create request (auth required, cooldown enforced) → concierge notified → admin approves/declines → client notified → cooldown set.

**Independent Test**: Authed user POST `/v1/noor-requests` with valid payload → 201 + `NOR-XXXXXXXX` ref_id + row in `noor_allocation_requests` with `status=pending`. Concierge `PATCH /v1/admin/noor-requests/{id}` with `status=approved` → row updated, `cooldown_until` set to +90 days, user receives approval email. Second request by same user → 409 Cooldown.

### Tests for Group E

- [ ] T170 [P] [E] Integration test `tests/integration/test_noor_workflow.py::test_create_request_ok` — seed user, POST valid payload, assert 201 + row
- [ ] T171 [P] [E] Integration test `test_noor_workflow.py::test_blocks_pending` — user has pending row, POST again, assert 409
- [ ] T172 [P] [E] Integration test `test_noor_workflow.py::test_blocks_cooldown` — user has approved row with `cooldown_until=now+1d`, POST again, assert 409
- [ ] T173 [P] [E] Integration test `test_noor_workflow.py::test_approve_sets_cooldown` — PATCH status=approved, assert `cooldown_until` = `submitted_at + NOOR_COOLDOWN_DAYS`
- [ ] T174 [P] [E] Integration test `test_noor_workflow.py::test_decline_no_cooldown` — PATCH status=declined, POST new request → 201 (no block)
- [ ] T175 [P] [E] Integration test `test_noor_workflow.py::test_anonymous_forbidden` — no Bearer, POST → 401
- [ ] T176 [P] [E] Integration test `test_noor_workflow.py::test_admin_token_required` — PATCH without `X-Admin-Token` → 401

### Implementation for Group E

- [ ] T177 [P] [E] Create `backend/app/db/repositories/noor_requests.py` — `create(session, user_id, payload)`, `user_has_active(session, user_id) -> bool` (cooldown + pending check), `get(id)`, `list(status, limit)`, `review(id, status, notes, reviewer)`
- [ ] T178 [P] [E] Create `backend/app/services/notifications/email.py` — Resend wrapper, `send_client_confirmation(to, template_vars)`, `send_concierge_alert(to, template_vars)`, sync `resend.Emails.send` wrapped via `asyncio.to_thread`
- [ ] T179 [P] [E] Create `backend/app/services/notifications/slack.py` — async webhook client, `notify_noor_request(request, user)`, `notify_appointment(appointment)`
- [ ] T180 [E] Create `backend/app/services/noor_workflow.py` — `create_noor_request(session, user, payload)` (checks cooldown, generates `NOR-XXXXXXXX` ref_id, inserts row, fires email + Slack tasks), `review_request(session, id, decision, reviewer)` (updates status, sets cooldown, fires notifications)
- [ ] T181 [E] Create `backend/app/api/noor_routes.py` — POST `/v1/noor-requests` (Bearer), GET `/v1/noor-requests/me` (Bearer)
- [ ] T182 [E] Create `backend/app/api/admin_routes.py` — GET `/v1/admin/noor-requests`, GET `/v1/admin/noor-requests/{id}`, PATCH `/v1/admin/noor-requests/{id}` — all gated on `X-Admin-Token` == `ADMIN_API_TOKEN`
- [ ] T183 [E] Wire noor_routes + admin_routes into `backend/app/main.py`
- [ ] T184 [E] Update `backend/app/skills/noor.py` — when user's intent is to request Noor, the skill prompts the bot to collect the 5 fields (full_name, purpose, timeline, delivery_location, contact_method+details) conversationally, then call `POST /v1/noor-requests` internally or return a structured payload the orchestrator submits
- [ ] T185 [P] [E] Build the 2 inline HTML templates in `email.py` (`client-confirmation`, `concierge-alert`) and 2 Slack channels (`#noor-requests`, `#appointments`); document template variable schema in `backend/README.md` (Resend has no provider-side dynamic templates — we render HTML in Python)

**Group E Checkpoint**: Run full flow end-to-end with real Resend + Slack sandbox, verify: (a) client gets confirmation email in <30s, (b) `#noor-requests` message in <10s, (c) approve from admin panel → client gets approval email + cooldown set + `user_activity` row for `noor_request_approved`.

---

## Group F — Appointments + Notifications (Slice 5b, ~1 day)

**Goal**: Migrate the existing `/appointment-request` endpoint into `/v1/appointments` with full persistence + concierge notifications. Preserve backward compatibility with the existing unversioned endpoint for one release.

**Independent Test**: POST `/v1/appointments` → 201 + `APT-XXXXXXXX` + DB row + concierge email + Slack notification. GET `/v1/appointments/{ref}` with Bearer → 200 with status. Admin PATCH sets `status=confirmed` + `scheduled_at` + `meeting_link` → client receives confirmation email.

### Tests for Group F

- [ ] T190 [P] [F] Integration test `tests/integration/test_appointment_workflow.py::test_create_and_notify` — POST, assert row + email + Slack (mocked)
- [ ] T191 [P] [F] Integration test `test_appointment_workflow.py::test_status_fetch` — POST + GET by ref, assert status
- [ ] T192 [P] [F] Integration test `test_appointment_workflow.py::test_admin_confirm` — PATCH confirm, assert row updated + client email fired

### Implementation for Group F

- [ ] T193 [P] [F] Create `backend/app/db/repositories/appointments.py` — `create(session, user_id, payload)`, `get_by_ref(ref_id)`, `list(status)`, `confirm(ref_id, scheduled_at, meeting_link, confirmed_by, notes)`, `cancel(ref_id)`
- [ ] T194 [F] Create `backend/app/services/appointment_workflow.py` — `create_appointment()`, `confirm_appointment()`, `cancel_appointment()` — each fires appropriate notifications
- [ ] T195 [F] Create `backend/app/api/appointment_routes.py` — POST `/v1/appointments` (optional auth), GET `/v1/appointments/{ref_id}` (Bearer), extend admin_routes with `/v1/admin/appointments` endpoints
- [ ] T196 [F] Migrate existing `POST /appointment-request` in routes.py to call `appointment_workflow.create_appointment()` — keeps old endpoint working while new one is canonical
- [ ] T197 [F] Deprecate old endpoint in OpenAPI (`deprecated: true`) with sunset notice; keep for one release cycle

**Group F Checkpoint**: End-to-end appointment flow exercised in staging with real WP login + real SendGrid — confirm the concierge team reproduces the intended workflow.

---

## Group G — Test & Harden (Slice 5c, ~1.5 days)

**Goal**: Full suite green, load-tested, chaos-tested, ready for production deploy.

### Tests for Group G

- [ ] T200 [P] [G] Load test `tests/load/test_rate_limit_under_load.py` using `locust` — 100 simulated IPs, 1 req/sec each over 5 min; assert (a) each IP capped at 5/min, (b) backend p95 stays ≤3s for allowed requests
- [ ] T201 [P] [G] Chaos test `tests/chaos/test_degraded_modes.py` — simulate (1) Redis down, (2) Neon down, (3) OpenAI timeout, (4) Qdrant timeout, (5) Resend 500; assert system returns brand-safe fallback in each case and does not crash
- [ ] T202 [P] [G] End-to-end journey test `tests/e2e/test_full_user_journey.py` — anonymous → chat → profile question → login → Noor request → admin approve → second chat session → personalized greeting
- [ ] T203 [P] [G] Security test `tests/security/test_no_leaks.py` — 50 known prompt-injection payloads + 10 error-triggering requests; assert: no API key, no stack trace, no system prompt fragment, no admin token in any response body
- [ ] T204 [P] [G] Data privacy check `tests/security/test_pii_handling.py` — user deletion test: set `users.status='deleted'`, assert logs contain no raw PII after deletion; verify `chat_messages.user_id` is soft-nulled

### Implementation for Group G

- [ ] T205 [G] Add Prometheus metrics (or equivalent): `chat_requests_total`, `chat_latency_seconds` histogram, `rate_limit_hits_total`, `openai_errors_total`, `neon_errors_total`, `notification_failures_total`
- [ ] T206 [G] Add `/metrics` endpoint (gated by internal network only / admin token)
- [ ] T207 [G] Update `backend/app/utils/logging.py` JSON formatter to always include `request_id`, `user_id` (if authed), `visitor_id`, `route`, `latency_ms`, `intent`, `skill`
- [ ] T208 [G] Update `backend/README.md` with Phase 2 architecture diagram, env var reference, and deploy runbook
- [ ] T209 [G] Update `docker-compose.yml` with postgres + redis + wp_mock local services (mirrors quickstart.md §10)
- [ ] T210 [G] Create `backend/Dockerfile.prod` multi-stage build (builder + runtime, non-root user, no dev deps)
- [ ] T211 [G] Remove `ENABLE_RATE_LIMIT` feature flag after full rollout; rate limiter always-on in main

**Group G Checkpoint**: All tests green; staging load test passes; security test passes; documentation updated; ready for production cut.

---

## Phase 2 Dependencies & Execution Order

### Slice Dependencies

```
Phase 2-Setup (T100–T104)
        │
        ▼
Phase 2-Foundational (T110–T116)
        │
        ▼
   Group A (T120–T128)  ← MUST complete first (rate limit blocks everything from going wild)
        │
        ├──────────────────────┐
        ▼                      ▼
   Group B (T130–T137)    (Group C can start as soon as A is done)
        │                      │
        ▼                      ▼
   Group D (T160–T169)    Group C (T140–T152)
   [D needs B + C]    ◄──────┘
        │
        ▼
   Group E (T170–T185)  [E needs C for auth]
        │
        ▼
   Group F (T190–T197)  [F reuses E's notification services]
        │
        ▼
   Group G (T200–T211)  [G gates production deploy]
```

### Parallel opportunities within Phase 2

- **Within Phase 2-Setup**: T101, T102, T103 parallel (after T100 package install)
- **Within Foundational**: T111, T112, T114, T115, T116 parallel (different files)
- **Within Group A**: all tests T120–T123 parallel; implementation T124/T125 parallel
- **Within Group B**: T133, T134 parallel
- **Within Group C**: T145, T146, T147, T152 parallel
- **Within Group D**: T164, T165 parallel
- **Within Group E**: T177, T178, T179, T185 parallel
- **Groups C and B can proceed in parallel** once Group A is deployed
- **Group F can start as soon as Group E's notification services (T178, T179) are done** — doesn't need rest of E

### Independent delivery checkpoints

Each group is an independently deployable slice. Stop after any group to:
- Validate behavior in staging
- Gather feedback
- Decide whether to proceed

---

## Phase 2 Acceptance Criteria

### Before Each Group Merge

- ✅ All group tests green
- ✅ No regression in Phase 1 tests
- ✅ p95 latency ≤3s under nominal load
- ✅ No secrets / stack traces in error paths
- ✅ Structured logs have `request_id` + `user_id` (where available)

### Before Phase 2 Release

- ✅ T100–T211 complete (78 tasks)
- ✅ ADR-0001 and ADR-0002 marked `Accepted`
- ✅ Load test T200 passes: 100 IPs × 5 min, zero crashes, rate-limit correct
- ✅ Chaos test T201 passes: all 5 degradation modes return brand-safe fallbacks
- ✅ Security test T203 passes: zero leaks across 50+ payloads
- ✅ Staging soak test: 24h continuous light traffic, no memory leaks
- ✅ Client walkthrough: concierge team exercises admin flow end-to-end and signs off
- ✅ Runbook documented: how to respond to (a) rate limit false positive, (b) Neon outage, (c) WP auth outage, (d) Resend quota exceeded

