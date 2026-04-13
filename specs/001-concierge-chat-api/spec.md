# Feature Specification: AI Concierge Backend — Chat Intelligence

**Feature Branch**: `001-concierge-chat-api`
**Created**: 2026-04-14
**Status**: Draft
**Input**: User description: "Build a standalone AI Concierge backend using FastAPI and OpenAI Responses API — backend chatbot intelligence only, no auth, no frontend, no WordPress."

---

## Clarifications

### Session 2026-04-14

- Q: How is conversation context transmitted? → A: As a JSON array in the request body.
- Q: How should the system handle external service failures (AI/vector store down)? → A: Hybrid retry + fallback — 1–2 retries with brief backoff, then return safe fallback reply if still unavailable.
- Q: How should the system classify message intent for skill routing? → A: Hybrid rule-based + LLM fallback with explicit rules, structured LLM output, logged routing decisions, <100–200ms latency constraint.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Basic Chat Interaction (Priority: P1)

A visitor sends a plain-language message to the concierge and receives a precise, grounded, on-tone reply.

**Why this priority**: This is the system's core capability. Without it, nothing else functions. All other stories depend on a working chat loop.

**Independent Test**: Send a POST request with `{ "message": "Tell me about the Noor Collection" }` and verify the reply is non-empty, on-topic, and returned within 3 seconds.

**Acceptance Scenarios**:

1. **Given** a valid message is sent to `POST /chat`, **When** the system processes it, **Then** a JSON response `{ "reply": "..." }` is returned within 4 seconds.
2. **Given** a message that matches known RAG knowledge, **When** processed, **Then** the reply references accurate, grounded information (not invented).
3. **Given** an empty or whitespace-only message, **When** sent, **Then** the system returns a structured error response without crashing.

---

### User Story 2 — Skill-Based Response Routing (Priority: P2)

The system detects the intent of each incoming message and routes it to the correct skill (product, compare, noor, bespoke, general), producing a skill-appropriate reply.

**Why this priority**: Routing determines response quality and precision. Without skill routing, all replies would be generic and off-brand.

**Independent Test**: Send messages with clearly distinct intents (product inquiry, comparison request, fallback query) and verify each routes to the correct skill handler and produces a contextually appropriate reply.

**Acceptance Scenarios**:

1. **Given** a message asking about a specific product, **When** processed, **Then** the product skill is invoked and the reply describes that product accurately.
2. **Given** a message asking to compare two items, **When** processed, **Then** the compare skill is invoked and the reply presents a structured comparison.
3. **Given** a message that does not match any defined skill, **When** processed, **Then** the general (fallback) skill handles it with a graceful, on-brand reply.
4. **Given** a message referencing "Noor", **When** processed, **Then** the noor skill is invoked and acknowledges the intent without attempting a full workflow.
5. **Given** a custom or bespoke request, **When** processed, **Then** the bespoke skill handles it with an appropriately tailored response.

---

### User Story 3 — RAG-Grounded Responses (Priority: P2)

When a visitor asks a factual question, the system retrieves relevant knowledge chunks from the vector store and uses them to ground the reply — never inventing information.

**Why this priority**: RAG is what separates this concierge from a generic chatbot. Without grounding, the system hallucination risk is unacceptable.

**Independent Test**: Ask a factual question whose answer exists in the vector store. Verify the reply accurately reflects the stored knowledge and does not introduce invented data.

**Acceptance Scenarios**:

1. **Given** a question with a matching knowledge chunk, **When** processed, **Then** up to 3 relevant chunks are retrieved and the reply is grounded in them.
2. **Given** a question with no matching chunks, **When** processed, **Then** the system acknowledges uncertainty rather than inventing an answer.
3. **Given** any factual reply, **When** inspected, **Then** no information is present that is not derivable from retrieved chunks or the system prompt.

---

### User Story 4 — Short-Term Conversation Context (Priority: P3)

The system maintains awareness of the recent conversation, allowing follow-up questions to be answered coherently without the visitor repeating themselves.

**Why this priority**: Context continuity improves quality but is not required for a functional MVP. It can be layered in after P1 and P2 are stable.

**Independent Test**: Send a sequence of 3 related messages (initial question, follow-up, further refinement). Verify the final reply is coherent in relation to the full sequence.

**Acceptance Scenarios**:

1. **Given** a conversation with up to 15 previous messages, **When** a follow-up is sent, **Then** the reply is contextually aware of prior messages.
2. **Given** a conversation exceeding 15 messages, **When** a new message is sent, **Then** only the most recent 15 messages are included in context (oldest are dropped).
3. **Given** a first message in a session, **When** processed, **Then** the system starts a fresh context with no prior assumptions.

---

### Edge Cases

