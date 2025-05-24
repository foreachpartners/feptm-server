"""Utility functions for the application."""

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

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


def parse_decimal_safely(value: str, default: Decimal = Decimal("0")) -> Decimal:
    """Parse string to Decimal safely.

    Args:
        value: String value to parse
        default: Default value if parsing fails

    Returns:
        Parsed Decimal value or default
    """
    if not value or not value.strip():
        return default

    try:
        # Replace comma with dot for European number format
        cleaned_value = value.strip().replace(",", ".")
        return Decimal(cleaned_value)
    except (InvalidOperation, ValueError):
        return default


def parse_date_safely(value: str, date_format: str) -> Optional[datetime]:
    """Parse string to datetime safely.

    Args:
        value: String value to parse
        date_format: Expected date format

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not value or not value.strip():
        return None

    try:
        return datetime.strptime(value.strip(), date_format)
    except ValueError:
        return None


def clean_string_value(value: str) -> Optional[str]:
    """Clean and validate string value.

    Args:
        value: String value to clean

    Returns:
        Cleaned string or None if empty
    """
    if not value:
        return None

    cleaned = value.strip()
    return cleaned if cleaned else None


def validate_required_fields(data: dict, required_fields: List[str]) -> List[str]:
    """Validate that required fields are present and not empty.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        List of missing field names
    """
    missing_fields = []

    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)

    return missing_fields


def generate_timesheet_title(specialist_name: str, project_name: str) -> str:
    """Generate a standard timesheet title.

    Args:
        specialist_name: Name of the specialist
        project_name: Name of the project

    Returns:
        Formatted timesheet title
    """
    return f"Time Tracking for {specialist_name}. Project {project_name}"


def extract_id_from_hyperlink_formula(formula: str) -> Optional[str]:
    """Extract ID from Google Sheets HYPERLINK formula.

    Args:
        formula: HYPERLINK formula string

    Returns:
        Extracted ID or None if not found
    """
    if not formula:
        return None

    # Handle both HYPERLINK formulas and direct URLs
    try:
        url = formula

        # If it's a HYPERLINK formula, extract the URL
        if "HYPERLINK" in formula:
            # HYPERLINK formula format: =HYPERLINK("url"; "text") or =HYPERLINK("url", "text")
            start_quote = formula.find('"') + 1
            end_quote = formula.find('"', start_quote)

            if start_quote > 0 and end_quote > start_quote:
                url = formula[start_quote:end_quote]

        # Extract ID from URL
        if "drive.google.com" in url:
            # For drive folders: https://drive.google.com/drive/folders/FOLDER_ID
            if "/folders/" in url:
                return url.split("/folders/")[-1].split("?")[0].split("/")[0]
            # For files: https://drive.google.com/file/d/FILE_ID
            elif "/file/d/" in url:
                return url.split("/file/d/")[-1].split("/")[0]

        elif "docs.google.com/spreadsheets" in url:
            # For spreadsheets: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID
            if "/spreadsheets/d/" in url:
                return url.split("/spreadsheets/d/")[-1].split("/")[0].split("?")[0]

        # Fallback: try to extract ID as last part after /
        if "/" in url:
            potential_id = url.split("/")[-1].split("?")[0]
            # Check if it looks like a Google ID (alphanumeric, underscores, hyphens)
            if len(potential_id) > 20 and all(
                c.isalnum() or c in "_-" for c in potential_id
            ):
                return potential_id

    except Exception:
        pass

    return None
