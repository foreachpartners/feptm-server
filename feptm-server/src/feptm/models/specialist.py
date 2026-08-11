"""Specialist model definitions."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Specialist(BaseModel):
    """Specialist model representing a team member on a project."""

    name: str
    role: str
    project: str | None = None
    internal_rate: Decimal = Decimal(0)
    external_rate: Decimal = Decimal(0)
    date: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    timesheet: str | None = None
    row_index: int | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "John Doe",
            "role": "Developer",
            "project": "E-Commerce Platform",
            "internal_rate": "20.00",
            "external_rate": "25.00",
            "date": "2023-02-15T12:00:00Z",
            "timesheet": "1abCdEfGhIjKlMnOpQrStUvWxYz",
        },
    })
