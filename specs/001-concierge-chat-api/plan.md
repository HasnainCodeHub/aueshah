# Implementation Plan: AI Concierge Backend — Chat Intelligence

**Branch**: `001-concierge-chat-api` | **Date**: 2026-04-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-concierge-chat-api/spec.md`

---

## Summary

Build a stateless, controlled AI concierge backend (FastAPI) with hybrid skill routing, RAG-grounded responses, and graceful failure handling. The system accepts chat messages with optional conversation context, classifies intent via rule-based routing + LLM fallback, retrieves up to 3 relevant knowledge chunks, constructs a multi-prompt (system + skill + RAG + context), calls OpenAI Responses API (gpt-4.1), and returns a structured reply. On failure, retry 1–2 times with backoff; if still unavailable, return a safe fallback response. Include a temporary Next.js test UI (removable, no business logic).

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (async web framework), OpenAI Python SDK (gpt-4.1 Responses API), Qdrant Python client (vector search), Pydantic (validation), httpx (async HTTP)  
**Storage**: Qdrant (vector store, pre-populated); Neon/PostgreSQL optional for Phase 2 persistence  
**Testing**: pytest, pytest-asyncio, httpx test client  
**Target Platform**: Linux/Docker container (cloud-ready)  
**Project Type**: Backend (Python FastAPI) + temporary frontend test UI (Next.js)  
**Performance Goals**: 3 seconds p95 end-to-end latency; 95% success rate under normal load  
**Constraints**: No authentication, no persistent session state, stateless API, <100–200ms skill routing latency, p95 ≤3 second end-to-end latency  
**Scale/Scope**: Phase 1 single-user load (~1–10 concurrent requests during testing)

---

## Constitution Check

**GATE: Must pass before Phase 1 design. Re-check after implementation.**

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **Backend-first** | All logic in FastAPI; test UI is external client only | ✅ Clear | Next.js UI has no business logic; all AI, routing, RAG on backend |
| **Separation of Concerns** | api/ → services/ → skills/, rag/, db/; no cross-layer leakage | ✅ Clear | Layered structure defined below; layer boundaries explicit |
| **Stateless API** | Context passed explicitly in request; no server-side session state | ✅ Clear | Conversation context in request body (JSON array); no session cookies |
| **All AI calls server-side** | OpenAI keys, prompts, tool schemas never reach client | ✅ Clear | Keys in env vars; prompts in backend config; no client-side AI calls |
| **Async-first** | All I/O (DB, OpenAI, Qdrant) via async/await; no blocking calls | ✅ Clear | FastAPI async handlers; httpx async client; async Qdrant calls; async DB if added |
| **System prompt = brand brain** | System prompt defines tone/persona/limits; single authority | ✅ Clear | System prompt stored in config; passed to every AI call; immutable |
| **RAG = knowledge layer** | Retrieved chunks ground responses; distinct from system prompt | ✅ Clear | RAG service retrieves top-3 chunks; injected into prompt context |
| **No hallucination** | Never invent catalog data, pricing, availability, people; prefer uncertainty | ✅ Clear | RAG grounding required; fallback response acknowledges limits |
| **Uncertainty > error** | "I don't know" is correct; invented answer is critical failure | ✅ Clear | Fallback response is uncertainty-safe ("temporarily unable...") |
| **Consistent tone** | Controlled, minimal, premium; no verbose/casual/speculative | ✅ Clear | Enforced by system prompt; skill prompts inherit tone |
| **Skills & routing** | All behaviors routed through 5 named skills; explicit, auditable routing | ✅ Clear | Hybrid routing with config-driven rules; skill registry source of truth |
| **Skill modularity** | Each skill is isolated; swappable without affecting others | ✅ Clear | Skill interface (input/output/fallback) defined; decoupled from orchestration |
| **Tooling rules** | Tools explicit, validated, no auto-trigger, deterministic handling | ✅ Clear | Noor tool schema defined; no tool loops; explicit invocation only |
| **Top-k limit** | Max 3–5 chunks per RAG query; no over-retrieval | ✅ Clear | top_k=3 hard limit in RAG service |
| **Retry + fallback** | Retry 1–2 times; then fallback response; log all attempts | ✅ Clear | Retry strategy defined in core orchestration; logging at each step |
| **Noor exclusion** | No auto-indexing of Noor data; manual review + approval required | ✅ Clear | Noted as Phase 1 constraint; Noor skill is stub (intent-only) |

**Gate Result**: ✅ **PASS** — All constitution principles mapped to design; no violations.

---

## Phase 1 Design Clarifications

Explicit decisions made for Phase 1 implementation (2026-04-14):

### 1. LLM Classification Fallback

- **Prompt**: `"Classify the user intent into one of: product, compare, noor, bespoke, general. Return JSON: {intent: ..., confidence: ...}"`
- **Temperature**: 0 (deterministic)
- **Structured Output**: JSON only (intent label + confidence score)
- **No Skill Descriptions**: LLM classifier receives only the user message and list of valid intents
- **Rationale**: Minimal, lightweight, deterministic; no dependency on skill metadata bloat

### 2. Stateless Context Management

- **Caller Responsibility**: API does NOT manage conversation history; caller maintains full context
- **Request Format**: Context passed in request body each time: `{ "message": "...", "context": [history...] }`
- **No Session Cookies**: Stateless API only; no server-side session store
- **Context Limit**: Enforce 10–15 message maximum in orchestrator (truncate older messages)
- **No Echo in Response**: API does NOT return context in response; caller re-sends maintained context on next request
- **Test UI**: Next.js test UI manages chat state locally (in-memory array)

### 3. Error Response Codes

- Use **standard HTTP status codes only**:
  - `200` → Success
  - `400` → Bad request (validation error, injection detected, empty message)
  - `429` → Rate limit (deferred to Phase 2)
  - `500` → Internal server error (unexpected exception)
  - `503` → Service unavailable (AI provider timeout after retries, RAG failure, etc.)
- **No Custom Codes**: Avoid non-standard codes; all errors mapped to 1 of 5 above

### 4. Test UI in Phase 1

- **Include in Tasks**: Next.js test UI is required for Phase 1 validation and testing
- **Minimal Implementation**: ChatInput, ChatWindow, optional JsonDebugger; no styling, no persistence
- **Zero Business Logic**: All logic in backend; UI is pure client
- **Fully Decoupled**: Delete `/ui/` directory; backend continues unaffected
- **Local State Only**: UI manages conversation history in memory (lost on page reload; expected for test UI)

### 5. Noor Tool Phase 1

- **Schema Definition Only**: Include Noor tool schema definition in Phase 1 tasks
- **No Execution Logic**: Do NOT implement tool execution (webhook, function call, etc.) yet
- **Integration Point**: Define where tool execution *would* happen (tool_handler); leave stub/placeholder
- **No Auto-Trigger**: Tool must not be invoked automatically; marked for Phase 2 workflow implementation
- **Skill Remains Stub**: Noor skill detects intent, acknowledges it; no tool invocation in Phase 1

---

## Project Structure

### Documentation (this feature)

```text
specs/001-concierge-chat-api/
├── spec.md              # Clarified feature specification
├── plan.md              # This file (architectural plan)
├── research.md          # (Phase 0 output, if research needed)
├── data-model.md        # Phase 1 output (data entities, schemas)
├── contracts/           # Phase 1 output (API contracts)
│   ├── openapi.yaml     # OpenAPI 3.0 schema for /chat
│   └── errors.md        # Error codes and response structures
├── quickstart.md        # Phase 1 output (dev setup, running locally)
└── checklists/
    └── requirements.md  # Quality checklist (requirements validation)
