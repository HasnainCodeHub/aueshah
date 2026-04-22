"""T207: Structured logging — JSON formatter with request-scoped context.

`request_id` (and optionally `user_id` / `visitor_id`) are stored on a
`ContextVar` so any logger.info() inside a request automatically carries them
without threading them through every call.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional


_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_visitor_id_var: ContextVar[Optional[str]] = ContextVar("visitor_id", default=None)


def set_request_context(
    *,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    visitor_id: Optional[str] = None,
) -> tuple:
    """Set per-request log context. Returns the prior tokens for `reset_context`."""
    rid = request_id or uuid.uuid4().hex
    return (
        _request_id_var.set(rid),
        _user_id_var.set(user_id),
        _visitor_id_var.set(visitor_id),
    )


def reset_request_context(tokens: tuple) -> None:
    rid_t, uid_t, vid_t = tokens
    _request_id_var.reset(rid_t)
    _user_id_var.reset(uid_t)
    _visitor_id_var.reset(vid_t)


def get_request_id() -> Optional[str]:
    return _request_id_var.get()


_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
}


class JSONFormatter(logging.Formatter):
    """Emit each LogRecord as a single JSON object, enriched with request context."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        rid = _request_id_var.get()
        if rid:
            log_obj["request_id"] = rid
        uid = _user_id_var.get()
        if uid:
            log_obj["user_id"] = uid
        vid = _visitor_id_var.get()
        if vid:
            log_obj["visitor_id"] = vid

        # Surface common extras the codebase already passes via `extra=...`.
        for key in (
            "component", "intent", "skill", "latency_ms", "route",
            "reference_id", "ip", "code", "error_code", "count", "limit",
            "to", "subject", "status", "decision", "reviewed_by", "path",
        ):
            val = getattr(record, key, None)
            if val is not None:
                log_obj[key] = val

        # Catch any other one-off keys passed by callers.
        for key, val in record.__dict__.items():
            if key in _RESERVED or key in log_obj or key.startswith("_"):
                continue
            try:
                json.dumps(val)
            except (TypeError, ValueError):
                continue
            log_obj[key] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure stdout JSON logging."""
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger(name), {})
