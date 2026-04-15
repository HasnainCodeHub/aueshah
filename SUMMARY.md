# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-04-15
**Branch**: `001-concierge-chat-api`
**Purpose**: Full context for any next Claude session picking up this project.

---

## 1. The Client

**Aueshah** — luxury fine jewelry house (https://aueshah.com/).
- 30+ years heritage (founded 1987 as Al-Syed Jewellers by Syed Rashid Ali Shah; Aueshah launched 2018).
- Brand meaning: **Au** (gold, elemental symbol) + **esha** (desire) + **Shah** (family lineage).
- Philosophy: *"Not crafted to impress. Crafted to be felt."*
- Ethical sourcing, lifetime warranty, blockchain-backed authenticity (NFT on Ethereum).

### Offerings
- **Categories**: rings, bracelets, earrings, pendants, necklaces, tiaras, waist adornments.
- **Collections**: **Noor** (limited 143-piece edition), **Empire Allegiance**, **Velvet Line**, **Luxura Series**.
- **Bespoke service**: custom design led by a private concierge and atelier.
- **Support**: repairs, virtual appointments, size guide (US/EU/UK PDFs), warranty.

### Catalog size
- 60 non-Noor pieces scraped with full detail (EUR 1,818 – EUR 2,913,410).
- 5 Noor pieces (ring, bracelet, earrings, necklace, tiara) — all 925 sterling silver + 18k gold plating, Mughal jali design.

---

## 2. What We're Building

A stateless, controlled **FastAPI** concierge backend + **Next.js** chat UI:
- All routing + model invocation now runs through the **OpenAI Agents SDK** (triage agent with native handoffs to 5 specialists).
- Skills: `product`, `compare`, `noor`, `bespoke`, `general`.
- **Hybrid knowledge**: static JSON for Noor profile matching (deterministic scoring) + Qdrant RAG for everything else.
- **Two-layer off-topic defense**: keyword regex guardrail + prompt-level SCOPE section → warm 200 OK redirect (no error bubble in UI).
- Async end-to-end. Model: **gpt-4.1** (OpenAI).
- Strict constitution compliance (12 principles, `.specify/memory/constitution.md`).

### Latency budgets (p95 ≤ 3s)
Routing ≤ Agents SDK overhead · RAG ≤ 2.5s (trans-region to Qdrant Cloud eu-west-1) · AI ≤ 2s.

---

## 3. Stack & Tooling

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI async, Pydantic v2, **openai-agents** SDK, qdrant-client |
| Package manager | **uv** (`backend/pyproject.toml` + `uv.lock`) |
| UI | Next.js 14 (Pages Router), React 18, TypeScript |
| Vector store | **Qdrant Cloud (eu-west-1)** — collection `aueshah_knowledge`, 101 points loaded |
| Deploy (planned) | Docker Compose (`docker-compose.yml` present) |

### Commands
```bash
# Backend
cd backend
uv sync                                                   # one-time
uv run uvicorn app.main:app --reload --port 8000          # dev
uv run pytest tests/integration/ -v                       # tests

# UI
cd ui
npm install
npm run dev                                               # http://localhost:3000

# RAG loader (re-run whenever heritage.md / products.json changes)
cd backend
python -m scripts.load_rag
python -m scripts.smoke_rag                               # sanity-check retrieval
```

Backend runs on http://localhost:8000 (health: `GET /health`).

---

## 4. Project Structure (important files only)

```
aueshah/
├── .specify/memory/constitution.md          # 12 non-negotiable principles
├── specs/001-concierge-chat-api/            # spec.md / plan.md / tasks.md
├── Data.txt                                 # Brand brain source (already encoded in SYSTEM_PROMPT)
├── backend/
│   ├── pyproject.toml                       # uv-managed deps (openai-agents added)
│   ├── .env                                 # OPENAI_API_KEY, QDRANT_*, RAG_TIMEOUT=2.5
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes.py                    # POST /chat, GET /health, off-topic fast-path
│   │   ├── core/
│   │   │   ├── agents_factory.py            # ★ Triage agent + 5 specialists + tools
│   │   │   └── orchestrator.py              # Thin Runner.run wrapper
│   │   ├── services/
│   │   │   ├── rag_service.py               # Qdrant query_points — real retrieval
│   │   │   └── noor_catalog.py              # Deterministic Noor profile matcher
│   │   ├── data/
│   │   │   ├── heritage.md                  # 35+ RAG chunks (---separated)
│   │   │   ├── products.json                # 60 non-Noor pieces with full detail
│   │   │   ├── products_index.json          # Lightweight enumeration index
│   │   │   └── noor_catalog.json            # 5 Noor pieces (deterministic matcher + RAG)
│   │   ├── config/
│   │   │   ├── settings.py                  # qdrant_collection=aueshah_knowledge, embedding_dim=1536
│   │   │   └── prompts.py                   # ★ Aueshah v2.0 brand brain + OFF_TOPIC_RESPONSE
│   │   ├── utils/validators.py              # injection_guardrail + off_topic_guardrail
│   │   └── models/{schemas,errors}.py       # +OffTopic exception (code=200)
│   ├── scripts/
│   │   ├── load_rag.py                      # Embed + upsert to Qdrant
│   │   └── smoke_rag.py                     # 5-query sanity check
│   └── tests/integration/test_api_endpoint.py
├── ui/                                       # Next.js chat (dark theme, gradient, typing dots)
├── CLAUDE.md                                # Project rules for Claude (read first!)
└── SUMMARY.md                               # ← this file
```

**Deleted** in the Agents SDK migration: `app/skills/*`, `app/core/intent_classifier.py`, `app/core/prompt_builder.py`, `app/services/ai_client.py`, `app/config/routing_rules.yaml`, `app/config/skills_registry.py`.

---

## 5. Prompt System (Critical)

### `backend/app/config/prompts.py` — Aueshah Concierge Intelligence **v2.0 Supreme Edition**

- 7-layer intelligence (client analysis → emotional intent → aesthetic mapping → recommendation → conversational behavior → subtle upsell → brand signature).
- **SCOPE & GRACEFUL REDIRECTION** section — soft acknowledgement → gentle bridge → warm invitation for off-topic messages that slip past the keyword guardrail.
- **PROFILING GATE** in product skill — must collect age + skin_tone + style_preference before calling `noor_recommend`.
- `OFF_TOPIC_RESPONSE` constant used by both the fast-path in `routes.py` and the `OffTopic` handler.

### 5 Specialist agents (in `agents_factory.py`)
- **product**: one piece (+ optional statement) via `search_catalog` tool.
- **compare**: A/B essences using `search_catalog`.
- **noor**: profile → `noor_recommend` tool (deterministic scoring in `noor_catalog.py`) → private concierge invite.
- **bespoke**: warm atelier handoff.
- **general**: heritage / appointments / warranty / policies / sizing; default fallback.

Triage agent has `input_guardrails=[injection_guardrail, off_topic_guardrail]`.

---

## 6. Current Runtime State

### ✅ Working
- OpenAI Agents SDK wired — triage agent with 5 handoffs.
- Qdrant collection `aueshah_knowledge` loaded with **101 points** (heritage + products + Noor narratives).
- Real retrieval verified via `scripts/smoke_rag.py`:
  - "warranty" → lifetime warranty chunk (score 0.76)
  - "Noor origin" → noor-collection-story (0.74)
  - "rose gold morganite ring" → Whisper Ring (0.60)
  - "refund windows" → refund-return-policy (0.52)
  - "hallmark" → hallmark-and-provenance (0.62)
- Off-topic guardrail returns 200 OK with warm redirect.
- Injection guardrail returns 400.

### ⏳ Not yet verified end-to-end
- Full live chat flow (`uvicorn` + UI + real profiling → Noor recommendation).
- Context/multi-turn via `context[]` array in request body.
- Integration test suite under `tests/integration/` — structure predates Agents SDK migration; may need rewiring.

---

## 7. Architectural Decisions Made This Session

| Decision | Rationale |
|---|---|
| **OpenAI Agents SDK over custom orchestrator** | Native handoffs, guardrails, tools — replaces intent_classifier + prompt_builder + ai_client. Deletes ~1,000 LOC of scaffolding. |
| **Hybrid storage (not pure RAG, not pure JSON)** | Noor: deterministic profile scoring (metal_tone × style × age_tier × occasion) needs exact control — stays as JSON. Heritage + 60-piece catalog + narratives embed well — Qdrant. |
| **Off-topic → 200 OK, not 400** | UI renders as normal assistant message (no error bubble). `OffTopic` exception has `code=200`. |
| **RAG timeout 2.5s** | Trans-region TLS to Qdrant Cloud eu-west-1 from Pakistan needs more than 0.5s. Still inside 3s p95 budget. |

Worth formalizing as ADRs (`/sp.adr <title>`):
- ADR: Migration to OpenAI Agents SDK.
- ADR: Hybrid storage — structured Noor JSON + Qdrant RAG.
- ADR: Off-topic as warm 200 redirect via input guardrail.

---

## 8. .env Secrets (DO NOT COMMIT — verified in `.gitignore`)

`backend/.env` currently holds (real values, not placeholders):
```
OPENAI_API_KEY=sk-svcacct-...
OPENAI_MODEL=gpt-4.1
QDRANT_URL=https://871454ad-...eu-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGci...
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=2.5            # bumped from 0.5 for trans-region TLS
ROUTING_TIMEOUT_MS=200
LOG_LEVEL=INFO
EMBEDDING_MODEL=text-embedding-3-small
```

`ui/.env`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## 9. UI State (unchanged from v1)

Modern dark-theme chat UI: `_app.tsx` globals, gradient background, avatar bubbles (U / Au), 3-dot typing indicator, auto-growing textarea, mobile-responsive <640px, error message variant, empty-state hero with 4 suggestion chips.

---

## 10. What's Done vs Pending

### ✅ Done
- Constitution + spec / plan / tasks.
- OpenAI Agents SDK migration (triage + 5 specialists + guardrails + tools).
- Aueshah v2.0 brand-brain prompt.
- Full catalog scrape from aueshah.com — 60 non-Noor + 5 Noor pieces + heritage pages.
- Qdrant loader (`scripts/load_rag.py`) — 101 points indexed, verified.
- Real `rag_service.retrieve()` via `query_points`.
- Two-layer off-topic defense (regex guardrail + prompt SCOPE).
- UI polished.
- `.env` properly gitignored.

### ⏳ Pending
1. **Live-test full flow** — start backend + UI, run: greeting → profiling → Noor recommendation → off-topic drift → warm redirect.
2. **Rewire integration tests** (`tests/integration/test_api_endpoint.py`) — predates Agents SDK, likely needs updates.
3. **Add rate limiting / basic auth** on `/chat` before public deploy.
4. **ADRs** (see §7) — formalize architectural decisions.
5. **Phase 2+** — conversation context end-to-end, production logging, deployment.

---

## 11. PHR / ADR Discipline

Per `CLAUDE.md`:
- Every user prompt → create a **PHR** under `history/prompts/<route>/`.
- Routes: `constitution/`, `001-concierge-chat-api/`, `general/`.
- Significant architecture decisions → **suggest** (never auto-create) an ADR via `/sp.adr <title>`.

---

## 12. Quick Orientation Checklist for New Claude Session

Before any work:
1. Read `CLAUDE.md` (operational rules).
2. Read `.specify/memory/constitution.md` (12 principles).
3. Read this file (`SUMMARY.md`).
4. Scan `backend/app/core/agents_factory.py` — that's the whole runtime.
5. Scan `backend/app/config/prompts.py` — that's the brand brain.
6. Check `git status` and current branch before editing.

**Non-negotiables**:
- Factual detail lives in Qdrant (`aueshah_knowledge`) and JSON files under `app/data/` — **never** the system prompt (except brand voice).
- Never hallucinate pieces, prices, stock, materials. Always prefer uncertainty.
- API keys never leave server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- Re-run `python -m scripts.load_rag` whenever `heritage.md` / `products.json` / `noor_catalog.json` changes.
