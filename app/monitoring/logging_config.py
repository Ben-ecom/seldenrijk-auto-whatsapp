"""
Structured logging configuration using structlog.
Provides JSON-formatted logs with context and correlation IDs.
"""
import logging
import sys
import os
from typing import Any
import structlog
from structlog.types import Processor

def configure_logging(log_level: str = None) -> None:
    """
    Configure structured logging with structlog.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Shared processors for both dev and prod
    shared_processors: list[Processor] = [
        # Add log level
        structlog.stdlib.add_log_level,

        # Add logger name
        structlog.stdlib.add_logger_name,

        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),

        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),

        # Format exception info
        structlog.processors.format_exc_info,

        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Development vs Production formatting
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "development":
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
    else:
        # JSON output for production (better for log aggregation)
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    print(f"✅ Logging configured (level: {log_level}, environment: {environment})")

def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)

# Context manager for adding request context to logs
class LogContext:
    """
    Context manager for adding contextual information to all logs.

    Example:
        with LogContext(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
    """

    def __init__(self, **context):
        self.context = context
        self.token = None

    def __enter__(self):
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars(*self.context.keys())

# Middleware for adding request_id to logs
def add_request_id(request_id: str) -> None:
    """
    Add request_id to all subsequent logs in the current context.

    Args:
        request_id: Unique request identifier
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)

def clear_request_context() -> None:
    """Clear all contextual variables from logs."""
    structlog.contextvars.clear_contextvars()
