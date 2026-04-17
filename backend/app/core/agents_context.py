"""Thread-local context for passing request-scoped data into Agents SDK tool calls.

The Agents SDK function tools don't receive the FastAPI request — they're plain
async callables. We use a ContextVar to thread the authenticated user ID from
the route handler into the tool without coupling the SDK to FastAPI.
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional

_current_user_id: ContextVar[Optional[uuid.UUID]] = ContextVar("_current_user_id", default=None)


def set_current_user_id(user_id: Optional[uuid.UUID]) -> None:
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[uuid.UUID]:
    return _current_user_id.get()
