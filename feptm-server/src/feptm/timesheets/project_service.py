"""Service for handling project timesheets and related operations."""

from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.storage.protocols import (
    FormulaProviderProtocol,
    ProjectStorageProtocol,
    SpecialistStorageProtocol,
)


class TimesheetProjectService:
    """Facade orchestrating project creation and specialist sync across storage."""

    def __init__(
        self,
        project_storage: ProjectStorageProtocol,
        specialist_storage: SpecialistStorageProtocol,
        formula_provider: FormulaProviderProtocol,
        timesheet_template_id: str = "",
    ) -> None:
        self._projects = project_storage
        self._specialists = specialist_storage
        self._formulas = formula_provider
        self._timesheet_template_id = timesheet_template_id

    def create_project(
        self,
        project_name: str,
        template_ids: dict[str, str],
        parent_folder_id: str | None = None,
    ) -> dict[str, str]:
        result = self._projects.create_project(
            project_name, template_ids, parent_folder_id
        )

        project = Project(name=project_name)
        project.drive_folder_id = result["drive_folder_id"]
        project.project_info_spreadsheet_id = result.get("info_spreadsheet_id", "")
        project.report_spreadsheet_id = result.get("report_spreadsheet_id", "")
        project.calculations_spreadsheet_id = result.get(
            "calculations_spreadsheet_id", ""
        )

        self._projects.update_project_info_sheet(
            project.project_info_spreadsheet_id, project
        )
        return result  # AR-ARCH-001:allow — facade return type preserved for API compat

    def sync_project_specialists(
        self, project_id: str
    ) -> tuple[list[Specialist], int, int]:
        project = self._projects.get_project_metadata(project_id)

        if not project.drive_folder_id:
            raise Exception(
                f"Cannot create timesheets: drive folder ID not found for project '{project.name}'."
            )

        context = TimesheetContext(
            folder_id=project.drive_folder_id, project_name=project.name
        )

        specialists, new_count = self._specialists.list_from_sheet(project_id)

        if not specialists:
            return [], 0, 0

        for sp in specialists:
            if not sp.timesheet:
                self._specialists.create_timesheet(
                    sp, context, self._timesheet_template_id
                )

        if new_count > 0:
            self._specialists.update_timesheet_ids(project_id, "Team", specialists)

        for sp in specialists:
            if not sp.timesheet:
                continue
            import_formula = self._formulas.get_import_timesheet_formula(sp.timesheet)
            if project.report_spreadsheet_id:
                self._projects.add_specialist_to_report(
                    project.report_spreadsheet_id, sp, import_formula
                )
                self._projects.update_current_period(
                    project.report_spreadsheet_id, sp, self._formulas
                )
            if project.calculations_spreadsheet_id:
                self._projects.add_specialist_to_report(
                    project.calculations_spreadsheet_id, sp, import_formula
                )
                self._projects.update_current_period(
                    project.calculations_spreadsheet_id, sp, self._formulas
                )

        log.info(
            "Synchronized %d specialists, created %d new timesheets",
            len(specialists),
            new_count,
        )
        return specialists, len(specialists), new_count
