"""Core constants for the application."""

from enum import Enum


class DateFormat(str, Enum):
    """Date formats used in the application."""

    DISPLAY_DATETIME = "%Y-%m-%d %H:%M:%S UTC"
    SHEET_DATE = "%Y-%m-%d"
    SHEET_DISPLAY_DATE = "%b %d, %Y"
