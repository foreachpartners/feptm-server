"""Configuration settings for the application."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import Field, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Project info
    PROJECT_NAME: str = "FEPTM API"
    PROJECT_DESCRIPTION: str = "Time & Materials accounting with Google Sheets"
    VERSION: str = "0.1.0"

    # Base directory (project root)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Google credentials
    GOOGLE_CREDENTIALS_FILE: Optional[Union[str, Path]] = None
    GOOGLE_TOKEN_FILE: Optional[Path] = (
        Path(os.environ.get("HOME", os.path.expanduser("~")))
        / ".google_sheets_token.json"
    )

    # Google Drive folder for projects
    GOOGLE_PROJECTS_FOLDER_ID: Optional[str] = None

    # Google Sheets template IDs
    GOOGLE_PROJECT_INFO_TEMPLATE_ID: Optional[str] = None
    GOOGLE_PROJECT_REPORT_TEMPLATE_ID: Optional[str] = None
    GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID: Optional[str] = None
    GOOGLE_TIMESHEET_TEMPLATE_ID: Optional[str] = None

    # Specialist roles
    SPECIALIST_ROLES: list[str] = Field(
        default=["Developer", "QA", "Designer", "Project Manager", "DevOps"]
    )

    @root_validator(pre=True)
    def expand_all_paths(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Expand ~ in paths and set default credentials path."""
        base_dir = Path(__file__).resolve().parent.parent.parent.parent

        for field_name, field_value in values.items():
            if isinstance(field_value, str) and "~" in field_value:
                values[field_name] = os.path.expanduser(field_value)

        # Default: credentials.json in project root
        if not values.get("GOOGLE_CREDENTIALS_FILE"):
            values["GOOGLE_CREDENTIALS_FILE"] = base_dir / "credentials.json"
        else:
            creds_path = Path(values["GOOGLE_CREDENTIALS_FILE"])
            if not creds_path.is_absolute():
                creds_path = base_dir / creds_path
            values["GOOGLE_CREDENTIALS_FILE"] = creds_path

        return values

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
