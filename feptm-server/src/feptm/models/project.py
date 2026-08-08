"""Project model definitions."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from feptm.models.specialist import Specialist


class Project(BaseModel):
    """Project model representing a client project."""

    name: str = Field(..., min_length=1, description="Project name cannot be empty")
    drive_folder_id: str | None = None
    project_info_spreadsheet_id: str | None = None
    report_spreadsheet_id: str | None = None
    calculations_spreadsheet_id: str | None = None
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modified: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "E-Commerce Platform",
            "drive_folder_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
            "project_info_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
            "report_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
            "calculations_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
            "created": "2023-02-15T12:00:00Z",
            "modified": "2023-06-20T15:30:00Z",
        },
    })


class ProjectMetaResponse(BaseModel):
    """Response model for project metadata creation."""

    created: datetime
    modified: datetime
    drive_folder_id: str | None = None
    drive_folder_url: str | None = None
    project_info_spreadsheet_id: str | None = None
    project_info_spreadsheet_url: str | None = None
    report_spreadsheet_id: str | None = None
    report_spreadsheet_url: str | None = None
    calculations_spreadsheet_id: str | None = None
    calculations_spreadsheet_url: str | None = None


class ProjectSyncRequest(BaseModel):
    """Request model for syncing project specialists."""

    project_id: str = Field(..., min_length=1, description="Project ID cannot be empty")


class ProjectSyncResponse(BaseModel):
    """Response model for project specialist sync operation."""

    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project_id: str
    specialists_found: int
    specialists_created: int
    specialists: list[Specialist]
