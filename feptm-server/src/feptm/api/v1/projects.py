"""API endpoints for projects."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from feptm.core.config import settings
from feptm.dependencies import get_timesheet_project_service
from feptm.models import (
    ProjectListItem,
    ProjectListResponse,
    ProjectMetaResponse,
    ProjectSyncRatesRequest,
    ProjectSyncRatesResponse,
    ProjectSyncRequest,
    ProjectSyncResponse,
)
from feptm.timesheets.project_service import TimesheetProjectService

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    project_name: str = Field(
        ..., min_length=1, description="Project name cannot be empty"
    )


# @req FR-PROJECT-001
@router.get("/", response_model=ProjectListResponse)
async def list_projects() -> ProjectListResponse:
    try:
        if not settings.GOOGLE_PROJECTS_FOLDER_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_PROJECTS_FOLDER_ID not configured.",
            )

        service: TimesheetProjectService = get_timesheet_project_service()
        folders = service.list_projects(settings.GOOGLE_PROJECTS_FOLDER_ID)

        return ProjectListResponse(
            projects=[
                ProjectListItem(name=f["name"], drive_folder_id=f["id"])
                for f in folders
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load the project list: {e}"
        )


@router.post("/create", response_model=ProjectMetaResponse)
async def create_project(request: ProjectCreateRequest) -> ProjectMetaResponse:
    try:
        info_id = settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID
        report_id = settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID
        calc_id = settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID

        missing = []
        if not info_id:
            missing.append("GOOGLE_PROJECT_INFO_TEMPLATE_ID")
        if not report_id:
            missing.append("GOOGLE_PROJECT_REPORT_TEMPLATE_ID")
        if not calc_id:
            missing.append("GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID")
        if missing:
            raise HTTPException(
                status_code=500,
                detail=f"Missing configuration: {', '.join(missing)}",
            )

        service: TimesheetProjectService = get_timesheet_project_service()

        result = service.create_project(
            project_name=request.project_name,
            template_ids={
                "info": info_id or "",
                "report": report_id or "",
                "calculations": calc_id or "",
            },
            parent_folder_id=settings.GOOGLE_PROJECTS_FOLDER_ID,
        )

        from feptm.timesheets.config_service import UrlPattern

        return ProjectMetaResponse(
            created=datetime.now(UTC),
            modified=datetime.now(UTC),
            drive_folder_id=result.get("drive_folder_id", ""),
            drive_folder_url=UrlPattern.DRIVE_FOLDER.format(
                folder_id=result.get("drive_folder_id", "")
            )
            if result.get("drive_folder_id")
            else None,
            project_info_spreadsheet_id=result.get("info_spreadsheet_id", ""),
            project_info_spreadsheet_url=UrlPattern.SPREADSHEET.format(
                spreadsheet_id=result.get("info_spreadsheet_id", "")
            )
            if result.get("info_spreadsheet_id")
            else None,
            report_spreadsheet_id=result.get("report_spreadsheet_id", ""),
            report_spreadsheet_url=UrlPattern.SPREADSHEET.format(
                spreadsheet_id=result.get("report_spreadsheet_id", "")
            )
            if result.get("report_spreadsheet_id")
            else None,
            calculations_spreadsheet_id=result.get("calculations_spreadsheet_id", ""),
            calculations_spreadsheet_url=UrlPattern.SPREADSHEET.format(
                spreadsheet_id=result.get("calculations_spreadsheet_id", "")
            )
            if result.get("calculations_spreadsheet_id")
            else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")


# @req FR-SYNC-001, FR-SPECIALIST-001
@router.post("/sync", response_model=ProjectSyncResponse)
async def sync_project_specialists(request: ProjectSyncRequest) -> ProjectSyncResponse:
    try:
        if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_TIMESHEET_TEMPLATE_ID not configured.",
            )

        service: TimesheetProjectService = get_timesheet_project_service()
        specialists, total, created = service.sync_project_specialists(
            project_id=request.project_id
        )

        return ProjectSyncResponse(
            project_id=request.project_id,
            specialists_found=total,
            specialists_created=created,
            specialists=specialists,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to sync project specialists: {e}"
        )


# @req FR-SYNC-RATES-001, FR-SYNC-001
@router.post("/sync-rates", response_model=ProjectSyncRatesResponse)
async def sync_project_rates(
    request: ProjectSyncRatesRequest,
) -> ProjectSyncRatesResponse:
    try:
        service: TimesheetProjectService = get_timesheet_project_service()
        specialists, updated = service.sync_project_rates(
            project_id=request.project_id
        )

        return ProjectSyncRatesResponse(
            project_id=request.project_id,
            specialists_updated=updated,
            specialists=specialists,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to sync specialist rates: {e}"
        )
