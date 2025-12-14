"""
Central logging configuration for ProRyx.
Provides setup functions and logger management.
"""

import logging
import os

from .file_logger import FileLogger, configure_external_loggers, setup_file_logging
from .middleware import TransactionIdFilter, setup_logging_middleware
from .structured_logger import setup_structured_logging


class LoggingConfig:
    """Central logging configuration manager."""

    def __init__(self):
        self.file_logger: FileLogger | None = None
        self.transaction_filter: TransactionIdFilter | None = None
        self._is_configured = False

    def setup(
        self,
        log_to_file: bool = True,
        log_level: str = "INFO",
        log_file_path: str = "logs/app.log",
        use_json_format: bool = True,
        max_bytes: int = 50 * 1024 * 1024,
        backup_count: int = 5,
    ) -> logging.Logger:
        """
        Set up comprehensive logging configuration.

        Args:
            log_to_file: Whether to enable file logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file_path: Path to the log file
            use_json_format: Whether to use JSON formatting
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep

        Returns:
            Configured main logger instance
        """
        if self._is_configured:
            return get_logger()

        self.transaction_filter = setup_logging_middleware()

        if log_to_file:
            self.file_logger = setup_file_logging(
                enabled=True,
                log_file_path=log_file_path,
                log_level=log_level,
                use_json_format=use_json_format,
                max_bytes=max_bytes,
                backup_count=backup_count,
            )

            if self.file_logger:
                queue_handler = self.file_logger.get_queue_handler()
                queue_handler.addFilter(self.transaction_filter)
                configure_external_loggers(queue_handler)
        else:
            logger = setup_structured_logging(log_level)

            for handler in logger.handlers:
                handler.addFilter(self.transaction_filter)

        main_logger = get_logger()
        self._is_configured = True

        return main_logger

    def shutdown(self) -> None:
        """Shutdown logging gracefully."""
        if self.file_logger:
            self.file_logger.stop()
        self._is_configured = False


# Global logging configuration instance
_logging_config = LoggingConfig()


def setup_logging(
    log_to_file: bool | None = None,
    log_level: str | None = None,
    log_file_path: str | None = None,
    use_json_format: bool | None = None,
) -> logging.Logger:
    """
    Set up logging with environment variable support.

    Args:
        log_to_file: Whether to enable file logging (env: LOG_TO_FILE)
        log_level: Logging level (env: LOG_LEVEL)
        log_file_path: Path to log file (env: LOG_FILE_PATH)
        use_json_format: Whether to use JSON format (env: LOG_FORMAT=json)

    Returns:
        Configured main logger instance
    """
    if log_to_file is None:
        log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    if log_file_path is None:
        log_file_path = os.getenv("LOG_FILE_PATH", "logs/app.log")

    if use_json_format is None:
        log_format = os.getenv("LOG_FORMAT", "json").lower()
        use_json_format = log_format == "json"

    return _logging_config.setup(
        log_to_file=log_to_file,
        log_level=log_level,
        log_file_path=log_file_path,
        use_json_format=use_json_format,
    )


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name (will be prefixed with app name)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"proryx_backend.{name}")
    return logging.getLogger("proryx_backend")


def shutdown_logging() -> None:
    """Shutdown logging gracefully."""
    _logging_config.shutdown()