- What happens when the message payload is malformed JSON?
- What happens when the vector store is unreachable at query time?
- What happens when the AI provider returns an error or timeout?
- What happens when a message exceeds a reasonable character limit?
- What happens when a message contains prompt-injection attempts (e.g., "ignore previous instructions")?
- What happens when no relevant RAG chunks are found for a factual query?
- What happens when skill routing produces an ambiguous classification?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a `POST /chat` endpoint that accepts `{ "message": "string", "context": [{"role": "user"|"assistant", "content": "string"}, ...] }` (context optional) and returns `{ "reply": "string" }`.
- **FR-002**: System MUST validate all incoming request payloads and reject malformed or missing fields with a structured error response.
- **FR-003**: System MUST route every incoming message through a named skill (product, compare, noor, bespoke, or general) before generating a response.
- **FR-003a**: Skill routing MUST use a hybrid strategy: (1) Rule-based keyword/pattern matching first (e.g., "compare"→compare skill, "noor"→noor skill, "bespoke"/"custom"→bespoke skill); (2) If no clear match, invoke lightweight LLM classification (temperature=0, structured output: intent label only); (3) Default to general skill if LLM classification fails.
- **FR-004**: System MUST use a system prompt to enforce tone, persona, and behavioral constraints on every AI call.
- **FR-005**: System MUST query the vector store for each message and retrieve a maximum of 3 relevant knowledge chunks.
- **FR-006**: System MUST inject retrieved chunks into the AI prompt context before generating a reply.
- **FR-007**: System MUST include only the most recent 10–15 messages in the active conversation context sent to the AI.
- **FR-008**: System MUST return a reply that does not contain invented or unverifiable factual claims.
- **FR-009**: System MUST return a structured error (not a stack trace) for all failure conditions, including AI provider errors and vector store failures.
- **FR-010**: System MUST complete the full request-to-response cycle in under 3 seconds under normal operating conditions.
- **FR-011**: System MUST NOT expose API keys, system prompt content, or internal configuration in any response.
- **FR-012**: System MUST sanitize all user inputs before they reach the AI or vector store query layer.
- **FR-013**: The noor skill MUST acknowledge noor-related intent without triggering any automated workflow or data retrieval from noor-specific indexed sources.
- **FR-014**: System MUST use async I/O for all external calls (AI provider, vector store).
- **FR-015**: On AI provider or vector store timeout/failure, system MUST retry 1–2 times with brief exponential backoff (e.g., 100ms, 500ms) before proceeding to fallback.
- **FR-016**: If retries exhaust and service remains unavailable, system MUST return a safe, on-brand fallback reply (e.g., "I'm temporarily unable to provide a detailed response. Please try again.") in place of a technical error.
- **FR-017**: All retry attempts and fallback activations MUST be logged with sufficient context for ops troubleshooting (service name, attempt count, final outcome).
- **FR-018**: Skill routing rules (keyword patterns for each skill) MUST be stored in explicit, auditable configuration (e.g., JSON config file or environment-based rules) — not hardcoded in business logic.
- **FR-019**: Each routing decision MUST be logged with the source (rule-based vs. LLM) and the classified intent label for observability and debugging.
- **FR-020**: Skill routing MUST complete in under 100–200ms overhead, including optional LLM fallback calls.

### Key Entities

- **ChatRequest**: Incoming payload — `message` (string, required, non-empty, max length enforced), `context` (optional array of role/content pairs: `[{"role": "user"|"assistant", "content": "string"}, ...]`, max 15 entries, ordered chronologically).
- **ChatResponse**: Outgoing payload — `reply` (string, always present on success).
- **Skill**: A named behavior unit with a defined input contract, output contract, and invocation condition. Skills: `product`, `compare`, `noor`, `bespoke`, `general`.
- **RAGChunk**: A retrieved knowledge fragment — semantic content, source reference, relevance score.
- **ConversationContext**: An ordered list of recent message/reply pairs, capped at 15 entries, passed to the AI on each call.
- **SkillRouter**: The logic unit responsible for classifying a message and selecting the appropriate skill. Classification is deterministic and auditable.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every valid chat request receives a well-formed `{ "reply": "string" }` response — 100% of requests under normal conditions.
- **SC-002**: End-to-end response time is under 3 seconds for 95% of requests under normal load (p95 ≤ 3 seconds).
- **SC-003**: Skill routing correctly classifies message intent for at least 90% of test cases covering all five skills.
- **SC-004**: Zero responses contain fabricated factual claims when a matching RAG chunk is present in the store.
- **SC-005**: Zero API keys, system prompt content, or internal stack traces appear in any client-facing response.
- **SC-006**: Follow-up questions within a 15-message window are answered coherently without the visitor restating prior context.
- **SC-007**: System returns a safe, structured error response for 100% of failure conditions (AI timeout, store unavailable, malformed input).
- **SC-008**: When external service fails, system exhausts 1–2 retries before returning a fallback reply, maintaining ≤3 second p95 latency even during degraded conditions.

---

## Assumptions

- The vector store (Qdrant) is pre-populated with indexed knowledge chunks before this feature is tested end-to-end.
- Knowledge chunking (500–800 token chunks, embedding generation, and indexing) is a prerequisite operation handled separately from the chat endpoint itself.
- Conversation context is passed by the caller on each request (the API is stateless); the server does not persist session state between calls.
- Skill routing is implemented as a lightweight classification step (keyword/pattern-based or a small classification call) — a full ML classifier is out of scope for this phase.
- The "noor" skill is a stub in this phase: it detects and acknowledges noor-related intent but does not execute any workflow.
- No rate limiting infrastructure is required in this phase (per constraints), but the system must not crash under reasonable single-user load.
- The AI model used is `gpt-4.1` via the OpenAI Responses API.

---

## Out of Scope

- User authentication or session management
- Frontend, UI, or WordPress integration
- Rate limiting or API gateway configuration
- Noor skill full workflow implementation
- Knowledge ingestion pipeline (chunking, embedding, indexing)
- Persistent conversation storage (no database for chat history in this phase)
- Multi-tenancy or per-client configuration

---

## Dependencies

- OpenAI Responses API access (`gpt-4.1` model)
- Qdrant vector store instance, pre-populated with knowledge chunks
- Environment variable management (`.env`) for all secrets
- Python async runtime (FastAPI with async handlers)
