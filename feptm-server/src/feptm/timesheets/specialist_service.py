"""Service for working with specialists in Google Sheets."""

from feptm.core.log import log
from feptm.models.context import TimesheetContext
from feptm.models.specialist import Specialist
from feptm.storage.protocols import SpecialistStorageProtocol


class SpecialistService:
    """Facade for specialist synchronization across storage."""

    def __init__(
        self,
        specialist_storage: SpecialistStorageProtocol,
        timesheet_template_id: str = "",
    ) -> None:
        self._storage = specialist_storage
        self._timesheet_template_id = timesheet_template_id

    def sync_specialists(
        self,
        spreadsheet_id: str,
        context: TimesheetContext,
        sheet_name: str = "Team",
    ) -> tuple[list[Specialist], int]:
        specialists, existing_count = self._storage.list_from_sheet(
            spreadsheet_id, sheet_name
        )
        if not specialists:
            return [], 0

        new_specialists = [sp for sp in specialists if not sp.timesheet]
        for sp in new_specialists:
            self._storage.create_timesheet(sp, context, self._timesheet_template_id)

        new_count = len(new_specialists)
        if new_count > 0:
            self._storage.update_timesheet_ids(spreadsheet_id, sheet_name, specialists)

        log.info(
            "Synced %d specialists, created %d new timesheets",
            len(specialists),
            new_count,
        )
        return specialists, new_count
