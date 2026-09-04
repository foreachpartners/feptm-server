"""Service for handling project timesheets and related operations."""

import time
from datetime import UTC, datetime

from feptm.core.log import log
from feptm.core import utils
from feptm.core.exceptions import PeriodAlreadyClosedError
from feptm.models.context import TimesheetContext
from feptm.models.payment_period import ClosePeriodResponse
from feptm.models.project import Project
from feptm.models.specialist import Specialist
from feptm.storage.protocols import (
    FormulaProviderProtocol,
    ProjectStorageProtocol,
    SpecialistStorageProtocol,
)


def _has_duplicate_names(specialists: list[Specialist]) -> bool:
    name_rows: dict[str, list[int]] = {}
    for sp in specialists:
        if not sp.name:
            continue
        ri = sp.row_index or 0
        if sp.name not in name_rows:
            name_rows[sp.name] = []
        name_rows[sp.name].append(ri)

    dups = {n: rows for n, rows in name_rows.items() if len(rows) > 1}
    if dups:
        dup_detail = ", ".join(
            f"'{name}' (rows: {', '.join(str(r) for r in rows)})"
            for name, rows in dups.items()
        )
        log.error(
            "Duplicate specialist names found in Team sheet: %s. "
            "Aborting sync — rename the duplicates in the Team sheet to resolve.",
            dup_detail,
        )
        return True
    return False


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

    def list_projects(self, parent_folder_id: str) -> list[dict[str, str]]:
        result = self._projects.list_projects(parent_folder_id)
        return sorted(result, key=lambda x: x["name"].lower())

    def get_project_card(self, folder_id: str) -> dict:
        return self._projects.get_project_card(folder_id)

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

        for sp in specialists:
            sp.project = project.name

        if not specialists:
            return [], 0, 0

        if _has_duplicate_names(specialists):
            return [], 0, 0

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
            time.sleep(0.25)  # AR-ARCH-005:allow

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

        for sp in specialists:
            sp.project = project.name

        if not specialists:
            return [], 0

        if _has_duplicate_names(specialists):
            return [], 0

        valid_specialists: list[Specialist] = []
        for sp in specialists:
            if sp.internal_rate is None or sp.external_rate is None or sp.internal_rate < 0 or sp.external_rate < 0:
                if sp.internal_rate is None:
                    log.error(
                        "Invalid rate for specialist '%s': internal_rate='<empty>' "
                        "is not a valid number. Previous rate retained.",
                        sp.name,
                    )
                elif sp.internal_rate < 0:
                    log.error(
                        "Invalid rate for specialist '%s': internal_rate='%s' "
                        "is not a valid rate (must be non-negative). Previous rate retained.",
                        sp.name, sp.internal_rate,
                    )
                if sp.external_rate is None:
                    log.error(
                        "Invalid rate for specialist '%s': external_rate='<empty>' "
                        "is not a valid number. Previous rate retained.",
                        sp.name,
                    )
                elif sp.external_rate < 0:
                    log.error(
                        "Invalid rate for specialist '%s': external_rate='%s' "
                        "is not a valid rate (must be non-negative). Previous rate retained.",
                        sp.name, sp.external_rate,
                    )
                continue
            valid_specialists.append(sp)

        created_count = 0
        for sp in valid_specialists:
            if not sp.timesheet:
                self._specialists.create_timesheet(
                    sp, context, self._timesheet_template_id
                )
                created_count += 1

        if created_count > 0:
            self._specialists.update_timesheet_ids(project_id, "Team", valid_specialists)

        for sp in valid_specialists:
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

        updated_count = sum(1 for sp in valid_specialists if sp.timesheet)
        log.info("Synced rates for %d specialists", updated_count)
        return specialists, updated_count

    def close_period(
        self,
        project_id: str,
        period_name: str,
    ) -> ClosePeriodResponse:
        project = self._projects.get_project_metadata(project_id)
        specialists, _ = self._specialists.list_from_sheet(project_id)

        if _has_duplicate_names(specialists):
            return ClosePeriodResponse(
                created=datetime.now(UTC),
                project_id=project_id,
                period_name=period_name,
                entries_updated=0,
                specialists_processed=0,
                report_archived=False,
                calculations_archived=False,
            )

        if project.report_spreadsheet_id and self._projects.is_period_closed(
            project.report_spreadsheet_id, period_name
        ):
            raise PeriodAlreadyClosedError(period_name)
        if project.calculations_spreadsheet_id and self._projects.is_period_closed(
            project.calculations_spreadsheet_id, period_name
        ):
            raise PeriodAlreadyClosedError(period_name)

        total_entries = 0
        specialists_processed = 0
        report_archived = False
        calculations_archived = False

        # Step 1: Archive Current Period FIRST (before timesheet updates)
        # This captures hours before IMPORTRANGE formulas recalculate to 0
        if project.report_spreadsheet_id:
            report_archived = self._projects.archive_current_period(
                project.report_spreadsheet_id,
                period_name,
            )
        if project.calculations_spreadsheet_id:
            calculations_archived = self._projects.archive_current_period(
                project.calculations_spreadsheet_id,
                period_name,
            )

        # Step 2: Update timesheet Payment Periods
        for sp in specialists:
            if not sp.timesheet:
                continue
            ts_id = utils.extract_id_from_hyperlink_formula(sp.timesheet) or sp.timesheet
            updated = self._projects.close_period_in_timesheet(
                ts_id, period_name
            )
            specialists_processed += 1
            total_entries += updated

        active_names = {sp.name for sp in specialists}
        stale_specialists: list[Specialist] = []
        if project.calculations_spreadsheet_id:
            stale_specialists = self._projects.get_stale_specialists(
                project.calculations_spreadsheet_id, active_names
            )
            for sp in stale_specialists:
                sp.project = project.name
                if not sp.timesheet:
                    continue
                ts_id = utils.extract_id_from_hyperlink_formula(sp.timesheet) or sp.timesheet
                updated = self._projects.close_period_in_timesheet(
                    ts_id, period_name
                )
                specialists_processed += 1
                total_entries += updated

        # Step 3: If no entries were updated, delete the archived tabs
        if total_entries == 0:
            if report_archived and project.report_spreadsheet_id:
                self._projects.delete_sheet(project.report_spreadsheet_id, period_name)
                report_archived = False
            if calculations_archived and project.calculations_spreadsheet_id:
                self._projects.delete_sheet(project.calculations_spreadsheet_id, period_name)
                calculations_archived = False
        else:
            if report_archived and project.report_spreadsheet_id:
                self._projects.protect_archived_sheet(
                    project.report_spreadsheet_id,
                    period_name,
                    payment_status_col_idx=5,
                )
            if calculations_archived and project.calculations_spreadsheet_id:
                self._projects.protect_archived_sheet(
                    project.calculations_spreadsheet_id,
                    period_name,
                    payment_status_col_idx=5,
                )
            if project.report_spreadsheet_id:
                removed = self._projects.remove_stale_specialists(
                    project.report_spreadsheet_id, active_names
                )
                log.info("Removed %d stale specialists from report Current Period", removed)
            if project.calculations_spreadsheet_id:
                removed = self._projects.remove_stale_specialists(
                    project.calculations_spreadsheet_id, active_names
                )
                log.info("Removed %d stale specialists from calculations Current Period", removed)

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
