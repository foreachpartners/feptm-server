"""Mappers for converting between domain models and spreadsheet data."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, List

from feptm.adapters.sheets.constants import ColumnName, RowName, TeamSheetConfig
from feptm.core.constants import DateFormat
from feptm.core.exceptions import ValidationError
from feptm.core.utils import parse_decimal_safely
from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Rate, Specialist


def build_column_index(headers: List[str]) -> dict[str, int]:
    """Build column name to index mapping from header row.
    
    Args:
        headers: Header row with column names
        
    Returns:
        Dict mapping column name (lowercase) to column index
    """
    return {str(h).strip().lower(): i for i, h in enumerate(headers) if h}


def get_column_letter(col_index: dict[str, int], column_name: str) -> str | None:
    """Get column letter (A, B, C...) for a column name.
    
    Args:
        col_index: Column name to index mapping
        column_name: Column name to look up
        
    Returns:
        Column letter or None if not found
    """
    key = column_name.lower()
    if key not in col_index:
        return None
    idx = col_index[key]
    # Convert 0-based index to column letter (A=0, B=1, ..., Z=25, AA=26...)
    result = ""
    while idx >= 0:
        result = chr(ord('A') + idx % 26) + result
        idx = idx // 26 - 1
    return result


def get_cell_value(row: List[str], col_index: dict[str, int], column_name: str, default: str = "") -> str:
    """Get cell value by column name.
    
    Args:
        row: Data row
        col_index: Column name to index mapping
        column_name: Column name to look up
        default: Default value if column not found or empty
        
    Returns:
        Cell value or default
    """
    key = column_name.lower()
    if key not in col_index:
        return default
    idx = col_index[key]
    if idx >= len(row):
        return default
    value = row[idx]
    return str(value).strip() if value else default


def row_to_specialist(
    row: List[str], 
    col_index: dict[str, int], 
    timesheet_id: str
) -> Specialist:
    """Convert Team sheet row to Specialist using column name mapping.

    FR-002.1: One row represents one rate period. Multiple rows with same
    Timesheet ID represent rate history.

    Args:
        row: Data row
        col_index: Column name to index mapping from build_column_index()
        timesheet_id: Timesheet ID (specialist identifier)

    Returns:
        Specialist domain model with one rate period

    Raises:
        ValidationError: If required data is missing
    """
    # Get values by column name
    name = get_cell_value(row, col_index, ColumnName.NAME.value)
    role = get_cell_value(row, col_index, ColumnName.ROLE.value)
    internal_rate_str = get_cell_value(row, col_index, ColumnName.INTERNAL_RATE.value, "0")
    external_rate_str = get_cell_value(row, col_index, ColumnName.EXTERNAL_RATE.value, "0")
    start_date_str = get_cell_value(row, col_index, ColumnName.DATE.value)
    row_timesheet_id = get_cell_value(row, col_index, ColumnName.TIMESHEET.value)

    # Validate timesheet ID matches (for safety)
    if row_timesheet_id and row_timesheet_id != timesheet_id:
        raise ValidationError(
            f"Timesheet ID mismatch: expected {timesheet_id}, got {row_timesheet_id}"
        )

    if not name:
        raise ValidationError("Specialist name is required")

    if not role:
        raise ValidationError("Specialist role is required")

    # Parse rates (handles comma as decimal separator)
    internal_rate = parse_decimal_safely(internal_rate_str, Decimal("0"))
    external_rate = parse_decimal_safely(external_rate_str, Decimal("0"))

    # Parse start date
    start_date = _parse_date(start_date_str)

    # Create rate
    rate = Rate(
        internal=internal_rate,
        external=external_rate,
        start_date=start_date,
    )

    return Specialist(
        name=name,
        role=role,
        rates=[rate],
        joined_date=start_date,
    )


def _parse_date(date_str: str) -> date:
    """Parse date string in multiple formats.
    
    Args:
        date_str: Date string
        
    Returns:
        Parsed date or today if parsing fails
    """
    if not date_str:
        return date.today()
        
    date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y"]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return date.today()


def specialist_to_row(specialist: Specialist, timesheet_id: str, project_name: str = "") -> List[List[str]]:
    """Convert Specialist domain model to Team sheet rows.

    FR-002.1: One Specialist may produce multiple rows (one per rate period).

    Args:
        specialist: Specialist domain model (may contain multiple rates)
        timesheet_id: Timesheet ID (specialist identifier)
        project_name: Project name for column C

    Returns:
        List of rows, one per rate period

    Note:
        Each row: [Name, Role, Project, Internal Rate, External Rate, Date, Timesheet]
        A: Name | B: Role | C: Project | D: Internal Rate | E: External Rate | F: Date | G: Timesheet
    """
    rows = []
    for rate in sorted(specialist.rates, key=lambda r: r.start_date):
        row = [
            specialist.name,
            specialist.role,
            project_name,  # Column C: Project
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
