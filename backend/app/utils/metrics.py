"""T205: Prometheus metrics — counters, histograms, and a small registry.

Default metrics live on the global REGISTRY so we can scrape them via
`prometheus_client.generate_latest()`. Lazy import in `routes.py` keeps the
dependency optional in test environments.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram


CHAT_REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total chat requests received, labeled by intent and result.",
    ["intent", "result"],
)


CHAT_LATENCY_SECONDS = Histogram(
    "chat_latency_seconds",
    "End-to-end /chat latency in seconds.",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0),
)


RATE_LIMIT_HITS_TOTAL = Counter(
    "rate_limit_hits_total",
    "Number of requests blocked by the rate limiter.",
)


OPENAI_ERRORS_TOTAL = Counter(
    "openai_errors_total",
    "Total OpenAI errors after retry, labeled by kind.",
    ["kind"],  # 'timeout', 'error', 'rate_limit'
)


NEON_ERRORS_TOTAL = Counter(
    "neon_errors_total",
    "Total Neon Postgres errors caught by repositories / persistence writer.",
)


NOTIFICATION_FAILURES_TOTAL = Counter(
    "notification_failures_total",
    "Resend notification failures (best-effort sends).",
    ["channel"],  # 'email'
)


NOOR_REQUESTS_TOTAL = Counter(
    "noor_requests_total",
    "Noor allocation submissions, labeled by outcome.",
    ["outcome"],  # 'created', 'blocked_pending', 'blocked_cooldown'
)


APPOINTMENT_REQUESTS_TOTAL = Counter(
    "appointment_requests_total",
    "Appointment submissions, labeled by appointment_type.",
    ["appointment_type"],
)


TOKENS_USED_TOTAL = Counter(
    "tokens_used_total",
    "Total tokens consumed by AI model calls, labeled by type.",
    ["type"],  # 'prompt', 'completion'
)
