"""
app/utils/logger.py
--------------------
Structured logging setup using structlog.

Structured logging emits JSON-formatted log entries in production,
making logs searchable by fields (user_id, chat_id, status_code, etc.)
rather than requiring regex parsing of unstructured text.

Example output (dev mode):
  2024-01-15 10:30:45 [info     ] User logged in     username=alice

Example output (prod mode / JSON):
  {"event": "User logged in", "username": "alice", "level": "info", "timestamp": "..."}
"""

import logging
import sys

import structlog
from app.config.settings import settings


def setup_logging() -> None:
    """
    Configure structlog with appropriate renderers for dev vs production.
    Called once at application startup.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.DEBUG:
        # Human-readable colored output for development
        renderer = structlog.dev.ConsoleRenderer()
    else:
        # Machine-readable JSON for production log aggregation (e.g. CloudWatch, Datadog)
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a named structured logger.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("Something happened", user_id="123", action="login")
    """
    return structlog.get_logger(name)
