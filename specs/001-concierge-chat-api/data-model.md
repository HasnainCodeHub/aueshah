# Phase 1 Data Model — AI Concierge Phase 2

**Date**: 2026-04-16
**Storage**: Neon Serverless Postgres (primary OLTP) + Qdrant (vector store, unchanged)
**ORM**: SQLAlchemy 2.0 async with `asyncpg`
**Migrations**: Alembic

---

## Entity overview

```
┌──────────┐        ┌────────────────┐
│  users   │◄───────│ chat_messages  │
│          │        └────────────────┘
│  (wp_    │
│  user_id)│───────►┌────────────────┐
│          │        │  appointments  │
│          │        └────────────────┘
│          │
│          │───────►┌──────────────────────────┐
│          │        │ noor_allocation_requests │
│          │        └──────────────────────────┘
│          │
│          │───────►┌────────────────┐
└──────────┘        │ user_activity  │
                    └────────────────┘
```

All tables use UUIDv4 primary keys, `TIMESTAMPTZ` timestamps (UTC), and soft FK constraints with `ON DELETE SET NULL` to preserve audit trails when a user is deleted.

---

## Table 1: `users`

The canonical user record. One row per WordPress account. Anonymous visitors do **not** have rows here — they're tracked via `visitor_id` in `chat_messages` and merged on first login.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | Internal identifier; used in all FKs |
| `wp_user_id` | `BIGINT` | UNIQUE NOT NULL | WordPress user ID (`sub` claim) |
| `email` | `CITEXT` | UNIQUE NOT NULL | Case-insensitive; comes from WP token |
| `display_name` | `VARCHAR(255)` | NOT NULL | From WP `display_name` claim |
| `phone` | `VARCHAR(32)` | NULL | Optional, user-provided |
| `age_range` | `VARCHAR(32)` | NULL | Profiling Q1: e.g. `25-34`, `35-44` |
| `skin_tone` | `VARCHAR(32)` | NULL | Profiling Q2: `warm`, `cool`, `neutral` |
| `style_preference` | `VARCHAR(64)` | NULL | Profiling Q3: `heritage`, `modern`, `minimalist`, etc. |
| `preferred_collection` | `VARCHAR(64)` | NULL | Learned: most-discussed collection |
| `favorite_metals` | `TEXT[]` | DEFAULT `'{}'` | Learned: e.g. `{silver, gold}` |
| `favorite_styles` | `TEXT[]` | DEFAULT `'{}'` | Learned tags |
| `role` | `VARCHAR(16)` | NOT NULL DEFAULT `'client'` | `client` \| `concierge` \| `admin` |
| `status` | `VARCHAR(16)` | NOT NULL DEFAULT `'active'` | `active` \| `suspended` \| `deleted` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | First login timestamp |
| `last_seen_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | Updated on every authed request |

**Indexes**:
- `PRIMARY KEY (id)`
- `UNIQUE (wp_user_id)` — hot path for auth lookup
- `UNIQUE (email)` — for admin search
- `INDEX (last_seen_at)` — for engagement analytics

**Validation rules**:
- `email` must match basic regex; normalized to lowercase on write
- `age_range` must be one of the allowlist: `{18-24, 25-34, 35-44, 45-54, 55+}`
- `skin_tone` must be one of: `{warm, cool, neutral}`
- `style_preference` free-form but capped at 64 chars
- `favorite_metals` / `favorite_styles` entries capped at 32 chars each, max 10 entries

---

## Table 2: `chat_messages`

Stores every user message and assistant reply. Used for (a) personalization summaries, (b) audit trail, (c) future analytics. **Not** replayed verbatim into prompts — prompt context remains capped at 15 entries from the caller (constitution VI.3).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | |
| `user_id` | `UUID` | NULL, FK → `users(id)` ON DELETE SET NULL | Null for anonymous |
| `visitor_id` | `UUID` | NOT NULL | Browser cookie id; persists across login for merge |
| `session_id` | `UUID` | NOT NULL | Reset on page load / logout; groups a single conversation |
| `role` | `VARCHAR(16)` | NOT NULL CHECK (`role IN ('user','assistant','system')`) | |
| `content` | `TEXT` | NOT NULL | Raw message content |
| `intent` | `VARCHAR(32)` | NULL | Classified intent: `product`, `compare`, `noor`, `bespoke`, `general`, `off_topic` |
| `skill` | `VARCHAR(32)` | NULL | Skill that handled the message |
| `routing_source` | `VARCHAR(16)` | NULL | `rule` \| `llm` \| `guardrail` |
| `latency_ms` | `INTEGER` | NULL | End-to-end latency for assistant turn |
| `rag_chunk_ids` | `TEXT[]` | DEFAULT `'{}'` | Qdrant chunk IDs used for grounding (audit) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | |

**Indexes**:
- `PRIMARY KEY (id)`
- `INDEX (user_id, created_at DESC)` — hot path: load last N for user
- `INDEX (visitor_id, created_at DESC)` — anonymous path
- `INDEX (session_id, created_at ASC)` — replay a conversation
- `INDEX (intent)` — analytics

**Retention**: Rows >12 months old are archived to cold storage (out of scope for Phase 2; tracked as follow-up).

**Merge-on-login behavior**: When an anonymous visitor authenticates, run `UPDATE chat_messages SET user_id = :new_id WHERE visitor_id = :vid AND user_id IS NULL` in the same transaction as the user upsert.

---

## Table 3: `appointments`

Formal appointment requests captured by the bot, fulfilled manually by concierge.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | |
| `reference_id` | `VARCHAR(20)` | UNIQUE NOT NULL | Public ID: `APT-XXXXXXXX` |
| `user_id` | `UUID` | NULL, FK → `users(id)` ON DELETE SET NULL | |
| `email` | `VARCHAR(255)` | NOT NULL | Captured at request time (may differ from user email) |
| `phone` | `VARCHAR(32)` | NULL | |
| `appointment_type` | `VARCHAR(32)` | NOT NULL CHECK (`appointment_type IN ('virtual','in-person','bespoke','general')`) | |
| `preferred_date` | `VARCHAR(255)` | NULL | Free-text ("next Tuesday afternoon") |
| `notes` | `TEXT` | NULL | User-provided context |
| `status` | `VARCHAR(16)` | NOT NULL DEFAULT `'pending'` CHECK (`status IN ('pending','confirmed','completed','cancelled')`) | |
| `confirmed_by` | `VARCHAR(128)` | NULL | Concierge who confirmed |
| `scheduled_at` | `TIMESTAMPTZ` | NULL | Final scheduled time after concierge confirmation |
| `meeting_link` | `VARCHAR(512)` | NULL | Zoom/Meet/Calendly link |
| `internal_notes` | `TEXT` | NULL | Concierge-only |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | Trigger-maintained |

**State machine**:
```
  [created]
     │
     ▼
  pending ──(concierge confirm)──► confirmed ──(date passes)──► completed
     │
     └────(user cancels / concierge declines)──► cancelled
