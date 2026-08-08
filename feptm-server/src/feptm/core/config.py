"""Configuration settings for the application."""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Project info
    PROJECT_NAME: str = "Time & Materials Accounting API"
    PROJECT_DESCRIPTION: str = (
        "Backend service for time and materials accounting with Google Sheets"
    )
    VERSION: str = "0.1.0"

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

    # API settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    API_KEY: str | None = None

    # Google API settings
    GOOGLE_CREDENTIALS_FILE: Path | None = (
        Path(__file__).resolve().parent.parent.parent.parent / "credentials.json"
        if (
            Path(__file__).resolve().parent.parent.parent.parent / "credentials.json"
        ).exists()
        else None
    )
    GOOGLE_TOKEN_FILE: Path | None = (
        Path(os.environ.get("HOME", os.path.expanduser("~")))
        / ".google_sheets_token.json"
    )

    GOOGLE_TIMESHEET_TEMPLATE_ID: str | None = None
    GOOGLE_REPORT_TEMPLATE_ID: str | None = None

    # Config sheet ID for formulas
    GOOGLE_CONFIG_SHEET_ID: str | None = None

    # Google Drive settings for projects
    # Important: make sure all these files are accessible to the user
    # authenticated via OAuth (enable "Share by link" access)
    GOOGLE_PROJECTS_FOLDER_ID: str | None = (
        None  # Specify the Google Drive folder ID here
    )

    # Google Sheets templates - specify your identifiers here or update environment variables
    # To make templates accessible, "Share by link" must be enabled for them (Share > General Access)
    GOOGLE_PROJECT_INFO_TEMPLATE_ID: str | None = None
    GOOGLE_PROJECT_REPORT_TEMPLATE_ID: str | None = None
    GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID: str | None = None

    # Model configurations
    SPECIALIST_ROLES: list[str] = Field(
        default=["Developer", "QA", "Designer", "Project Manager", "DevOps"]
    )

    @model_validator(mode='before')
    def expand_all_paths(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Process all Path fields, expanding tildes and converting to Path type."""
        for field_name, field_value in values.items():
            if isinstance(field_value, str) and "~" in field_value:
                # If it's a string with a tilde - expand the path
                values[field_name] = os.path.expanduser(field_value)
        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


# Load settings
settings = Settings()
