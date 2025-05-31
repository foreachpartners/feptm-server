"""Logging handlers for the application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from feptm.core.config import settings
from feptm.core.logging.formatters import JSONFormatter


def get_console_handler() -> logging.StreamHandler:
    """Create console handler with JSON formatting.
    
    Returns:
        Configured console handler
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    return handler


def get_file_handler(
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> Optional[RotatingFileHandler]:
    """Create rotating file handler with JSON formatting.
    
    Args:
        log_file: Path to log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured file handler or None if log_file is not set
    """
    if not log_file:
        return None

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(JSONFormatter())
    return handler
