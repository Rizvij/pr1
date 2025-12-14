"""
Request tracking middleware for logging correlation.
Provides transaction ID generation and request/response logging.
"""

import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for transaction ID
_transaction_id: ContextVar[str | None] = ContextVar("transaction_id", default=None)


def generate_transaction_id() -> str:
    """Generate a unique transaction ID for request tracking."""
    return str(uuid.uuid4())[:8]


def get_transaction_id() -> str:
    """Get the current transaction ID or generate a new one."""
    txn_id = _transaction_id.get()
    if txn_id is None:
        txn_id = generate_transaction_id()
        _transaction_id.set(txn_id)
    return txn_id


def set_transaction_id(txn_id: str) -> None:
    """Set the transaction ID for the current context."""
    _transaction_id.set(txn_id)


class TransactionIdFilter(logging.Filter):
    """Logging filter that adds transaction ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add transaction ID to the log record."""
        record.transaction_id = get_transaction_id()
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request/response logging with transaction tracking."""

    def __init__(self, app, logger: logging.Logger | None = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger("proryx_backend.requests")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging and transaction tracking."""
        txn_id = generate_transaction_id()
        set_transaction_id(txn_id)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        self.logger.info(
            "Request started",
            extra={
                "transaction_id": txn_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
            },
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            self.logger.info(
                "Request completed",
                extra={
                    "transaction_id": txn_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "response_size": response.headers.get("content-length"),
                    "content_type": response.headers.get("content-type"),
                },
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            self.logger.error(
                "Request failed",
                extra={
                    "transaction_id": txn_id,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "transaction_id": txn_id},
            )


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware that only sets transaction ID without detailed logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Set transaction ID for the request context."""
        txn_id = request.headers.get("x-transaction-id")
        if not txn_id:
            txn_id = generate_transaction_id()

        set_transaction_id(txn_id)

        response = await call_next(request)
        response.headers["x-transaction-id"] = txn_id

        return response


def setup_logging_middleware() -> TransactionIdFilter:
    """Set up logging middleware components."""
    return TransactionIdFilter()
