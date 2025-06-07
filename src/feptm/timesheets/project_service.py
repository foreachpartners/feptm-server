"""Service for working with Google Sheets and projects."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from feptm.core import utils
from feptm.core.config import settings
from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    ColumnName,
    DateFormat,
    FormulaName,
    RangeFormat,
    RowName,
    SheetName,
    UrlPattern,
    config_service,
)
from feptm.timesheets.specialist_service import SpecialistService


class TimesheetProjectService:
    """Service for handling project timesheets and related operations."""

    def __init__(self, google_sheets_service: GoogleSheetsService) -> None:
        """Initialize with Google Sheets service.

        Args:
            google_sheets_service: Google Sheets service instance
        """
        self.google_sheets_service = google_sheets_service
        self.specialist_service = SpecialistService(google_sheets_service)

    def update_project_info_sheet(self, spreadsheet_id: str, project: Project) -> None:
        """Update the project info sheet with project details.

        Args:
            spreadsheet_id: ID of the spreadsheet
            project: Project object with at least the name

        Returns:
            None
        """
        try:
            # Prepare basic project data
            project_data = []

            # Title row
            project_data.append(["Project Information", ""])

            # Headers
            project_data.append([RowName.FIELD.value, RowName.VALUE.value])

            # Project metadata
            project_data.append(
                [
                    RowName.PROJECT_ID.value,
                    project.project_info_spreadsheet_id or "Not assigned yet",
                ]
            )
            project_data.append([RowName.NAME.value, project.name])
            project_data.append(
                [
                    RowName.CREATED.value,
                    datetime.strftime(
                        project.created, DateFormat.DISPLAY_DATETIME.value
                    ),
                ]
            )
            project_data.append(
                [
                    RowName.MODIFIED.value,
                    datetime.strftime(
                        project.modified, DateFormat.DISPLAY_DATETIME.value
                    ),
                ]
            )

            # Add hyperlink to Google Drive folder if available
            folder_url = (
                UrlPattern.DRIVE_FOLDER.format(folder_id=project.drive_folder_id)
                if project.drive_folder_id
                else ""
            )
            project_data.append(
                [
                    RowName.PROJECT_FOLDER.value,
                    f'=HYPERLINK("{folder_url}"; "{folder_url}")',
                ]
            )

            # Add links to created documents
            project_data.append(
                [
                    RowName.PAYMENT_DISTRIBUTION.value,
                    f'=HYPERLINK("{project.calculations_spreadsheet_url}"; "{project.calculations_spreadsheet_url}")',
                ]
            )
            project_data.append(
                [
                    RowName.GENERAL_EXPENSES.value,
                    f'=HYPERLINK("{project.report_spreadsheet_url}"; "{project.report_spreadsheet_url}")',
                ]
            )

            # Use the service to update the sheet
            self.google_sheets_service.update_sheet_data(
                spreadsheet_id=spreadsheet_id,
                sheet_name=SheetName.PROJECT_INFO.value,
                data=project_data,
            )

            return None
        except Exception as error:
            raise Exception(f"Failed to update project info sheet: {error}")

    def _create_spreadsheet_from_template(
        self, template_id: Optional[str], new_title: str, folder_id: str
    ) -> Dict[str, str]:
        """Helper method to create a spreadsheet from a template.

        Args:
            template_id: ID of the template spreadsheet
            new_title: Title for the new spreadsheet
            folder_id: ID of the folder where to place the copy

        Returns:
            Dictionary with spreadsheet ID and URL

        Raises:
            Exception: If template ID is not configured or accessible
        """
        if not template_id:
            raise Exception("Template ID is not configured in settings")

        # Create spreadsheet from template
        result = self.google_sheets_service.ensure_spreadsheet_from_template(
            template_id=template_id, new_title=new_title, folder_id=folder_id
        )

        log.info(
            f"Created spreadsheet: {new_title} (ID: {result.get('spreadsheet_id')})"
        )
        return result

    def create_project(self, project: Project) -> Dict[str, str]:
        """Create a project in Google Drive with all required components.

        Args:
            project: Project object with at least the name

        Returns:
            Dictionary with project details including IDs and URLs
        """
        if not self.google_sheets_service.is_initialized():
            raise Exception(
                "Google services are not initialized. Please check your credentials and scopes."
            )

        try:
            project_name = project.name

            log.info(f"Creating project: {project_name}")

            # 1. Create a folder for the project
            parent_folder_id = settings.GOOGLE_PROJECTS_FOLDER_ID

            # Create folder in root or parent folder
            if parent_folder_id:
                # Verify that parent folder exists and is accessible
                try:
                    parent_folder = self.google_sheets_service.get_file(
                        parent_folder_id
                    )
                    log.info(
                        f"Parent folder found: {parent_folder.get('name')} (ID: {parent_folder.get('id')})"
                    )
                except Exception as error:
                    raise Exception(
                        f"Parent folder with ID {parent_folder_id} not found or not accessible: {str(error)}"
                    )

                folder_info = self.google_sheets_service.create_drive_folder(
                    f"{project_name}", parent_folder_id
                )
            else:
                # If no parent folder ID is set, create in the root of Google Drive
                folder_info = self.google_sheets_service.create_drive_folder(
                    f"{project_name}"
                )

            project_folder_id = folder_info["folder_id"]
            log.info(
                f"Created project folder: {project_name} (ID: {project_folder_id})"
            )

            # 2. Create project info spreadsheet from template
            project_info = self._create_spreadsheet_from_template(
                template_id=settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID,
                new_title=f"{project_name} - Project info",
                folder_id=project_folder_id,
            )

            # 3. Create report spreadsheet from template
            report = self._create_spreadsheet_from_template(
                template_id=settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID,
                new_title=f"{project_name} - General Expenses",
                folder_id=project_folder_id,
            )

            # 4. Create calculations spreadsheet from template
            calculations = self._create_spreadsheet_from_template(
                template_id=settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID,
                new_title=f"{project_name} - Payment Distribution",
                folder_id=project_folder_id,
            )

            # Update project with information about created resources
            project.drive_folder_id = project_folder_id
            project.project_info_spreadsheet_id = project_info["spreadsheet_id"]
            project.report_spreadsheet_id = report["spreadsheet_id"]
            project.calculations_spreadsheet_id = calculations["spreadsheet_id"]
            project.modified = datetime.utcnow()

            # Update main project information
            log.info(
                f"Updating project info with links to related documents:\n"
                f"  - Project name: {project_name}\n"
                f"  - Project info URL: {project_info['spreadsheet_url']}\n"
                f"  - Folder URL: https://drive.google.com/drive/folders/{project_folder_id}\n"
                f"  - Calculations URL: {calculations['spreadsheet_url']}\n"
                f"  - Report URL: {report['spreadsheet_url']}"
            )

            self.update_project_info_sheet(project_info["spreadsheet_id"], project)
            log.info(f"Project info updated successfully")

            # Return all information about the created project
            return {
                "drive_folder_id": project_folder_id,
                "drive_folder_url": folder_info["folder_url"],
                "project_info_spreadsheet_id": project_info["spreadsheet_id"],
                "project_info_spreadsheet_url": project_info["spreadsheet_url"],
                "report_spreadsheet_id": report["spreadsheet_id"],
                "report_spreadsheet_url": report["spreadsheet_url"],
                "calculations_spreadsheet_id": calculations["spreadsheet_id"],
                "calculations_spreadsheet_url": calculations["spreadsheet_url"],
            }
        except Exception as e:
            # Clean up any created resources on failure
            try:
                if "project_folder_id" in locals():
                    self.google_sheets_service.delete_file(project_folder_id)
                    log.warning(f"Cleaned up folder {project_folder_id} after error")
            except Exception as cleanup_error:
                log.error(
                    f"Failed to clean up resources after error: {str(cleanup_error)}"
                )

            raise Exception(f"Failed to create project: {str(e)}")

    def sync_project_specialists(
        self, project_id: str
    ) -> Tuple[List[Specialist], int, int]:
        """Synchronize specialists from project info sheet.

        This method coordinates the entire synchronization process:
        1. Validates project exists and extracts metadata
        2. Creates timesheet context for specialists
        3. Delegates specialist synchronization to SpecialistService
        4. Links specialist timesheets to report and calculation sheets

        Args:
            project_id: ID of the project info spreadsheet

        Returns:
            Tuple containing (specialists, total_count, new_timesheets_created)

        Raises:
            Exception: If synchronization fails
        """
        try:
            # Validate project and get metadata
            project = self._validate_and_extract_project(project_id)

            # Check if we have required data for timesheet creation
            if not project.drive_folder_id:
                raise Exception(
                    f"Cannot create timesheets: drive folder ID not found for project '{project.name}'. Please ensure the project folder is properly linked in the project info sheet."
                )

            # Create context for timesheet operations
            context = TimesheetContext(
                folder_id=project.drive_folder_id, project_name=project.name
            )

            # Delegate specialist synchronization
            specialists, new_count = self.specialist_service.sync_specialists(
                spreadsheet_id=project_id, context=context
            )

            if not specialists:
                log.info("No specialists found in project sheet")
                return [], 0, 0

            # Link timesheets to reports and calculations for new specialists
            new_specialists = [s for s in specialists if s.timesheet and new_count > 0]
            if new_specialists:
                self._link_timesheets_to_reports(project, new_specialists)

            log.info(
                "Synchronized %d specialists, created %d new timesheets",
                len(specialists),
                new_count,
            )
            return specialists, len(specialists), new_count

        except Exception as e:
            log.error("Failed to sync project specialists: %s", str(e))
            raise Exception(f"Failed to sync project specialists: {str(e)}")

    def _validate_and_extract_project(self, project_id: str) -> Project:
        """Validate project exists and extract its metadata.

        Args:
            project_id: ID of the project info spreadsheet

        Returns:
            Project object with metadata

        Raises:
            Exception: If project validation or metadata extraction fails
        """
        try:
            project_info = self.google_sheets_service.get_file(project_id)
            log.debug("Project found: %s", project_info.get("name"))
        except Exception as e:
            raise Exception(f"Project with ID {project_id} not found: {str(e)}")

        return self._extract_project_metadata(project_id)

    def _link_timesheets_to_reports(
        self, project: Project, specialists: List[Specialist]
    ) -> None:
        """Link specialist timesheets to report and calculation sheets.

        Args:
            project: Project object with metadata
            specialists: List of specialists with timesheets to link
        """
        self._link_specialist_timesheets(project=project, specialists=specialists)

    def _extract_project_metadata(self, project_id: str) -> Project:
        """Extract project metadata from project info sheet.

        Args:
            project_id: ID of the project info spreadsheet

        Returns:
            Project object with metadata

        Raises:
            Exception: If metadata extraction fails
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            # Get project info sheet
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=project_id, sheet_name=SheetName.PROJECT_INFO.value
            )

            if not sheet:
                raise Exception("Project info sheet not found")

            # Read project data
            range_name = RangeFormat.PROJECT_INFO.value
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=project_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values:
                raise Exception("No data found in project info sheet")

            # Extract project metadata
            project_name = ""
            drive_folder_id = None
            report_spreadsheet_id = None
            calculations_spreadsheet_id = None

            for row in values:
                if len(row) < 2:
                    continue

                field = row[0].strip()
                value = row[1].strip()

                log.debug("Processing field: '%s' with value: '%s'", field, value)

                if field == RowName.NAME.value:
                    project_name = value
                    log.debug("Found project name: %s", project_name)
                elif field == RowName.PROJECT_FOLDER.value:
                    # Extract folder ID from HYPERLINK formula using utility
                    drive_folder_id = utils.extract_id_from_hyperlink_formula(value)
                    log.debug(
                        "Extracted drive_folder_id: %s from value: %s",
                        drive_folder_id,
                        value,
                    )
                elif field == RowName.GENERAL_EXPENSES.value:
                    # Extract report ID from HYPERLINK formula using utility
                    report_spreadsheet_id = utils.extract_id_from_hyperlink_formula(
                        value
                    )
                    log.debug(
                        "Extracted report_spreadsheet_id: %s", report_spreadsheet_id
                    )
                elif field == RowName.PAYMENT_DISTRIBUTION.value:
                    # Extract calculations ID from HYPERLINK formula using utility
                    calculations_spreadsheet_id = (
                        utils.extract_id_from_hyperlink_formula(value)
                    )
                    log.debug(
                        "Extracted calculations_spreadsheet_id: %s",
                        calculations_spreadsheet_id,
                    )

            if not project_name:
                raise Exception("Project name not found in project info sheet")

            # If drive_folder_id not found, try to get it from the project file's parent
            if not drive_folder_id:
                log.warning(
                    "Drive folder ID not found in project info, trying to get from file metadata"
                )
                try:
                    file_info = self.google_sheets_service.get_file(project_id)
                    parents = file_info.get("parents", [])
                    if parents:
                        drive_folder_id = parents[0]
                        log.info(
                            "Found drive folder ID from file metadata: %s",
                            drive_folder_id,
                        )
                except Exception as e:
                    log.warning(
                        "Failed to get drive folder ID from file metadata: %s", str(e)
                    )

            # Create Project object
            project = Project(
                name=project_name,
                drive_folder_id=drive_folder_id,
                project_info_spreadsheet_id=project_id,
                report_spreadsheet_id=report_spreadsheet_id,
                calculations_spreadsheet_id=calculations_spreadsheet_id,
            )

            log.debug("Created project object with folder_id: %s", drive_folder_id)
            return project

        except Exception as e:
            log.error("Error extracting project metadata: %s", str(e))
            raise Exception(f"Failed to extract project metadata: {str(e)}")

    def _link_specialist_timesheets(
        self, project: Project, specialists: List[Specialist]
    ) -> None:
        """Link specialist timesheets to report and calculations sheets.

        Args:
            project: Project object
            specialists: List of specialists to link

        Raises:
            Exception: If linking fails
        """
        try:
            if (
                not project.report_spreadsheet_id
                or not project.calculations_spreadsheet_id
            ):
                raise Exception(
                    "Project report or calculations spreadsheet ID not found"
                )

            # Get tabs in the report sheet
            report_sheets = self._get_spreadsheet_sheets(project.report_spreadsheet_id)
            calculations_sheets = self._get_spreadsheet_sheets(
                project.calculations_spreadsheet_id
            )

            # For each specialist
            for specialist in specialists:
                # Check if the specialist already has a tab in the report
                specialist_tab_name = specialist.name

                # Check if tab exists in report
                if specialist_tab_name not in report_sheets:
                    # Create a new tab
                    self._create_specialist_tab_in_report(
                        project.report_spreadsheet_id, specialist_tab_name, specialist
                    )

                # Check if tab exists in calculations
                if specialist_tab_name not in calculations_sheets:
                    # Create a new tab
                    self._create_specialist_tab_in_calculations(
                        project.calculations_spreadsheet_id,
                        specialist_tab_name,
                        specialist,
                    )

                # Update the Current Period tab in the report (General Expenses)
                self._update_general_expenses_current_period_tab(
                    spreadsheet_id=project.report_spreadsheet_id, specialist=specialist
                )

                # Update the Current Period tab in the calculations (Payment Distribution)
                self._update_payment_distribution_current_period_tab(
                    spreadsheet_id=project.calculations_spreadsheet_id,
                    specialist=specialist,
                )

        except Exception as e:
            log.error("Error linking specialist timesheets: %s", str(e))
            raise Exception(f"Failed to link specialist timesheets: {str(e)}")

    def _update_general_expenses_current_period_tab(
        self, spreadsheet_id: str, specialist: Specialist
    ) -> None:
        """Update Current Period tab in General Expenses spreadsheet with specialist.

        Args:
            spreadsheet_id: ID of the General Expenses spreadsheet
            specialist: Specialist object

        Raises:
            Exception: If update fails
        """
        try:
            sheet_name = SheetName.CURRENT_PERIOD.value
            sheet_data = self._get_current_period_sheet_data(spreadsheet_id, sheet_name)

            if not sheet_data:
                return

            values, headers, sheet = sheet_data

            # Check if specialist already exists
            if self._specialist_exists_in_current_period(
                values, headers, specialist.name
            ):
                log.info(
                    "Specialist %s already exists in Current Period", specialist.name
                )
                return

            # Find insert position
            insert_row, should_insert = self._find_insert_position_for_specialist(values, headers)

            # Insert row if needed and update data
            self._insert_and_update_specialist_row(
                spreadsheet_id, sheet_name, sheet, insert_row, should_insert, specialist, headers, values
            )

            log.info("Added %s to %s tab", specialist.name, sheet_name)

        except Exception as e:
            log.error(
                "Failed to update General Expenses Current Period tab: %s", str(e)
            )
            raise Exception(
                f"Failed to update General Expenses Current Period tab: {str(e)}"
            )

    def _get_current_period_sheet_data(
        self, spreadsheet_id: str, sheet_name: str
    ) -> Optional[Tuple[List[List], List[str], Dict]]:
        """Get sheet data for Current Period operations.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet

        Returns:
            Tuple of (values, headers, sheet) or None if not found
        """
        if not self.google_sheets_service.sheets_service:
            raise Exception("Google Sheets service not initialized")

        sheet = self.google_sheets_service.get_sheet_by_name(
            spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
        )

        if not sheet:
            log.warning(
                "Sheet '%s' not found in spreadsheet %s", sheet_name, spreadsheet_id
            )
            return None

        # Get current data
        range_name = RangeFormat.CURRENT_PERIOD.value.format(sheet_name=sheet_name)
        result = (
            self.google_sheets_service.sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )

        values = result.get("values", [])
        if not values:
            log.warning("No data found in sheet '%s'", sheet_name)
            return None

        headers = values[0]
        return values, headers, sheet

    def _specialist_exists_in_current_period(
        self, values: List[List], headers: List[str], specialist_name: str
    ) -> bool:
        """Check if specialist already exists in Current Period sheet.

        Args:
            values: Sheet values
            headers: Header row
            specialist_name: Name of the specialist to check

        Returns:
            True if specialist exists
        """
        specialist_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST.value]
        )
        if specialist_idx is None:
            return False

        for i, row in enumerate(values[1:], start=1):  # Skip header
            if len(row) > specialist_idx and row[specialist_idx] == specialist_name:
                return True

        return False

    def _find_insert_position_for_specialist(
        self, values: List[List], headers: List[str]
    ) -> Tuple[int, bool]:
        """Find the position where to insert a new specialist.

        Args:
            values: Sheet values
            headers: Header row

        Returns:
            Tuple of (row index for insertion (0-based), should_insert_new_row)
        """
        specialist_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST.value]
        )
        if specialist_idx is None:
            return 1, False  # Use row 2, don't insert new row

        last_data_row = None
        total_row = None
        has_specialists = False

        for i, row in enumerate(values[1:], start=1):  # Skip header
            if len(row) > specialist_idx and row[specialist_idx]:
                has_specialists = True
                last_data_row = i

            # Check for total row (usually has formula or specific pattern)
            if i > 0 and len(row) > specialist_idx:
                if (
                    not row[specialist_idx]
                    or row[specialist_idx] == "0"
                    or (len(row) > 2 and "$" in str(row[2]) and not row[0])
                ):
                    total_row = i
                    break

        # Determine insert position
        if not has_specialists:
            # First specialist - check if there's an empty row after header
            if len(values) > 1 and (len(values[1]) == 0 or not any(values[1])):
                return 1, False  # Use existing empty row 2, don't insert
            else:
                return 1, True  # Insert new row after header

        # For subsequent specialists, always insert new row
        if last_data_row is not None:
            insert_row = last_data_row + 1
        else:
            insert_row = 1

        # Insert before total row if it exists
        if total_row is not None and insert_row >= total_row:
            insert_row = total_row

        return insert_row, True

    def _insert_and_update_specialist_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        sheet: Dict,
        insert_row: int,
        should_insert: bool,
        specialist: Specialist,
        headers: List[str],
        values: List[List],
    ) -> None:
        """Insert new row if needed and update with specialist data using template copying.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            sheet: Sheet object
            insert_row: Row index for insertion
            should_insert: Whether to insert a new row
            specialist: Specialist object with data
            headers: Column headers
            values: Current sheet values for template detection
        """
        sheet_id = sheet.get("properties", {}).get("sheetId")
        target_row = insert_row + 1  # Convert to 1-based indexing

        # Insert row if needed
        if should_insert:
            try:
                request = {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": insert_row,
                            "endIndex": insert_row + 1,
                        },
                        "inheritFromBefore": True,
                    }
                }

                self.google_sheets_service.batch_update(
                    spreadsheet_id=spreadsheet_id, requests=[request]
                )
                log.debug("Inserted new row at position %d", insert_row)
            except Exception as e:
                log.warning("Failed to insert row, continuing with update: %s", str(e))

        # Find template row to copy formatting and formulas from
        template_row = self._find_template_row_for_specialist(values, headers)
        
        if template_row:
            try:
                # Copy formatting and formulas from template row
                self._copy_row_formatting(
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    source_row=template_row,
                    target_row=target_row,
                    paste_type="PASTE_NORMAL"  # Copy everything: formulas, formatting, etc.
                )
                log.debug("Copied template from row %d to row %d", template_row, target_row)
            except Exception as e:
                log.warning("Failed to copy template formatting: %s", str(e))
        else:
            # No template row found (first specialist) - add formulas from config
            try:
                self._add_formulas_from_config(
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    target_row=target_row,
                    headers=headers,
                )
                log.debug("Added formulas from config for first specialist")
            except Exception as e:
                log.warning("Failed to add formulas from config: %s", str(e))

        # Update specialist-specific data (name, role, rates)
        self._update_specialist_data_in_row(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            target_row=target_row,
            specialist=specialist,
            headers=headers,
        )

    def _add_formulas_from_config(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        target_row: int,
        headers: List[str],
    ) -> None:
        """Add formulas from configuration for the first specialist.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            target_row: Target row to update (1-based)
            headers: Column headers
        """
        # Add working hours formula
        hours_worked_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.HOURS_WORKED.value]
        )
        if hours_worked_idx is not None:
            try:
                working_hours_formula = config_service.get_formula(
                    FormulaName.CALCULATE_WORKING_HOURS
                )
                range_name = f"{sheet_name}!{self._column_letter(hours_worked_idx)}{target_row}"
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=[[working_hours_formula]],
                    value_input_option="USER_ENTERED",
                )
                log.debug("Added working hours formula to row %d", target_row)
            except Exception as e:
                log.warning("Failed to set hours calculation formula: %s", str(e))

        # Add total cost formula for General Expenses sheet
        total_cost_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.TOTAL_COST_USD.value]
        )
        if total_cost_idx is not None:
            try:
                gross_total_cost_formula = config_service.get_formula(
                    FormulaName.GROSS_TOTAL_COST
                )
                range_name = f"{sheet_name}!{self._column_letter(total_cost_idx)}{target_row}"
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=[[gross_total_cost_formula]],
                    value_input_option="USER_ENTERED",
                )
                log.debug("Added total cost formula to row %d", target_row)
            except Exception as e:
                log.warning("Failed to set total cost formula: %s", str(e))

        # Add specialist work cost formula for Payment Distribution sheet
        specialist_cost_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST_WORK_COST_USD.value]
        )
        if specialist_cost_idx is not None:
            try:
                specialist_cost_formula = config_service.get_formula(
                    FormulaName.NET_TOTAL_COST
                )
                range_name = f"{sheet_name}!{self._column_letter(specialist_cost_idx)}{target_row}"
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=[[specialist_cost_formula]],
                    value_input_option="USER_ENTERED",
                )
                log.debug("Added specialist work cost formula to row %d", target_row)
            except Exception as e:
                log.warning("Failed to set specialist work cost formula: %s", str(e))

        # Add client work cost formula for Payment Distribution sheet
        client_cost_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.CLIENT_WORK_COST_USD.value]
        )
        if client_cost_idx is not None:
            try:
                client_cost_formula = config_service.get_formula(
                    FormulaName.GROSS_TOTAL_COST
                )
                range_name = f"{sheet_name}!{self._column_letter(client_cost_idx)}{target_row}"
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=[[client_cost_formula]],
                    value_input_option="USER_ENTERED",
                )
                log.debug("Added client work cost formula to row %d", target_row)
            except Exception as e:
                log.warning("Failed to set client work cost formula: %s", str(e))

        # Add revenue formula for Payment Distribution sheet
        revenue_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.REVENUE_USD.value]
        )
        if revenue_idx is not None:
            try:
                revenue_formula = config_service.get_formula(FormulaName.REVENUE)
                range_name = f"{sheet_name}!{self._column_letter(revenue_idx)}{target_row}"
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=[[revenue_formula]],
                    value_input_option="USER_ENTERED",
                )
                log.debug("Added revenue formula to row %d", target_row)
            except Exception as e:
                log.warning("Failed to set revenue formula: %s", str(e))

    def _update_specialist_data_in_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        target_row: int,
        specialist: Specialist,
        headers: List[str],
    ) -> None:
        """Update specialist-specific data in a row (name, role, rates).

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            target_row: Target row to update (1-based)
            specialist: Specialist object with data
            headers: Column headers
        """
        # Prepare updates for specialist-specific fields only
        updates = []
        
        # Update specialist name
        specialist_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST.value]
        )
        if specialist_idx is not None:
            range_name = f"{sheet_name}!{self._column_letter(specialist_idx)}{target_row}"
            updates.append((range_name, [[specialist.name]]))

        # Update specialist role
        role_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST_ROLE.value]
        )
        if role_idx is not None:
            range_name = f"{sheet_name}!{self._column_letter(role_idx)}{target_row}"
            updates.append((range_name, [[specialist.role]]))

        # Update hourly rate (external rate for general expenses)
        rate_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.HOURLY_RATE_USD.value]
        )
        if rate_idx is not None:
            range_name = f"{sheet_name}!{self._column_letter(rate_idx)}{target_row}"
            updates.append((range_name, [[str(specialist.external_rate)]]))

        # For payment distribution sheet, also update internal rates
        internal_rate_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST_HOURLY_RATE_USD.value]
        )
        if internal_rate_idx is not None:
            range_name = f"{sheet_name}!{self._column_letter(internal_rate_idx)}{target_row}"
            updates.append((range_name, [[str(specialist.internal_rate)]]))

        # For payment distribution sheet, also update client rate
        client_rate_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.CLIENT_HOURLY_RATE_USD.value]
        )
        if client_rate_idx is not None:
            range_name = f"{sheet_name}!{self._column_letter(client_rate_idx)}{target_row}"
            updates.append((range_name, [[str(specialist.external_rate)]]))

        # Apply all updates
        for range_name, values in updates:
            try:
                self.google_sheets_service.update_range(
                    spreadsheet_id=spreadsheet_id,
                    range_name=range_name,
                    values=values,
                    value_input_option="USER_ENTERED",
                )
            except Exception as e:
                log.warning("Failed to update %s: %s", range_name, str(e))

        log.debug("Updated specialist data for %s in row %d", specialist.name, target_row)

    def _update_payment_distribution_current_period_tab(
        self, spreadsheet_id: str, specialist: Specialist
    ) -> None:
        """Update Current Period tab in Payment Distribution spreadsheet with specialist.

        Args:
            spreadsheet_id: ID of the Payment Distribution spreadsheet
            specialist: Specialist object

        Raises:
            Exception: If update fails
        """
        try:
            sheet_name = SheetName.CURRENT_PERIOD.value
            sheet_data = self._get_current_period_sheet_data(spreadsheet_id, sheet_name)

            if not sheet_data:
                return

            values, headers, sheet = sheet_data

            # Check if specialist already exists
            if self._specialist_exists_in_current_period(
                values, headers, specialist.name
            ):
                log.info(
                    "Specialist %s already exists in Current Period", specialist.name
                )
                return

            # Find insert position
            insert_row, should_insert = self._find_insert_position_for_specialist(values, headers)

            # Insert row if needed and update data
            self._insert_and_update_specialist_row(
                spreadsheet_id, sheet_name, sheet, insert_row, should_insert, specialist, headers, values
            )

            log.info("Added %s to %s tab", specialist.name, sheet_name)

        except Exception as e:
            log.error(
                "Failed to update Payment Distribution Current Period tab: %s", str(e)
            )
            raise Exception(
                f"Failed to update Payment Distribution Current Period tab: {str(e)}"
            )

    def _get_spreadsheet_sheets(self, spreadsheet_id: str) -> List[str]:
        """Get list of sheet names in a spreadsheet.

        Args:
            spreadsheet_id: ID of the spreadsheet

        Returns:
            List of sheet names
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            spreadsheet = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            sheets = spreadsheet.get("sheets", [])
            return [sheet.get("properties", {}).get("title", "") for sheet in sheets]

        except Exception as e:
            log.error("Error getting spreadsheet sheets: %s", str(e))
            raise Exception(f"Failed to get spreadsheet sheets: {str(e)}")

    def _create_specialist_tab_in_report(
        self, spreadsheet_id: str, tab_name: str, specialist: Specialist
    ) -> None:
        """Create a tab for a specialist in the report spreadsheet.

        Args:
            spreadsheet_id: ID of the report spreadsheet
            tab_name: Name for the new tab
            specialist: Specialist object

        Raises:
            Exception: If tab creation fails
        """
        try:
            # Create a new sheet
            request = {"addSheet": {"properties": {"title": tab_name}}}

            self.google_sheets_service.batch_update(
                spreadsheet_id=spreadsheet_id, requests=[request]
            )

            # Add IMPORTRANGE formula directly in cell A1
            if specialist.timesheet is None:
                raise ValueError(
                    f"Specialist {specialist.name} does not have a timesheet ID"
                )

            import_formula = config_service.get_import_specialist_timesheet_formula(
                specialist_timesheet_id=specialist.timesheet
            )

            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )

            log.info("Created tab for %s in report spreadsheet", specialist.name)

        except Exception as e:
            log.error("Error creating specialist tab in report: %s", str(e))
            raise Exception(f"Failed to create specialist tab in report: {str(e)}")

    def _create_specialist_tab_in_calculations(
        self, spreadsheet_id: str, tab_name: str, specialist: Specialist
    ) -> None:
        """Create a tab for a specialist in the calculations spreadsheet.

        Args:
            spreadsheet_id: ID of the calculations spreadsheet
            tab_name: Name for the new tab
            specialist: Specialist object

        Raises:
            Exception: If tab creation fails
        """
        try:
            # Create a new sheet
            request = {"addSheet": {"properties": {"title": tab_name}}}

            self.google_sheets_service.batch_update(
                spreadsheet_id=spreadsheet_id, requests=[request]
            )

            # Add IMPORTRANGE formula directly in cell A1
            if specialist.timesheet is None:
                raise ValueError(
                    f"Specialist {specialist.name} does not have a timesheet ID"
                )

            import_formula = config_service.get_import_specialist_timesheet_formula(
                specialist_timesheet_id=specialist.timesheet
            )

            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )

            log.info("Created tab for %s in calculations spreadsheet", specialist.name)

        except Exception as e:
            log.error("Error creating specialist tab in calculations: %s", str(e))
            raise Exception(
                f"Failed to create specialist tab in calculations: {str(e)}"
            )

    def _copy_row_formatting(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        source_row: int, 
        target_row: int,
        paste_type: str = "PASTE_NORMAL"
    ) -> None:
        """Copy row formatting and formulas from one row to another.

        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            source_row: Source row to copy from (1-based)
            target_row: Target row to copy to (1-based)
            paste_type: Type of paste operation (PASTE_NORMAL, PASTE_FORMULA, PASTE_FORMAT)

        Raises:
            Exception: If copying fails
        """
        try:
            # Get sheet ID for the requests
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            sheet_id = None
            spreadsheet = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )

            for sheet in spreadsheet.get("sheets", []):
                if sheet.get("properties", {}).get("title") == sheet_name:
                    sheet_id = sheet.get("properties", {}).get("sheetId")
                    break

            if not sheet_id:
                raise Exception(f"Sheet ID not found for '{sheet_name}'")

            # Prepare copy paste request
            request = {
                "copyPaste": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": source_row - 1,
                        "endRowIndex": source_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 100,  # Large enough number to cover all columns
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": target_row - 1,
                        "endRowIndex": target_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 100,  # Large enough number to cover all columns
                    },
                    "pasteType": paste_type,
                    "pasteOrientation": "NORMAL",
                }
            }

            # Execute the request
            self.google_sheets_service.batch_update(
                spreadsheet_id=spreadsheet_id, requests=[request]
            )

            log.info(
                "Successfully copied row %d to row %d with paste type %s",
                source_row,
                target_row,
                paste_type,
            )

        except Exception as e:
            log.error("Error copying row formatting: %s", str(e))
            raise Exception(f"Failed to copy row formatting: {str(e)}")

    def _find_template_row_for_specialist(
        self, values: List[List], headers: List[str]
    ) -> Optional[int]:
        """Find a template row to copy formatting and formulas from.

        Args:
            values: Sheet values
            headers: Header row

        Returns:
            Row index (1-based) of template row or None if not found
        """
        specialist_idx = self.google_sheets_service.find_column_index(
            headers, [ColumnName.SPECIALIST.value]
        )
        if specialist_idx is None:
            return None

        # Look for the last row with specialist data (not total/summary rows)
        for i in range(len(values) - 1, 0, -1):  # Start from end, skip header
            row = values[i]
            if (len(row) > specialist_idx and 
                row[specialist_idx] and 
                row[specialist_idx] != "0" and
                not (len(row) > 2 and "$" in str(row[2]) and not row[0])):  # Skip total rows
                return i + 1  # Convert to 1-based indexing
        
        return None

    def _column_letter(self, index: int) -> str:
        """Convert column index to letter (A, B, C, etc.).

        Args:
            index: Zero-based column index

        Returns:
            Column letter
        """
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord("A")) + result
            index = index // 26 - 1
        return result
