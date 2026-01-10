"""Constants for Google Sheets adapter."""

from enum import Enum


class SheetName(str, Enum):
    """Sheet names used in spreadsheets."""

    PROJECT_INFO = "Project info"
    TEAM = "Team"
    CURRENT_PERIOD = "Current Period"
    FORMULAS = "Formulas"
    TIMESHEET = "timesheet"


class ColumnName(str, Enum):
    """Column names used in spreadsheets."""

    # Common columns
    NAME = "Name"
    ROLE = "Role"

    # Team sheet columns
    INTERNAL_RATE = "Internal Rate"
    EXTERNAL_RATE = "External Rate"
    START_DATE = "Start Date"
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
