"""API endpoints for payment periods."""

from fastapi import APIRouter, HTTPException

from feptm.dependencies import get_timesheet_project_service
from feptm.models.payment_period import ClosePeriodRequest, ClosePeriodResponse
from feptm.timesheets.project_service import TimesheetProjectService

router = APIRouter()


# @req FR-PAYMENT-001
@router.put("", response_model=ClosePeriodResponse)
async def close_payment_period(request: ClosePeriodRequest) -> ClosePeriodResponse:
    try:
        service: TimesheetProjectService = get_timesheet_project_service()
        return service.close_period(
            project_id=request.project_id,
            period_name=request.period_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to close payment period: {e}"
        )
