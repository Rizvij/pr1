"""
Structured JSON logging configuration for ProRyx.
Provides JSON-formatted logs optimized for modern observability platforms.
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Any

try:
    from pythonjsonlogger.json import JsonFormatter

    BaseFormatter = JsonFormatter
except ImportError:
    from pythonjsonlogger.jsonlogger import JsonFormatter

    BaseFormatter = JsonFormatter

# Import get_transaction_id lazily to avoid circular import
get_txn_id = None


class StructuredFormatter(BaseFormatter):
    """Custom JSON formatter that adds standard fields for observability."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to every log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.now().astimezone().isoformat()

        # Add transaction ID from the record (set by middleware)
        global get_txn_id
        if get_txn_id is None:
            from proryx_backend.core.logging.middleware import (
                get_transaction_id as get_txn_id,
            )
        log_record["transaction_id"] = getattr(record, "transaction_id", get_txn_id())

        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger_name"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno
        log_record["filename"] = record.filename

        # Add service metadata
        log_record["service"] = {
            "name": "proryx-backend",
            "version": "0.1.0",
        }

        # Handle exceptions with full stack trace
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stacktrace": traceback.format_exception(*record.exc_info),
            }

        # Remove duplicate or internal fields
        for field in ["msg", "args", "created", "msecs", "relativeCreated", "pathname"]:
            log_record.pop(field, None)


def setup_structured_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up structured JSON logging for the application.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("proryx_backend")
    logger.setLevel(getattr(logging, log_level.upper()))

    logger.handlers = []

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    formatter = StructuredFormatter(
        fmt="%(timestamp)s %(level)s %(transaction_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Configure external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    return logger


def get_structured_logger(name: str | None = None) -> logging.Logger:
    """Get a structured logger instance."""
    if name:
        return logging.getLogger(f"proryx_backend.{name}")
    return logging.getLogger("proryx_backend")
