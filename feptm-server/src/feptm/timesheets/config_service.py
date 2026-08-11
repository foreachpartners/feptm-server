"""Configuration constants and service enums for Google Sheets operations."""

from enum import Enum


class FormulaName(Enum):
    CALCULATE_WORKING_HOURS = "Calculate working hours"
    IMPORT_SPECIALIST_TIMESHEET = "Import specialist timesheet"
    GROSS_TOTAL_COST = "Gross total cost"
    NET_TOTAL_COST = "Net total cost"
    REVENUE = "Revenue"


class SheetName(Enum):
    PROJECT_INFO = "Project info"
    TEAM = "Team"
    CURRENT_PERIOD = "Current period"
    FORMULAS = "Formulas"


class ColumnName(Enum):
    NAME = "Name"
    ROLE = "Role"
    PROJECT = "Project"
    INTERNAL_RATE = "Internal Rate"
    EXTERNAL_RATE = "External Rate"
    DATE = "Date"
    TIMESHEET = "Timesheet"
    SPECIALIST = "Specialist"
    SPECIALIST_ROLE = "Specialist Role"
    HOURS_WORKED = "Hours Worked"
    HOURLY_RATE_USD = "Hourly Rate (USD)"
    TOTAL_COST_USD = "Total Cost (USD)"
    CLIENT_HOURLY_RATE_USD = "Client Hourly Rate (USD)"
    SPECIALIST_HOURLY_RATE_USD = "Specialist Hourly Rate (USD)"
    CLIENT_WORK_COST_USD = "Client Work Cost (USD)"
    SPECIALIST_WORK_COST_USD = "Specialist Work Cost (USD)"
    REVENUE_USD = "Revenue (USD)"
    TASK_NAME = "Task Name"
    WORK_HOURS = "Work Hours"
    PAYMENT_PERIOD = "Payment Period"
    PAYMENT_STATUS = "Payment Status"
    PERIOD = "Period"


class DateFormat(Enum):
    DISPLAY_DATETIME = "%Y-%m-%d %H:%M:%S UTC"
    SHEET_DATE = "%b %d, %Y"


class RangeFormat(Enum):
    SPECIALIST_DATA = "{sheet_name}!A1:Z100"
    PROJECT_INFO = "Project info!A1:B20"
    CURRENT_PERIOD = "{sheet_name}!A1:J100"
    TIMESHEET_DATA = "{sheet_name}!A1:F100"
    SINGLE_CELL = "{sheet_name}!A1"
    HEADER_ROW = "{sheet_name}!A1:{column}{row}"


class RowName(Enum):
    FIELD = "Field"
    VALUE = "Value"
    PROJECT_ID = "Project ID"
    NAME = "Name"
    CREATED = "Created"
    MODIFIED = "Modified"
    PROJECT_FOLDER = "Project Folder"
    PAYMENT_DISTRIBUTION = "Payment Distribution"
    GENERAL_EXPENSES = "General Expenses"


class UrlPattern:
    DRIVE_FOLDER = "https://drive.google.com/drive/folders/{folder_id}"
    SPREADSHEET = "https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    DRIVE_FOLDERS_SEGMENT = "drive/folders/"
    SPREADSHEETS_SEGMENT = "spreadsheets/d/"
