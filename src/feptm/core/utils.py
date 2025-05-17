"""Utility functions for the application."""

import uuid
from datetime import datetime
from typing import Any, Dict

from feptm.core.config import settings
from feptm.core.log import log


def generate_uuid() -> str:
    """Generate a UUID string.

    Returns:
        str: UUID as string
    """
    return str(uuid.uuid4())


def format_date(date: datetime) -> str:
    """Format a date object to string.

    Args:
        date: Date to format

    Returns:
        str: Formatted date string
    """
    return date.strftime("%Y-%m-%d")


def format_date_range(start_date: datetime, end_date: datetime) -> str:
    """Format a date range to string.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        str: Formatted date range string
    """
    if start_date.month == end_date.month and start_date.year == end_date.year:
        return f"{start_date.strftime('%b %Y')}"
    elif start_date.year == end_date.year:
        return f"{start_date.strftime('%b')} - {end_date.strftime('%b %Y')}"
    else:
        return f"{start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')}"
