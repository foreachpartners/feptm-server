"""Payment period models for closing and archiving reports."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ClosePeriodRequest(BaseModel):
    project_id: str = Field(..., min_length=1, description="Project ID cannot be empty")
    period_name: str = Field(..., min_length=1, description="Period name cannot be empty")


class ClosePeriodResponse(BaseModel):
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_id: str
    period_name: str
    entries_updated: int
    specialists_processed: int
    report_archived: bool
    calculations_archived: bool
