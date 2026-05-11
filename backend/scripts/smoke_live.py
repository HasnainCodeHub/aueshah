"""Smoke test against the /chat endpoint. Pass URL as first arg.

Usage:
    python scripts/smoke_live.py                                # defaults to local
    python scripts/smoke_live.py https://aueshah.onrender.com   # against live
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
ENDPOINT = f"{BASE.rstrip('/')}/chat"

QUERIES = [
    ("STORY",  "Tell me the Noor Collection Story."),
    ("STORY",  "What does 99 mean in the Noor Tiara price?"),
    ("STORY",  "Why does the Noor Ring cost 1,096 euros? What's the meaning behind the price?"),
    ("STORY",  "When is Noor's birthday?"),
    ("STORY",  "Who designed the Noor Collection and why?"),
    ("GATE",   "How many Noor pieces are left? What's the current stock?"),
    ("GATE",   "Can I buy a Noor Ring? I'd like to place an order."),
]

print(f"Target: {ENDPOINT}\n")
for tag, q in QUERIES:
    print(f"=== [{tag}] {q}")
    data = json.dumps({"message": q}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json", "Origin": "https://aueshah.com"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
        reply = body.get("reply", "")
        meta = body.get("metadata", {}) or {}
        print(f"   skill={meta.get('skill')} intent={meta.get('intent')} latency={meta.get('latency_ms')}ms")
        print(f"   reply: {reply}\n")
    except Exception as e:
        print(f"   ERROR: {e}\n")
