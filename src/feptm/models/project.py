"""Project model definitions."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field

from feptm.models.specialist import Specialist


class Project(BaseModel):
    """Project model representing a client project."""

    name: str
    drive_folder_id: Optional[str] = None
    project_info_spreadsheet_id: Optional[str] = None
    report_spreadsheet_id: Optional[str] = None
    calculations_spreadsheet_id: Optional[str] = None
    created: datetime = Field(default_factory=datetime.utcnow)
    modified: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    def drive_folder_url(self) -> Optional[str]:
        """Get the Google Drive folder URL."""
        if not self.drive_folder_id:
            return None
        return f"https://drive.google.com/drive/folders/{self.drive_folder_id}"

    @computed_field
    def project_info_spreadsheet_url(self) -> Optional[str]:
        """Get the project info spreadsheet URL."""
        if not self.project_info_spreadsheet_id:
            return None
        return (
            f"https://docs.google.com/spreadsheets/d/{self.project_info_spreadsheet_id}"
        )

    @computed_field
    def report_spreadsheet_url(self) -> Optional[str]:
        """Get the report spreadsheet URL."""
        if not self.report_spreadsheet_id:
            return None
        return f"https://docs.google.com/spreadsheets/d/{self.report_spreadsheet_id}"

    @computed_field
    def calculations_spreadsheet_url(self) -> Optional[str]:
        """Get the calculations spreadsheet URL."""
        if not self.calculations_spreadsheet_id:
            return None
        return (
            f"https://docs.google.com/spreadsheets/d/{self.calculations_spreadsheet_id}"
        )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "name": "E-Commerce Platform",
                "drive_folder_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
                "project_info_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
                "report_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
                "calculations_spreadsheet_id": "1abCdEfGhIjKlMnOpQrStUvWxYz",
                "created": "2023-02-15T12:00:00Z",
                "modified": "2023-06-20T15:30:00Z",
            }
        }


class ProjectMetaResponse(BaseModel):
    """Response model for project metadata creation."""

    created: datetime
    modified: datetime
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    project_info_spreadsheet_id: Optional[str] = None
    project_info_spreadsheet_url: Optional[str] = None
    report_spreadsheet_id: Optional[str] = None
    report_spreadsheet_url: Optional[str] = None
    calculations_spreadsheet_id: Optional[str] = None
    calculations_spreadsheet_url: Optional[str] = None


class ProjectSyncRequest(BaseModel):
    """Request model for syncing project specialists."""

    project_id: str


class ProjectSyncResponse(BaseModel):
    """Response model for project specialist sync operation."""

    created: datetime = Field(default_factory=datetime.utcnow)
    project_id: str
    specialists_found: int
    specialists_created: int
    specialists: List[Specialist]