```

### Source Code (repository root)

```text
backend/                         # FastAPI backend
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entrypoint
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # POST /chat route
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main request orchestrator
│   │   ├── intent_classifier.py # Hybrid rule+LLM routing
│   │   ├── prompt_builder.py   # Multi-prompt construction
│   │   └── tool_handler.py     # Tool invocation (deterministic, no loops)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_client.py        # OpenAI Responses API wrapper
│   │   ├── rag_service.py      # Embedding + Qdrant retrieval
│   │   ├── embedding_client.py # Embedding generation (OpenAI embeddings)
│   │   └── failure_handler.py  # Retry + fallback logic
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── base.py             # Skill base class (interface)
│   │   ├── product.py          # Product skill
│   │   ├── compare.py          # Compare skill
│   │   ├── noor.py             # Noor skill (intent-only stub)
│   │   ├── bespoke.py          # Bespoke skill
│   │   └── general.py          # General/fallback skill
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── entities.py         # Data entities (if persistent store added)
│   │   └── errors.py           # Error response models
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Environment config
│   │   ├── prompts.py          # System prompt, skill prompts, templates
│   │   ├── routing_rules.yaml  # Hybrid routing rules (keywords, patterns)
│   │   └── skills_registry.py  # Skill definitions, metadata
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py          # Structured logging setup
│   │   └── validators.py       # Input sanitization, prompt injection detection
│   └── db/
│       ├── __init__.py
│       └── models.py           # (Optional Phase 2) Neon/PostgreSQL models
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   ├── test_intent_classifier.py
│   │   ├── test_prompt_builder.py
│   │   ├── test_skills.py
│   │   └── test_failure_handler.py
│   ├── integration/
│   │   ├── test_orchestrator.py # End-to-end request flow
│   │   ├── test_api_endpoint.py
│   │   └── test_rag_integration.py
│   └── contracts/
│       └── test_api_schema.py   # OpenAPI schema validation
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker build for backend
└── docker-compose.yml          # Local dev setup

