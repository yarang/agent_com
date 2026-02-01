"""
Structured logging configuration for MCP Broker Server.

This module provides centralized logging setup with support for both
JSON and text formatted logs, appropriate for development and production.
"""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Type alias for log context
LogContext = dict[str, Any]


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for production environments.

    Formats log records as JSON objects with consistent field names
    for parsing and analysis in log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        import json

        # Create base log entry
        log_entry: LogContext = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra context from record
        if hasattr(record, "context"):
            log_entry["context"] = record.context  # type: ignore

        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable log formatter for development environments.

    Formats log records as readable text with colors for terminal output.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as colored text string.

        Args:
            record: The log record to format

        Returns:
            Formatted log string with colors
        """
        color = self.COLORS.get(record.levelname, "")
        level = f"{color}{record.levelname}{self.RESET}"
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        logger_name = record.name

        message = record.getMessage()
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return f"{timestamp} | {level:8} | {logger_name}: {message}"


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Path | None = None,
) -> None:
    """Configure logging for the MCP Broker Server.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Log format ('json' or 'text')
        log_file: Optional path to log file

    Example:
        >>> setup_logging(level="DEBUG", format_type="text")
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on format type
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = TextFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Server started")
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding structured context to log records.

    Example:
        >>> with LogContext("session_id", session_id):
        ...     logger.info("Session connected")
        ...
        >>> with LogContext({"session_id": sid, "message_id": mid}):
        ...     logger.info("Message delivered")
    """

    def __init__(self, key: str | LogContext, value: Any = None) -> None:
        """Initialize log context.

        Args:
            key: Context key or dict of multiple key-value pairs
            value: Context value (if key is a string)
        """
        if isinstance(key, dict):
            self.context: LogContext = key
        else:
            self.context = {key: value}

    def __enter__(self) -> None:
        """Add context to logger factory."""
        self._old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self._old_factory(*args, **kwargs)
            record.context = self.context  # type: ignore
            return record

        logging.setLogRecordFactory(record_factory)

    def __exit__(self, *args: Any) -> None:
        """Restore original logger factory."""
        logging.setLogRecordFactory(self._old_factory)
