# Aueshah AI Concierge — Session Handoff Summary

**Last updated**: 2026-05-06
**Branch**: `001-concierge-chat-api`
**HEAD**: `f9b29d3` — *Fix Render deploy: align requirements.txt with pyproject + multi-recipient alerts*
**Status**: **DEPLOYED & LIVE.** Backend on Render (`https://aueshah.onrender.com`), WordPress Bespoke page widget pointed at it, full chat → DB → email path validated. Pending: Resend domain verification, optional Render plan upgrade.

---

## 0. SESSION HISTORY (newest first)

| Commit | Date | Summary |
|---|---|---|
| `f9b29d3` | 2026-05-06 | Render deploy fix (requirements.txt) + multi-recipient concierge alerts |
| `9caeceb` | 2026-05-05 | Render deploy config + widget UI polish + auth/upsert hardening |
| `1b139ca` | 2026-05-04 | submit_appointment tool, SendGrid→Resend swap, profiling-intent fix |
| `eaa9cec` | 2026-05-04 | (Zaid Rehan) WP integration: cookie-based auth bridge, LLM profile extraction, PNA CORS |
| `424b53e` | 2026-04-23 | WP HS256 auth swap + Phase 2 deployment prep |
| `029ba62` | 2026-04-17 | Closed all 7 client requirements gaps |

The cloudflared quick-tunnel era is **over** — backend has a stable HTTPS URL now.

---

## 1. Brand context (unchanged)