```

**Indexes**:
- `PRIMARY KEY (id)`
- `UNIQUE (reference_id)`
- `INDEX (user_id, created_at DESC)`
- `INDEX (status, created_at DESC)` — concierge admin list

---

## Table 4: `noor_allocation_requests`

The **client-critical new table**. Tracks formal requests for the 143-piece Noor Collection.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | |
| `reference_id` | `VARCHAR(20)` | UNIQUE NOT NULL | Public ID: `NOR-XXXXXXXX` |
| `user_id` | `UUID` | NOT NULL, FK → `users(id)` | Noor requires authentication (no anonymous) |
| `full_name` | `VARCHAR(255)` | NOT NULL | Collected explicitly (may differ from account name) |
| `purpose` | `TEXT` | NOT NULL | Why they want Noor |
| `timeline` | `VARCHAR(128)` | NOT NULL | When needed |
| `delivery_location` | `VARCHAR(255)` | NOT NULL | Ship-to region |
| `contact_method` | `VARCHAR(16)` | NOT NULL CHECK (`contact_method IN ('email','phone','both')`) | |
| `contact_details` | `VARCHAR(255)` | NOT NULL | Email or phone string |
| `status` | `VARCHAR(16)` | NOT NULL DEFAULT `'pending'` CHECK (`status IN ('pending','approved','declined')`) | |
| `cooldown_until` | `TIMESTAMPTZ` | NULL | Set on approval: `submitted_at + 90 days` |
| `submitted_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | |
| `reviewed_at` | `TIMESTAMPTZ` | NULL | Concierge action timestamp |
| `reviewed_by` | `VARCHAR(128)` | NULL | Concierge identifier |
| `internal_notes` | `TEXT` | NULL | Concierge-only |
| `source` | `VARCHAR(32)` | NOT NULL DEFAULT `'AI Concierge'` | Provenance |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | Trigger |

