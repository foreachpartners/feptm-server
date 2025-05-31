"""Logging formatters for the application."""

import json
import logging
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self) -> None:
        """Initialize the formatter."""
        super().__init__()
        self.default_fields = {
            "timestamp": "",
            "level": "",
            "logger": "",
            "message": "",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string containing log data
        """
        message = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields from the record
        if hasattr(record, "extra"):
            message.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            message["exception"] = self.formatException(record.exc_info)

        return json.dumps(message)