**Aueshah** — luxury fine jewelry house (https://aueshah.com/). 30+ years heritage (founded 1987 as Al-Syed Jewellers, rebranded Aueshah 2018). Brand: **Au** (gold) + **esha** (desire) + **Shah** (lineage). Philosophy: *"Not crafted to impress. Crafted to be felt."* Ethical sourcing, lifetime warranty, NFT-backed authenticity.

**Catalog**: 60 non-Noor pieces + 5 Noor (limited 143-piece edition, sterling silver + 18k gold, Mughal jali). Skills: `product`, `compare`, `noor`, `bespoke`, `general`. Latency budget p95 ≤ 3s.

---

## 2. Live deployment

### Render service
| Field | Value |
|---|---|
| Public URL | **https://aueshah.onrender.com** |
| Workspace ID | `tea-d7sh7if7f7vs73daetgg` (Shah's workspace, `shahs.jewel@gmail.com`) |
| Service ID | `srv-d7t7qook1i2s73cebb0g` |
| Service slug | `aueshah` |
| Plan | **free** (sleeps after 15 min idle, ~30s cold start) |
| Runtime | **python** (not docker — `render.yaml` was effectively ignored; service was created via dashboard, not Blueprint) |
| Region | `oregon` |
| Branch | `001-concierge-chat-api` (autoDeploy on commit) |
| Build cmd | `pip install -r requirements.txt` |
| Start cmd | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Render API key (CLI cache) | `~/.render/cli.yaml` (`rnd_XXHIUpc24W98YW3m2OGP9IXDlufM`) |

**Render CLI is configured** — workspace already set, can run `render services`, `render logs --resources srv-d7t7qook1i2s73cebb0g`, `render deploys list` directly.

For env-var read/write the CLI doesn't expose them, use the REST API:
```bash
curl -sS -H "Authorization: Bearer rnd_XXHIUpc24W98YW3m2OGP9IXDlufM" \
  "https://api.render.com/v1/services/srv-d7t7qook1i2s73cebb0g/env-vars?limit=100"
```

All 19 env vars are set on Render and **byte-match the local `backend/.env`**, including the asyncpg-flavored `NEON_DATABASE_URL` (`+asyncpg`, `?ssl=require`, no `channel_binding`).

### What's verified live (2026-05-06)
| Probe | Result |
|---|---|
| `GET /health` | 200 `{"status":"ok"}` |
| `POST /chat` cold (anon) | 200, ~10s (cold start) |
| `POST /chat` warm | 200, ~4.8s, agents-SDK routing returns correct `intent`+`skill` |
| CORS preflight from `https://aueshah.com` | 200 with `access-control-allow-origin: https://aueshah.com` and `access-control-allow-private-network: true` |
| `POST /v1/auth/wp-login` (malformed token) | 401 `{"error":"Malformed token"}` |
| `POST /appointment-request` valid | 200, **row `APT-CFC7091E` written to Neon**, both Resend sends to `shahs.jewel@gmail.com` accepted, send to `service@aueshah.com` rejected as expected (Resend sandbox) |

### WordPress widget
Bespoke page (id=`1102`) `BACKEND` constant **now points at `https://aueshah.onrender.com`** (swapped 2026-05-05T23:56). The cloudflared workflow is no longer used.

---

## 3. Stack & infra (current — all client-owned)

| Layer | Service | Identifier |
|---|---|---|
| Backend host | **Render** (free, oregon) | https://aueshah.onrender.com |
| Database | **Neon Postgres** | `ep-shy-dawn-amcvb648-pooler.c-5.us-east-1.aws.neon.tech/neondb` (alembic at **0003**) |
| Vector store | **Qdrant Cloud** sa-east-1 | `3b21e494-…sa-east-1-0.aws.cloud.qdrant.io`, collection `aueshah_knowledge` (3072d, **108 points**) |
| Cache / rate limit | **Upstash Redis** | `inspired-labrador-115364.upstash.io` |
| Email | **Resend** (acct `shahs.jewel@gmail.com`) | sandbox sender `onboarding@resend.dev` — **`aueshah.com` NOT verified yet** → only `shahs.jewel@gmail.com` deliverable |
| Auth | WordPress **HS256** JWT shared secret → backend HS256 session JWT (python-jose) | `JWT_AUTH_SECRET_KEY` matches aueshah.com `wp-config.php` |
| Concierge alert recipients | comma-list, fan-out one Resend send per address | `shahs.jewel@gmail.com,service@aueshah.com` |
| Package manager | **uv** | `backend/pyproject.toml` + `uv.lock` |
| Local dev | uvicorn on `127.0.0.1:8001` (port 8000 has stuck system-Python process) | |

### Local commands
```bash
cd backend
uv sync                                                       # one-time
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001      # dev
uv run pytest tests/ -q                                       # 122 passing, 5 stale (Zaid's gate change, see §6)
uv run python -m scripts.load_rag                             # re-embed → Qdrant
uv run alembic upgrade head                                   # 0001 → 0002 → 0003
```

---

## 4. Repo structure (delta from 2026-05-05)

```
aueshah/
├── render.yaml                              committed but effectively unused — service is python runtime, not docker
├── SUMMARY.md                               (this file)
├── CLAUDE.md, LOCAL_CHANGES_RECOVERY.md     CLAUDE.md is operational rules; recovery doc is historical
├── specs/001-concierge-chat-api/            spec/plan/tasks
├── history/adr/                             ADR-0001, 0002 (0003-0005 still pending)
├── backend/
│   ├── .env                                 gitignored — see §7
│   ├── .env.backup                          gitignored — pre-migration credentials
│   ├── requirements.txt                     ★ aligned with pyproject.toml (qdrant-client>=1.12.0, openai>=1.51.0, openai-agents)
│   ├── alembic/versions/                    0001 + 0002 + 0003 (profile_facts JSONB)
│   ├── Dockerfile (basic), Dockerfile.prod  Render uses NEITHER (python runtime). Both kept for portability.
│   ├── app/
│   │   ├── core/agents_factory.py           triage + 5 specialists. Tools: search_catalog, noor_recommend, submit_noor_request, submit_appointment (last is on BOTH general AND bespoke)
│   │   ├── config/settings.py               ★ concierge_alert_recipients property (splits comma-list)
│   │   ├── config/prompts.py                brand brain v2.0 + TONE section (no AI-tells)
│   │   ├── services/appointment_workflow.py ★ fan-out one Resend per recipient under asyncio.gather(return_exceptions=True)
│   │   ├── services/noor_workflow.py        ★ same fan-out pattern
│   │   ├── services/notifications/email.py  Resend (sync resend.Emails.send wrapped in asyncio.to_thread)
│   │   └── db/repositories/users.py         defensive two-step upsert (wp_user_id → email fallback → reconcile)
│   └── scripts/
│       ├── widget3.html                     WP chat widget JS — embedded in Bespoke page 1102
│       └── load_rag.py, smoke_rag.py
└── ui/                                       Next.js test harness (dev only)
```

---

## 5. Client requirements

All 17 sections of `requirements.docx` remain satisfied. No regressions this session.

---

## 6. What's done this session (2026-05-06)

1. **Render deployed.** Build initially failed — `requirements.txt` pinned `qdrant-client==2.7.0` (doesn't exist; latest is 1.17.x) and `openai==1.3.0` (predates Responses API + Agents SDK). Realigned `requirements.txt` to mirror `pyproject.toml`. Build passed, service live.
2. **Multi-recipient concierge alerts.** New `Settings.concierge_alert_recipients` property splits `CONCIERGE_ALERT_EMAIL` on commas. `appointment_workflow._fire_notifications` and `noor_workflow._fire_notifications_on_create` now loop and append one `send_concierge_*_alert` coroutine per address, all under `asyncio.gather(return_exceptions=True)` so one bad recipient doesn't fail the rest. Default = `shahs.jewel@gmail.com,service@aueshah.com`.
3. **WordPress widget pointed at Render.** Surgical regex-replace on Bespoke page 1102 — `BACKEND` constant swapped from the dead `trycloudflare.com` URL to `https://aueshah.onrender.com`. Cloudflared workflow retired.
4. **End-to-end verified on Render.** `/health`, `/chat` (cold + warm), CORS preflight from `aueshah.com`, `/v1/auth/wp-login` schema, `/appointment-request` writes to Neon and fires Resend fan-out. `APT-CFC7091E` is the proof row.
5. **Render CLI workspace set** (`tea-d7sh7if7f7vs73daetgg`); confirmed Render's `NEON_DATABASE_URL` matches the local `.env` exactly (correct asyncpg format).

### Known test status — 122 / 127
The 5 failing tests are **pre-existing** from Zaid's `eaa9cec` (he removed the selective-memory gate; tests assert old gated behavior). Not bugs from this session:
- `test_chat_with_context`, `test_selective_memory_no_qualifying_intent`, `test_selective_memory_expired_noor`, `test_build_preamble_returns_none_when_no_personal_data`, `test_build_preamble_returns_none_without_qualifying_intent`

---

## 7. backend/.env (gitignored)

Live values in `backend/.env`. Same set is mirrored in Render env vars and **matches byte-for-byte** for the things that matter (DB URL, Qdrant, Redis, Resend).

```
OPENAI_API_KEY=sk-svcacct-…
OPENAI_MODEL=gpt-4.1
EMBEDDING_MODEL=text-embedding-3-large

NEON_DATABASE_URL=postgresql+asyncpg://neondb_owner:…@ep-shy-dawn-amcvb648-pooler.c-5.us-east-1.aws.neon.tech/neondb?ssl=require
QDRANT_URL=https://3b21e494-…sa-east-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGci…
REDIS_URL=rediss://default:gQAAAAAA…@inspired-labrador-115364.upstash.io:6379

RESEND_API_KEY=re_ayWdJVPU_…                  (client account, sandbox until aueshah.com verified)
RESEND_FROM_EMAIL=Aueshah Concierge <onboarding@resend.dev>
CONCIERGE_ALERT_EMAIL=shahs.jewel@gmail.com,service@aueshah.com

JWT_SIGNING_KEY=…                              (signs OUR session JWTs)
ADMIN_API_TOKEN=…                              (gates /admin/*)
JWT_AUTH_SECRET_KEY='pEB-g<T%lIIb5#…'          (HS256, must match aueshah.com wp-config.php)
WP_BASE_URL=https://aueshah.com
WP_ISSUER=https://aueshah.com

# Not set
SLACK_WEBHOOK_NOOR=
SLACK_WEBHOOK_APPOINTMENTS=
```

---

## 8. WordPress site state (aueshah.com)

- **Platform**: WordPress + WooCommerce. Bespoke page id=`1102`, slug=`bespoke`.
- **Login**: WooCommerce at `/my-account/`.
- **Plugins**: JWT Authentication for WP-API (HS256, secret in `wp-config.php`), WPCode Lite (likely hosts Zaid's mint-token snippet).
- **Custom REST endpoint**: `POST /wp-json/aueshah/v1/mint-token` — cookie-auth → `{token, user_email, user_display_name}` for the logged-in WP user.
- **Bespoke widget**: chat surface inside Gutenberg `<!-- wp:html -->` blocks; the JS lives in an inline `<script>` block on the page. Source of truth = `backend/scripts/widget3.html`. To update: surgical regex-replace the `<script>...</script>` block containing `BACKEND` + `WP_MINT` via WP REST. **Always refetch live page as baseline first.** Backups in `backend/.bespoke-*.json` (gitignored).

### WP admin credentials (committed by user request — rotate if repo visibility changes)

```
URL  : https://aueshah.com
User : claude-concierge
App password : keEG TqQ3 bphl wewX xoCd ewBQ
Role : administrator (verified caps include edit_pages, unfiltered_html, manage_woocommerce)
```

Use HTTP Basic: `curl -u 'claude-concierge:keEG TqQ3 bphl wewX xoCd ewBQ' …`

### User flow
```
User on /bespoke/
  → widget runs ensureSession()
  → POST /wp-json/aueshah/v1/mint-token (cookie auth)         → {wp_token, user_email, user_display_name}
  → POST https://aueshah.onrender.com/v1/auth/wp-login        → {access_token, user}  (Neon row created on first login)
  → POST https://aueshah.onrender.com/chat (Bearer token)     → {reply, metadata}
```

Lazy provisioning: a Neon row is created the first time a WP user opens chat.

---

## 9. What's remaining

### PRIORITY 1 — Real user flow validation
Open `https://aueshah.com/bespoke/` in a private window. Log in via the chat widget (any WP user account). Confirm the chat unlocks (not stuck on login/register), ask for an appointment, give details, verify email lands at `shahs.jewel@gmail.com` within ~10s. This is the only check that proves end-to-end works for real users.

### PRIORITY 2 — Resend domain verification (currently the biggest functional gap)
Until `aueshah.com` is added at **resend.com/domains** and DNS-verified, **only `shahs.jewel@gmail.com` is a deliverable recipient**. Sends to `service@aueshah.com` and to chat-user-supplied emails return Resend's sandbox 403 *"You can only send testing emails to your own email address…"* — handled gracefully (warning, not crash) but those emails never arrive.

Steps:
1. Resend dashboard → Domains → Add `aueshah.com`
2. Add the 3 DNS records (SPF / DKIM / DMARC) in aueshah.com's DNS
3. Verify; usually 5–30 min
4. On Render, change `RESEND_FROM_EMAIL=Aueshah Concierge <concierge@aueshah.com>` (or similar verified-domain sender)

### PRIORITY 3 — Optional Render plan upgrade ($7/mo Starter)
Free plan sleeps after 15 min idle → ~30s cold start on first request. Starter eliminates sleep, gives 5× CPU (cuts warm chat from ~4.8s to ~2–3s, back inside the p95 ≤ 3s SLA), zero-downtime deploys, and graceful shutdowns. Same URL, same env vars — no code change.

```bash
render services update srv-d7t7qook1i2s73cebb0g --plan starter --confirm
```

### PRIORITY 4 — CORS lockdown
Currently `allow_origin_regex=".*"`. For production, change to explicit `https://aueshah.com` (the production block is commented in `backend/app/main.py` lines ~71–81, ready to paste).

### PRIORITY 5 — Deferred cleanup
| Task | Notes |
|---|---|
| ADR-0003 / 0004 / 0005 | RS256→HS256 swap; SendGrid→Resend + appointment tool; service migration to client accounts |
| Update 5 stale tests | Match Zaid's no-gate personalization (not a code bug) |
| Slack webhooks | Set `SLACK_WEBHOOK_NOOR` / `SLACK_WEBHOOK_APPOINTMENTS` if client wants them |
| WP `scripts/wp_mock.py` | Obsolete (was JWKS mock for the old RS256 flow) |
| Old data migration | Greenfield client stack — prior 7 users / 108 vectors / appointments not migrated |

---

## 10. Quick orientation for new Claude session

### Before any work
1. Read `CLAUDE.md` (operational rules) + this file.
2. `git status` / `git log -3 --oneline` / current branch.
3. Check `backend/.env` for what's connected.
4. If user mentions chat broken on the live site:
   - First check: `curl -sS https://aueshah.onrender.com/health` (free plan may be cold-booting — give it 30s)
   - Second check: `render logs --resources srv-d7t7qook1i2s73cebb0g --limit 50 --confirm -o text`
   - Third check: WP page 1102's `BACKEND` constant still says `https://aueshah.onrender.com`

### Key files to scan
- `backend/app/core/agents_factory.py` — triage + 5 specialists + 4 tools
- `backend/app/config/prompts.py` — brand brain + TONE + 5 skill prompts
- `backend/app/config/settings.py` — env vars + `concierge_alert_recipients`
- `backend/app/services/appointment_workflow.py` + `noor_workflow.py` — multi-recipient fan-out
- `backend/app/api/routes.py` — POST /chat, /appointment-request, /health
- `backend/app/auth/wp_verifier.py` — HS256 WP token verification
- `backend/app/db/repositories/users.py` — defensive upsert
- `backend/app/db/models.py` — has `profile_facts: JSONB` (migration 0003)
- `backend/scripts/widget3.html` — WP chat widget (inlined into Bespoke page)
- `backend/requirements.txt` — must stay aligned with `pyproject.toml` (Render's `pip install` builds from this)

### Render operations
```bash
# Workspace already set — these work directly:
render services -o json --confirm
render logs --resources srv-d7t7qook1i2s73cebb0g --limit 100 --confirm -o text
render logs --resources srv-d7t7qook1i2s73cebb0g --tail --confirm
render deploys list --service srv-d7t7qook1i2s73cebb0g --confirm
render restart srv-d7t7qook1i2s73cebb0g --confirm

# Env vars — REST API only (CLI doesn't expose them)
curl -sS -H "Authorization: Bearer rnd_XXHIUpc24W98YW3m2OGP9IXDlufM" \
  "https://api.render.com/v1/services/srv-d7t7qook1i2s73cebb0g/env-vars?limit=100"
```

### Non-negotiables
- Factual detail in Qdrant + JSON, **never** the system prompt.
- Never hallucinate pieces, prices, stock, materials. Prefer uncertainty.
- API keys never leave the server. All AI calls server-side.
- Keep diffs minimal. No unrelated refactors.
- Live edits to `aueshah.com` are high blast-radius — show the diff and confirm before pushing.
- `requirements.docx` is the authoritative client spec — all 17 sections must stay matched.
- `backend/requirements.txt` and `backend/pyproject.toml` must stay aligned (Render builds from `requirements.txt`).

### Resume from
**Priority 1: real user flow validation.** Then **Priority 2: Resend domain verification** to unblock `service@aueshah.com` + chat-user emails. Plan upgrade is purely UX — only after the client confirms cold start bothers them.
