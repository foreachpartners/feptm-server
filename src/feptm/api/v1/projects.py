"""API endpoints for projects."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from feptm.core.config import settings
from feptm.models import (
    Project,
    ProjectMetaResponse,
    ProjectSyncRequest,
    ProjectSyncResponse,
    Specialist,
)
from feptm.services.google_sheets_service import google_sheets_service
from feptm.timesheets.project_service import TimesheetProjectService

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""

    project_name: str = Field(..., min_length=1, description="Project name cannot be empty")


@router.post("/create", response_model=ProjectMetaResponse)
async def create_project(request: ProjectCreateRequest) -> ProjectMetaResponse:
    """Create a new project in Google Drive.

    This endpoint creates:
    1. A folder in Google Drive with the project name
    2. A Google Sheet with project info based on the template
    3. A report file linked to the project info
    4. A calculations sheet for the project

    Args:
        request: Project creation request containing project name

    Returns:
        Project creation response with IDs and URLs

    Raises:
        HTTPException: If creation fails
    """
    try:
        # Validate configuration
        if not settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured. Please set this value in the environment variables.",
            )

        if not settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_PROJECT_REPORT_TEMPLATE_ID not configured. Please set this value in the environment variables.",
            )

        if not settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID not configured. Please set this value in the environment variables.",
            )

        # Create minimal Project with just the name
        project = Project(name=request.project_name)

        # Initialize timesheet project service with the Google Sheets service
        timesheet_service = TimesheetProjectService(google_sheets_service)

        # Create project in Google Drive
        result = timesheet_service.create_project(project)

        # Return the response
        return ProjectMetaResponse(
            created=project.created,
            modified=project.modified,
            drive_folder_id=result.get("drive_folder_id", ""),
            drive_folder_url=result.get("drive_folder_url", ""),
            project_info_spreadsheet_id=result.get("project_info_spreadsheet_id", ""),
            project_info_spreadsheet_url=result.get("project_info_spreadsheet_url", ""),
            report_spreadsheet_id=result.get("report_spreadsheet_id", ""),
            report_spreadsheet_url=result.get("report_spreadsheet_url", ""),
            calculations_spreadsheet_id=result.get("calculations_spreadsheet_id", ""),
            calculations_spreadsheet_url=result.get("calculations_spreadsheet_url", ""),
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.post("/sync", response_model=ProjectSyncResponse)
async def sync_project_specialists(request: ProjectSyncRequest) -> ProjectSyncResponse:
    """Synchronize specialists for a project.

    This endpoint:
    1. Analyzes the project's spreadsheet for specialists information
    2. Creates timesheets for specialists who don't have them
    3. Links the timesheets to project reports and calculations

    Args:
        request: Project sync request containing project ID

    Returns:
        Project sync response with specialists info

    Raises:
        HTTPException: If synchronization fails
    """
    try:
        # Validate configuration
        if not settings.GOOGLE_TIMESHEET_TEMPLATE_ID:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_TIMESHEET_TEMPLATE_ID not configured. Please set this value in the environment variables.",
            )

        # Initialize timesheet project service
        timesheet_service = TimesheetProjectService(google_sheets_service)

        # Sync project specialists
        specialists, total_count, created_count = (
            timesheet_service.sync_project_specialists(project_id=request.project_id)
        )

        # Return the response
        return ProjectSyncResponse(
            project_id=request.project_id,
            specialists_found=total_count,
            specialists_created=created_count,
            specialists=specialists,
        )
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to sync project specialists: {str(e)}"
        )
