"""
File logging configuration with queue-based writing and rotation.
Provides non-blocking file logging with automatic rotation.
"""

import logging
import os
import queue
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from .structured_logger import StructuredFormatter


class FileLogger:
    """Queue-based file logger with rotation capabilities."""

    def __init__(
        self,
        log_file_path: str = "logs/app.log",
        max_bytes: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 5,
        log_level: str = "INFO",
        use_json_format: bool = True,
    ):
        self.log_file_path = log_file_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_level = log_level
        self.use_json_format = use_json_format
        self._log_queue = queue.Queue()
        self._listener: QueueListener | None = None
        self._queue_handler: QueueHandler | None = None

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def setup_file_handler(self) -> RotatingFileHandler:
        """Set up rotating file handler with appropriate formatter."""
        file_handler = RotatingFileHandler(
            self.log_file_path, maxBytes=self.max_bytes, backupCount=self.backup_count
        )
        file_handler.setLevel(getattr(logging, self.log_level.upper()))

        if self.use_json_format:
            formatter = StructuredFormatter(
                fmt="%(timestamp)s %(level)s %(transaction_id)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(transaction_id)s | "
                "%(filename)s:%(lineno)d | %(message)s"
            )

        file_handler.setFormatter(formatter)
        return file_handler

    def setup_console_handler(self) -> logging.StreamHandler:
        """Set up console handler with appropriate formatter."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level.upper()))

        if self.use_json_format:
            formatter = StructuredFormatter(
                fmt="%(timestamp)s %(level)s %(transaction_id)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        else:
            formatter = logging.Formatter(
                "\033[1;32m%(asctime)s\033[0m | "
                "\033[1;34m%(levelname)s\033[0m | "
                "\033[1;33m%(filename)s:%(lineno)d\033[0m | %(message)s"
            )

        console_handler.setFormatter(formatter)
        return console_handler

    def start_queue_listener(self, handlers: list[logging.Handler]) -> None:
        """Start the queue listener with provided handlers."""
        self._listener = QueueListener(
            self._log_queue, *handlers, respect_handler_level=True
        )
        self._listener.daemon = True
        self._listener.start()

    def get_queue_handler(self) -> QueueHandler:
        """Get the queue handler for adding to loggers."""
        if self._queue_handler is None:
            self._queue_handler = QueueHandler(self._log_queue)
            self._queue_handler.setLevel(getattr(logging, self.log_level.upper()))
        return self._queue_handler

    def stop(self) -> None:
        """Stop the queue listener gracefully."""
        if self._listener:
            self._listener.stop()
            self._listener = None


def setup_file_logging(
    enabled: bool = True,
    log_file_path: str = "logs/app.log",
    log_level: str = "INFO",
    use_json_format: bool = True,
    max_bytes: int = 50 * 1024 * 1024,
    backup_count: int = 5,
) -> FileLogger | None:
    """
    Set up file logging with queue-based writing.

    Args:
        enabled: Whether to enable file logging
        log_file_path: Path to the log file
        log_level: Logging level
        use_json_format: Whether to use JSON formatting
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        FileLogger instance if enabled, None otherwise
    """
    if not enabled:
        return None

    try:
        file_logger = FileLogger(
            log_file_path=log_file_path,
            max_bytes=max_bytes,
            backup_count=backup_count,
            log_level=log_level,
            use_json_format=use_json_format,
        )

        handlers = []
        console_handler = file_logger.setup_console_handler()
        handlers.append(console_handler)

        file_handler = file_logger.setup_file_handler()
        handlers.append(file_handler)

        file_logger.start_queue_listener(handlers)

        return file_logger

    except Exception as e:
        logging.error(f"Failed to setup file logging: {e}")
        return None


def configure_external_loggers(queue_handler: QueueHandler) -> None:
    """Configure external library loggers to use our queue handler."""
    external_loggers = [
        "urllib3",
        "sqlalchemy",
        "uvicorn",
        "fastapi",
        "asyncmy",
        "aiohttp",
    ]

    for logger_name in external_loggers:
        ext_logger = logging.getLogger(logger_name)
        ext_logger.handlers.clear()
        ext_logger.addHandler(queue_handler)
        ext_logger.propagate = False

        if logger_name in ["urllib3"]:
            ext_logger.setLevel(logging.WARNING)
        elif logger_name == "sqlalchemy":
            ext_logger.setLevel(logging.WARNING)
        else:
            ext_logger.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(queue_handler)
    root_logger.setLevel(logging.INFO)

    logging.captureWarnings(True)
    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.handlers.clear()
    warnings_logger.addHandler(queue_handler)
    warnings_logger.propagate = False
    warnings_logger.setLevel(logging.WARNING)
