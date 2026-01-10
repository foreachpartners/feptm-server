"""FastAPI dependency injection setup."""

from functools import lru_cache
from typing import TYPE_CHECKING

import pygsheets

from feptm.adapters.google.auth import authorize_pygsheets
from feptm.adapters.google.drive_client import GoogleDriveClient
from feptm.adapters.sheets.client import PygSheetsClient
from feptm.adapters.sheets.project_repository import SpreadsheetProjectRepository
from feptm.adapters.sheets.specialist_repository import SpreadsheetSpecialistRepository
from feptm.core.config import settings
from feptm.core.exceptions import GoogleApiError, ValidationError
from feptm.core.log import log
from feptm.domain.services.period_service import PeriodService
from feptm.domain.services.project_service import ProjectService
from feptm.domain.services.protocols import (
    PeriodRepository,
    ProjectRepository,
    SpecialistRepository,
)
from feptm.domain.services.specialist_service import SpecialistService

if TYPE_CHECKING:
    from pygsheets.client import Client


@lru_cache()
def get_pygsheets_client() -> "Client":
    """Get authorized pygsheets client (cached).

    Returns:
        Authorized pygsheets client

    Raises:
        GoogleApiError: If authorization fails
    """
    if not settings.GOOGLE_CREDENTIALS_FILE:
        raise ValidationError("GOOGLE_CREDENTIALS_FILE not configured")

    try:
        gc = authorize_pygsheets(
            credentials_file=settings.GOOGLE_CREDENTIALS_FILE,
            token_file=settings.GOOGLE_TOKEN_FILE,
        )
        log.info("Initialized pygsheets client")
        return gc
    except Exception as e:
        log.error(f"Failed to initialize pygsheets client: {e}")
        raise GoogleApiError(f"Failed to initialize pygsheets client: {e}") from e


@lru_cache()
def get_pygsheets_client_wrapper() -> PygSheetsClient:
    """Get PygSheetsClient wrapper (cached).

    Returns:
        PygSheetsClient instance
    """
    credentials_file = (
        str(settings.GOOGLE_CREDENTIALS_FILE)
        if settings.GOOGLE_CREDENTIALS_FILE
        else None
    )
    return PygSheetsClient(credentials_file=credentials_file)


def get_drive_client() -> GoogleDriveClient:
    """Get GoogleDriveClient.

    Returns:
        GoogleDriveClient instance
    """
    gc = get_pygsheets_client()
    return GoogleDriveClient(gc)


def get_project_repository() -> ProjectRepository:
    """Get ProjectRepository implementation.

    Returns:
        SpreadsheetProjectRepository instance

    Raises:
        ValidationError: If template IDs not configured
    """
    if not settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID:
        raise ValidationError("GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured")
    if not settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID:
        raise ValidationError("GOOGLE_PROJECT_REPORT_TEMPLATE_ID not configured")
    if not settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID:
        raise ValidationError("GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID not configured")

    client = get_pygsheets_client_wrapper()
    drive_client = get_drive_client()

    return SpreadsheetProjectRepository(
        client=client,
        drive_client=drive_client,
        project_info_template_id=settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID,
        report_template_id=settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID,
        calculations_template_id=settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID,
        projects_folder_id=settings.GOOGLE_PROJECTS_FOLDER_ID,
    )


def get_specialist_repository() -> SpecialistRepository:
    """Get SpecialistRepository implementation.

    Returns:
        SpreadsheetSpecialistRepository instance

    Raises:
        ValidationError: If timesheet template ID not configured
    """
    if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
        raise ValidationError("GOOGLE_TIMESHEET_TEMPLATE_ID not configured")

    client = get_pygsheets_client_wrapper()

    return SpreadsheetSpecialistRepository(
        client=client,
        timesheet_template_id=settings.GOOGLE_TIMESHEET_TEMPLATE_ID,
    )


def get_project_service() -> ProjectService:
    """Get ProjectService.

    Returns:
        ProjectService instance with injected repository
    """
    repository = get_project_repository()
    return ProjectService(repository=repository)


def get_specialist_service() -> SpecialistService:
    """Get SpecialistService.

    Returns:
        SpecialistService instance with injected repository
    """
    repository = get_specialist_repository()
    return SpecialistService(repository=repository)


# PeriodRepository not yet implemented - placeholder for future
def get_period_service() -> PeriodService:
    """Get PeriodService.

    Returns:
        PeriodService instance

    Raises:
        NotImplementedError: PeriodRepository not yet implemented
    """
    raise NotImplementedError("PeriodRepository not yet implemented")
