"""End-to-end smoke test against local server + Neon + Upstash.

Verifies:
  1. /health                        → 200
  2. /chat                          → 200, reply non-empty, DB chat_messages row
  3. /appointment-request           → 200, DB appointments row
  4. Admin (no token)               → 401
  5. Admin (bad token)              → 401
  6. Admin (good token)             → 200
  7. Rate limit (30 rapid chats)    → some 429 (Upstash working)

Run the server first:
    uv run uvicorn app.main:app --port 8000

Then run:
    uv run python smoke_test.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

BASE = "http://127.0.0.1:8000"
ADMIN_TOKEN = os.getenv("ADMIN_API_TOKEN", "")
DB_URL = os.getenv("NEON_DATABASE_URL", "")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}[PASS]{RESET} {msg}")


def fail(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")


def info(msg):
    print(f"{YELLOW}[..]{RESET} {msg}")


results = {"passed": 0, "failed": 0}


def check(cond, msg):
    if cond:
        ok(msg)
        results["passed"] += 1
    else:
        fail(msg)
        results["failed"] += 1


async def db_count_recent(table: str, minutes: int = 5) -> int:
    """Count rows in a table created in the last N minutes via direct SQL."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        col = "created_at" if table == "appointments" else "created_at"
        q = text(f"SELECT COUNT(*) FROM {table} WHERE {col} > NOW() - INTERVAL '{minutes} minutes'")
        result = await conn.execute(q)
        count = result.scalar() or 0
    await engine.dispose()
    return count


async def main():
    print(f"\n{'='*60}")
    print("AUESHAH CONCIERGE — END-TO-END SMOKE TEST")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(base_url=BASE, timeout=30) as ac:
        # 1. /health
        info("1. /health")
        r = await ac.get("/health")
        check(r.status_code == 200 and r.json().get("status") == "ok", f"/health → 200 {r.json()}")

        # 2. /chat (baseline count first)
        info("\n2. /chat")
        before = await db_count_recent("chat_messages", minutes=5)
        r = await ac.post("/chat", json={"message": "Tell me about the Noor collection"})
        check(r.status_code == 200, f"/chat → status {r.status_code}")
        body = r.json() if r.status_code == 200 else {}
        reply = body.get("reply", "")
        check(len(reply) > 20, f"/chat reply length {len(reply)} chars")
        meta = body.get("metadata", {})
        info(f"   skill={meta.get('skill')}, intent={meta.get('intent')}, latency={meta.get('latency_ms')}ms")

        # Let fire-and-forget persistence settle
        await asyncio.sleep(3)
        after = await db_count_recent("chat_messages", minutes=5)
        check(after > before, f"chat_messages row persisted to Neon (before={before}, after={after})")

        # 3. /appointment-request
        info("\n3. /appointment-request")
        apt_before = await db_count_recent("appointments", minutes=5)
        r = await ac.post("/appointment-request", json={
            "email": "smoketest@aueshah.com",
            "appointment_type": "virtual",
            "phone": "+44 7000 000000",
            "preferred_date": "2026-05-20 14:00 GMT",
            "notes": "Smoke test — please ignore.",
        })
        check(r.status_code == 200, f"/appointment-request → {r.status_code}")
        apt_body = r.json() if r.status_code == 200 else {}
        ref_id = apt_body.get("reference_id", "")
        check(ref_id.startswith("APT-"), f"reference_id={ref_id}")

        await asyncio.sleep(1)
        apt_after = await db_count_recent("appointments", minutes=5)
        check(apt_after > apt_before, f"appointments row persisted to Neon ({apt_before} → {apt_after})")

        # 4. Admin — no token
        info("\n4. Admin auth gate")
        r = await ac.get("/v1/admin/noor-requests")
        check(r.status_code == 401, f"admin without token → 401 (got {r.status_code})")

        # 5. Admin — bad token
        r = await ac.get("/v1/admin/noor-requests", headers={"X-Admin-Token": "wrong"})
        check(r.status_code == 401, f"admin with bad token → 401 (got {r.status_code})")

        # 6. Admin — good token
        r = await ac.get("/v1/admin/noor-requests", headers={"X-Admin-Token": ADMIN_TOKEN})
        check(r.status_code == 200, f"admin with correct token → 200 (got {r.status_code})")
        if r.status_code == 200:
            info(f"   returned {len(r.json())} requests")

        # 7. Rate limit — fire 30 chats rapidly
        info("\n5. Rate limit (Upstash)")
        rate_results = []
        async def bang(i):
            try:
                rr = await ac.post("/chat", json={"message": f"ping {i}"}, timeout=10)
                return rr.status_code
            except Exception:
                return 0
        codes = await asyncio.gather(*[bang(i) for i in range(35)])
        n_200 = sum(1 for c in codes if c == 200)
        n_429 = sum(1 for c in codes if c == 429)
        info(f"   35 concurrent /chat → {n_200}×200, {n_429}×429, other: {35 - n_200 - n_429}")
        check(n_429 > 0, f"rate limiter tripped on burst (saw {n_429} × 429 responses)")

    print(f"\n{'='*60}")
    print(f"RESULT: {GREEN}{results['passed']} passed{RESET}, {RED}{results['failed']} failed{RESET}")
    print(f"{'='*60}\n")
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
