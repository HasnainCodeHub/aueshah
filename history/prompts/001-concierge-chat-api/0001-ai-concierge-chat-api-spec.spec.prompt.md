---
id: "0001"
title: AI Concierge Chat API Spec
stage: spec
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-concierge-chat-api
branch: 001-concierge-chat-api
user: HasnainCodeHub
command: /sp.specify
labels: ["spec","fastapi","openai","rag","qdrant","skills","concierge","chat-api"]
links:
  spec: specs/001-concierge-chat-api/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-concierge-chat-api/spec.md
  - specs/001-concierge-chat-api/checklists/requirements.md
tests:
  - none
---

## Prompt

/sp.specify
Build a standalone AI Concierge backend using FastAPI and OpenAI Responses API.

This phase focuses ONLY on backend chatbot intelligence. No authentication and no frontend or WordPress integration is required.

SYSTEM PURPOSE:
The system is a controlled AI concierge that provides refined, minimal, and accurate responses. It is not a generic chatbot.

CORE FEATURES:
- POST /chat endpoint
- Accepts user message input
- Returns AI-generated response
- Uses OpenAI Responses API (gpt-4.1)
- Uses system prompt to control tone and behavior
- Implements skill-based routing (product, compare, noor, bespoke, general)
- Integrates RAG using a vector database (Quadrant)
- Retrieves top 3 relevant chunks per query
- Maintains short conversation context (last 10–15 messages max)

INPUT FORMAT:
{ "message": "string" }

OUTPUT FORMAT:
{ "reply": "string" }

AI BEHAVIOR:
- Must be precise, minimal, and controlled
- Must not hallucinate or invent information
- Must rely on RAG for factual knowledge
- Must follow system prompt strictly

RAG REQUIREMENTS:
- Chunk data into 500–800 words
- Use embeddings for retrieval
- Inject only relevant chunks into prompt

SKILLS:
- Product skill → explain product
- Compare skill → compare items
- Noor skill → handle Noor intent (no full workflow yet)
- Bespoke skill → handle custom requests
- General skill → fallback

CONSTRAINTS:
- No authentication
- No frontend logic
- No WordPress integration
- No API key exposure
- Keep responses under control (not verbose)

SUCCESS CRITERIA:
- API returns correct responses
- RAG improves accuracy
- Skills route correctly
- System is stable and fast (<4 seconds response time)

## Response snapshot

Created feature branch `001-concierge-chat-api` and wrote a complete spec at `specs/001-concierge-chat-api/spec.md`. The spec covers:
- 4 user stories (P1–P3): basic chat, skill routing, RAG grounding, conversation context
- 7 edge cases
- 14 functional requirements (FR-001 to FR-014)
- 6 key entities (ChatRequest, ChatResponse, Skill, RAGChunk, ConversationContext, SkillRouter)
- 7 measurable success criteria (SC-001 to SC-007)
- Documented assumptions, out-of-scope items, and dependencies
- Quality checklist created and validated (all items pass, no clarifications needed)

## Outcome

- ✅ Impact: Complete, validated feature spec for the AI Concierge Backend chat API; ready for `/sp.plan`.
- 🧪 Tests: Spec quality checklist at `specs/001-concierge-chat-api/checklists/requirements.md` — all items pass (1 validation run).
- 📁 Files: `specs/001-concierge-chat-api/spec.md` (created), `specs/001-concierge-chat-api/checklists/requirements.md` (created).
- 🔁 Next prompts: `/sp.plan` to generate the architectural plan; optionally `/sp.clarify` if further refinement is desired.
- 🧠 Reflection: All 12 user-specified constraints were encoded without requiring any clarification markers. Noor skill stub assumption and stateless context assumption were the two non-obvious decisions — both documented in Assumptions.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): requirements.md checklist — PASS (all items)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run `/sp.plan` and verify that the 14 FRs map cleanly to architectural components without gaps.
