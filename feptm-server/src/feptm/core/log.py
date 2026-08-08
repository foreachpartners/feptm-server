"""Logging configuration for the application."""

import logging
import sys

from feptm.core.config import settings

# Define log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int | None = None,
    format_str: str = DEFAULT_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> None:
    """
    Setup basic logging configuration.

    Args:
        level: Logging level (defaults to DEBUG in dev mode, INFO in production)
        format_str: Log message format
        date_format: Date format for log messages
    """
    if level is None:
        level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Configure basic logging with console handler
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set level for external libraries
    for logger_name in ["uvicorn", "uvicorn.error", "fastapi"]:
        ext_logger = logging.getLogger(logger_name)
        ext_logger.handlers = []
        ext_logger.propagate = True


# Initialize logging with default settings
setup_logging()

# Create global logger to be used across the application
log = logging.getLogger("feptm")
