"""Mappers for converting between domain models and spreadsheet data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List

from feptm.adapters.sheets.constants import RowName
from feptm.core.constants import DateFormat
from feptm.core.exceptions import ValidationError
from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Rate, Specialist


def row_to_specialist(row: List[str], timesheet_id: str) -> Specialist:
    """Convert Team sheet row to Specialist domain model.

    FR-002.1: One row represents one rate period. Multiple rows with same
    Timesheet ID represent rate history. This function creates a Specialist
    with one rate period. Multiple calls with same timesheet_id should be
    merged to create a Specialist with multiple rates.

    Args:
        row: Team sheet row data [Name, Role, Internal Rate, External Rate, Start Date, Timesheet]
        timesheet_id: Timesheet ID (specialist identifier)

    Returns:
        Specialist domain model with one rate period

    Raises:
        ValidationError: If row data is invalid

    Note:
        Team sheet structure (FR-002.1):
        Name | Role | Internal Rate | External Rate | Start Date | Timesheet
    """
    if len(row) < 6:
        raise ValidationError(f"Invalid row data: expected 6 columns, got {len(row)}")

    name = row[0].strip() if row[0] else ""
    role = row[1].strip() if row[1] else ""
    internal_rate_str = row[2].strip() if row[2] else "0"
    external_rate_str = row[3].strip() if row[3] else "0"
    start_date_str = row[4].strip() if row[4] else ""
    row_timesheet_id = row[5].strip() if len(row) > 5 and row[5] else ""

    # Validate timesheet ID matches (for safety)
    if row_timesheet_id and row_timesheet_id != timesheet_id:
        raise ValidationError(
            f"Timesheet ID mismatch: expected {timesheet_id}, got {row_timesheet_id}"
        )

    if not name:
        raise ValidationError("Specialist name is required")

    if not role:
        raise ValidationError("Specialist role is required")

    # Parse rates
    try:
        internal_rate = Decimal(internal_rate_str)
        external_rate = Decimal(external_rate_str)
    except ValueError as e:
        raise ValidationError(f"Invalid rate value: {e}") from e

    # Parse start date (FR-002.1: YYYY-MM-DD format)
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationError(f"Invalid date format (expected YYYY-MM-DD): {e}") from e

    # Create rate
    rate = Rate(
        internal=internal_rate,
        external=external_rate,
        start_date=start_date,
    )

    # Create specialist with one rate
    specialist = Specialist(
        name=name,
        role=role,
        rates=[rate],
        joined_date=start_date,  # Use first rate start_date as joined_date
    )

    return specialist


def specialist_to_row(specialist: Specialist, timesheet_id: str) -> List[List[str]]:
    """Convert Specialist domain model to Team sheet rows.

    FR-002.1: One Specialist may produce multiple rows (one per rate period).

    Args:
        specialist: Specialist domain model (may contain multiple rates)
        timesheet_id: Timesheet ID (specialist identifier)

    Returns:
        List of rows, one per rate period

    Note:
        Each row: [Name, Role, Internal Rate, External Rate, Start Date, Timesheet]
    """
    rows = []
    for rate in sorted(specialist.rates, key=lambda r: r.start_date):
        row = [
            specialist.name,
            specialist.role,
            str(rate.internal),
            str(rate.external),
            rate.start_date.strftime("%Y-%m-%d"),
            timesheet_id,
        ]
        rows.append(row)
    return rows


def merge_specialists_by_timesheet_id(
    specialists: List[Specialist],
) -> List[Specialist]:
    """Merge specialists with same name into one with multiple rate periods.

    FR-002.1: Multiple rows with same Timesheet ID represent rate history.
    This function merges them into a single Specialist with multiple rates.

    Args:
        specialists: List of specialists (each with one rate period)

    Returns:
        List of merged specialists (each with multiple rate periods)

    Note:
        Specialists are grouped by name. In real implementation, grouping
        should be done by Timesheet ID from Team sheet.
    """
    # Group by name (in real implementation, group by timesheet_id)
    grouped: dict[str, Specialist] = {}
    for spec in specialists:
        if spec.name not in grouped:
            grouped[spec.name] = Specialist(
                name=spec.name,
                role=spec.role,
                rates=spec.rates.copy(),
                joined_date=spec.joined_date,
            )
        else:
            # Merge rates
            existing = grouped[spec.name]
            for rate in spec.rates:
                if rate.start_date not in {r.start_date for r in existing.rates}:
                    existing.add_rate(rate)

    return list(grouped.values())


def project_to_row(project: Project, project_id: str) -> List[List[str]]:
    """Convert Project domain model to Project Info sheet rows.

    Args:
        project: Project domain model
        project_id: External project ID (spreadsheet ID)

    Returns:
        List of rows for Project Info sheet

    Note:
        Project Info sheet structure:
        Field | Value
        Project ID | {spreadsheet_id}
        Name | {project_name}
        Created | {datetime}
    """
    from feptm.core.constants import DateFormat

    return [
        [RowName.FIELD.value, RowName.VALUE.value],
        [RowName.PROJECT_ID.value, project_id],
        [RowName.NAME.value, project.name],
        [
            RowName.CREATED.value,
            project.created.strftime(DateFormat.DISPLAY_DATETIME.value),
        ],
    ]


def row_to_project(
    data: List[List[str]], project_id: str
) -> Project:
    """Convert Project Info sheet rows to Project domain model.

    Args:
        data: Project Info sheet data
        project_id: External project ID (spreadsheet ID)

    Returns:
        Project domain model

    Raises:
        ValidationError: If data format is invalid
    """
    if not data or len(data) < 3:
        raise ValidationError("Invalid project data: insufficient rows")

    # Find Name field
    name = ""
    created_str = ""

    # Skip header row
    for row in data[1:]:
        if len(row) >= 2:
            field = str(row[0]).strip()
            value = str(row[1]).strip() if row[1] else ""
            if field == RowName.NAME.value:
                name = value
            elif field == RowName.CREATED.value:
                created_str = value

    if not name:
        raise ValidationError("Project name not found in data")

    # Parse created date
    try:
        created = datetime.strptime(created_str, DateFormat.DISPLAY_DATETIME.value)
    except (ValueError, IndexError):
        # Fallback to current time if parsing fails
        created = datetime.utcnow()

    return Project(name=name, created=created)