**State machine**:
```
  [created]
     │
     ▼
  pending ──(concierge approve)──► approved  (sets cooldown_until = now + 90d)
     │
     └────(concierge decline)──► declined  (no cooldown; user may reapply)
```

**Cooldown enforcement** (application-level, pre-insert check):
```sql
-- Block if user has any pending OR approved-within-cooldown request
SELECT 1 FROM noor_allocation_requests
WHERE user_id = $1
  AND (status = 'pending'
       OR (status = 'approved' AND cooldown_until > now()))
LIMIT 1;
```

**Indexes**:
- `PRIMARY KEY (id)`
- `UNIQUE (reference_id)`
- `INDEX (user_id, status)` — cooldown check path (hot)
- `INDEX (status, submitted_at DESC)` — concierge admin list
- `INDEX (cooldown_until)` — analytics / cleanup

---

## Table 5: `user_activity`

Append-only audit / event log. Powers analytics, troubleshooting, and re-engagement.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, default `gen_random_uuid()` | |
| `user_id` | `UUID` | NOT NULL, FK → `users(id)` ON DELETE CASCADE | |
| `activity_type` | `VARCHAR(64)` | NOT NULL | e.g. `login`, `chat_message`, `appointment_created`, `noor_request_submitted`, `noor_request_approved`, `profile_updated` |
| `details` | `JSONB` | DEFAULT `'{}'::jsonb` | Event-specific payload |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT `now()` | |

**Indexes**:
- `PRIMARY KEY (id)`
- `INDEX (user_id, created_at DESC)` — user timeline
- `INDEX (activity_type, created_at DESC)` — type-filtered analytics
- `GIN (details)` — JSONB key lookups

**Write policy**: Writes are fire-and-forget via `asyncio.create_task()` — never block the client response. Failures are logged but do not fail the parent request.

---

## Global conventions

- **UUIDv4** for all PKs via `gen_random_uuid()` (pgcrypto)
- **`CITEXT`** for case-insensitive email (requires `CREATE EXTENSION IF NOT EXISTS citext;`)
- **`TIMESTAMPTZ`** everywhere (UTC) — never naive timestamps
- **`updated_at`** maintained by an `updated_at_trigger()` function shared across all tables that need it
- **Soft deletes** via `status = 'deleted'` rather than row removal — preserves audit trail and cross-table FKs
- **No raw SQL** outside `app/db/` (constitution II.2)

---

## Alembic migration plan

**`0001_initial.py`** creates everything in one migration:

```python
# pseudocode
op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

op.execute("""
  CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
  BEGIN NEW.updated_at = now(); RETURN NEW; END;
  $$ LANGUAGE plpgsql;
""")

op.create_table("users", ...)
op.create_table("chat_messages", ...)
op.create_table("appointments", ...)
op.create_table("noor_allocation_requests", ...)
op.create_table("user_activity", ...)

# Apply updated_at triggers to appointments, noor_allocation_requests, users
for tbl in ("users", "appointments", "noor_allocation_requests"):
    op.execute(f"""
      CREATE TRIGGER {tbl}_set_updated_at
      BEFORE UPDATE ON {tbl}
      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)
```

Downgrade drops all tables in reverse dependency order.

---

## Relationship to existing entities

From `spec.md`:
- **ChatRequest / ChatResponse** — unchanged shape; behavior now persists to `chat_messages` if authed
- **Skill** — unchanged
- **RAGChunk** — unchanged; chunk IDs used for grounding are now logged to `chat_messages.rag_chunk_ids`
- **ConversationContext** — still caller-supplied; server caps at 15; server-side personalization is additive, not replacing
- **SkillRouter** — unchanged
