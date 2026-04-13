"""Structured logging setup."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "component"):
            log_obj["component"] = record.component
        if hasattr(record, "intent"):
            log_obj["intent"] = record.intent
        if hasattr(record, "skill"):
            log_obj["skill"] = record.skill
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get a logger with extra context support."""
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {})
