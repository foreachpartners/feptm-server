"""Service for working with Google Sheets and projects."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from feptm.core.config import settings
from feptm.core.log import log
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.timesheets.config_service import (
    config_service, FormulaName, SheetName, ColumnName, 
    DateFormat, RangeFormat, RowName, UrlPattern
)
from feptm.timesheets.specialist_service import SpecialistService


class TimesheetProjectService:
    """Service for handling project timesheets."""

    def __init__(self, google_sheets_service: GoogleSheetsService):
        """Initialize with Google Sheets service."""
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
                [RowName.CREATED.value, datetime.strftime(project.created, DateFormat.DISPLAY_DATETIME.value)]
            )
            project_data.append(
                [
                    RowName.MODIFIED.value,
                    datetime.strftime(project.modified, DateFormat.DISPLAY_DATETIME.value),
                ]
            )

            # Add hyperlink to Google Drive folder if available
            folder_url = (
                UrlPattern.DRIVE_FOLDER.format(folder_id=project.drive_folder_id)
                if project.drive_folder_id
                else ""
            )
            project_data.append(
                [RowName.PROJECT_FOLDER.value, f'=HYPERLINK("{folder_url}"; "{folder_url}")']
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

        This method:
        1. Loads project info by ID
        2. Extracts specialists info from the project info sheet
        3. Creates timesheets for specialists who don't have them
        4. Updates the specialists info sheet with timesheet IDs
        5. Links specialist timesheets to report and calculation sheets

        Args:
            project_id: The ID of the project info spreadsheet

        Returns:
            Tuple containing:
            - List of all specialists
            - Total number of specialists found
            - Number of new timesheets created

        Raises:
            Exception: If synchronization fails
        """
        try:
            # 1. Validate the project spreadsheet exists
            try:
                project_info = self.google_sheets_service.get_file(project_id)
                log.info(f"Project info found: {project_info.get('name')}")
            except Exception as e:
                raise Exception(f"Project with ID {project_id} not found: {str(e)}")

            # 2. Get project metadata from the sheet
            project = self._extract_project_metadata(project_id)

            # 3. Get specialists from the project info sheet
            specialists, existing_timesheets = (
                self.specialist_service.get_specialists_from_sheet(
                    spreadsheet_id=project_id, sheet_name=SheetName.TEAM.value
                )
            )

            if not specialists:
                log.info("No specialists found in the project info sheet")
                return [], 0, 0

            log.info(
                f"Found {len(specialists)} specialists, {existing_timesheets} with existing timesheets"
            )

            # 4. Create timesheets for specialists without them
            specialists_with_new_timesheets = self._create_specialist_timesheets(
                project=project,
                specialists=specialists
            )

            new_timesheets_created = len(specialists_with_new_timesheets)

            # 5. Update project info sheet with timesheet IDs
            if new_timesheets_created > 0:
                self.specialist_service.update_specialists_sheet(
                    spreadsheet_id=project_id,
                    sheet_name=SheetName.TEAM.value,
                    specialists=specialists_with_new_timesheets,
                )

            # 6. Link timesheets to report and calculations sheets
            if specialists_with_new_timesheets:
                self._link_specialist_timesheets(
                    project=project, specialists=specialists_with_new_timesheets
                )

            return specialists, len(specialists), new_timesheets_created

        except Exception as e:
            log.error(f"Error syncing project specialists: {str(e)}")
            raise Exception(f"Failed to sync project specialists: {str(e)}")

    def _create_specialist_timesheets(self, project: Project, specialists: List[Specialist]) -> List[Specialist]:
        """Helper method to create timesheets for specialists without them.
        
        Args:
            project: Project object with folder_id
            specialists: List of specialists to check and create timesheets for
            
        Returns:
            List of specialists for which timesheets were created
            
        Raises:
            Exception: If folder_id is None or timesheet creation fails
        """
        specialists_with_new_timesheets = []
        
        for specialist in specialists:
            if not specialist.timesheet:
                # Make sure folder_id is not None
                if not project.drive_folder_id:
                    log.warning(
                        "Project drive folder ID is None, can't create timesheets"
                    )
                    break

                # Create timesheet
                result = self.specialist_service.create_specialist_timesheet(
                    specialist=specialist,
                    project_name=project.name,
                    folder_id=project.drive_folder_id,
                )
                specialists_with_new_timesheets.append(specialist)
                
        return specialists_with_new_timesheets

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

                if field == RowName.NAME.value:
                    project_name = value
                elif field == RowName.PROJECT_FOLDER.value:
                    # Extract folder ID from HYPERLINK formula or URL
                    if UrlPattern.DRIVE_FOLDERS_SEGMENT in value:
                        drive_folder_id = (
                            value.split(UrlPattern.DRIVE_FOLDERS_SEGMENT)[-1]
                            .split('"')[0]
                            .split(";")[0]
                        )
                elif field == RowName.GENERAL_EXPENSES.value:
                    # Extract report ID from HYPERLINK formula or URL
                    if UrlPattern.SPREADSHEETS_SEGMENT in value:
                        report_spreadsheet_id = (
                            value.split(UrlPattern.SPREADSHEETS_SEGMENT)[-1]
                            .split('"')[0]
                            .split(";")[0]
                        )
                elif field == RowName.PAYMENT_DISTRIBUTION.value:
                    # Extract calculations ID from HYPERLINK formula or URL
                    if UrlPattern.SPREADSHEETS_SEGMENT in value:
                        calculations_spreadsheet_id = (
                            value.split(UrlPattern.SPREADSHEETS_SEGMENT)[-1]
                            .split('"')[0]
                            .split(";")[0]
                        )

            if not project_name:
                raise Exception("Project name not found in project info sheet")

            # Create Project object
            project = Project(
                name=project_name,
                drive_folder_id=drive_folder_id,
                project_info_spreadsheet_id=project_id,
                report_spreadsheet_id=report_spreadsheet_id,
                calculations_spreadsheet_id=calculations_spreadsheet_id,
            )

            return project

        except Exception as e:
            log.error(f"Error extracting project metadata: {str(e)}")
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
            log.error(f"Error linking specialist timesheets: {str(e)}")
            raise Exception(f"Failed to link specialist timesheets: {str(e)}")

    def _update_general_expenses_current_period_tab(
        self, spreadsheet_id: str, specialist: Specialist
    ) -> None:
        """Update the Current Period tab in General Expenses spreadsheet with the specialist.

        Args:
            spreadsheet_id: ID of the General Expenses spreadsheet
            specialist: Specialist object

        Raises:
            Exception: If update fails
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            # Find the sheet with the exact name from Google Sheet
            sheet_name = SheetName.CURRENT_PERIOD.value
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
            )

            if not sheet:
                log.warning(f"{sheet_name} tab not found in {spreadsheet_id}")
                return

            # Get the current data
            range_name = RangeFormat.CURRENT_PERIOD.value.format(sheet_name=sheet_name)
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values:
                log.warning(f"No data found in {sheet_name} tab")
                return

            # Get table headers
            headers = values[0]
            
            # Find indices of required columns
            specialist_idx = self._find_column_index(headers, ColumnName.SPECIALIST.value)
            role_idx = self._find_column_index(headers, ColumnName.SPECIALIST_ROLE.value)
            hours_worked_idx = self._find_column_index(headers, ColumnName.HOURS_WORKED.value)
            
            log.info(f"Headers: {headers}")
            log.info(f"Hours Worked column index: {hours_worked_idx}")
            
            if specialist_idx is None or role_idx is None:
                log.warning("Required columns not found in Current period tab")
                return

            # Find the last row before the total sum and check if specialist exists
            last_data_row = None
            total_row = None
            specialist_exists = False
            has_any_specialists = False
            
            for i, row in enumerate(values):
                # Check if this specialist already exists
                if i > 0 and len(row) > specialist_idx and row[specialist_idx] == specialist.name:
                    log.info(f"Specialist {specialist.name} already exists in row {i+1}")
                    specialist_exists = True
                    return  # Specialist already exists, do nothing
                
                # Check if there are any specialists
                if i > 0 and len(row) > specialist_idx and row[specialist_idx]:
                    has_any_specialists = True
                    last_data_row = i
                
                # If we find a total row (usually contains sums or "Total")
                if i > 0 and len(row) > specialist_idx:
                    # Check if this is a total row (usually has numeric values without specialist name)
                    if (not row[specialist_idx] or row[specialist_idx] == "0" or 
                        (len(row) > 2 and "$" in str(row[2]) and not row[0])):
                        total_row = i
                        break
            
            # If this is the first specialist in the document, use row 2
            if not has_any_specialists and len(values) > 1:
                insert_row = 1  # Row 2 in 0-based indexing is 1
                # No need to insert a new row, use existing
                need_to_insert_row = False
            else:
                # Determine where to insert the new specialist (if there are already specialists)
                if last_data_row is not None:
                    # Insert after last data row
                    insert_row = last_data_row + 1
                else:
                    # If no data, insert after header
                    insert_row = 1
                
                # If there is a total row, insert before it
                if total_row is not None and (insert_row is None or insert_row >= total_row):
                    insert_row = total_row
                
                need_to_insert_row = True
            
            # Get sheet ID for operations
            sheet_id = sheet.get("properties", {}).get("sheetId")
            
            # 1. Insert new row before total (if needed)
            if need_to_insert_row and total_row is not None:
                # Create insert row request
                request = {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": insert_row,
                            "endIndex": insert_row + 1
                        },
                        "inheritFromBefore": True
                    }
                }
                
                # Execute request
                self.google_sheets_service.batch_update(
                    spreadsheet_id=spreadsheet_id,
                    requests=[request]
                )
            
            # 2. Fill cells with specialist data
            update_data = [""] * len(headers)
            update_data[specialist_idx] = specialist.name
            update_data[role_idx] = specialist.role
            
            # Add working hours formula if column exists
            if hours_worked_idx is not None:
                try:
                    # Get calculation formula from config
                    working_hours_formula = config_service.get_formula(FormulaName.CALCULATE_WORKING_HOURS)
                    # Use formula directly without modifications
                    update_data[hours_worked_idx] = working_hours_formula
                    log.info(f"Set working hours formula for {specialist.name}: {working_hours_formula}")
                except Exception as e:
                    log.warning(f"Failed to set hours calculation formula: {str(e)}")
            
            # For General Expenses document
            rate_idx = self._find_column_index(headers, ColumnName.HOURLY_RATE_USD.value)
            total_cost_idx = self._find_column_index(headers, ColumnName.TOTAL_COST_USD.value)
            
            if rate_idx is not None:
                update_data[rate_idx] = str(specialist.external_rate)
                
            # Add Gross total cost formula if total cost column exists
            if total_cost_idx is not None:
                try:
                    gross_total_cost_formula = config_service.get_formula(FormulaName.GROSS_TOTAL_COST)
                    update_data[total_cost_idx] = gross_total_cost_formula
                    log.info(f"Set total cost formula for {specialist.name}: {gross_total_cost_formula}")
                except Exception as e:
                    log.warning(f"Failed to set total cost formula: {str(e)}")
            
            # Update data
            target_row = insert_row + 1  # 1-based indexing for range
            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_name}!A{target_row}:{self._column_letter(len(headers)-1)}{target_row}",
                values=[update_data],
                value_input_option="USER_ENTERED",
            )
            
            log.info(f"Added {specialist.name} to {sheet_name} tab in row {target_row}")

        except Exception as e:
            log.error(f"Error updating General Expenses Current Period tab: {str(e)}")
            raise Exception(f"Failed to update General Expenses Current Period tab: {str(e)}")
            
    def _update_payment_distribution_current_period_tab(
        self, spreadsheet_id: str, specialist: Specialist
    ) -> None:
        """Update the Current Period tab in Payment Distribution spreadsheet with the specialist.

        Args:
            spreadsheet_id: ID of the Payment Distribution spreadsheet
            specialist: Specialist object

        Raises:
            Exception: If update fails
        """
        try:
            # Check if sheets service is initialized
            if not self.google_sheets_service.sheets_service:
                raise Exception("Google Sheets service not initialized")

            # Find the sheet with the exact name from Google Sheet
            sheet_name = SheetName.CURRENT_PERIOD.value
            sheet = self.google_sheets_service.get_sheet_by_name(
                spreadsheet_id=spreadsheet_id, sheet_name=sheet_name
            )

            if not sheet:
                log.warning(f"{sheet_name} tab not found in {spreadsheet_id}")
                return

            # Get the current data
            range_name = RangeFormat.CURRENT_PERIOD.value.format(sheet_name=sheet_name)
            result = (
                self.google_sheets_service.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])
            if not values:
                log.warning(f"No data found in {sheet_name} tab")
                return

            # Get table headers
            headers = values[0]
            
            # Find indices of required columns
            specialist_idx = self._find_column_index(headers, ColumnName.SPECIALIST.value)
            role_idx = self._find_column_index(headers, ColumnName.SPECIALIST_ROLE.value)
            hours_worked_idx = self._find_column_index(headers, ColumnName.HOURS_WORKED.value)
            
            log.info(f"Headers: {headers}")
            log.info(f"Hours Worked column index: {hours_worked_idx}")
            
            if specialist_idx is None or role_idx is None:
                log.warning("Required columns not found in Current period tab")
                return

            # Find the last row before the total sum and check if specialist exists
            last_data_row = None
            total_row = None
            specialist_exists = False
            has_any_specialists = False
            
            for i, row in enumerate(values):
                # Check if this specialist already exists
                if i > 0 and len(row) > specialist_idx and row[specialist_idx] == specialist.name:
                    log.info(f"Specialist {specialist.name} already exists in row {i+1}")
                    specialist_exists = True
                    return  # Specialist already exists, do nothing
                
                # Check if there are any specialists
                if i > 0 and len(row) > specialist_idx and row[specialist_idx]:
                    has_any_specialists = True
                    last_data_row = i
                
                # If we find a total row (usually contains sums or "Total")
                if i > 0 and len(row) > specialist_idx:
                    # Check if this is a total row (usually has numeric values without specialist name)
                    if (not row[specialist_idx] or row[specialist_idx] == "0" or 
                        (len(row) > 2 and "$" in str(row[2]) and not row[0])):
                        total_row = i
                        break
            
            # If this is the first specialist in the document, use row 2
            if not has_any_specialists and len(values) > 1:
                insert_row = 1  # Row 2 in 0-based indexing is 1
                # No need to insert a new row, use existing
                need_to_insert_row = False
            else:
                # Determine where to insert the new specialist (if there are already specialists)
                if last_data_row is not None:
                    # Insert after last data row
                    insert_row = last_data_row + 1
                else:
                    # If no data, insert after header
                    insert_row = 1
                
                # If there is a total row, insert before it
                if total_row is not None and (insert_row is None or insert_row >= total_row):
                    insert_row = total_row
                
                need_to_insert_row = True
            
            # Get sheet ID for operations
            sheet_id = sheet.get("properties", {}).get("sheetId")
            
            # 1. Insert new row before total (if needed)
            if need_to_insert_row and total_row is not None:
                # Create insert row request
                request = {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": insert_row,
                            "endIndex": insert_row + 1
                        },
                        "inheritFromBefore": True
                    }
                }
                
                # Execute request
                self.google_sheets_service.batch_update(
                    spreadsheet_id=spreadsheet_id,
                    requests=[request]
                )
            
            # 2. Fill cells with specialist data
            update_data = [""] * len(headers)
            update_data[specialist_idx] = specialist.name
            update_data[role_idx] = specialist.role
            
            # Add working hours formula if column exists
            if hours_worked_idx is not None:
                try:
                    # Get calculation formula from config
                    working_hours_formula = config_service.get_formula(FormulaName.CALCULATE_WORKING_HOURS)
                    # Use formula directly without modifications
                    update_data[hours_worked_idx] = working_hours_formula
                    log.info(f"Set working hours formula for {specialist.name}: {working_hours_formula}")
                except Exception as e:
                    log.warning(f"Failed to set hours calculation formula: {str(e)}")
            
            # For Payment Distribution document
            client_rate_idx = self._find_column_index(headers, ColumnName.CLIENT_HOURLY_RATE_USD.value)
            specialist_rate_idx = self._find_column_index(headers, ColumnName.SPECIALIST_HOURLY_RATE_USD.value)
            
            if client_rate_idx is not None:
                update_data[client_rate_idx] = str(specialist.external_rate)
            
            if specialist_rate_idx is not None:
                update_data[specialist_rate_idx] = str(specialist.internal_rate)
            
            # Add formulas for cost and revenue calculations
            client_work_cost_idx = self._find_column_index(headers, ColumnName.CLIENT_WORK_COST_USD.value)
            specialist_work_cost_idx = self._find_column_index(headers, ColumnName.SPECIALIST_WORK_COST_USD.value)
            revenue_idx = self._find_column_index(headers, ColumnName.REVENUE_USD.value)
            
            try:
                # Get formulas from config using the generic get_formula method
                if client_work_cost_idx is not None:
                    try:
                        client_work_cost_formula = config_service.get_formula(FormulaName.GROSS_TOTAL_COST)
                        update_data[client_work_cost_idx] = client_work_cost_formula
                        log.info(f"Set client work cost formula for {specialist.name}: {client_work_cost_formula}")
                    except Exception as e:
                        log.warning(f"Failed to set client work cost formula: {str(e)}")
                
                if specialist_work_cost_idx is not None:
                    try:
                        specialist_work_cost_formula = config_service.get_formula(FormulaName.NET_TOTAL_COST)
                        update_data[specialist_work_cost_idx] = specialist_work_cost_formula
                        log.info(f"Set specialist work cost formula for {specialist.name}: {specialist_work_cost_formula}")
                    except Exception as e:
                        log.warning(f"Failed to set specialist work cost formula: {str(e)}")
                
                if revenue_idx is not None:
                    try:
                        revenue_formula = config_service.get_formula(FormulaName.REVENUE)
                        update_data[revenue_idx] = revenue_formula
                        log.info(f"Set revenue formula for {specialist.name}: {revenue_formula}")
                    except Exception as e:
                        log.warning(f"Failed to set revenue formula: {str(e)}")
            except Exception as e:
                log.warning(f"Failed to set one or more cost/revenue formulas: {str(e)}")
            
            # Update data
            target_row = insert_row + 1  # 1-based indexing for range
            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=f"{sheet_name}!A{target_row}:{self._column_letter(len(headers)-1)}{target_row}",
                values=[update_data],
                value_input_option="USER_ENTERED",
            )
            
            log.info(f"Added {specialist.name} to {sheet_name} tab in row {target_row}")

        except Exception as e:
            log.error(f"Error updating Payment Distribution Current Period tab: {str(e)}")
            raise Exception(f"Failed to update Payment Distribution Current Period tab: {str(e)}")
            
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
            log.error(f"Error getting spreadsheet sheets: {str(e)}")
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
            import_formula = config_service.get_import_specialist_timesheet_formula(
                specialist_timesheet_id=specialist.timesheet
            )

            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )

            log.info(f"Created tab for {specialist.name} in report spreadsheet")

        except Exception as e:
            log.error(f"Error creating specialist tab in report: {str(e)}")
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
            import_formula = config_service.get_import_specialist_timesheet_formula(
                specialist_timesheet_id=specialist.timesheet
            )

            self.google_sheets_service.update_range(
                spreadsheet_id=spreadsheet_id,
                range_name=RangeFormat.SINGLE_CELL.value.format(sheet_name=tab_name),
                values=[[import_formula]],
                value_input_option="USER_ENTERED",
            )

            log.info(f"Created tab for {specialist.name} in calculations spreadsheet")

        except Exception as e:
            log.error(f"Error creating specialist tab in calculations: {str(e)}")
            raise Exception(
                f"Failed to create specialist tab in calculations: {str(e)}"
            )
            
    def _find_column_index(self, headers: list, column_name: str) -> int:
        """Find the index of a column by its name.
        
        Args:
            headers: List of column headers
            column_name: Name of the column to find
            
        Returns:
            Index of the column or None if not found
        """
        for i, header in enumerate(headers):
            if header == column_name:
                return i
        return None
        
    def _copy_row_formatting(self, spreadsheet_id: str, sheet_name: str, source_row: int, target_row: int) -> None:
        """Copy row formatting and formulas from one row to another.
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            sheet_name: Name of the sheet
            source_row: Source row to copy from (1-based)
            target_row: Target row to copy to (1-based)
            
        Raises:
            Exception: If copying fails
        """
        try:
            # Get sheet ID for the requests
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
                        "endColumnIndex": 100  # Достаточно большое число для покрытия всех колонок
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": target_row - 1,
                        "endRowIndex": target_row,
                        "startColumnIndex": 0,
                        "endColumnIndex": 100  # Достаточно большое число для покрытия всех колонок
                    },
                    "pasteType": "PASTE_FORMULA",
                    "pasteOrientation": "NORMAL"
                }
            }
            
            # Execute the request
            self.google_sheets_service.batch_update(
                spreadsheet_id=spreadsheet_id,
                requests=[request]
            )
            
            log.info(f"Successfully copied formatting from row {source_row} to row {target_row}")
            
        except Exception as e:
            log.error(f"Error copying row formatting: {str(e)}")
            raise Exception(f"Failed to copy row formatting: {str(e)}")

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
