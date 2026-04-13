---
id: "001"
title: AI Concierge Backend Constitution
stage: constitution
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: none
branch: master
user: HasnainCodeHub
command: /sp.constitution
labels: ["constitution","fastapi","openai","rag","qdrant","neon","postgres","ai-concierge"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - none
---

## Prompt

/sp.constitution
Create a project constitution for an AI Concierge Backend built with FastAPI, OpenAI Responses API, Neon (Postgres), and RAG (Quadrant).

The constitution must define non-negotiable principles, constraints, and standards that all future specs, plans, tasks, and implementations must follow.

Keep it concise but strict. Include the following mandatory sections:

1. SYSTEM PURPOSE
- Define the system as a controlled AI concierge (not a chatbot)
- Emphasize precision, restraint, and guided interaction

2. ARCHITECTURE PRINCIPLES
- Backend-first architecture (no logic in frontend)
- Strict separation of concerns (API, services, skills, RAG, DB)
- Modular, scalable, and stateless API design
- All AI calls must be server-side only

3. AI BEHAVIOR RULES
- System prompt controls behavior (brand brain)
- RAG provides knowledge (never mix roles)
- Never hallucinate or invent data
- Prefer uncertainty over incorrect answers
- Maintain consistent tone (controlled, minimal, premium)

4. SKILLS & INTELLIGENCE LAYER
- All behaviors must be routed through defined skills
- No direct response generation without skill context
- Skills must be modular and replaceable

5. RAG STANDARDS
- No dumping full data into prompts
- Use chunking (500–800 words)
- Retrieve top-k (max 3–5 chunks)
- Always ground responses in retrieved context
- Keep Noor-related data out of automated indexing

6. MEMORY & PERSONALIZATION
- Use visitor_id as primary identity
- Store only necessary summaries (not full history in prompt)
- Limit active context to recent messages (10–15 max)
- Respect privacy and avoid intrusive personalization

7. TOOLING RULES
- All function/tool calls must be explicit and validated
- Never auto-trigger tools without clear intent
- Handle tool responses deterministically (no loops)

8. API CONTRACT STABILITY
- Request/response formats must remain stable
- All responses must be clean JSON
- No breaking changes without versioning

9. SECURITY & SAFETY
- API keys must never be exposed
- Validate and sanitize all inputs
- Enforce rate limiting and error handling
- No storage of sensitive data without purpose

10. PERFORMANCE & RELIABILITY
- Optimize for low latency and minimal token usage
- Use async operations
- Implement graceful fallbacks on failure

11. ITERATION PRINCIPLE
- All improvements must go through spec → plan → tasks → implement cycle
- No direct code changes outside spec-driven workflow

12. NON-GOALS
- Not a generic chatbot
- Not a support bot
- Not a UI system
- Not autonomous decision-maker without constraints

Ensure the constitution is strict, enforceable, and acts as a permanent foundation for all future development.

## Response snapshot

Created `.specify/memory/constitution.md` with 12 ratified sections covering system purpose, architecture, AI behavior, skills layer, RAG standards, memory/personalization, tooling, API contract stability, security, performance, iteration principle, and non-goals. Constitution is strict, enforceable, and version-stamped at 1.0.0 (ratified 2026-04-14).

## Outcome

- ✅ Impact: Permanent constitutional foundation established for the AI Concierge Backend; all future specs, plans, tasks, and implementations must comply.
- 🧪 Tests: N/A — constitution is a governance document, not executable code.
- 📁 Files: `.specify/memory/constitution.md` created/overwritten; `history/prompts/constitution/001-ai-concierge-backend-constitution.constitution.prompt.md` created.
- 🔁 Next prompts: `/sp.specify` to write the first feature spec; `/sp.adr` to record any technology-selection decisions (FastAPI, Qdrant, Neon).
- 🧠 Reflection: Constitution covers all 12 requested sections with strict, enforceable language. No placeholders remain. Governance section anchors amendment process to ADR ratification.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run `/sp.adr` for technology stack decisions (FastAPI + Qdrant + Neon) to document rationale before first spec.
