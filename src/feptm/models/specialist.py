"""Specialist model definitions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class Specialist(BaseModel):
    """Specialist model representing a team member on a project."""

    name: str
    role: str
    project: Optional[str] = None
    internal_rate: Decimal = Decimal("0")
    external_rate: Decimal = Decimal("0")  # Ставка для клиента
    date: Optional[datetime] = Field(default_factory=datetime.utcnow)
    timesheet: Optional[str] = None

    @computed_field
    def timesheet_url(self) -> Optional[str]:
        """Get the timesheet URL."""
        if not self.timesheet:
            return None
        return f"https://docs.google.com/spreadsheets/d/{self.timesheet}"

    @computed_field
    def has_timesheet(self) -> bool:
        """Check if specialist has a timesheet."""
        return self.timesheet is not None

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "role": "Developer",
                "project": "E-Commerce Platform",
                "internal_rate": "20.00",
                "external_rate": "25.00",
                "date": "2023-02-15T12:00:00Z",
                "timesheet": "1abCdEfGhIjKlMnOpQrStUvWxYz",
            }
        }
