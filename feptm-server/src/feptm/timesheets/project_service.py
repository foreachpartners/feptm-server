"""Service for handling project timesheets and related operations."""

from collections import Counter
from datetime import UTC, datetime

from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.payment_period import ClosePeriodResponse
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.storage.protocols import (
    FormulaProviderProtocol,
    ProjectStorageProtocol,
    SpecialistStorageProtocol,
)


def _resolve_display_names(specialists: list[Specialist]) -> None:
    name_counts = Counter(sp.name for sp in specialists if sp.name)
    for sp in specialists:
        if name_counts.get(sp.name, 0) > 1 and sp.row_index is not None:
            sp.display_name = f"{sp.name} ({sp.row_index})"
        else:
            sp.display_name = sp.name


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

        specialists, _ = self._specialists.list_from_sheet(project_id)

        if not specialists:
            return [], 0, 0

        _resolve_display_names(specialists)

        new_count = 0
        for sp in specialists:
            if not sp.timesheet:
                self._specialists.create_timesheet(
                    sp, context, self._timesheet_template_id
                )
                new_count += 1

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

        active_names = {sp.display_name or sp.name for sp in specialists}
        if project.report_spreadsheet_id:
            self._projects.remove_stale_specialists(
                project.report_spreadsheet_id, active_names
            )
        if project.calculations_spreadsheet_id:
            self._projects.remove_stale_specialists(
                project.calculations_spreadsheet_id, active_names
            )

        log.info(
            "Synchronized %d specialists, created %d new timesheets",
            len(specialists),
            new_count,
        )
        return specialists, len(specialists), new_count

    def sync_project_rates(
        self, project_id: str
    ) -> tuple[list[Specialist], int]:
        specialists, _ = self._specialists.list_from_sheet(project_id)
        if not specialists:
            return [], 0

        project = self._projects.get_project_metadata(project_id)

        if not project.drive_folder_id:
            raise Exception(
                f"Cannot sync rates: drive folder ID not found for project '{project.name}'."
            )

        context = TimesheetContext(
            folder_id=project.drive_folder_id, project_name=project.name
        )

        specialists, _ = self._specialists.list_from_sheet(project_id)
        if not specialists:
            return [], 0

        _resolve_display_names(specialists)

        created_count = 0
        for sp in specialists:
            if not sp.timesheet:
                self._specialists.create_timesheet(
                    sp, context, self._timesheet_template_id
                )
                created_count += 1

        if created_count > 0:
            self._specialists.update_timesheet_ids(project_id, "Team", specialists)

        for sp in specialists:
            if not sp.timesheet:
                continue
            import_formula = self._formulas.get_import_timesheet_formula(
                sp.timesheet
            )
            if project.report_spreadsheet_id:
                self._projects.add_specialist_to_report(
                    project.report_spreadsheet_id, sp, import_formula
                )
                self._projects.sync_rates_to_current_period(
                    project.report_spreadsheet_id, sp
                )
            if project.calculations_spreadsheet_id:
                self._projects.add_specialist_to_report(
                    project.calculations_spreadsheet_id, sp, import_formula
                )
                self._projects.sync_rates_to_current_period(
                    project.calculations_spreadsheet_id, sp
                )

        active_names = {sp.display_name or sp.name for sp in specialists}
        if project.report_spreadsheet_id:
            self._projects.remove_stale_specialists(
                project.report_spreadsheet_id, active_names
            )
        if project.calculations_spreadsheet_id:
            self._projects.remove_stale_specialists(
                project.calculations_spreadsheet_id, active_names
            )

        updated_count = sum(1 for sp in specialists if sp.timesheet)
        log.info("Synced rates for %d specialists", updated_count)
        return specialists, updated_count

    def close_period(
        self,
        project_id: str,
        period_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> ClosePeriodResponse:
        project = self._projects.get_project_metadata(project_id)
        specialists, _ = self._specialists.list_from_sheet(project_id)

        _resolve_display_names(specialists)

        total_entries = 0
        specialists_processed = 0
        report_archived = False
        calculations_archived = False

        for sp in specialists:
            if not sp.timesheet:
                continue
            updated = self._projects.close_period_in_timesheet(
                sp.timesheet, period_name, start_date, end_date
            )
            specialists_processed += 1
            total_entries += updated

        if total_entries > 0:
            if project.report_spreadsheet_id:
                report_archived = self._projects.archive_current_period(
                    project.report_spreadsheet_id,
                    period_name,
                    specialists,
                    start_date,
                    end_date,
                )
                if report_archived:
                    self._projects.protect_archived_sheet(
                        project.report_spreadsheet_id,
                        period_name,
                        payment_status_col_idx=5,
                    )
            if project.calculations_spreadsheet_id:
                calculations_archived = self._projects.archive_current_period(
                    project.calculations_spreadsheet_id,
                    period_name,
                    specialists,
                    start_date,
                    end_date,
                )
                if calculations_archived:
                    self._projects.protect_archived_sheet(
                        project.calculations_spreadsheet_id,
                        period_name,
                        payment_status_col_idx=5,
                    )

        log.info(
            "Closed period %s: %d entries updated, %d specialists processed",
            period_name,
            total_entries,
            specialists_processed,
        )
        return ClosePeriodResponse(
            created=datetime.now(UTC),
            project_id=project_id,
            period_name=period_name,
            entries_updated=total_entries,
            specialists_processed=specialists_processed,
            report_archived=report_archived,
            calculations_archived=calculations_archived,
        )
