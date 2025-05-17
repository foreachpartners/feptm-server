"""Service for working with specialists in Google Sheets."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, cast

from feptm.core.config import settings
from feptm.core.log import log
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    config_service, FormulaName, SheetName, ColumnName, 
    DateFormat, RangeFormat
)


class SpecialistService:
    """Service for handling specialists and their timesheets."""

    def __init__(self, google_sheets_service: GoogleSheetsService):
        """Initialize with Google Sheets service."""
        self.google_sheets_service = google_sheets_service

    def get_specialists_from_sheet(
        self, spreadsheet_id: str, sheet_name: str = SheetName.TEAM.value
    ) -> Tuple[List[Specialist], int]:
        """Extract specialists data from a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet containing specialists data
            sheet_name: Name of the sheet with specialists data (default: "Team")

        Returns:
            Tuple containing list of specialist objects and count of specialists with created timesheets

        Raises:
            Exception: If sheet cannot be read or data is invalid
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            # Check if the specialists sheet exists
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
            )

            if not sheet:
                log.warning(
                    f"Sheet '{sheet_name}' not found in spreadsheet {spreadsheet_id}"
                )
                return [], 0

            # Read the specialists data from the sheet
            range_name = RangeFormat.SPECIALIST_DATA.value.format(sheet_name=sheet_name)
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values or len(values) < 2:  # Need at least header row + 1 data row
                log.warning(f"No data found in '{sheet_name}' sheet")
                return [], 0

            # Extract header row to identify columns
            headers = values[0]

            # Find required column indices
            name_idx = self._find_column_index(
                headers, [ColumnName.NAME.value]
            )
            role_idx = self._find_column_index(
                headers, [ColumnName.ROLE.value]
            )
            project_idx = self._find_column_index(headers, [ColumnName.PROJECT.value])
            internal_rate_idx = self._find_column_index(
                headers, [ColumnName.INTERNAL_RATE.value]
            )
            external_rate_idx = self._find_column_index(
                headers, [ColumnName.EXTERNAL_RATE.value]
            )
            date_idx = self._find_column_index(headers, [ColumnName.DATE.value])
            timesheet_idx = self._find_column_index(
                headers, [ColumnName.TIMESHEET.value]
            )

            # Need at least name and role
            if name_idx is None or role_idx is None:
                missing = []
                if name_idx is None:
                    missing.append(ColumnName.NAME.value)
                if role_idx is None:
                    missing.append(ColumnName.ROLE.value)

                raise Exception(
                    f"Required columns missing in specialists sheet: {', '.join(missing)}"
                )

            # Process data rows
            specialists = []
            created_count = 0

            for row in values[1:]:  # Skip header row
                # Skip empty rows
                if not row or len(row) <= max(name_idx, role_idx):
                    continue

                # Get name values
                name = row[name_idx].strip() if name_idx < len(row) else ""

                # Get other fields
                role = row[role_idx].strip() if role_idx < len(row) else ""
                project = (
                    row[project_idx].strip()
                    if project_idx is not None and project_idx < len(row)
                    else None
                )

                # Parse date
                date = None
                if (
                    date_idx is not None
                    and date_idx < len(row)
                    and row[date_idx].strip()
                ):
                    date_str = row[date_idx].strip()
                    try:
                        # Use only the format from Google Sheet: "Mar 29, 2025"
                        date = datetime.strptime(date_str, DateFormat.SHEET_DATE.value)
                    except Exception:
                        log.warning(f"Invalid date format for {name}: {date_str}")

                # Parse rates using Decimal for precision
                internal_rate = Decimal("0")
                external_rate = Decimal("0")

                if internal_rate_idx is not None and internal_rate_idx < len(row):
                    rate_str = row[internal_rate_idx].strip().replace(",", ".")
                    try:
                        internal_rate = Decimal(rate_str)
                    except (InvalidOperation, ValueError):
                        log.warning(
                            f"Invalid internal rate value for {name}: {rate_str}"
                        )

                if external_rate_idx is not None and external_rate_idx < len(row):
                    rate_str = row[external_rate_idx].strip().replace(",", ".")
                    try:
                        external_rate = Decimal(rate_str)
                    except (InvalidOperation, ValueError):
                        log.warning(
                            f"Invalid external rate value for {name}: {rate_str}"
                        )

                # Get timesheet ID if available
                timesheet = None
                if timesheet_idx is not None and timesheet_idx < len(row):
                    timesheet = row[timesheet_idx].strip()
                    if timesheet:
                        created_count += 1

                # Skip rows with empty required fields
                if not name or not role:
                    continue

                # Create specialist object
                specialist = Specialist(
                    name=name,
                    role=role,
                    project=project,
                    internal_rate=internal_rate,
                    external_rate=external_rate,
                    date=date or datetime.utcnow(),
                    timesheet=timesheet,
                )

                specialists.append(specialist)

            return specialists, created_count

        except Exception as e:
            log.error(f"Error extracting specialists from sheet: {str(e)}")
            raise Exception(f"Failed to extract specialists data: {str(e)}")

    def create_specialist_timesheet(
        self, specialist: Specialist, project_name: str, folder_id: str
    ) -> Dict[str, str]:
        """Create a timesheet for a specialist based on a template.

        Args:
            specialist: Specialist object
            project_name: Name of the project
            folder_id: ID of the Google Drive folder where to create the timesheet

        Returns:
            Dictionary with spreadsheet ID and URL

        Raises:
            Exception: If timesheet cannot be created
        """
        if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
            raise Exception("Timesheet template ID not configured")

        try:
            # Create a title for the timesheet
            timesheet_title = (
                f"Time Tracking for {specialist.name}. Project {project_name}"
            )

            # Create the timesheet from template
            result = self.google_sheets_service.ensure_spreadsheet_from_template(
                template_id=settings.GOOGLE_TIMESHEET_TEMPLATE_ID,
                new_title=timesheet_title,
                folder_id=folder_id,
            )

            log.info(f"Created timesheet for {specialist.name}")

            # Update the specialist object
            specialist.timesheet = result["spreadsheet_id"]

            return result
        except Exception as e:
            log.error(f"Error creating timesheet for {specialist.name}: {str(e)}")
            raise Exception(f"Failed to create timesheet: {str(e)}")

    def update_specialists_sheet(
        self, spreadsheet_id: str, sheet_name: str, specialists: List[Specialist]
    ) -> None:
        """Update the specialists sheet with timesheet IDs.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet with specialists data
            specialists: List of specialist objects

        Raises:
            Exception: If sheet cannot be updated
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            # Get current data to find the correct rows
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
            )

            if not sheet:
                raise Exception(f"Sheet '{sheet_name}' not found")

            # Read the specialists data from the sheet
            range_name = RangeFormat.SPECIALIST_DATA.value.format(sheet_name=sheet_name)
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values:
                raise Exception(f"No data found in '{sheet_name}' sheet")

            # Find the headers
            headers = values[0]

            # Find column indices
            name_idx = self._find_column_index(
                headers, [ColumnName.NAME.value]
            )
            timesheet_idx = self._find_column_index(
                headers, [ColumnName.TIMESHEET.value]
            )

            # If Timesheet column doesn't exist, add it
            if timesheet_idx is None:
                # Add the column header
                timesheet_idx = len(headers)
                headers.append(ColumnName.TIMESHEET.value)

                # Update the header row
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=RangeFormat.HEADER_ROW.value.format(
                        sheet_name=sheet_name, 
                        column=self._column_letter(timesheet_idx),
                        row=1
                    ),
                    values=[headers],
                )

            # Ensure we have a way to identify specialists
            if name_idx is None:
                raise Exception("Name column not found in specialists sheet")

            # Update timesheet IDs for each specialist
            for specialist in specialists:
                if not specialist.timesheet:
                    continue

                # Find this specialist in the sheet
                for i, row in enumerate(values[1:], start=1):  # Skip header row
                    if len(row) <= name_idx:
                        continue

                    # Try matching by name
                    sheet_name_value = row[name_idx].strip()
                    if sheet_name_value.lower() == specialist.name.lower():
                        # Ensure the row has enough cells
                        while len(row) <= timesheet_idx:
                            row.append("")

                        # Update timesheet ID
                        row[timesheet_idx] = specialist.timesheet

                        # Update this row in the sheet
                        self.google_sheets_service.update_range(
                            spreadsheet_id=spreadsheet_id,
                            range_name=f"{sheet_name}!A{i+1}:{self._column_letter(len(row)-1)}{i+1}",
                            values=[row],
                        )

                        log.info(f"Updated timesheet ID for {specialist.name}")
                        break

        except Exception as e:
            log.error(f"Error updating specialists sheet: {str(e)}")
            raise Exception(f"Failed to update specialists sheet: {str(e)}")

    def prepare_report_specialist_data(
        self, specialist: Specialist, project_name: str
    ) -> List[List[Any]]:
        """Prepare data for the report sheet for a specialist.

        Args:
            specialist: Specialist object
            project_name: Name of the project

        Returns:
            List of rows with formatted data for the report
        """
        # Get IMPORTRANGE formula from config
        import_formula = config_service.get_import_specialist_timesheet_formula(
            specialist_timesheet_id=specialist.timesheet
        )
        
        # Basic specialist information for report
        return [[specialist.name, specialist.role, import_formula]]

    def _find_column_index(
        self, headers: List[str], possible_names: List[str]
    ) -> Optional[int]:
        """Find column index by possible header names.

        Args:
            headers: List of headers
            possible_names: List of possible names for the column

        Returns:
            Index of the column or None if not found
        """
        for name in possible_names:
            for i, header in enumerate(headers):
                if header.strip().lower() == name.lower():
                    return i
        return None

    def _column_letter(self, index: int) -> str:
        """Convert column index to letter (0 = A, 1 = B, etc.).

        Args:
            index: Zero-based index

        Returns:
            Column letter(s)
        """
        result = ""
        while index >= 0:
            result = chr(index % 26 + 65) + result
            index = index // 26 - 1
        return result
