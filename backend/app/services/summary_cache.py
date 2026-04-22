"""T165: Per-user summary cache.

Avoids re-summarizing chat history on every turn. Keyed by user_id with a
short TTL so freshly-saved messages eventually feed into the next summary.
"""
from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from typing import Optional

DEFAULT_TTL_SECONDS = 600  # 10 min
DEFAULT_MAX_ENTRIES = 1024


class SummaryCache:
    """Simple in-process LRU with TTL — safe for single-process FastAPI workers."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: OrderedDict[str, tuple[float, str]] = OrderedDict()

    def get(self, user_id: uuid.UUID) -> Optional[str]:
        key = str(user_id)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, user_id: uuid.UUID, value: str) -> None:
        key = str(user_id)
        self._store[key] = (time.monotonic(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def invalidate(self, user_id: uuid.UUID) -> None:
        self._store.pop(str(user_id), None)

    def clear(self) -> None:
        self._store.clear()


_cache: SummaryCache | None = None


def get_summary_cache() -> SummaryCache:
    global _cache
    if _cache is None:
        _cache = SummaryCache()
    return _cache
