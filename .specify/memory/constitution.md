# AI Concierge Backend Constitution

> This document is the permanent, non-negotiable foundation for all development on the AI Concierge Backend. Every spec, plan, task, and line of code must conform to these principles. No exceptions without a ratified ADR.

---

## I. SYSTEM PURPOSE

This system is a **controlled AI concierge** — not a chatbot, not a support bot, not a general-purpose assistant.

- It exists to guide visitors through a defined experience with precision and restraint.
- Every response must be purposeful, grounded, and within the bounds of the system's defined knowledge.
- The concierge operates within strict behavioral rails defined by the system prompt (brand brain) and the RAG knowledge layer.
- Ambiguity is resolved by restraint: when in doubt, the system acknowledges uncertainty rather than speculating.

**Non-goal restatement:** This system will never behave as a generic assistant, a decision-making authority, or a UI layer.

---

## II. ARCHITECTURE PRINCIPLES

1. **Backend-first.** All business logic, AI calls, skill routing, and data access live exclusively in the backend. The frontend consumes clean API responses — nothing more.
2. **Strict separation of concerns.** The codebase is organized into distinct layers with no cross-layer leakage:
   - `api/` — Route handlers and request validation only.
   - `services/` — Orchestration logic; coordinates skills, RAG, and DB.
   - `skills/` — Discrete, modular behavior units.
   - `rag/` — Retrieval and chunking logic only; no response generation.
   - `db/` — Neon/Postgres access via typed models; no raw SQL outside this layer.
3. **Stateless API design.** Every request must be self-contained. Session context is passed by the caller, not held server-side between requests.
4. **All AI calls are server-side only.** OpenAI API keys, prompts, and tool definitions never reach the client under any circumstance.
5. **Async-first.** All I/O operations (DB, OpenAI, Qdrant) must use async/await patterns. Blocking calls are prohibited.

---

## III. AI BEHAVIOR RULES

1. **System prompt = brand brain.** The system prompt defines tone, persona, scope, and behavioral limits. It is the single authority on how the concierge presents itself. It must not be overridden, leaked, or bypassed.
2. **RAG = knowledge layer.** Retrieved chunks provide factual grounding. The system prompt and RAG play distinct roles and must never be conflated in code or logic.
3. **No hallucination.** The system must never fabricate property data, pricing, availability, people, or policies. If information is not retrievable or not known, the concierge says so.
4. **Uncertainty is preferred over error.** A response of "I don't have that information" is correct behavior. An invented answer is a critical failure.
5. **Consistent tone.** All responses must be controlled, minimal, and premium. Verbose, casual, or speculative language is a violation.
6. **No prompt injection tolerance.** User inputs that attempt to override the system prompt, extract internal data, or alter behavior must be detected and neutralized.

---

## IV. SKILLS & INTELLIGENCE LAYER

1. **All behaviors are routed through defined skills.** There is no code path that generates a response without passing through a named, registered skill.
2. **No direct generation.** Services must never call the OpenAI API directly to generate a response without a skill context providing the intent, constraints, and expected output shape.
3. **Skills are modular and replaceable.** Each skill is an isolated unit with a defined input contract, output contract, and failure behavior. Replacing one skill must not affect others.
4. **Skills must be explicitly invoked.** Auto-detection of skill intent may inform routing, but the final routing decision must be deterministic and auditable.
5. **Skill registry is the source of truth.** Any capability the system exposes must be listed in the skill registry. Undocumented capabilities are prohibited.

---

## V. RAG STANDARDS

1. **No full-data prompting.** Raw documents, full property listings, or large data blobs must never be injected into a prompt directly.
2. **Chunking is mandatory.** All documents must be chunked at **500–800 tokens** before indexing. Chunks must preserve semantic coherence (no mid-sentence splits).
3. **Top-k retrieval limit.** Retrieval must return a maximum of **3–5 chunks** per query. Over-retrieval degrades response quality and increases latency.
4. **Responses must be grounded.** Every factual claim in a concierge response must be traceable to a retrieved chunk. Ungrounded claims are a failure mode.
5. **Noor-related data is excluded from automated indexing.** Any content related to "Noor" must be manually reviewed and explicitly approved before indexing.
6. **Qdrant is the sole vector store.** No other embedding or vector search solution may be introduced without a ratified ADR.

---

## VI. MEMORY & PERSONALIZATION

