"""Logging configuration for the application."""

import logging
from pathlib import Path
from typing import Optional, List

from feptm.core.config import settings
from feptm.core.logging.handlers import get_console_handler, get_file_handler


def setup_logging(
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
) -> None:
    """Setup logging configuration with structured output and rotation.

    Args:
        level: Logging level (defaults to DEBUG in dev mode, INFO in production)
        log_file: Path to log file (optional)
    """
    if level is None:
        level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Get handlers
    handlers: List[logging.Handler] = [get_console_handler()]
    if log_file:
        file_handler = get_file_handler(log_file)
        if file_handler:
            handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
    )

    # Configure external loggers
    for logger_name in ["uvicorn", "uvicorn.error", "fastapi"]:
        ext_logger = logging.getLogger(logger_name)
        ext_logger.handlers = []
        ext_logger.propagate = True


# Initialize logging with default settings
log_file = settings.BASE_DIR / "logs" / "feptm.log" if not settings.DEBUG else None
setup_logging(log_file=log_file)

# Create global logger
log = logging.getLogger("feptm")


# Add context manager for structured logging
class LogContext:
    """Context manager for adding context to log messages."""

    def __init__(self, **kwargs) -> None:
        self.extra = kwargs
        self._old_factory = None

    def __enter__(self) -> None:
        if self.extra:
            old_factory = logging.getLogRecordFactory()

            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                record.extra = getattr(record, "extra", {})
                record.extra.update(self.extra)
                return record

            self._old_factory = old_factory
            logging.setLogRecordFactory(record_factory)

    def __exit__(self, *args) -> None:
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)
