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
