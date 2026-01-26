"""API v1 endpoints for projects."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from feptm.core.exceptions import GoogleApiError, NotFoundError, ValidationError
from feptm.domain.models.project import Project
from feptm.domain.models.specialist import Specialist
from feptm.domain.services.project_service import ProjectService
from feptm.domain.services.specialist_service import SpecialistService
from feptm.interfaces.api.dependencies import (
    get_project_service,
    get_specialist_service,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""

    project_name: str = Field(
        ..., min_length=1, description="Project name cannot be empty"
    )


class ProjectResponse(BaseModel):
    """Response model for project operations."""

    project_id: str
    name: str
    created: datetime


class ProjectSyncRequest(BaseModel):
    """Request model for syncing project specialists."""

    project_id: str = Field(
        ..., min_length=1, description="Project ID cannot be empty"
    )


class ProjectSyncResponse(BaseModel):
    """Response model for project specialist sync operation."""

    project_id: str
    specialists_found: int
    specialists_created: int
    specialists: List[dict]  # Simplified for now


@router.post("/create", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Create a new project.

    FR-001: Creates project structure with Project Info, Report, and Calculations spreadsheets.

    Args:
        request: Project creation request
        project_service: Injected ProjectService

    Returns:
        ProjectResponse with project ID and metadata

    Raises:
        HTTPException: If creation fails
    """
    try:
        project_id, project = project_service.create_project(request.project_name)
        return ProjectResponse(
            project_id=project_id,
            name=project.name,
            created=project.created,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GoogleApiError as e:
        raise HTTPException(status_code=500, detail=f"Google API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")


@router.post("/sync", response_model=ProjectSyncResponse)
async def sync_project_specialists(
    request: ProjectSyncRequest,
    project_service: ProjectService = Depends(get_project_service),
    specialist_service: SpecialistService = Depends(get_specialist_service),
) -> ProjectSyncResponse:
    """Synchronize specialists for a project.

    FR-002: Detects new specialists (without Timesheet ID), creates timesheets,
    updates Team sheet with Timesheet ID, creates report tabs.

    Args:
        request: Project sync request
        project_service: Injected ProjectService
        specialist_service: Injected SpecialistService

    Returns:
        ProjectSyncResponse with specialists info

    Raises:
        HTTPException: If synchronization fails
    """
    try:
        # Verify project exists
        project = project_service.get_project(request.project_id)

        # Sync specialists: find new ones, create timesheets, update reports
        created_specialists = specialist_service.sync_project_specialists(
            request.project_id
        )

        # Get updated list of all specialists
        all_specialists = specialist_service.get_project_team(request.project_id)

        return ProjectSyncResponse(
            project_id=request.project_id,
            specialists_found=len(all_specialists),
            specialists_created=len(created_specialists),
            specialists=[
                {"name": s.name, "role": s.role, "rates_count": len(s.rates)}
                for s in created_specialists
            ],
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GoogleApiError as e:
        raise HTTPException(status_code=500, detail=f"Google API error: {e}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to sync project specialists: {e}"
        )
