"""Service for working with configuration settings from Google Sheets."""

from enum import Enum, auto
from typing import Any, Dict, cast

from feptm.core.config import settings
from feptm.core.log import log
from feptm.services.google_sheets_service import google_sheets_service


class FormulaName(Enum):
    """Enumeration of available formula names in the configuration sheet."""

    CALCULATE_WORKING_HOURS = "Calculate working hours"
    IMPORT_SPECIALIST_TIMESHEET = "Import specialist timesheet"
    GROSS_TOTAL_COST = "Gross total cost"
    NET_TOTAL_COST = "Net total cost"
    REVENUE = "Revenue"


class SheetName(Enum):
    """Enumeration of sheet names used in spreadsheets."""

    PROJECT_INFO = "Project info"
    TEAM = "Team"
    CURRENT_PERIOD = "Current period"
    FORMULAS = "Formulas"


class ColumnName(Enum):
    """Enumeration of column names used in spreadsheets."""

    # Common columns
    NAME = "Name"
    ROLE = "Role"

    # Specialist sheet columns
    PROJECT = "Project"
    INTERNAL_RATE = "Internal Rate"
    EXTERNAL_RATE = "External Rate"
    DATE = "Date"
    TIMESHEET = "Timesheet"

    # Current period tab columns
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


class DateFormat(Enum):
    """Enumeration of date formats used in the application."""

    DISPLAY_DATETIME = "%Y-%m-%d %H:%M:%S UTC"
    SHEET_DATE = "%b %d, %Y"


class RangeFormat(Enum):
    """Enumeration of range formats used in Google Sheets API calls."""

    SPECIALIST_DATA = "{sheet_name}!A1:Z100"
    PROJECT_INFO = "Project info!A1:B20"
    CURRENT_PERIOD = "{sheet_name}!A1:J100"
    SINGLE_CELL = "{sheet_name}!A1"
    HEADER_ROW = "{sheet_name}!A1:{column}{row}"


class RowName(Enum):
    """Enumeration of row identifiers used in project info sheets."""

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
    """Constants for URL patterns."""

    DRIVE_FOLDER = "https://drive.google.com/drive/folders/{folder_id}"
    SPREADSHEET = "https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    DRIVE_FOLDERS_SEGMENT = "drive/folders/"
    SPREADSHEETS_SEGMENT = "spreadsheets/d/"


class ConfigService:
    """Service for accessing configuration from Google Sheets."""

    def __init__(self):
        """Initialize the service."""
        self.google_sheets_service = google_sheets_service
        self._formula_cache: Dict[str, str] = {}

    def get_formula(self, formula_name: FormulaName) -> str:
        """Get a formula by name from the configuration spreadsheet.

        Args:
            formula_name: Enum value for the formula to retrieve

        Returns:
            The formula value

        Raises:
            Exception: If formula not found or configuration sheet not set
        """
        # Check if formula is in cache
        formula_key = formula_name.value
        if formula_key in self._formula_cache:
            return self._formula_cache[formula_key]

        # Not in cache, need to retrieve it
        if not settings.GOOGLE_CONFIG_SHEET_ID:
            raise Exception("GOOGLE_CONFIG_SHEET_ID not set in environment variables")

        if not self.google_sheets_service.is_initialized():
            raise Exception("Google Sheets service not initialized")

        try:
            # Find the "Formulas" sheet
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=settings.GOOGLE_CONFIG_SHEET_ID,
                sheet_name=SheetName.FORMULAS.value,
            )

            if not sheet:
                raise Exception(
                    "Formulas sheet not found in the configuration spreadsheet"
                )

            # Get the formulas data
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=settings.GOOGLE_CONFIG_SHEET_ID,
                    range=f"{SheetName.FORMULAS.value}!A:C",
                )
                .execute()
            )

            values = result.get("values", [])
            if not values or len(values) <= 1:  # Check if we have data (besides header)
                raise Exception("No formulas found in the configuration spreadsheet")

            # Skip header row and process formulas
            for row in values[1:]:
                if len(row) >= 2:  # Should have at least formula name and value
                    current_formula_name = row[0].strip()
                    formula_value = row[1].strip()

                    # Add to cache regardless if it's the one we're looking for
                    if formula_value:
                        self._formula_cache[current_formula_name] = formula_value

                    # If this is the formula we're looking for, return it
                    if current_formula_name == formula_key and formula_value:
                        return formula_value

            # If we get here, the formula was not found
            raise Exception(
                f"Formula '{formula_key}' not found in configuration spreadsheet"
            )

        except Exception as e:
            log.error(f"Error getting formula: {str(e)}")
            raise

    def get_import_specialist_timesheet_formula(
        self, specialist_timesheet_id: str
    ) -> str:
        """Get the Import specialist timesheet formula with specialist's timesheet ID.

        Args:
            specialist_timesheet_id: ID of the specialist's timesheet to use in the formula

        Returns:
            The formula with the specialist's timesheet ID inserted

        Raises:
            Exception: If formula not found
        """
        formula = self.get_formula(FormulaName.IMPORT_SPECIALIST_TIMESHEET)
        return formula.replace("SpecialistSpreadsheetID", specialist_timesheet_id)


# Create singleton instance
config_service = ConfigService()
