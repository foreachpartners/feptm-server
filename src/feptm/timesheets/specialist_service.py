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

    def __init__(self, google_sheets_service: GoogleSheetsService) -> None:
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
            values, headers = self._extract_and_validate_sheet_data(spreadsheet_id, sheet_name)
            specialists, created_count = self._parse_specialists_data(values, headers)
            
            log.info("Extracted %d specialists from sheet '%s'", len(specialists), sheet_name)
            return specialists, created_count

        except Exception as e:
            log.error("Failed to extract specialists from sheet '%s': %s", sheet_name, str(e))
            raise Exception(f"Failed to extract specialists data: {str(e)}")

    def _extract_and_validate_sheet_data(
        self, spreadsheet_id: str, sheet_name: str
    ) -> Tuple[List[List], List[str]]:
        """Extract and validate sheet data and headers.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet

        Returns:
            Tuple of values and headers

        Raises:
            Exception: If sheet cannot be read or is invalid
        """
        if not self.google_sheets_service.sheets_service:
            raise Exception("Google Sheets service not initialized")

        # Check if the specialists sheet exists
        sheet = self.google_sheets_service.get_sheet_by_name(
            spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
        )

        if not sheet:
            log.warning("Sheet '%s' not found in spreadsheet %s", sheet_name, spreadsheet_id)
            return [], []

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
            log.warning("No data found in sheet '%s'", sheet_name)
            return [], []

        headers = values[0]
        self._validate_required_headers(headers)
        
        return values, headers

    def _validate_required_headers(self, headers: List[str]) -> None:
        """Validate that required columns exist in headers.

        Args:
            headers: List of column headers

        Raises:
            Exception: If required columns are missing
        """
        name_idx = self._find_column_index(headers, [ColumnName.NAME.value])
        role_idx = self._find_column_index(headers, [ColumnName.ROLE.value])

        if name_idx is None or role_idx is None:
            missing = []
            if name_idx is None:
                missing.append(ColumnName.NAME.value)
            if role_idx is None:
                missing.append(ColumnName.ROLE.value)

            raise Exception(f"Required columns missing in specialists sheet: {', '.join(missing)}")

    def _parse_specialists_data(
        self, values: List[List], headers: List[str]
    ) -> Tuple[List[Specialist], int]:
        """Parse specialists data from sheet values.

        Args:
            values: Sheet values including headers
            headers: Column headers

        Returns:
            Tuple of specialists list and count of specialists with timesheets
        """
        # Map column indices
        headers_map = self._build_headers_map(headers)
        
        specialists = []
        created_count = 0

        for row in values[1:]:  # Skip header row
            # Skip empty rows
            if not row or len(row) <= max(headers_map["name"], headers_map["role"]):
                continue

            specialist = self._parse_specialist_row(row, headers_map)
            if specialist:
                specialists.append(specialist)
                if specialist.timesheet:
                    created_count += 1

        return specialists, created_count

    def _build_headers_map(self, headers: List[str]) -> Dict[str, Optional[int]]:
        """Build mapping of column names to indices.

        Args:
            headers: List of column headers

        Returns:
            Dictionary mapping column names to indices
        """
        return {
            "name": self._find_column_index(headers, [ColumnName.NAME.value]),
            "role": self._find_column_index(headers, [ColumnName.ROLE.value]),
            "project": self._find_column_index(headers, [ColumnName.PROJECT.value]),
            "internal_rate": self._find_column_index(headers, [ColumnName.INTERNAL_RATE.value]),
            "external_rate": self._find_column_index(headers, [ColumnName.EXTERNAL_RATE.value]),
            "date": self._find_column_index(headers, [ColumnName.DATE.value]),
            "timesheet": self._find_column_index(headers, [ColumnName.TIMESHEET.value]),
        }

    def _parse_specialist_row(
        self, row: List, headers_map: Dict[str, Optional[int]]
    ) -> Optional[Specialist]:
        """Parse a single specialist row.

        Args:
            row: Row data
            headers_map: Mapping of column names to indices

        Returns:
            Specialist object or None if row is invalid
        """
        # Get required fields
        name = row[headers_map["name"]].strip() if headers_map["name"] < len(row) else ""
        role = row[headers_map["role"]].strip() if headers_map["role"] < len(row) else ""

        # Skip rows with empty required fields
        if not name or not role:
            return None

        # Get optional fields
        project = self._get_optional_field(row, headers_map["project"])
        date = self._parse_date_field(row, headers_map["date"], name)
        internal_rate = self._parse_decimal_field(row, headers_map["internal_rate"], name, "internal rate")
        external_rate = self._parse_decimal_field(row, headers_map["external_rate"], name, "external rate")
        timesheet = self._get_optional_field(row, headers_map["timesheet"])

        return Specialist(
            name=name,
            role=role,
            project=project,
            internal_rate=internal_rate,
            external_rate=external_rate,
            date=date or datetime.utcnow(),
            timesheet=timesheet,
        )

    def _get_optional_field(self, row: List, column_idx: Optional[int]) -> Optional[str]:
        """Get optional field value from row.

        Args:
            row: Row data
            column_idx: Column index

        Returns:
            Field value or None
        """
        if column_idx is not None and column_idx < len(row):
            value = row[column_idx].strip()
            return value if value else None
        return None

    def _parse_date_field(
        self, row: List, column_idx: Optional[int], specialist_name: str
    ) -> Optional[datetime]:
        """Parse date field from row.

        Args:
            row: Row data
            column_idx: Column index
            specialist_name: Specialist name for logging

        Returns:
            Parsed datetime or None
        """
        if column_idx is not None and column_idx < len(row):
            date_str = row[column_idx].strip()
            if date_str:
                try:
                    return datetime.strptime(date_str, DateFormat.SHEET_DATE.value)
                except Exception:
                    log.warning("Invalid date format for %s: %s", specialist_name, date_str)
        return None

    def _parse_decimal_field(
        self, row: List, column_idx: Optional[int], specialist_name: str, field_name: str
    ) -> Decimal:
        """Parse decimal field from row.

        Args:
            row: Row data
            column_idx: Column index
            specialist_name: Specialist name for logging
            field_name: Field name for logging

        Returns:
            Parsed Decimal value or Decimal("0")
        """
        if column_idx is not None and column_idx < len(row):
            rate_str = row[column_idx].strip().replace(",", ".")
            try:
                return Decimal(rate_str)
            except (InvalidOperation, ValueError):
                log.warning("Invalid %s value for %s: %s", field_name, specialist_name, rate_str)
        return Decimal("0")

    def create_specialist_timesheet(
        self, specialist: Specialist, project_name: str, folder_id: str
    ) -> Dict[str, str]:
        """Create a timesheet for a specialist based on template.

        Args:
            specialist: Specialist object containing name and role
            project_name: Name of the project
            folder_id: ID of the Google Drive folder where to create the timesheet

        Returns:
            Dictionary with spreadsheet ID and URL

        Raises:
            Exception: If timesheet creation fails
        """
        if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
            raise Exception("Timesheet template ID not configured")

        try:
            # Create a title for the timesheet
            timesheet_title = f"Time Tracking for {specialist.name}. Project {project_name}"

            # Create the timesheet from template
            result = self.google_sheets_service.ensure_spreadsheet_from_template(
                template_id=settings.GOOGLE_TIMESHEET_TEMPLATE_ID,
                new_title=timesheet_title,
                folder_id=folder_id,
            )

            log.info("Created timesheet for %s", specialist.name)

            # Update the specialist object
            specialist.timesheet = result["spreadsheet_id"]

            return result
        except Exception as e:
            log.error("Failed to create timesheet for %s: %s", specialist.name, str(e))
            raise Exception(f"Failed to create timesheet: {str(e)}")



    def update_specialists_sheet(
        self, spreadsheet_id: str, sheet_name: str, specialists: List[Specialist]
    ) -> bool:
        """Update specialists sheet with timesheet IDs.

        Args:
            spreadsheet_id: ID of the project spreadsheet
            specialists: List of specialists with timesheet IDs

        Returns:
            True if update was successful

        Raises:
            Exception: If update fails
        """
        try:
            sheet_data = self._prepare_timesheet_updates(spreadsheet_id, sheet_name, specialists)
            if not sheet_data:
                log.info("No timesheet updates needed")
                return True

            self._apply_timesheet_updates(spreadsheet_id, sheet_name, sheet_data)
            log.info("Successfully updated specialists sheet with %d timesheet IDs", len(sheet_data))
            return True

        except Exception as e:
            log.error("Failed to update specialists sheet: %s", str(e))
            raise Exception(f"Failed to update specialists sheet: {str(e)}")

    def _prepare_timesheet_updates(
        self, spreadsheet_id: str, sheet_name: str, specialists: List[Specialist]
    ) -> List[Tuple[int, str]]:
        """Prepare list of timesheet updates.

        Args:
            spreadsheet_id: ID of the project spreadsheet
            specialists: List of specialists

        Returns:
            List of tuples (row_index, timesheet_id) for updates
        """
        # Get current sheet data
        range_name = RangeFormat.SPECIALIST_DATA.value.format(sheet_name=sheet_name)
        result = (
            self.google_sheets_service.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values:
            return []

        headers = values[0]
        timesheet_col_idx = self._find_column_index(headers, [ColumnName.TIMESHEET.value])
        name_col_idx = self._find_column_index(headers, [ColumnName.NAME.value])

        if timesheet_col_idx is None or name_col_idx is None:
            log.warning("Required columns not found for timesheet updates")
            return []

        # Find specialists that need timesheet ID updates
        updates = []
        for specialist in specialists:
            if not specialist.timesheet:
                continue

            # Find the row for this specialist
            row_idx = self._find_specialist_row(values, name_col_idx, specialist.name)
            if row_idx is not None:
                updates.append((row_idx + 1, specialist.timesheet))  # +1 for 1-based indexing

        return updates

    def _find_specialist_row(self, values: List[List], name_col_idx: int, specialist_name: str) -> Optional[int]:
        """Find row index for a specialist by name.

        Args:
            values: Sheet values
            name_col_idx: Index of the name column
            specialist_name: Name of the specialist to find

        Returns:
            Zero-based row index or None if not found
        """
        for i, row in enumerate(values[1:], start=1):  # Skip header row
            if name_col_idx < len(row) and row[name_col_idx].strip() == specialist_name:
                return i
        return None

    def _apply_timesheet_updates(
        self, spreadsheet_id: str, sheet_name: str, updates: List[Tuple[int, str]]
    ) -> None:
        """Apply timesheet ID updates to the sheet.

        Args:
            spreadsheet_id: ID of the project spreadsheet
            updates: List of (row_index, timesheet_id) updates
        """
        # Find timesheet column
        range_name = RangeFormat.SPECIALIST_DATA.value.format(sheet_name=sheet_name)
        result = (
            self.google_sheets_service.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )

        headers = result.get("values", [[]])[0]
        timesheet_col_idx = self._find_column_index(headers, [ColumnName.TIMESHEET.value])

        if timesheet_col_idx is None:
            raise Exception("Timesheet column not found")

        # Convert column index to letter
        timesheet_col_letter = self._column_index_to_letter(timesheet_col_idx)

        # Apply updates
        for row_idx, timesheet_id in updates:
            update_range = f"{sheet_name}!{timesheet_col_letter}{row_idx}"
            
            self.google_sheets_service.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption="RAW",
                body={"values": [[timesheet_id]]},
            ).execute()

            log.debug("Updated timesheet ID for row %d", row_idx)

    def _column_index_to_letter(self, col_idx: int) -> str:
        """Convert column index to letter (A, B, C, etc.).

        Args:
            col_idx: Zero-based column index

        Returns:
            Column letter
        """
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
        return result

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


