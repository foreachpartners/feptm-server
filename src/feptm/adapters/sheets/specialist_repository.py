"""Specialist repository implementation using Google Sheets via pygsheets."""

from typing import List

import pygsheets

from feptm.adapters.sheets.client import PygSheetsClient
from feptm.adapters.sheets.constants import (
    ColumnName,
    CurrentPeriodConfig,
    ProjectInfoConfig,
    SheetName,
    TeamSheetConfig,
)
from feptm.adapters.sheets.formula_templates import (
    CALCULATE_HOURS,
    GROSS_TOTAL,
    IMPORT_TIMESHEET,
    NET_TOTAL,
    REVENUE,
)
from feptm.adapters.sheets.mappers import (
    build_column_index,
    get_cell_value,
    get_column_letter,
    merge_specialists_by_timesheet_id,
    row_to_specialist,
    specialist_to_row,
)
from feptm.core.config import settings
from feptm.core.exceptions import GoogleApiError, NotFoundError, ValidationError
from feptm.core.log import log
from feptm.domain.models.specialist import Specialist
from feptm.domain.services.protocols import SpecialistRepository


class SpreadsheetSpecialistRepository(SpecialistRepository):
    """Specialist repository using Google Sheets via pygsheets.

    FR-002: Creates timesheet, updates Team sheet, creates report tabs with IMPORTRANGE,
    applies calculation formulas.
    FR-002.1: Supports multiple rate periods per specialist (multiple rows with same Timesheet ID).
    """

    def __init__(
        self,
        client: PygSheetsClient,
        timesheet_template_id: str,
    ) -> None:
        """Initialize SpreadsheetSpecialistRepository.

        Args:
            client: PygSheetsClient for spreadsheet operations
            timesheet_template_id: Template ID for timesheet spreadsheet
        """
        self._client = client
        self._timesheet_template_id = timesheet_template_id

    def create_timesheet(
        self, specialist: Specialist, project_id: str
    ) -> str:
        """Create timesheet for specialist, return timesheet ID.

        FR-002: Creates timesheet from template, places in project folder.

        Args:
            specialist: Specialist domain model
            project_id: External project ID (Project Info spreadsheet ID)

        Returns:
            Timesheet ID (serves as specialist identifier)

        Raises:
            ValidationError: If timesheet template not configured
            NotFoundError: If project not found
            GoogleApiError: If timesheet creation fails
        """
        if not self._timesheet_template_id:
            raise ValidationError("GOOGLE_TIMESHEET_TEMPLATE_ID not configured")

        try:
            # Get project folder ID from Project Info spreadsheet
            project_folder_id = self._get_project_folder_id(project_id)
            if not project_folder_id:
                raise NotFoundError(
                    f"Project folder ID not found for project {project_id}"
                )

            # Get project name for timesheet title
            project_name = self._get_project_name(project_id)

            # FR-002: Create timesheet from template
            timesheet_title = f"Time Tracking for {specialist.name}. Project {project_name}"
            timesheet_spreadsheet = self._client.copy_spreadsheet(
                source_id=self._timesheet_template_id,
                title=timesheet_title,
                folder_id=project_folder_id,
            )

            timesheet_id = timesheet_spreadsheet.id
            log.info(f"Created timesheet for {specialist.name}: {timesheet_id}")
            return timesheet_id

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to create timesheet for {specialist.name}: {e}")
            raise GoogleApiError(f"Failed to create timesheet: {e}") from e

    def get_by_project(self, project_id: str) -> List[Specialist]:
        """Get all specialists for a project.

        FR-002.1: Reads Team sheet and merges rows with same Timesheet ID
        into specialists with multiple rate periods.

        Args:
            project_id: External project ID (Project Info spreadsheet ID)

        Returns:
            List of Specialist domain models with rate periods

        Raises:
            NotFoundError: If project not found
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.TEAM.value)
            if not ws:
                raise NotFoundError(
                    f"Team sheet not found in spreadsheet {project_id}"
                )

            # Read Team sheet data
            data = ws.get_values(TeamSheetConfig.START_CELL, TeamSheetConfig.END_CELL)
            if not data or len(data) < 2:
                return []

            # Build column index from header row
            col_index = build_column_index(data[0])

            # Group rows by Timesheet ID (FR-002.1)
            specialists_dict: dict[str, list[list[str]]] = {}
            for row in data[1:]:  # Skip header
                ts_id = get_cell_value(row, col_index, ColumnName.TIMESHEET.value)
                if ts_id:
                    if ts_id not in specialists_dict:
                        specialists_dict[ts_id] = []
                    specialists_dict[ts_id].append(row)

            # Convert rows to specialists and merge by Timesheet ID
            specialists_list = []
            for timesheet_id, rows in specialists_dict.items():
                # Each row represents a rate period (FR-002.1)
                rate_specialists = [
                    row_to_specialist(row, col_index, timesheet_id) for row in rows
                ]
                # Merge into one specialist with multiple rates
                merged = merge_specialists_by_timesheet_id(rate_specialists)
                if merged:
                    specialists_list.extend(merged)

            log.info(f"Found {len(specialists_list)} specialists for project {project_id}")
            return specialists_list

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to get specialists for project {project_id}: {e}")
            raise NotFoundError(f"Failed to get specialists: {e}") from e

    def get_specialists_without_timesheet(
        self, project_id: str
    ) -> List[tuple[Specialist, int]]:
        """Get specialists from Team sheet that don't have Timesheet ID.

        FR-002: Finds new specialists that need timesheets created.

        Args:
            project_id: External project ID (Project Info spreadsheet ID)

        Returns:
            List of (Specialist, row_index) tuples for specialists without Timesheet ID

        Raises:
            NotFoundError: If project not found
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.TEAM.value)
            if not ws:
                raise NotFoundError(
                    f"Team sheet not found in spreadsheet {project_id}"
                )

            data = ws.get_values(TeamSheetConfig.START_CELL, TeamSheetConfig.END_CELL)
            if not data or len(data) < 2:
                return []

            # Build column index from header row
            col_index = build_column_index(data[0])

            result = []
            for i, row in enumerate(data[1:], start=2):  # Skip header, 1-based row index
                # Check if row has data but no Timesheet ID
                name = get_cell_value(row, col_index, ColumnName.NAME.value)
                role = get_cell_value(row, col_index, ColumnName.ROLE.value)
                
                if name and role:  # Has Name and Role
                    ts_id = get_cell_value(row, col_index, ColumnName.TIMESHEET.value)
                    if not ts_id:
                        # Create specialist from row data using mapper
                        from feptm.adapters.sheets.mappers import _parse_date
                        from decimal import Decimal
                        from feptm.core.utils import parse_decimal_safely
                        from feptm.domain.models.specialist import Rate

                        internal_rate_str = get_cell_value(row, col_index, ColumnName.INTERNAL_RATE.value, "0")
                        external_rate_str = get_cell_value(row, col_index, ColumnName.EXTERNAL_RATE.value, "0")
                        start_date_str = get_cell_value(row, col_index, ColumnName.DATE.value)

                        internal_rate = parse_decimal_safely(internal_rate_str, Decimal("0"))
                        external_rate = parse_decimal_safely(external_rate_str, Decimal("0"))
                        start_date = _parse_date(start_date_str)

                        rate = Rate(
                            internal=internal_rate,
                            external=external_rate,
                            start_date=start_date,
                        )

                        specialist = Specialist(
                            name=name,
                            role=role,
                            rates=[rate],
                            joined_date=start_date,
                        )

                        result.append((specialist, i))

            log.info(f"Found {len(result)} specialists without timesheet in project {project_id}")
            return result

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to get specialists without timesheet: {e}")
            raise NotFoundError(f"Failed to get specialists: {e}") from e

    def update_team_sheet_timesheet_id(
        self, project_id: str, row_index: int, timesheet_id: str
    ) -> None:
        """Update Timesheet ID column for a specific row in Team sheet.

        Args:
            project_id: External project ID (Project Info spreadsheet ID)
            row_index: Row index (1-based)
            timesheet_id: Timesheet ID to write

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If update fails
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.TEAM.value)
            if not ws:
                raise NotFoundError(
                    f"Team sheet not found in spreadsheet {project_id}"
                )

            # Get header row to find Timesheet column
            header_data = ws.get_values("A1", "Z1")
            if not header_data or not header_data[0]:
                raise ValidationError("Team sheet has no headers")
            
            col_index = build_column_index(header_data[0])
            ts_column = get_column_letter(col_index, ColumnName.TIMESHEET.value)
            if not ts_column:
                raise ValidationError(f"Column '{ColumnName.TIMESHEET.value}' not found in Team sheet")

            # Write Timesheet ID to Timesheet column
            cell = f"{ts_column}{row_index}"
            ws.update_value(cell, timesheet_id)
            log.info(f"Updated Timesheet ID in row {row_index} to {timesheet_id}")

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to update Team sheet Timesheet ID: {e}")
            raise GoogleApiError(f"Failed to update Team sheet: {e}") from e

    def create_report_tabs(
        self, project_id: str, specialist: Specialist, timesheet_id: str
    ) -> None:
        """Create specialist tabs in reports and apply formulas.

        FR-002.5-8: Creates tabs in General Expenses and Payment Distribution reports
        with IMPORTRANGE formulas, adds rows to Current Period sheets.

        Args:
            project_id: External project ID (Project Info spreadsheet ID)
            specialist: Specialist domain model
            timesheet_id: Timesheet ID

        Raises:
            GoogleApiError: If operation fails
        """
        self._create_report_tabs_and_formulas(project_id, specialist, timesheet_id)

    def update_team_sheet(
        self, project_id: str, specialist: Specialist, timesheet_id: str
    ) -> None:
        """Update Team sheet with specialist information.

        FR-002: Updates Team sheet with timesheet ID.
        FR-002.1: Creates multiple rows for multiple rate periods (one row per rate).

        Args:
            project_id: External project ID (Project Info spreadsheet ID)
            specialist: Specialist domain model (may contain multiple rates)
            timesheet_id: Timesheet ID (specialist identifier)

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If update operation fails
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.TEAM.value)
            if not ws:
                raise NotFoundError(
                    f"Team sheet not found in spreadsheet {project_id}"
                )

            # FR-002.1: Create rows for each rate period
            project_name = self._get_project_name(project_id)
            rows = specialist_to_row(specialist, timesheet_id, project_name)

            # Check if specialist already exists (by Timesheet ID)
            existing_rows = self._find_rows_by_timesheet_id(ws, timesheet_id)

            if existing_rows:
                # FR-002.1: Update existing rows or add new rate periods
                # For simplicity, append new rate periods as new rows
                # In production, might need to update/merge existing rows
                start_row = len(existing_rows) + 2  # After existing rows, skip header
            else:
                # New specialist: append at end
                existing_data = ws.get_values(TeamSheetConfig.START_CELL, TeamSheetConfig.END_CELL)
                start_row = len(existing_data) + 1 if existing_data else 2

            # Write rows for each rate period
            for i, row in enumerate(rows):
                row_num = start_row + i
                ws.update_values(crange=f"A{row_num}", values=[row])

            log.info(
                f"Updated Team sheet with {len(rows)} rows for specialist {specialist.name}"
            )

            # FR-002.5-8: Create report tabs and apply formulas (if this is a new specialist)
            if not existing_rows:
                self._create_report_tabs_and_formulas(
                    project_id, specialist, timesheet_id
                )

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to update Team sheet: {e}")
            raise GoogleApiError(f"Failed to update Team sheet: {e}") from e

    def _find_rows_by_timesheet_id(
        self, worksheet: pygsheets.Worksheet, timesheet_id: str
    ) -> List[int]:
        """Find row indices for rows with given Timesheet ID.

        Args:
            worksheet: Team sheet worksheet
            timesheet_id: Timesheet ID to search for

        Returns:
            List of row indices (1-based)
        """
        data = worksheet.get_values(TeamSheetConfig.START_CELL, TeamSheetConfig.END_CELL)
        if not data or len(data) < 2:
            return []

        # Build column index from header row
        col_index = build_column_index(data[0])

        rows = []
        for i, row in enumerate(data[1:], start=2):  # Skip header, 1-based
            ts_id = get_cell_value(row, col_index, ColumnName.TIMESHEET.value)
            if ts_id == timesheet_id:
                rows.append(i)

        return rows

    def _create_report_tabs_and_formulas(
        self, project_id: str, specialist: Specialist, timesheet_id: str
    ) -> None:
        """Create specialist tabs in reports and apply formulas.

        FR-002.5-8: Creates tabs in General Expenses and Payment Distribution reports
        with IMPORTRANGE formulas, adds rows to Current Period sheets with calculation formulas.

        Args:
            project_id: External project ID (Project Info spreadsheet ID)
            specialist: Specialist domain model
            timesheet_id: Timesheet ID

        Raises:
            GoogleApiError: If operation fails
        """
        try:
            # Get report IDs from Project Info sheet
            report_id, calculations_id = self._get_report_ids(project_id)
            if not report_id or not calculations_id:
                log.warning(
                    f"Report IDs not found for project {project_id}, skipping report tab creation"
                )
                return

            # FR-002.5-6: Create specialist tabs with IMPORTRANGE
            self._create_specialist_tab(report_id, specialist.name, timesheet_id, "timesheet!A:D")
            self._create_specialist_tab(
                calculations_id, specialist.name, timesheet_id, "timesheet!A:E"
            )

            # FR-002.7-8: Add specialist row to Current Period sheets with formulas
            self._add_specialist_to_current_period(
                report_id, specialist, timesheet_id
            )
            self._add_specialist_to_current_period(
                calculations_id, specialist, timesheet_id
            )

            log.info(
                f"Created report tabs and formulas for specialist {specialist.name}"
            )

        except Exception as e:
            log.error(f"Failed to create report tabs: {e}")
            # Don't fail the whole operation if report tabs fail
            log.warning("Continuing without report tabs due to error")

    def _create_specialist_tab(
        self, spreadsheet_id: str, tab_name: str, timesheet_id: str, range_str: str
    ) -> None:
        """Create specialist tab with IMPORTRANGE formula.

        FR-002.5-6: Creates tab named after specialist with IMPORTRANGE formula.

        Args:
            spreadsheet_id: Report spreadsheet ID
            tab_name: Tab name (specialist name)
            timesheet_id: Timesheet ID for IMPORTRANGE
            range_str: Range string for IMPORTRANGE (e.g., "timesheet!A:D")
        """
        try:
            spreadsheet = self._client.open_spreadsheet(spreadsheet_id)

            # Check if tab already exists (FR-002.1: MUST NOT duplicate)
            try:
                ws = spreadsheet.worksheet_by_title(tab_name)
                if ws:
                    log.info(f"Tab {tab_name} already exists, skipping creation")
                    return
            except pygsheets.WorksheetNotFound:
                pass  # Tab doesn't exist, create it

            # Create new worksheet
            ws = spreadsheet.add_worksheet(title=tab_name, rows=100, cols=20)

            # FR-002.5-6: Add IMPORTRANGE formula in A1
            import_formula = IMPORT_TIMESHEET.render(spreadsheet_id=timesheet_id)
            # Update range_str in formula
            import_formula = import_formula.replace("timesheet!A:E", range_str)
            self._client.set_cell_formula(ws, "A1", import_formula)

            log.info(f"Created tab {tab_name} with IMPORTRANGE in {spreadsheet_id}")

        except Exception as e:
            log.error(f"Failed to create specialist tab {tab_name}: {e}")
            raise

    def _add_specialist_to_current_period(
        self, spreadsheet_id: str, specialist: Specialist, timesheet_id: str
    ) -> None:
        """Add specialist row to Current Period sheet with calculation formulas.

        FR-002.7-8: Adds row to Current Period sheet and applies calculation formulas.

        Args:
            spreadsheet_id: Report spreadsheet ID
            specialist: Specialist domain model
            timesheet_id: Timesheet ID
        """
        try:
            spreadsheet = self._client.open_spreadsheet(spreadsheet_id)
            ws = spreadsheet.worksheet_by_title(SheetName.CURRENT_PERIOD.value)
            if not ws:
                log.warning(
                    f"Current Period sheet not found in {spreadsheet_id}, skipping"
                )
                return

            # Find next empty row (after header)
            data = ws.get_values(CurrentPeriodConfig.START_CELL, CurrentPeriodConfig.END_CELL)
            if not data:
                next_row = 2
            else:
                next_row = len(data) + 1

            # Check if specialist already exists (FR-002.1: MUST NOT duplicate)
            if data and len(data) > 1:
                for row in data[1:]:
                    if len(row) > 0 and row[0] == specialist.name:
                        log.info(
                            f"Specialist {specialist.name} already in Current Period, skipping"
                        )
                        return

            # Get first rate for initial values (FR-002.1: formulas handle multiple periods)
            first_rate = specialist.rates[0] if specialist.rates else None
            if not first_rate:
                log.warning(
                    f"Specialist {specialist.name} has no rates, skipping Current Period"
                )
                return

            # Prepare row data (columns depend on report type)
            # General Expenses: Specialist | Role | Period | Hours Worked | Rate | Total Cost
            # Payment Distribution: Specialist | Role | Period | Hours | Specialist Rate | Client Rate | Specialist Cost | Client Cost | Revenue

            # Detect report type by checking column headers
            headers = data[0] if data else []
            is_payment_distribution = "Revenue" in str(headers) or "Client Rate" in str(headers)

            if is_payment_distribution:
                # Payment Distribution format
                # Use formulas with row number
                row_ref = next_row
                updates = [
                    (f"A{row_ref}", specialist.name),
                    (f"B{row_ref}", specialist.role),
                    (f"C{row_ref}", ""),  # Period (filled manually)
                    (f"D{row_ref}", CALCULATE_HOURS.render(row=str(row_ref))),  # Hours
                    (f"E{row_ref}", str(first_rate.internal)),  # Specialist Rate
                    (f"F{row_ref}", str(first_rate.external)),  # Client Rate
                    (f"G{row_ref}", NET_TOTAL.render(row=str(row_ref))),  # Specialist Cost
                    (f"H{row_ref}", GROSS_TOTAL.render(row=str(row_ref))),  # Client Cost
                    (f"I{row_ref}", REVENUE.render(row=str(row_ref))),  # Revenue
                ]
            else:
                # General Expenses format
                row_ref = next_row
                updates = [
                    (f"A{row_ref}", specialist.name),
                    (f"B{row_ref}", specialist.role),
                    (f"C{row_ref}", ""),  # Period (filled manually)
                    (f"D{row_ref}", CALCULATE_HOURS.render(row=str(row_ref))),  # Hours Worked
                    (f"E{row_ref}", str(first_rate.external)),  # Hourly Rate
                    (f"F{row_ref}", GROSS_TOTAL.render(row=str(row_ref))),  # Total Cost
                ]

            # Batch update cells
            self._client.batch_update_values(ws, updates)

            log.info(
                f"Added specialist {specialist.name} to Current Period in {spreadsheet_id}"
            )

        except Exception as e:
            import traceback
            log.error(f"Failed to add specialist to Current Period: {e}")
            log.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _get_project_folder_id(self, project_id: str) -> str | None:
        """Get project folder ID from Project Info sheet.

        Args:
            project_id: Project Info spreadsheet ID

        Returns:
            Folder ID or None if not found
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            from feptm.adapters.sheets.constants import RowName

            ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
            if not ws:
                return None

            data = ws.get_values(ProjectInfoConfig.START_CELL, ProjectInfoConfig.END_CELL)
            if not data:
                return None

            # Find "Project Folder" row and extract ID from HYPERLINK
            for i, row in enumerate(data, start=1):
                if len(row) >= 2 and str(row[0]).strip() == RowName.PROJECT_FOLDER.value:
                    # Extract folder ID from URL in formula
                    cell = ws.cell(f"B{i}")
                    formula = cell.formula if cell.formula else ""
                    if formula and "folders/" in formula:
                        # Extract ID from HYPERLINK formula
                        import re
                        match = re.search(r"folders/([a-zA-Z0-9_-]+)", formula)
                        if match:
                            return match.group(1)

            return None

        except Exception:
            return None

    def _get_project_name(self, project_id: str) -> str:
        """Get project name from Project Info sheet.

        Args:
            project_id: Project Info spreadsheet ID

        Returns:
            Project name
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            from feptm.adapters.sheets.constants import RowName

            ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
            if not ws:
                return "Unknown"

            data = ws.get_values(ProjectInfoConfig.START_CELL, ProjectInfoConfig.END_CELL)
            if not data:
                return "Unknown"

            # Find "Name" row
            for row in data:
                if len(row) >= 2 and str(row[0]).strip() == RowName.NAME.value:
                    return str(row[1]) if row[1] else "Unknown"

            return "Unknown"

        except Exception:
            return "Unknown"

    def _get_report_ids(self, project_id: str) -> tuple[str | None, str | None]:
        """Get report and calculations spreadsheet IDs from Project Info sheet.

        Args:
            project_id: Project Info spreadsheet ID

        Returns:
            Tuple of (report_id, calculations_id)
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            from feptm.adapters.sheets.constants import RowName

            ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
            if not ws:
                return None, None

            data = ws.get_values(ProjectInfoConfig.START_CELL, ProjectInfoConfig.END_CELL)
            if not data:
                return None, None

            report_id = None
            calculations_id = None

            for i, row in enumerate(data, start=1):
                if len(row) >= 2:
                    field = str(row[0]).strip()
                    value = row[1]

                    if field == RowName.GENERAL_EXPENSES.value and value:
                        # Extract ID from HYPERLINK formula
                        cell = ws.cell(f"B{i}")
                        formula = cell.formula if cell.formula else ""
                        if formula:
                            import re
                            match = re.search(r"spreadsheets/d/([a-zA-Z0-9_-]+)", formula)
                            if match:
                                report_id = match.group(1)

                    elif field == RowName.PAYMENT_DISTRIBUTION.value and value:
                        # Extract ID from HYPERLINK formula
                        cell = ws.cell(f"B{i}")
                        formula = cell.formula if cell.formula else ""
                        if formula:
                            import re
                            match = re.search(r"spreadsheets/d/([a-zA-Z0-9_-]+)", formula)
                            if match:
                                calculations_id = match.group(1)

            return report_id, calculations_id

        except Exception:
            return None, None
