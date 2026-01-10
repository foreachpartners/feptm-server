"""Project repository implementation using Google Sheets via pygsheets."""

from feptm.adapters.google.auth import authorize_pygsheets
from feptm.adapters.google.drive_client import GoogleDriveClient
from feptm.adapters.sheets.client import PygSheetsClient
from feptm.adapters.sheets.constants import RowName, SheetName
from feptm.adapters.sheets.formula_templates import HYPERLINK
from feptm.adapters.sheets.mappers import project_to_row, row_to_project
from feptm.core.config import settings
from feptm.core.constants import DateFormat
from feptm.core.exceptions import GoogleApiError, NotFoundError, ValidationError
from feptm.core.log import log
from feptm.domain.models.project import Project
from feptm.domain.services.protocols import ProjectRepository


class SpreadsheetProjectRepository(ProjectRepository):
    """Project repository using Google Sheets via pygsheets.

    FR-001: Creates project structure with Project Info, Report, and Calculations spreadsheets.
    All Google IDs are stored in spreadsheets, not in domain models.
    """

    def __init__(
        self,
        client: PygSheetsClient,
        drive_client: GoogleDriveClient,
        project_info_template_id: str,
        report_template_id: str,
        calculations_template_id: str,
        projects_folder_id: str | None = None,
    ) -> None:
        """Initialize SpreadsheetProjectRepository.

        Args:
            client: PygSheetsClient for spreadsheet operations
            drive_client: GoogleDriveClient for folder operations
            project_info_template_id: Template ID for Project Info spreadsheet
            report_template_id: Template ID for General Expenses Report spreadsheet
            calculations_template_id: Template ID for Payment Distribution spreadsheet
            projects_folder_id: Parent folder ID for projects (optional)
        """
        self._client = client
        self._drive_client = drive_client
        self._project_info_template_id = project_info_template_id
        self._report_template_id = report_template_id
        self._calculations_template_id = calculations_template_id
        self._projects_folder_id = projects_folder_id

    def create(self, project: Project) -> str:
        """Create project from templates, return spreadsheet ID.

        FR-001: Creates folder, copies templates, fills Project Info sheet, links documents.

        Args:
            project: Project domain model

        Returns:
            Project Info spreadsheet ID (serves as project identifier)

        Raises:
            ValidationError: If template IDs not configured
            GoogleApiError: If creation fails
        """
        if not self._project_info_template_id:
            raise ValidationError("GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured")
        if not self._report_template_id:
            raise ValidationError("GOOGLE_PROJECT_REPORT_TEMPLATE_ID not configured")
        if not self._calculations_template_id:
            raise ValidationError("GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID not configured")

        try:
            log.info(f"Creating project: {project.name}")

            # FR-001.1: Create Google Drive folder
            project_folder_id = self._drive_client.create_folder(
                name=project.name, parent_id=self._projects_folder_id
            )
            folder_url = self._drive_client.get_folder_url(project_folder_id)
            log.info(f"Created project folder: {project_folder_id}")

            # FR-001.2-4: Create spreadsheets from templates
            project_info_spreadsheet = self._client.copy_spreadsheet(
                source_id=self._project_info_template_id,
                title=f"{project.name} - Project info",
                folder_id=project_folder_id,
            )
            project_info_id = project_info_spreadsheet.id
            project_info_url = f"https://docs.google.com/spreadsheets/d/{project_info_id}"

            report_spreadsheet = self._client.copy_spreadsheet(
                source_id=self._report_template_id,
                title=f"{project.name} - General Expenses",
                folder_id=project_folder_id,
            )
            report_id = report_spreadsheet.id
            report_url = f"https://docs.google.com/spreadsheets/d/{report_id}"

            calculations_spreadsheet = self._client.copy_spreadsheet(
                source_id=self._calculations_template_id,
                title=f"{project.name} - Payment Distribution",
                folder_id=project_folder_id,
            )
            calculations_id = calculations_spreadsheet.id
            calculations_url = (
                f"https://docs.google.com/spreadsheets/d/{calculations_id}"
            )

            # FR-001.5: Fill Project Info sheet with project data and links
            self._fill_project_info_sheet(
                spreadsheet=project_info_spreadsheet,
                project=project,
                project_id=project_info_id,
                folder_url=folder_url,
                report_url=report_url,
                calculations_url=calculations_url,
            )

            log.info(f"Created project: {project_info_id}")
            return project_info_id

        except Exception as e:
            log.error(f"Failed to create project: {e}")
            # Cleanup on failure
            try:
                if "project_folder_id" in locals():
                    self._drive_client.delete_file(project_folder_id)
            except Exception as cleanup_error:
                log.error(f"Failed to cleanup folder: {cleanup_error}")

            raise GoogleApiError(f"Failed to create project: {e}") from e

    def _fill_project_info_sheet(
        self,
        spreadsheet,
        project: Project,
        project_id: str,
        folder_url: str,
        report_url: str,
        calculations_url: str,
    ) -> None:
        """Fill Project Info sheet with project data and hyperlinks.

        Args:
            spreadsheet: pygsheets Spreadsheet object
            project: Project domain model
            project_id: Project Info spreadsheet ID
            folder_url: Drive folder URL
            report_url: Report spreadsheet URL
            calculations_url: Calculations spreadsheet URL
        """
        ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
        if not ws:
            raise ValidationError("Project Info sheet not found in template")

        # Fill project data using mappers
        row_data = project_to_row(project, project_id)

        # Add hyperlinks for folder and related spreadsheets
        # FR-001.5: Link all documents via HYPERLINK formulas
        row_data.append([RowName.PROJECT_FOLDER.value, HYPERLINK.render(url=folder_url)])
        row_data.append(
            [RowName.PAYMENT_DISTRIBUTION.value, HYPERLINK.render(url=calculations_url)]
        )
        row_data.append([RowName.GENERAL_EXPENSES.value, HYPERLINK.render(url=report_url)])

        # Update sheet starting from A1
        # pygsheets update_values accepts start cell and 2D array
        ws.update_values(crange="A1", values=row_data)

    def get_by_id(self, project_id: str) -> Project:
        """Load project from spreadsheet.

        Args:
            project_id: Project Info spreadsheet ID

        Returns:
            Project domain model

        Raises:
            NotFoundError: If project not found
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
            if not ws:
                raise NotFoundError(
                    f"Project Info sheet not found in spreadsheet {project_id}"
                )

            # Read data from A1 to B20 (assuming max 20 rows)
            data = ws.get_values("A1", "B20")
            if not data:
                raise NotFoundError(f"Project data not found in spreadsheet {project_id}")

            return row_to_project(data, project_id)

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to load project {project_id}: {e}")
            raise NotFoundError(f"Failed to load project: {e}") from e

    def save(self, project_id: str, project: Project) -> None:
        """Save project changes to spreadsheet.

        Args:
            project_id: Project Info spreadsheet ID
            project: Updated project domain model

        Raises:
            NotFoundError: If project not found
            GoogleApiError: If save operation fails
        """
        try:
            spreadsheet = self._client.open_spreadsheet(project_id)
            ws = spreadsheet.worksheet_by_title(SheetName.PROJECT_INFO.value)
            if not ws:
                raise NotFoundError(
                    f"Project Info sheet not found in spreadsheet {project_id}"
                )

            # Get existing data to preserve hyperlinks
            data = ws.get_values("A1", "B20")
            if not data:
                raise NotFoundError(f"Project data not found in spreadsheet {project_id}")

            # Update project fields (Name, Created, Modified)
            # Find and update Name field
            for i, row in enumerate(data, start=1):
                if len(row) >= 2 and str(row[0]).strip() == RowName.NAME.value:
                    ws.update_value(f"B{i}", project.name)
                    break

            # Update Modified timestamp
            modified_str = project.created.strftime(DateFormat.DISPLAY_DATETIME.value)
            for i, row in enumerate(data, start=1):
                if len(row) >= 2 and str(row[0]).strip() == RowName.MODIFIED.value:
                    ws.update_value(f"B{i}", modified_str)
                    break

            log.info(f"Saved project {project_id}")

        except NotFoundError:
            raise
        except Exception as e:
            log.error(f"Failed to save project {project_id}: {e}")
            raise GoogleApiError(f"Failed to save project: {e}") from e