1. **`visitor_id` is the primary identity key.** All personalization, history, and session context is anchored to `visitor_id`. No other identifier takes precedence.
2. **Store summaries, not transcripts.** Only distilled summaries of interactions are persisted. Full conversation history must not be stored or replayed in prompts.
3. **Active context is bounded.** A maximum of **10–15 recent messages** may be included in the active prompt context. Older context must be summarized or dropped.
4. **Privacy by default.** The system collects only what is necessary to serve the visitor. No behavioral profiling, no cross-visitor inference, no speculative enrichment.
5. **No intrusive personalization.** The concierge must not reference stored data in ways that feel surveillance-like or uncomfortable.

---

## VII. TOOLING RULES

1. **All tool/function calls are explicit.** Every tool invocation must be declared in the skill definition, validated against expected inputs, and logged.
2. **No auto-trigger.** Tools are never invoked speculatively or based on weak intent signals. Clear, unambiguous intent is required.
3. **Deterministic tool responses.** Tool outputs must be handled via defined response handlers. Loops, retries without backoff, and silent failures are prohibited.
4. **Tool errors surface cleanly.** A failed tool call must produce a structured error response — never a partial or hallucinated answer.

---

## VIII. API CONTRACT STABILITY

1. **Request/response formats are stable.** Once a route is shipped, its input and output shape is locked. Changes require versioning.
2. **All responses are clean JSON.** No plain-text responses, no mixed formats, no HTML fragments. Every API response conforms to a defined schema.
3. **No breaking changes without versioning.** Route or schema changes that break existing consumers must be introduced under a new version (e.g., `/v2/`). Old versions are deprecated with notice, not removed silently.
4. **Validation is strict.** All incoming requests are validated against Pydantic models at the API layer. Unvalidated input never reaches the service or AI layer.

---

## IX. SECURITY & SAFETY

1. **API keys are server-side secrets.** OpenAI keys, Qdrant keys, and database credentials are stored in environment variables only. They are never logged, returned in responses, or committed to version control.
2. **All inputs are sanitized.** User-supplied content is treated as untrusted. Injection attacks (prompt injection, SQL injection, path traversal) are actively mitigated.
3. **Rate limiting is mandatory.** All public-facing endpoints must enforce rate limits. No endpoint is exposed without throttling.
4. **Sensitive data has purpose.** No PII or sensitive visitor data is stored unless there is a defined, justified purpose. Purposeless storage is a violation.
5. **Error responses are safe.** Stack traces, internal paths, model names, and system prompt content must never appear in error responses sent to clients.

---

## X. PERFORMANCE & RELIABILITY

1. **Latency is a first-class concern.** All AI-involved endpoints target a p95 latency of **≤ 3 seconds**. Retrievals and DB queries target **≤ 200ms**.
2. **Token efficiency is required.** Prompts must be as concise as possible. Redundant context, repeated instructions, and verbose system prompts are code smells.
3. **Graceful degradation is mandatory.** If the AI layer, RAG, or DB is unavailable, the system must return a safe fallback response — never crash or hang.
4. **Async throughout.** FastAPI async endpoints, async DB drivers, and async OpenAI calls are required. Synchronous blocking in any I/O path is a defect.
5. **No silent failures.** All exceptions must be caught, logged with structured context, and surfaced as appropriate error responses.

---

## XI. ITERATION PRINCIPLE

1. **All changes go through the SDD cycle.** The mandatory sequence is: `spec → plan → tasks → implement`. No code is written outside this flow.
2. **No cowboy commits.** Direct code changes that bypass spec-driven workflow are prohibited, regardless of urgency.
3. **Specs are the source of truth.** If the code and the spec disagree, the spec is correct until the spec is formally amended.
4. **Small, testable increments.** Each task must be atomic — completable in isolation with a clear, verifiable acceptance criterion.

---

## XII. NON-GOALS

This system will never be:

- A **generic chatbot** capable of answering arbitrary questions.
- A **support bot** handling complaints, tickets, or escalations.
- A **UI system** — the frontend is a consumer, not a concern.
- An **autonomous decision-maker** — it operates within defined constraints and defers to human judgment at system boundaries.
- A **data store** — it facilitates interaction; it does not own or manage business data.

Introducing any of these capabilities requires a full constitutional amendment with ADR ratification.

---

## Governance

- This constitution supersedes all other guidelines, coding conventions, and informal agreements.
- Any amendment requires: (1) a written rationale, (2) an ADR documenting the decision, and (3) explicit user approval.
- All specs, plans, and tasks must cite compliance with relevant sections of this constitution.
- Every pull request must be reviewed against this constitution. Non-compliant PRs are rejected.

**Version**: 1.0.0 | **Ratified**: 2026-04-14 | **Last Amended**: 2026-04-14
