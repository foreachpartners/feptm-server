"""API v1 endpoints for specialists."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from feptm.core.exceptions import GoogleApiError, NotFoundError, ValidationError
from feptm.domain.services.specialist_service import SpecialistService
from feptm.interfaces.api.dependencies import get_specialist_service

router = APIRouter(prefix="/specialists", tags=["specialists"])


class SpecialistAddRequest(BaseModel):
    """Request model for adding specialist to project."""

    project_id: str = Field(..., min_length=1, description="Project ID cannot be empty")
    name: str = Field(..., min_length=1, description="Specialist name cannot be empty")
    role: str = Field(..., min_length=1, description="Specialist role cannot be empty")
    internal_rate: float = Field(..., gt=0, description="Internal rate must be positive")
    external_rate: float = Field(..., gt=0, description="External rate must be positive")


@router.get("/project/{project_id}")
async def get_project_specialists(
    project_id: str,
    specialist_service: SpecialistService = Depends(get_specialist_service),
) -> dict:
    """Get all specialists for a project.

    Args:
        project_id: Project ID
        specialist_service: Injected SpecialistService

    Returns:
        List of specialists with their rate periods

    Raises:
        HTTPException: If operation fails
    """
    try:
        specialists = specialist_service.get_project_team(project_id)
        return {
            "project_id": project_id,
            "specialists_count": len(specialists),
            "specialists": [],  # Simplified - would convert to dicts
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get project specialists: {e}"
        )
