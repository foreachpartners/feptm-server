"""Composition root — wires all dependencies."""

from feptm.core.config import settings
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.storage.config_storage import ConfigStorage
from feptm.storage.project_storage import ProjectStorage
from feptm.storage.specialist_storage import SpecialistStorage
from feptm.timesheets.project_service import TimesheetProjectService

_google_sheets_service: GoogleSheetsService | None = None


def get_google_sheets_service() -> GoogleSheetsService:
    global _google_sheets_service
    if _google_sheets_service is None:
        _google_sheets_service = GoogleSheetsService()
    return _google_sheets_service


def get_config_storage(
    sheets: GoogleSheetsService | None = None,
) -> ConfigStorage:
    if sheets is None:
        sheets = get_google_sheets_service()
    config_sheet_id = settings.GOOGLE_CONFIG_SHEET_ID or ""
    return ConfigStorage(sheets, config_sheet_id)


def get_project_storage(
    sheets: GoogleSheetsService | None = None,
) -> ProjectStorage:
    if sheets is None:
        sheets = get_google_sheets_service()
    return ProjectStorage(sheets)


def get_specialist_storage(
    sheets: GoogleSheetsService | None = None,
) -> SpecialistStorage:
    if sheets is None:
        sheets = get_google_sheets_service()
    return SpecialistStorage(sheets)


def get_timesheet_project_service() -> TimesheetProjectService:
    sheets = get_google_sheets_service()
    return TimesheetProjectService(
        project_storage=get_project_storage(sheets),
        specialist_storage=get_specialist_storage(sheets),
        formula_provider=get_config_storage(sheets),
        timesheet_template_id=settings.GOOGLE_TIMESHEET_TEMPLATE_ID or "",
    )
