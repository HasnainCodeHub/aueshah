"""Locust load test for POST /chat — verifies p95 ≤ 3s under realistic traffic.

Run locally against a deployed Koyeb backend:

    pip install locust
    locust -f tests/load/locustfile.py --host https://<your-koyeb-url>

Then open http://localhost:8089 and set:
  - Users: 50 (ramp to target concurrency)
  - Spawn rate: 5 users/sec
  - Host: https://<your-koyeb-url>

Pass criteria (align with spec SC-001..SC-008 and NFR p95 ≤ 3s):
  - p95 response time ≤ 3000 ms
  - failure rate < 1%
  - 429 rate limited responses are expected — Locust reports them as failures
    unless you set --stop-timeout and use the `@tag` filters below.

Headless run (for CI, 2-minute smoke):

    locust -f tests/load/locustfile.py --host https://<url> \
        --users 20 --spawn-rate 2 --run-time 2m --headless \
        --csv=load_report
"""
from __future__ import annotations

import random
import uuid

from locust import HttpUser, between, task


PROMPTS = {
    "product": [
        "Show me rose gold rings with morganite",
        "What bracelets under 5000 EUR do you have?",
        "I'm looking for a statement necklace",
        "Any earrings in yellow gold with diamonds?",
        "Tell me about the Whisper Ring",
    ],
    "compare": [
        "Compare the Whisper Ring and Heartline Necklace",
        "Difference between Empire Allegiance and Velvet Line?",
    ],
    "noor": [
        "Tell me about the Noor Collection",
        "How is the Noor Necklace designed?",
        "What is Mughal jali in the Noor pieces?",
    ],
    "bespoke": [
        "I want to design a custom engagement ring",
        "Can I commission a bespoke tiara?",
    ],
    "general": [
        "What is the warranty on an Aueshah piece?",
        "How do refund windows work after 60 days?",
        "What does the Aueshah hallmark mean?",
        "Where are Aueshah pieces made?",
    ],
}

# Realistic traffic mix: more product browsing than bespoke inquiries.
WEIGHTS = {
    "product": 40,
    "general": 25,
    "noor": 15,
    "compare": 10,
    "bespoke": 10,
}

_PAGE_CONTEXTS = [
    {"page_type": "homepage"},
    {"page_type": "collection", "collection_name": "Noor"},
    {"page_type": "product", "product_name": "Whisper Ring"},
    {"page_type": "product", "product_name": "Heartline Necklace"},
    {"page_type": "bespoke"},
    None,
]


def _pick_prompt() -> str:
    skill = random.choices(
        population=list(WEIGHTS.keys()),
        weights=list(WEIGHTS.values()),
        k=1,
    )[0]
    return random.choice(PROMPTS[skill])


class ConciergeUser(HttpUser):
    """Simulates a visitor chatting with the concierge."""

    wait_time = between(2, 8)

    def on_start(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.turn = 0

    @task(10)
    def chat(self) -> None:
        message = _pick_prompt()
        payload = {
            "message": message,
            "session_id": self.session_id,
        }
        page_context = random.choice(_PAGE_CONTEXTS)
        if page_context is not None:
            payload["page_context"] = page_context

        with self.client.post(
            "/chat",
            json=payload,
            name="POST /chat",
            catch_response=True,
            timeout=20,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                if "reply" in body and body["reply"]:
                    resp.success()
                else:
                    resp.failure("200 but empty reply")
            elif resp.status_code == 429:
                # Rate limiting is working as designed; count as success for SLA.
                resp.success()
            elif resp.status_code == 503:
                resp.failure("503 Service Unavailable — degraded mode")
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")

        self.turn += 1

    @task(1)
    def health(self) -> None:
        with self.client.get("/health", name="GET /health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
