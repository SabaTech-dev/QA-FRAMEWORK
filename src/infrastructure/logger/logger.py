"""Structured logging with JSON and console formatters"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    This follows Interface Segregation Principle (ISP) by providing
    a specific formatter without forcing unnecessary methods.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack"] = self.formatStack(record.stack_info)

        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for human-readable logs"""

    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Colored string
        """
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


class QALogger:
    """
    QA Framework logger with structured and console output.

    This class follows Single Responsibility Principle (SRP) by only
    handling logging functionality.
    """

    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(cls, name: str = "qa-framework") -> logging.Logger:
        """
        Get or create logger.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)

            # Remove existing handlers
            logger.handlers.clear()

            # Console handler with colored output
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = ColoredConsoleFormatter(
                fmt="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def setup_file_logging(
        cls, log_file: Path, level: int = logging.DEBUG, use_json: bool = False
    ) -> None:
        """
        Setup file logging.

        Args:
            log_file: Path to log file
            level: Logging level
            use_json: Use JSON formatter
        """
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        if use_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(formatter)

        for logger in cls._loggers.values():
            logger.addHandler(file_handler)
