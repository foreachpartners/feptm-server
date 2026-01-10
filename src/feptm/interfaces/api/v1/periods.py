"""API v1 endpoints for payment periods."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from feptm.core.exceptions import GoogleApiError, NotFoundError, ValidationError

router = APIRouter(prefix="/periods", tags=["periods"])


class PeriodCloseRequest(BaseModel):
    """Request model for closing payment period."""

    project_id: str = Field(..., min_length=1, description="Project ID cannot be empty")
    name: str = Field(..., min_length=1, description="Period name cannot be empty")
    start_date: date = Field(..., description="Period start date")
    end_date: date = Field(..., description="Period end date")


@router.post("/close")
async def close_period(request: PeriodCloseRequest) -> dict:
    """Close payment period for project.

    FR-004: Period close operation (placeholder for future implementation).

    Args:
        request: Period close request

    Returns:
        Success response

    Raises:
        HTTPException: If operation fails
    """
    # Placeholder - PeriodRepository not yet implemented
    raise HTTPException(
        status_code=501, detail="Period close operation not yet implemented"
    )
