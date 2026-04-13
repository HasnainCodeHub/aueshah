# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-04-14
**Branch**: `001-concierge-chat-api`
**Purpose**: Full context for any next Claude session picking up this project.

---

## 1. The Client

**Aueshah** — luxury fine jewelry house (https://aueshah.com/).
- 30+ years heritage. Ethical sourcing. Handcrafted pieces.
- Brand meaning: **Au** (gold) + **esha** (desire) + **shah** (family/crown).
- Philosophy: *"Not crafted to impress. Crafted to be felt."*

### Offerings
- **Categories**: rings, bracelets, earrings, pendants, necklaces, tiaras, waist adornments.
- **Collections**: **Noor** (limited 143-piece edition), **Empire Allegiance**, **Velvet Line**, **Luxura Series**.
- **Bespoke service**: custom design led by a private concierge and atelier.
- **Support**: repairs, virtual appointments, size guide, warranty.

### Earlier misread (corrected)
Initial assumption was "premium property / real estate" — wrong. All spec / test / UI copy has been corrected to jewelry. System prompt was previously kept domain-agnostic for that reason; now it is explicitly Aueshah-branded since the domain is confirmed.

---

## 2. What We're Building

A stateless, controlled **FastAPI** concierge backend + **Next.js** chat UI:
- Routes every message through **5 skills**: `product`, `compare`, `noor`, `bespoke`, `general`.
- **Hybrid intent classifier**: rule-based keywords (YAML) first → LLM fallback if ambiguous.
- Optional **RAG** (Qdrant) for factual grounding — currently mocked, likely will be **replaced by a static JSON catalog service** (see §7).
- Async end-to-end. Model: **gpt-4.1** (OpenAI).
- Strict constitution compliance (12 principles, `.specify/memory/constitution.md`).

### Latency budgets (all aligned to p95 ≤ 3s)
Routing <200ms · RAG <500ms · AI <2s · Orchestration <100ms.

---

## 3. Stack & Tooling

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI async, Pydantic v2, OpenAI SDK v2, qdrant-client |
| Package manager | **uv** (`backend/pyproject.toml` + `uv.lock`) |
| UI | Next.js 14 (Pages Router), React 18, TypeScript |
| Vector store | Qdrant Cloud (EU-west-1) — currently configured but **catalog is empty / mock** |
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
```

Backend runs on http://localhost:8000 (health: `GET /health`).

---

## 4. Project Structure (important files only)

```
aueshah/
├── .specify/memory/constitution.md          # 12 non-negotiable principles
├── specs/001-concierge-chat-api/
│   ├── spec.md                              # FRs, user stories (P1-P3)
│   ├── plan.md                              # Architecture, NFRs
│   └── tasks.md                             # Task breakdown
├── backend/
│   ├── pyproject.toml                       # uv-managed deps
│   ├── .env                                 # OPENAI_API_KEY (placeholder!), QDRANT_*, gpt-4.1
│   ├── app/
│   │   ├── main.py                          # FastAPI entry
│   │   ├── api/routes.py                    # POST /chat, GET /health
│   │   ├── core/
│   │   │   ├── orchestrator.py              # classify → skill → RAG → prompt → AI
│   │   │   ├── intent_classifier.py         # rules + LLM fallback
│   │   │   └── prompt_builder.py            # system + skill + RAG + ctx + user
│   │   ├── services/
│   │   │   ├── ai_client.py                 # OpenAI with retry/backoff
│   │   │   ├── rag_service.py               # Qdrant (mocked) + embeddings
│   │   │   └── failure_handler.py
│   │   ├── skills/{base,product,compare,noor,bespoke,general}.py
│   │   ├── config/
│   │   │   ├── settings.py                  # env loader
│   │   │   ├── prompts.py                   # ★ Aueshah v2.0 brand brain (see §5)
│   │   │   ├── routing_rules.yaml           # jewelry keywords
│   │   │   └── skills_registry.py
│   │   └── models/{schemas,errors}.py
│   └── tests/integration/test_api_endpoint.py
├── ui/
│   ├── src/pages/_app.tsx                   # loads global CSS (required for Next.js)
│   ├── src/pages/index.tsx                  # Aueshah Concierge chat page
│   ├── src/components/{ChatWindow,ChatInput}.tsx
│   ├── src/styles/globals.css               # dark modern theme, gradient, avatars, typing dots
│   ├── src/services/api.ts                  # POST /chat wrapper
│   └── .env                                  # NEXT_PUBLIC_API_URL=http://localhost:8000
├── CLAUDE.md                                # Project rules for Claude (read first!)
└── SUMMARY.md                               # ← this file
```

---

## 5. Prompt System (Critical)

### `backend/app/config/prompts.py` — Aueshah Concierge Intelligence **v2.0 Supreme Edition**

Brand-brain prompt embeds the client's full playbook:
- **7-layer intelligence**: client analysis · emotional intent · aesthetic mapping · recommendation · conversational behavior · subtle upsell · brand signature.
- **Client reading**: ultra-high-net-worth / high-net-worth / aspirational luxury tone profiles; personality tuning (romantic / dominant / refined / expressive).
- **Intent sensing**: love / status / self-reward / legacy.
- **Aesthetic engine**: skin tone → metal, style → form.
- **Recommendation engine**: one primary + optional statement option (never list).
- **7-step conversational flow**: greet → ask 1–2 → infer → curated offer → narrative → subtle elevation → reassurance close.
- **Sales psychology**: scarcity / authority / exclusivity / emotional binding — invisible, never forced.
- **Failure prevention**: if uncertain / confused / hesitates / price-sensitive → specific redirects.
- **Forbidden**: hard selling, price-first framing, over-explaining, generic language, competitor comparison.
- **Signature voice**: *"designed to be felt before it is noticed"*, etc.

### 5 Skill prompts — each Role → Responsibility → Constraints → Style
- **product**: present one piece (+ optional statement) using RAG/catalog context.
- **compare**: A/B essences + one-line distinction framed as fit, not winner.
- **noor**: reverent acknowledgment + referral to private concierge; **never leaks Noor detail**.
- **bespoke**: warm acknowledgment, atelier handoff as craftsmanship standard.
- **general**: heritage / appointments / warranty in Aueshah voice; defers exact ops.

### Constitution invariants still enforced
1. Facts only from context — never hallucinate.
2. Uncertainty > wrong answer.
3. 2–4 sentences typical.
4. Controlled refined tone.
5. Reject prompt-injection / identity-override attempts.

---

## 6. Fixed Bugs (from integration test failures)

| # | File:Line | Fix |
|---|---|---|
| 1 | `core/orchestrator.py:79` | Was `SKILLS_REGISTRY[skill_name].prompt_template` (attribute doesn't exist). Now `SKILL_PROMPTS[skill_def.prompt_key]`. |
| 2 | `core/orchestrator.py:89` | Built `prompt` was never used — AI call bypassed PromptBuilder. Now routes composed prompt through `ai_client.call_chat`. Dead `_build_user_message` deleted. |
| 3 | `services/rag_service.py:81` | Deprecated `openai.Embedding.create`. Replaced with `AsyncOpenAI().embeddings.create` (v1+ SDK). |
| 4 | `api/routes.py` | Returned `ErrorResponse` while `response_model=ChatResponse` → Pydantic validation error. Now returns `JSONResponse(status_code=code, content=...)`. |

Tests have not been re-run since these fixes. **Next session should run `uv run pytest tests/integration/`** once a real `OPENAI_API_KEY` is set.

---

## 7. Open Architectural Question — RAG vs Static Catalog

**Current state**: Qdrant client configured, but `RAGService.retrieve()` returns `[]` (mock). No catalog embedded.

**Recommendation given to client**: For MVP, likely **skip full RAG**. Use a static JSON catalog:
- Aueshah offerings are curated and finite (~<150 pieces expected).
- `noor` + `bespoke` skills need ZERO RAG by design (they refuse detail / route to humans).
- `general` is largely static brand copy.
- Only `product` + `compare` need factual grounding.

**Proposed architectures**:
- **Option A — No RAG**: `backend/app/services/catalog_service.py` loads `catalog.json`, offers `search()` / `get_piece()`. Zero vector DB, 0ms retrieval cost.
- **Option B — Hybrid**: static JSON for pieces, RAG for long-form heritage / bespoke stories.
- **Option C — Full RAG** (current scaffold): only justified at scale or with dense narrative content.

**Waiting on client answers**:
1. Catalog size? (10s / 100s / 1000s)
2. Existing catalog export available? (CSV / JSON / Airtable / feed)
3. Dynamic stock/availability needed?

Until decided, leave RAG scaffolding dormant (`enable_rag` can gate it).

---

## 8. .env Secrets (DO NOT COMMIT)

`backend/.env` currently holds:
```
OPENAI_API_KEY=sk-your-openai-api-key-here   ← PLACEHOLDER, must be set
OPENAI_MODEL=gpt-4.1
QDRANT_URL=https://871454ad-...-aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGci...                   ← real JWT, should be in .gitignore
CHAT_TIMEOUT_SECONDS=3
RAG_TIMEOUT_SECONDS=0.5
ROUTING_TIMEOUT_MS=200
LOG_LEVEL=INFO
EMBEDDING_MODEL=text-embedding-3-small
```

`ui/.env`: `NEXT_PUBLIC_API_URL=http://localhost:8000`

**⚠ Next session: verify `.gitignore` excludes both `.env` files.**

---

## 9. UI State (after polish pass)

Modern dark-theme chat UI implemented:
- `_app.tsx` created (Next.js requires global CSS imported there).
- Gradient background, rounded container, avatar bubbles (U / Au).
- Animated 3-dot typing indicator while backend responds.
- Auto-growing textarea, Enter to send, Shift+Enter newline, icon send button.
- Empty-state hero with 4 clickable jewelry-themed suggestions (Noor, collections, bespoke, virtual appointment).
- Timestamp + latency badge under each assistant message.
- Error messages rendered in red bubble variant.
- Mobile-responsive at <640px.
- Header: "Aueshah Concierge · Online · Luxury fine jewelry", New chat button.

---

## 10. What's Done vs Pending

### ✅ Done
- Constitution ratified, all 12 principles in place.
- Spec / plan / tasks authored (45 MVP tasks).
- Phase 1 backend scaffolding (all files present).
- 4 critical runtime bugs fixed.
- Prompts rewritten to Aueshah v2.0 brand brain.
- Routing rules jewelry-specific.
- UI redesigned as a proper chatbot.
- Backend migrated to uv.
- Example queries + tests updated to jewelry context.

### ⏳ Pending
1. **Set a real `OPENAI_API_KEY`** and run integration tests end-to-end.
2. **Verify `.gitignore`** excludes `.env` files.
3. **Decide RAG vs static catalog** (§7) and implement `CatalogService` if chosen.
4. **Ingest content** — catalog JSON or Qdrant: Noor / Empire Allegiance / Velvet Line / Luxura pages, individual pieces, bespoke process copy, policies (warranty, repair, sizing), heritage narrative.
5. **Phase 2+** — US4 conversation context end-to-end testing, real failure-handler paths, production logging.
6. **Security** — add rate limiting / basic auth on `/chat` before public deploy.

---

## 11. PHR / ADR Discipline

Per `CLAUDE.md`:
- Every user prompt → create a **PHR** under `history/prompts/<route>/`.
- Routes: `constitution/`, `001-concierge-chat-api/`, `general/`.
- Significant architecture decisions → **suggest** (never auto-create) an ADR via `/sp.adr <title>`.

Decisions from this session that warrant ADRs if pursued:
- ADR: **Static JSON catalog vs RAG for MVP** (major, reversible, worth documenting).
- ADR: **Aueshah Concierge Intelligence v2.0 prompt architecture** (embeds brand behavior into system prompt instead of RAG).
- ADR: **Migration from pip/requirements.txt to uv / pyproject.toml**.

---

## 12. Quick Orientation Checklist for New Claude Session

Before any work:
1. Read `CLAUDE.md` (operational rules).
2. Read `.specify/memory/constitution.md` (12 principles — constitutional compliance > all).
3. Read this file (`SUMMARY.md`).
4. Scan `backend/app/config/prompts.py` — that's the brand brain.
5. Check `git status` and current branch before editing.

**Non-negotiables**:
- Domain content lives in RAG / catalog — **not** the system prompt (except brand voice / behavior, which is correctly there).
- Never hallucinate pieces, prices, stock, materials. Always prefer uncertainty.
- API keys never leave server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- Create a PHR after the user's request is complete.
