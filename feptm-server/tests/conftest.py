"""Common test fixtures and configuration."""

import os
import sys
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("src"))

from feptm.api.router import router

test_app = FastAPI()
test_app.include_router(router, prefix="/api")


SAMPLE_SPREADSHEET_METADATA = {
    "spreadsheetId": "test-spreadsheet-id-123",
    "properties": {"title": "Test Spreadsheet"},
    "sheets": [
        {
            "properties": {"title": "Sheet1", "sheetId": 0},
            "data": [{"rowData": []}],
        },
        {
            "properties": {"title": "Project info", "sheetId": 1},
            "data": [{"rowData": []}],
        },
    ],
}

SAMPLE_SHEETS_VALUES = [
    ["Name", "Hours", "Rate"],
    ["John Doe", "40", "100"],
    ["Jane Smith", "35", "120"],
]

SAMPLE_DRIVE_FILE = {
    "id": "test-file-id-456",
    "name": "Test File",
    "mimeType": "application/vnd.google-apps.spreadsheet",
    "parents": ["test-parent-folder-id"],
}

SAMPLE_DRIVE_FOLDER = {
    "id": "test-folder-id-789",
    "name": "Test Folder",
    "mimeType": "application/vnd.google-apps.folder",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def mock_google_api_build():
    with patch("googleapiclient.discovery.build") as mock_build:
        mock_sheets = MagicMock()
        mock_drive = MagicMock()

        def build_side_effect(
            service: str, version: str, credentials: Any, **kwargs: Any
        ) -> MagicMock:
            return mock_sheets if service == "sheets" else mock_drive

        mock_build.side_effect = build_side_effect

        yield {"sheets": mock_sheets, "drive": mock_drive, "build": mock_build}


@pytest.fixture
def mock_google_sheets_service():
    with patch(
        "feptm.services.google_sheets_service.GoogleSheetsService"
    ) as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        mock_instance.is_initialized.return_value = True
        mock_instance.create_spreadsheet.return_value = {
            "spreadsheet_id": "new-spreadsheet-id",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-spreadsheet-id",
        }
        mock_instance.create_drive_folder.return_value = {
            "folder_id": "new-folder-id",
            "folder_url": "https://drive.google.com/drive/folders/new-folder-id",
        }
        
        # Mock _get_services to return mock services
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        mock_instance._get_services.return_value = (mock_drive, mock_sheets)
        mock_instance.sheets_service = mock_sheets
        mock_instance.drive_service = mock_drive

        yield mock_instance


@pytest.fixture
def mock_project_storage():
    return MagicMock()


@pytest.fixture
def mock_specialist_storage():
    return MagicMock()


@pytest.fixture
def mock_config_storage():
    mock = MagicMock()
    mock.get_formula.return_value = "=MOCK_FORMULA()"
    mock.get_import_timesheet_formula.return_value = (
        "=IMPORTRANGE(\"test-id\";\"Sheet1!A:Z\")"
    )
    return mock


@pytest.fixture
def mock_google_credentials():
    with patch("google.oauth2.credentials.Credentials") as mock_creds_class:
        credentials = MagicMock()
        credentials.valid = True
        credentials.expired = False
        credentials.refresh_token = "test-refresh-token"

        mock_creds_class.from_authorized_user_info.return_value = credentials

        yield {"Credentials": mock_creds_class, "instance": credentials}


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    return {
        "name": "Test Project",
        "drive_folder_id": "test-folder-123",
        "project_info_spreadsheet_id": "test-info-456",
        "report_spreadsheet_id": "test-report-789",
        "calculations_spreadsheet_id": "test-calc-012",
    }


@pytest.fixture
def sample_specialist_data() -> List[Dict[str, Any]]:
    return [
        {
            "name": "John Doe",
            "rate": "100",
            "hours": "40",
            "timesheet_id": "timesheet-john-123",
        },
        {
            "name": "Jane Smith",
            "rate": "120",
            "hours": "35",
            "timesheet_id": "timesheet-jane-456",
        },
    ]