ui/                             # Temporary Next.js test UI (removable)
├── src/
│   ├── components/
│   │   ├── ChatInput.tsx       # Input field + send button
│   │   ├── ChatWindow.tsx      # Message display
│   │   └── JsonDebugger.tsx    # Optional: raw response viewer
│   ├── pages/
│   │   └── index.tsx           # Main chat page
│   ├── services/
│   │   └── api.ts              # Fetch wrapper for /chat endpoint
│   └── styles/
│       └── globals.css         # Minimal styling
├── package.json
├── next.config.js
├── tsconfig.json
├── .env.example                # NEXT_PUBLIC_API_URL
└── README.md                   # Instructions (removable)
```

**Structure Decision**: Backend-first monorepo with FastAPI backend (`backend/`) and removable Next.js test UI (`ui/`). The backend is independently runnable and testable; the UI is a consumer-only client that can be deleted without affecting backend logic.

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Request: POST /chat                                   │
│  Payload: { "message": "Tell me about Product X", "context": [history...] }  │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │  API Layer              │
                        │  ✓ Validate schema      │
                        │  ✓ Sanitize inputs      │
                        │  ✓ Detect injection     │
                        └─────────────┬───────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────────┐
                    │  Intent Classifier (Hybrid Routing)  │
                    │  Step 1: Rule-based keywords/patterns│
                    │  Step 2: If no match → LLM classify  │
                    │  Step 3: Default → general skill     │
                    └─────────────┬────────────────────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │  Skill Selector    │
                         │  Route to skill    │
                         │  (product/compare/ │
                         │   noor/bespoke/    │
                         │   general)         │
                         └────────┬───────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
          ┌─────────▼─────────┐     ┌──────────▼──────────┐
          │  Skill: use_rag?  │     │  Skill: use_tool?   │
          │  YES: retrieve    │     │  YES: define in     │
          │  top_k=3 chunks   │     │  skill schema       │
          │  NO: skip RAG     │     │  (Noor only, Phase1)│
          └────────┬──────────┘     └────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  Prompt Builder                     │
    │  ───────────────────────────────────│
    │  1. System prompt (brand brain)     │
    │  2. Skill prompt (context/role)     │
    │  3. RAG chunks (if available)       │
    │  4. Conversation context (last 15)  │
    │  5. Current message                 │
    │  6. Tool schema (if applicable)     │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────┐
    │  OpenAI Responses API Call          │
    │  (with retry 1–2x + backoff)        │
    │                                     │
    │  Attempt 1: Send prompt             │
    │    → Success? Return response       │
    │    → Timeout/Error? Wait 200ms      │
    │                                     │
    │  Attempt 2: Retry                   │
    │    → Success? Return response       │
    │    → Timeout/Error? Wait 500ms      │
    │                                     │
    │  Attempt 3+: Failed                 │
    │    → Return safe fallback reply     │
    └──────────────┬──────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │  Tool Response Handler (if tool used)│
    │  Deterministic: no loops, explicit   │
    │  fallback if tool fails              │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │  Response Builder                    │
    │  { "reply": "...", "metadata": {...}}│
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │  Logging & Observability             │
    │  - Intent decision (rule/LLM)        │
    │  - Skill selected                    │
    │  - RAG chunks used (if any)          │
    │  - Retries (if any)                  │
    │  - Latency                           │
    │  - Errors (if any)                   │
    └──────────────┬───────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │  Response: POST /chat                │
    │  { "reply": "Based on our..."  }     │
    │  OR                                  │
    │  { "error": "..." } (error case)     │
    └──────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. API Layer (`app/api/routes.py`)

**Responsibility**: HTTP request/response handling, validation, error transformation.

**Scope**:
- Define `POST /chat` endpoint
- Accept `ChatRequest` (message: string, context: optional array)
- Validate payload using Pydantic schemas
- Call orchestrator with request data
- Catch exceptions and transform to `ChatResponse` or error response
- Return 200 on success, 400/500 on error (always structured JSON)

**Dependencies**: Pydantic, FastAPI, orchestrator service

---

### 2. Orchestrator (`app/core/orchestrator.py`)

**Responsibility**: Main request orchestration, flow control, state passing.

**Scope**:
- Receive validated ChatRequest
- Delegate to intent classifier → skill selector → RAG (if needed) → prompt builder → AI client
- Handle orchestration errors (timeouts, missing components)
- Delegate to failure handler on AI client failure
- Return structured ChatResponse (or raise exception for API layer to catch)
- Coordinate logging at each step

**Dependencies**: Intent classifier, skill router, RAG service, prompt builder, AI client, failure handler

---

### 3. Intent Classifier (`app/core/intent_classifier.py`)

**Responsibility**: Hybrid rule-based + LLM-based intent detection.

**Scope**:
- Load routing rules from `config/routing_rules.yaml` (keyword patterns per skill)
- Check message against rules in order: product → compare → noor → bespoke → general
- If no rule match: invoke lightweight LLM classifier (temperature=0, structured output)
- Return (skill_name, confidence, source: "rule"|"llm") tuple
- Log routing decision
- Ensure latency < 100–200ms (rules only ~ 10ms; LLM fallback ~ 200ms)

**Dependencies**: Routing rules config, OpenAI client (for LLM classification fallback), logging

---

### 4. Skill Router

**Responsibility**: Select and invoke the correct skill based on classification.

**Scope**:
- Receive (skill_name, ...) from intent classifier
- Load skill from registry (verify it exists)
- Extract skill metadata (use_rag, allow_tool, prompt template)
- Pass skill context to prompt builder
- No response generation (skill defines only metadata/instructions)

**Dependencies**: Skills registry, logging

---

### 5. Prompt Builder (`app/core/prompt_builder.py`)

**Responsibility**: Construct multi-part prompt for OpenAI call.

**Scope**:
- Receive: system_prompt, skill_prompt, rag_chunks (optional), conversation_context, current_message, tool_schema (optional)
- Assemble in order:
  1. System prompt (brand brain, tone, constraints)
  2. Skill-specific prompt (context, instructions)
  3. RAG chunks (if available): "Based on the following context: [chunks]"
  4. Conversation history (last 10–15 messages)
  5. Current message: "User: {message}"
  6. Tool schema (if tool_call allowed): "Tools available: [schema]"
- Ensure total token count is reasonable (< 4k tokens)
- Return assembled prompt dict for OpenAI API

**Dependencies**: Token counter (tiktoken), logging

---

### 6. AI Client (`app/services/ai_client.py`)

**Responsibility**: OpenAI Responses API wrapper with retry logic.

**Scope**:
- Initialize async httpx client with OpenAI API key
- Call gpt-4.1 Responses API with prompt, temperature=0 (deterministic)
- Handle response: extract reply text
- Detect tool use (if applicable) → delegate to tool handler
- Implement retry logic (1–2 retries, 200ms → 500ms backoff)
- On final failure: raise exception (for failure handler to catch)
- Log all attempts (success, retries, final failure)

**Dependencies**: OpenAI API, httpx, logging, failure handler

---

### 7. RAG Service (`app/services/rag_service.py`)

**Responsibility**: Vector search and chunk retrieval.

**Scope**:
- Receive query (message, optional skill context)
- Generate embedding via embedding client
- Query Qdrant: search with top_k=3, similarity threshold (if any)
- Return list of RAGChunk (content, source, relevance_score)
- Log retrieval metrics (chunks found, relevance scores)
- Timeout: 500ms; if exceeded, return empty list (RAG failure → continue without RAG)

**Dependencies**: Embedding client, Qdrant Python client, logging

---

### 8. Failure Handler (`app/services/failure_handler.py`)

**Responsibility**: Graceful degradation on external service failure.

**Scope**:
- Receive exception from AI client or RAG service
- Classify failure: timeout, rate limit, server error, invalid API key, etc.
- Decision logic:
  - AI client failure (after retries) → return safe fallback reply
  - RAG service failure → continue without RAG (orchestrator retries prompt builder without RAG chunks)
- Return safe response: `{ "reply": "I'm temporarily unable to provide a detailed response. Please try again." }`
- Log failure details (service, error code, attempt count) for ops visibility

**Dependencies**: Logging, error models

---

### 9. Skills Layer (`app/skills/base.py`, `*.py`)

**Responsibility**: Modular, reusable skill definitions.

**Scope**:
- Base class: `Skill(name, prompt_template, use_rag, allow_tool, output_schema)`
- Five skill implementations:
  - **ProductSkill**: RAG-enabled, retrieves product info
  - **CompareSkill**: RAG-enabled, retrieves comparative info
  - **NoorSkill**: Intent-only (Phase 1); tool schema defined but no execution
  - **BespokeSkill**: Custom requests, RAG optional, tool optional
  - **GeneralSkill**: Fallback, minimal RAG, no tools
- Each skill is isolated; swappable without affecting orchestration
- Skill registry stores all skill definitions

**Dependencies**: None (pure data)

---

### 10. Tool Handler (`app/core/tool_handler.py`)

**Responsibility**: Deterministic tool invocation (no loops).

**Scope**:
- Receive tool call from AI response (tool_name, tool_input)
- Validate against skill's allowed tool schema
- Execute tool function (Noor tool in Phase 1: stub that returns acknowledgment)
- Return tool response to AI in a second call (if allowed) OR embed in fallback response
- Ensure no loops: at most 1 tool call per request (no recursive tool use)
- Log tool invocation and outcome

**Dependencies**: Skill definitions, logging

---

### 11. Config (`app/config/`)

**Responsibility**: Centralized configuration storage.

**Scope**:
- `settings.py`: Environment variables (API keys, Qdrant URL, log level, timeouts)
- `prompts.py`: System prompt, skill prompts, fallback messages (all as strings/templates)
- `routing_rules.yaml`: Keyword patterns for each skill
  ```yaml
  skills:
    product:
      keywords: ["product", "tell me about", "features", "specifications"]
      patterns: ["product.*?(?:details|info|specs)"]
    compare:
      keywords: ["compare", "difference", "versus", "which"]
    noor:
      keywords: ["noor"]
    bespoke:
      keywords: ["custom", "bespoke", "specific"]
    general:
      keywords: []  # fallback
  ```
- `skills_registry.py`: Skill metadata (name, prompt, use_rag, allow_tool, output schema)

**Dependencies**: None

---

### 12. Models & Schemas (`app/models/`)

**Responsibility**: Data validation and serialization.

**Scope**:
- `schemas.py`:
  - `ChatRequest`: message (str), context (optional list of {role, content})
  - `ChatResponse`: reply (str), metadata (optional: intent, skill, latency_ms)
  - `ErrorResponse`: error (str), code (int)
- `entities.py`: Placeholder for Phase 2 (Neon/PostgreSQL entities)
- `errors.py`: Custom exception classes (RAGUnavailable, AITimeout, ValidationError)

**Dependencies**: Pydantic

---

## API Contract

### POST /chat

**Request**:
```json
{
  "message": "Tell me about Product X",
  "context": [
    {
      "role": "user",
      "content": "What are your best-selling items?"
    },
    {
      "role": "assistant",
      "content": "Our most popular products are [...]"
    }
  ]
}
```

- `message`: (string, required, non-empty, max 5000 chars)
- `context`: (array of {role, content}, optional, max 15 items, ordered chronologically)

**Response (Success)**:
```json
{
  "reply": "Based on our current inventory, Product X offers...",
  "metadata": {
    "intent": "product",
    "skill": "product",
    "latency_ms": 1250,
    "routing_source": "rule"
  }
}
```

- `reply`: (string, always present)
- `metadata`: (optional) — intent, skill used, latency, routing decision

**Response (Error)**:
```json
{
  "error": "I'm temporarily unable to provide a detailed response. Please try again.",
  "code": 503
}
```

- `error`: (string, always present on error)
- `code`: (int, HTTP-like; 400=validation, 503=unavailable, 500=internal)

**Status Codes**:
- `200`: Success
- `400`: Validation error (malformed JSON, empty message, injection detected)
- `503`: Service unavailable (AI provider, vector store down; after retries exhausted)
- `500`: Internal server error (unexpected exception)

---

## Non-Functional Requirements

### Performance

- **Latency**: p95 ≤ 3 seconds, p99 < 4 seconds
  - Routing: < 100–200ms (rules ~10ms, LLM ~200ms)
  - RAG: < 500ms
  - AI: < 2 seconds (including retries)
  - Orchestration overhead: < 100ms
- **Throughput**: Single-threaded async ~10–50 concurrent requests; phase 1 assumes <10
- **Token efficiency**: Prompts capped at ~3–4k tokens to stay under latency and cost budgets

### Reliability

- **Availability**: 95% success rate under normal load (phase 1 baseline)
- **Retry strategy**: 1–2 retries with exponential backoff (200ms, 500ms)
- **Fallback**: Safe fallback response on all failures
- **Logging**: All requests logged; retries/failures logged with context
- **Error isolation**: RAG failure doesn't block AI call; AI failure returns graceful fallback

### Observability

- **Structured logging**: JSON format with fields: timestamp, level, component, request_id, intent, skill, latency_ms, error (if any)
- **Metrics**: Request count, latency histogram, retry count, failure count (per service)
- **Tracing**: Request ID passed through all components for debugging

### Security & Safety

- **Input validation**: All inputs validated via Pydantic; sanitize before RAG/AI
- **Injection detection**: Heuristic check for prompt injection patterns
- **Key management**: All API keys in environment variables; never logged or returned
- **Response safety**: No API keys, system prompt, or internal paths in responses
- **RAG grounding**: No hallucination; fallback on missing context

---

## Temporary Test UI (Next.js)

### Purpose
- External client for manual testing of the chat API
- Completely removable; does NOT influence backend design

### Architecture
- Standalone Next.js app
- TypeScript for type safety
- Single page: chat interface
- Calls `POST /chat` endpoint (URL from `.env`)

### Components
- **ChatInput**: Text input + send button; disables send while awaiting response
- **ChatWindow**: Displays conversation history (user messages, assistant replies); scrolls to latest
- **JsonDebugger** (optional): Shows raw JSON response for debugging

### Features
- Display chat history (client-side state only; no persistent storage)
- Show latency and routing metadata (from response metadata)
- Handle API errors gracefully (display error message from response.error)
- Clear conversation button (reset client state)

### Constraints
- Zero business logic (all logic in backend)
- No authentication
- No persistent storage
- No styling (minimal CSS, focus on functionality)
- **Removal**: Delete `/ui` directory; backend continues unaffected

### Environment
```
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend URL
```

---

## Failure Scenarios & Handling

| Scenario | Handling | Result |
|----------|----------|--------|
| Malformed JSON | API validates, rejects with 400 | User sees error message |
| Empty message | Validation error, 400 | User must retry with content |
| Prompt injection | Heuristic detection, sanitize or reject | Either sanitized reply or error message |
| Intent ambiguous | LLM classifier handles; defaults to general | Reply from general skill |
| RAG unavailable (timeout) | Continue without RAG after 500ms timeout | Reply grounded in system prompt only |
| RAG no matches | Return empty chunks; continue | Reply acknowledges "I don't have specific info" |
| AI provider timeout | Retry 1–2x (200ms, 500ms); if still down, fallback | Safe fallback reply + 503 error |
| AI rate limit | Logged; fallback on exhaustion | Safe fallback reply |
| Skill not found | Should not happen (validated in router) | Internal error, 500 |
| Tool execution error | Log error, return fallback response | User sees uncertainty message |
| Total latency > 3s | Log warning; still return response | May miss p95 SLA (≤3s) but no data loss |

---

## Technical Decisions & Rationale

| Decision | Rationale | Alternatives |
|----------|-----------|--------------|
| FastAPI (async Python) | Python ecosystem (OpenAI SDK), easy to maintain, built-in async, pydantic validation | Node.js (simpler), Go (faster but overkill for phase 1) |
| Hybrid rule-based + LLM routing | Rule-based: fast, deterministic, auditable. LLM fallback: handles nuance. Balances performance + accuracy | Full LLM routing (slower, less deterministic) or pure rules (less accurate) |
| OpenAI Responses API (gpt-4.1) | Aligned with brand choice; tool-ready for phase 2; mature API | Anthropic (different API), open-source models (no tool support) |
| Qdrant (vector store) | Fast, cloud-native, explicit vector search; matches constitutional choice | Pinecone (proprietary), Weaviate (heavier) |
| Stateless API (context in request) | Simpler, no session management, easier testing, explicit data flow | Server-side session (adds state, complexity) |
| Fallback reply on failure | Improves UX; user never sees error message; ops can still debug via logs | Return error to user (hurts UX); return empty reply (confusing) |
| Skill modularity | Easy to test, swap, extend skills without affecting orchestration | Monolithic response generator (harder to maintain, harder to extend) |
| 10–15 message context limit | Balances token budget, latency, cost; prevents hallucination drift | No context (bad UX) or unlimited (expensive, slow) |
| Explicit tool schema (no auto-trigger) | Deterministic; no surprise tool calls; explicit logging | Auto-trigger (unpredictable, hard to debug) |

---

## Implementation Notes

### Phase 1 Scope (This Plan)

1. ✅ POST /chat endpoint (request/response validation)
2. ✅ Intent classifier (hybrid rule + LLM)
3. ✅ Skill router + 5 skills (product, compare, noor stub, bespoke, general)
4. ✅ Prompt builder (multi-part prompts)
5. ✅ OpenAI Responses API client (with retry + fallback)
6. ✅ RAG integration (Qdrant, top_k=3)
7. ✅ Failure handling (retry 1–2x, fallback response)
8. ✅ Structured logging (intent, skill, retries, errors)
9. ✅ Next.js test UI (minimal, removable)
10. ✅ API contracts (OpenAPI schema)

### Out of Scope (Phase 2+)

- Authentication / authorization
- User session persistence (visitor_id tracking)
- Long-term conversation memory
- Noor skill full workflow (tool execution)
- Production UI
- WordPress integration
- Rate limiting / API gateway
- Advanced observability (tracing, custom metrics)

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AI provider latency >> 4s | Monitor p95 latency; add timeouts; fallback on slow responses |
| RAG relevance poor | Tune chunking (500–800 tokens); verify Qdrant index quality; monitor retrieval accuracy |
| Skill routing misclassification | Start with conservative rules; log all LLM fallback decisions; iterate based on failures |
| Prompt injection attacks | Heuristic filtering; never directly concatenate user input into system prompt; test common payloads |
| API key exposure | Use environment variables only; never log keys; audit secret handling |
| No fallback response | Test all failure paths in CI; ensure fallback is safe and on-brand |

---

## Readiness for Phase 2 (Tasks)

Once implementation tasks are generated (via `/sp.tasks`), they will decompose this plan into:
1. Unit tests for each component (intent classifier, prompt builder, skills, etc.)
2. Integration tests (end-to-end request flow, RAG integration, AI client)
3. Contract tests (API schema validation)
4. Error scenario tests (timeouts, injection, RAG unavailable, etc.)
5. Async/await implementation details (FastAPI handlers, httpx client setup)
6. Configuration loading and environment variable validation
7. Docker setup and local dev environment

Each task will be P1–P3 (P1 = blocking, P2 = required, P3 = nice-to-have) and will reference this plan's components and data flow.
