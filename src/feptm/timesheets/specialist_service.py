"""Service for working with specialists in Google Sheets."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from feptm.core import utils
from feptm.core.config import settings
from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    ColumnName,
    DateFormat,
    RangeFormat,
    SheetName,
    config_service,
)


class SpecialistService:
    """Service for handling specialists and their timesheets."""

    def __init__(self, google_sheets_service: GoogleSheetsService) -> None:
        """Initialize with Google Sheets service."""
        self.google_sheets_service = google_sheets_service

    def sync_specialists(
        self,
        spreadsheet_id: str,
        context: TimesheetContext,
        sheet_name: str = SheetName.TEAM.value,
    ) -> Tuple[List[Specialist], int]:
        """Synchronize specialists for a project.

        Args:
            spreadsheet_id: ID of the spreadsheet containing specialists
            context: Context for timesheet creation
            sheet_name: Name of the sheet with specialists data

        Returns:
            Tuple containing list of specialists and count of new timesheets created
        """
        try:
            # Get existing specialists
            specialists, existing_count = self.get_specialists_from_sheet(
                spreadsheet_id, sheet_name
            )
            if not specialists:
                log.info("No specialists found in sheet")
                return [], 0

            # Create missing timesheets
            new_specialists = self._create_missing_timesheets(specialists, context)
            new_count = len(new_specialists)

            # Update specialists sheet with new timesheet IDs
            if new_count > 0:
                self.update_specialists_sheet(
                    spreadsheet_id, sheet_name, new_specialists
                )

            log.info(
                "Synchronized %d specialists, created %d new timesheets",
                len(specialists),
                new_count,
            )
            return specialists, new_count

        except Exception as e:
            log.error("Failed to sync specialists: %s", str(e))
            raise Exception(f"Failed to sync specialists: {str(e)}")

    def get_specialists_from_sheet(
        self, spreadsheet_id: str, sheet_name: str = SheetName.TEAM.value
    ) -> Tuple[List[Specialist], int]:
        """Extract specialists data from a Google Sheet.

        Args:
            spreadsheet_id: ID of the spreadsheet containing specialists data
            sheet_name: Name of the sheet with specialists data

        Returns:
            Tuple containing list of specialist objects and count of specialists with existing timesheets

        Raises:
            Exception: If sheet cannot be read or data is invalid
        """
        try:
            values, headers = self._extract_and_validate_sheet_data(
                spreadsheet_id, sheet_name
            )
            specialists, existing_count = self._parse_specialists_data(values, headers)

            log.info(
                "Extracted %d specialists from sheet '%s'", len(specialists), sheet_name
            )
            return specialists, existing_count

        except Exception as e:
            log.error(
                "Failed to extract specialists from sheet '%s': %s", sheet_name, str(e)
            )
            raise Exception(f"Failed to extract specialists data: {str(e)}")

    def create_timesheet(
        self, specialist: Specialist, context: TimesheetContext
    ) -> Dict[str, str]:
        """Create a timesheet for a specialist.

        Args:
            specialist: Specialist object
            context: Context containing folder_id and project_name

        Returns:
            Dictionary with spreadsheet ID and URL

        Raises:
            Exception: If timesheet creation fails
        """
        if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
            raise Exception("Timesheet template ID not configured")

        try:
            # Generate timesheet title using utility
            timesheet_title = utils.generate_timesheet_title(
                specialist.name, context.project_name
            )

            # Create the timesheet from template
            result = self.google_sheets_service.ensure_spreadsheet_from_template(
                template_id=settings.GOOGLE_TIMESHEET_TEMPLATE_ID,
                new_title=timesheet_title,
                folder_id=context.folder_id,
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
            sheet_name: Name of the sheet containing specialists
            specialists: List of specialists with timesheet IDs

        Returns:
            True if update was successful

        Raises:
            Exception: If update fails
        """
        try:
            sheet_data = self._prepare_timesheet_updates(
                spreadsheet_id, sheet_name, specialists
            )
            if not sheet_data:
                log.info("No timesheet updates needed")
                return True

            self._apply_timesheet_updates(spreadsheet_id, sheet_name, sheet_data)
            log.info(
                "Successfully updated specialists sheet with %d timesheet IDs",
                len(sheet_data),
            )
            return True

        except Exception as e:
            log.error("Failed to update specialists sheet: %s", str(e))
            raise Exception(f"Failed to update specialists sheet: {str(e)}")

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
        # Check if sheet exists
        sheet = self.google_sheets_service.get_sheet_by_name(
            spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
        )

        if not sheet:
            log.warning(
                "Sheet '%s' not found in spreadsheet %s", sheet_name, spreadsheet_id
            )
            return [], []

        # Get sheet data using utility method
        values, headers = self.google_sheets_service.get_sheet_data_with_headers(
            spreadsheet_id, sheet_name, RangeFormat.SPECIALIST_DATA.value
        )

        if not values or len(values) < 2:  # Need at least header row + 1 data row
            log.warning("No data found in sheet '%s'", sheet_name)
            return [], []

        self._validate_required_headers(headers)
        return values, headers

    def _validate_required_headers(self, headers: List[str]) -> None:
        """Validate that required columns exist in headers.

        Args:
            headers: List of column headers

        Raises:
            Exception: If required columns are missing
        """
        name_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.NAME.value]
        )
        role_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.ROLE.value]
        )

        if name_idx is None or role_idx is None:
            missing = []
            if name_idx is None:
                missing.append(ColumnName.NAME.value)
            if role_idx is None:
                missing.append(ColumnName.ROLE.value)

            raise Exception(
                f"Required columns missing in specialists sheet: {', '.join(missing)}"
            )

    def _parse_specialists_data(
        self, values: List[List], headers: List[str]
    ) -> Tuple[List[Specialist], int]:
        """Parse specialists data from sheet values.

        Args:
            values: Sheet values including headers
            headers: Column headers

        Returns:
            Tuple of specialists list and count of specialists with existing timesheets
        """
        # Map column indices using utility
        headers_map = self._build_headers_map(headers)

        specialists = []
        existing_count = 0

        for row in values[1:]:  # Skip header row
            # Skip empty rows
            name_idx = headers_map["name"]
            role_idx = headers_map["role"]
            
            # Both name and role columns should exist due to validation, but double-check
            if name_idx is None or role_idx is None:
                raise Exception("Required columns 'name' or 'role' not found after validation")
            
            if not row or len(row) <= max(name_idx, role_idx):
                continue

            specialist = self._parse_specialist_row(row, headers_map)
            if specialist:
                specialists.append(specialist)
                if specialist.timesheet:
                    existing_count += 1

        return specialists, existing_count

    def _build_headers_map(self, headers: List[str]) -> Dict[str, Optional[int]]:
        """Build mapping of column names to indices.

        Args:
            headers: List of column headers

        Returns:
            Dictionary mapping column names to indices
        """
        return {
            "name": self.google_sheets_service.find_column_index(
                headers, [ColumnName.NAME.value]
            ),
            "role": self.google_sheets_service.find_column_index(
                headers, [ColumnName.ROLE.value]
            ),
            "project": self.google_sheets_service.find_column_index(
                headers, [ColumnName.PROJECT.value]
            ),
            "internal_rate": self.google_sheets_service.find_column_index(
                headers, [ColumnName.INTERNAL_RATE.value]
            ),
            "external_rate": self.google_sheets_service.find_column_index(
                headers, [ColumnName.EXTERNAL_RATE.value]
            ),
            "date": self.google_sheets_service.find_column_index(
                headers, [ColumnName.DATE.value]
            ),
            "timesheet": self.google_sheets_service.find_column_index(
                headers, [ColumnName.TIMESHEET.value]
            ),
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
        name_idx = headers_map["name"]
        role_idx = headers_map["role"]

        name = (
            row[name_idx].strip()
            if name_idx is not None and name_idx < len(row)
            else ""
        )
        role = (
            row[role_idx].strip()
            if role_idx is not None and role_idx < len(row)
            else ""
        )

        # Skip rows with empty required fields
        if not name or not role:
            return None

        # Get optional fields using utilities
        project = self._get_optional_field(row, headers_map["project"])
        date = self._parse_date_field(row, headers_map["date"], name)
        internal_rate = self._parse_decimal_field(
            row, headers_map["internal_rate"], name, "internal rate"
        )
        external_rate = self._parse_decimal_field(
            row, headers_map["external_rate"], name, "external rate"
        )
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

    def _get_optional_field(
        self, row: List, column_idx: Optional[int]
    ) -> Optional[str]:
        """Get optional field value from row.

        Args:
            row: Row data
            column_idx: Column index

        Returns:
            Field value or None
        """
        if column_idx is not None and column_idx < len(row):
            return utils.clean_string_value(row[column_idx])
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
                parsed_date = utils.parse_date_safely(
                    date_str, DateFormat.SHEET_DATE.value
                )
                if parsed_date is None:
                    log.warning(
                        "Invalid date format for %s: %s", specialist_name, date_str
                    )
                return parsed_date
        return None

    def _parse_decimal_field(
        self,
        row: List,
        column_idx: Optional[int],
        specialist_name: str,
        field_name: str,
    ) -> Any:
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
            rate_str = row[column_idx].strip()
            if rate_str:
                result = utils.parse_decimal_safely(rate_str)
                if result == 0 and rate_str != "0":
                    log.warning(
                        "Invalid %s value for %s: %s",
                        field_name,
                        specialist_name,
                        rate_str,
                    )
                return result
        return utils.parse_decimal_safely("")  # Returns Decimal("0")

    def _create_missing_timesheets(
        self, specialists: List[Specialist], context: TimesheetContext
    ) -> List[Specialist]:
        """Create timesheets for specialists who don't have them.

        Args:
            specialists: List of all specialists
            context: Context for timesheet creation

        Returns:
            List of specialists for whom new timesheets were created
        """
        new_specialists = []
        for specialist in specialists:
            if not specialist.timesheet:
                try:
                    self.create_timesheet(specialist, context)
                    new_specialists.append(specialist)
                    log.debug("Created timesheet for %s", specialist.name)
                except Exception as e:
                    log.error(
                        "Failed to create timesheet for %s: %s", specialist.name, str(e)
                    )

        return new_specialists

    def _prepare_timesheet_updates(
        self, spreadsheet_id: str, sheet_name: str, specialists: List[Specialist]
    ) -> List[Tuple[int, str]]:
        """Prepare list of timesheet updates.

        Args:
            spreadsheet_id: ID of the project spreadsheet
            sheet_name: Name of the sheet
            specialists: List of specialists

        Returns:
            List of tuples (row_index, timesheet_id) for updates
        """
        # Get current sheet data
        values, headers = self.google_sheets_service.get_sheet_data_with_headers(
            spreadsheet_id, sheet_name, RangeFormat.SPECIALIST_DATA.value
        )

        if not values:
            return []

        timesheet_col_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.TIMESHEET.value]
        )
        name_col_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.NAME.value]
        )

        if timesheet_col_idx is None or name_col_idx is None:
            log.warning("Required columns not found for timesheet updates")
            return []

        # Find specialists that need timesheet ID updates
        updates = []
        for specialist in specialists:
            if not specialist.timesheet:
                continue

            # Find the row for this specialist using utility
            row_idx = self.google_sheets_service.find_specialist_row_index(
                values, name_col_idx, specialist.name
            )
            if row_idx is not None:
                updates.append(
                    (row_idx + 1, specialist.timesheet)
                )  # +1 for 1-based indexing

        return updates

    def _apply_timesheet_updates(
        self, spreadsheet_id: str, sheet_name: str, updates: List[Tuple[int, str]]
    ) -> None:
        """Apply timesheet ID updates to the sheet.

        Args:
            spreadsheet_id: ID of the project spreadsheet
            sheet_name: Name of the sheet
            updates: List of (row_index, timesheet_id) updates
        """
        # Get headers to find timesheet column
        values, headers = self.google_sheets_service.get_sheet_data_with_headers(
            spreadsheet_id, sheet_name, RangeFormat.SPECIALIST_DATA.value
        )

        timesheet_col_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.TIMESHEET.value]
        )

        if timesheet_col_idx is None:
            raise Exception("Timesheet column not found")

        # Convert column index to letter using utility
        timesheet_col_letter = self.google_sheets_service.column_index_to_letter(
            timesheet_col_idx
        )

        # Apply updates
        for row_idx, timesheet_id in updates:
            update_range = f"{sheet_name}!{timesheet_col_letter}{row_idx}"

            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=update_range,
                values=[[timesheet_id]],
                value_input_option="RAW",
            )

            log.debug("Updated timesheet ID for row %d", row_idx)

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
        if specialist.timesheet is None:
            raise ValueError(
                f"Specialist {specialist.name} does not have a timesheet ID"
            )

        import_formula = config_service.get_import_specialist_timesheet_formula(
            specialist_timesheet_id=specialist.timesheet
        )

        # Basic specialist information for report
        return [[specialist.name, specialist.role, import_formula]]
