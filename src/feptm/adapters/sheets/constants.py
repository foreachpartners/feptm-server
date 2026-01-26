"""Constants for Google Sheets adapter."""

from enum import Enum


class SheetName(str, Enum):
    """Sheet names used in spreadsheets."""

    PROJECT_INFO = "Project info"
    TEAM = "Team"
    CURRENT_PERIOD = "Current period"
    FORMULAS = "Formulas"
    TIMESHEET = "timesheet"


class ColumnName(str, Enum):
    """Column names used in spreadsheets."""

    # Common columns
    NAME = "Name"
    ROLE = "Role"

    # Team sheet columns
    PROJECT = "Project"
    INTERNAL_RATE = "Internal Rate"
    EXTERNAL_RATE = "External Rate"
    DATE = "Date"
    TIMESHEET = "Timesheet"

    # Current Period tab columns
    SPECIALIST = "Specialist"
    SPECIALIST_ROLE = "Specialist Role"
    PERIOD = "Period"
    HOURS_WORKED = "Hours Worked"
    HOURLY_RATE_USD = "Hourly Rate (USD)"
    TOTAL_COST_USD = "Total Cost (USD)"
    SPECIALIST_RATE = "Specialist Rate"
    CLIENT_RATE = "Client Rate"
    SPECIALIST_WORK_COST_USD = "Specialist Work Cost (USD)"
    CLIENT_WORK_COST_USD = "Client Work Cost (USD)"
    REVENUE_USD = "Revenue (USD)"
    PAYMENT_STATUS = "Payment Status"


class RowName(str, Enum):
    """Row identifiers used in project info sheets."""

    FIELD = "Field"
    VALUE = "Value"
    PROJECT_ID = "Project ID"
    NAME = "Name"
    CREATED = "Created"
    MODIFIED = "Modified"
    PROJECT_FOLDER = "Project Folder"
    PAYMENT_DISTRIBUTION = "Payment Distribution"
    GENERAL_EXPENSES = "General Expenses"


class TeamSheetConfig:
    """Configuration for Team sheet structure.
    
    Template columns: Name | Role | Project | Internal Rate | External Rate | Date | Timesheet
    Column order may vary - use header names for lookup.
    """
    
    # Data range for reading Team sheet
    START_CELL = "A1"
    END_CELL = "Z100"  # Wide range to capture all columns regardless of order
    MAX_ROWS = 100
    
    # Required columns (by name from ColumnName enum)
    REQUIRED_COLUMNS = [
        "Name",
        "Role",
        "Timesheet",
    ]
    
    # All expected columns
    EXPECTED_COLUMNS = [
        "Name",
        "Role", 
        "Project",
        "Internal Rate",
        "External Rate",
        "Date",
        "Timesheet",
    ]


class ProjectInfoConfig:
    """Configuration for Project info sheet structure."""
    
    START_CELL = "A1"
    END_CELL = "B20"


class CurrentPeriodConfig:
    """Configuration for Current period sheet structure."""
    
    START_CELL = "A1"
    END_CELL = "I100"
    MAX_ROWS = 100
