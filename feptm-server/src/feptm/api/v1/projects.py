"""API endpoints for projects."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from feptm.core.config import settings
from feptm.core.exceptions import (
    ProjectDuplicateNameError,
    ProjectFolderNotFoundError,
    ProjectSpreadsheetNotFoundError,
)
from feptm.dependencies import get_timesheet_project_service
from feptm.models import (
    ProjectCardResponse,
    ProjectCardTable,
    ProjectCardTimesheet,
    ProjectListItem,
    ProjectListResponse,
    ProjectMetaResponse,
    ProjectSyncRatesRequest,
    ProjectSyncRatesResponse,
    ProjectSyncRequest,
    ProjectSyncResponse,
)
from feptm.timesheets.config_service import UrlPattern
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
        folders = await asyncio.to_thread(
            service.list_projects, settings.GOOGLE_PROJECTS_FOLDER_ID
        )

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

        if settings.GOOGLE_PROJECTS_FOLDER_ID:
            existing_folders = await asyncio.to_thread(
                service.list_projects, settings.GOOGLE_PROJECTS_FOLDER_ID
            )
            requested_name_lower = request.project_name.strip().lower()
            for folder in existing_folders:
                if folder.get("name", "").strip().lower() == requested_name_lower:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Project with name '{request.project_name}' already exists.",
                    )

        result = await asyncio.to_thread(
            service.create_project,
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
        specialists, total, created = await asyncio.to_thread(
            service.sync_project_specialists, project_id=request.project_id
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
        specialists, updated = await asyncio.to_thread(
            service.sync_project_rates, project_id=request.project_id
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


# @req FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001
@router.get("/{drive_folder_id}/", response_model=ProjectCardResponse)
async def get_project_card(drive_folder_id: str) -> ProjectCardResponse:
    try:
        service: TimesheetProjectService = get_timesheet_project_service()
        card_data = await asyncio.to_thread(
            service.get_project_card, drive_folder_id
        )

        tables = {
            "project_info": ProjectCardTable(
                label="Project info / Team",
                spreadsheet_id=card_data["info_spreadsheet_id"],
                url=UrlPattern.SPREADSHEET.format(
                    spreadsheet_id=card_data["info_spreadsheet_id"]
                ),
            ),
            "general_expenses": ProjectCardTable(
                label="General Expenses",
                spreadsheet_id=card_data["report_spreadsheet_id"],
                url=UrlPattern.SPREADSHEET.format(
                    spreadsheet_id=card_data["report_spreadsheet_id"]
                ),
            ),
            "payment_distribution": ProjectCardTable(
                label="Payment Distribution",
                spreadsheet_id=card_data["calculations_spreadsheet_id"],
                url=UrlPattern.SPREADSHEET.format(
                    spreadsheet_id=card_data["calculations_spreadsheet_id"]
                ),
            ),
        }

        timesheets = [
            ProjectCardTimesheet(
                name=ts["name"],
                spreadsheet_id=ts["id"],
                url=UrlPattern.SPREADSHEET.format(spreadsheet_id=ts["id"]),
            )
            for ts in card_data["timesheets"]
        ]

        return ProjectCardResponse(
            name=card_data["name"],
            drive_folder_id=card_data["drive_folder_id"],
            project_id=card_data["project_id"],
            tables=tables,
            timesheets=timesheets,
        )
    except ProjectFolderNotFoundError:
        raise HTTPException(
            status_code=404, detail="Project folder not found."
        )
    except ProjectSpreadsheetNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Project spreadsheet not found: {e.expected_name}.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load project card: {e}"
        )
