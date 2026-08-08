"""Common test fixtures and configuration."""

import os
import sys
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.abspath("src"))

from feptm.api.router import router

# Create a test app that uses the router
test_app = FastAPI()
test_app.include_router(router, prefix="/api")


# Standard test data for Google Sheets API responses
SAMPLE_SPREADSHEET_METADATA = {
    "spreadsheetId": "test-spreadsheet-id-123",
    "properties": {"title": "Test Spreadsheet"},
    "sheets": [
        {
            "properties": {"title": "Sheet1", "sheetId": 0},
            "data": [{"rowData": []}]
        },
        {
            "properties": {"title": "Project info", "sheetId": 1},
            "data": [{"rowData": []}]
        }
    ]
}

SAMPLE_SHEETS_VALUES = [
    ["Name", "Hours", "Rate"],
    ["John Doe", "40", "100"],
    ["Jane Smith", "35", "120"]
]

SAMPLE_DRIVE_FILE = {
    "id": "test-file-id-456",
    "name": "Test File",
    "mimeType": "application/vnd.google-apps.spreadsheet",
    "parents": ["test-parent-folder-id"]
}

SAMPLE_DRIVE_FOLDER = {
    "id": "test-folder-id-789",
    "name": "Test Folder",
    "mimeType": "application/vnd.google-apps.folder"
}


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI application.
    
    Returns:
        TestClient: A FastAPI test client for async endpoint testing.
    """
    return TestClient(test_app)


@pytest.fixture
def mock_google_api_build():
    """Mock googleapiclient.discovery.build for comprehensive Google API testing.
    
    Returns:
        Dict containing mocked sheets and drive services.
    """
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_sheets = MagicMock()
        mock_drive = MagicMock()
        
        def build_side_effect(service: str, version: str, credentials: Any, **kwargs: Any) -> MagicMock:
            return mock_sheets if service == "sheets" else mock_drive
            
        mock_build.side_effect = build_side_effect
        
        yield {
            'sheets': mock_sheets,
            'drive': mock_drive,
            'build': mock_build
        }


@pytest.fixture
def mock_google_sheets_service():
    """Standard Google Sheets service mock for business logic testing.
    
    Returns:
        MagicMock: Configured GoogleSheetsService mock instance.
    """
    with patch('feptm.services.google_sheets_service.GoogleSheetsService') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Set up common return values
        mock_instance.is_initialized.return_value = True
        mock_instance.create_spreadsheet.return_value = {
            "spreadsheet_id": "new-spreadsheet-id",
            "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-spreadsheet-id"
        }
        mock_instance.create_drive_folder.return_value = {
            "folder_id": "new-folder-id",
            "folder_url": "https://drive.google.com/drive/folders/new-folder-id"
        }
        
        yield mock_instance


@pytest.fixture
def mock_google_credentials():
    """Mock Google OAuth credentials for authentication testing.
    
    Returns:
        MagicMock: Configured credentials mock.
    """
    with patch('google.oauth2.credentials.Credentials') as mock_creds_class:
        credentials = MagicMock()
        credentials.valid = True
        credentials.expired = False
        credentials.refresh_token = "test-refresh-token"
        
        mock_creds_class.from_authorized_user_info.return_value = credentials
        
        yield {
            'Credentials': mock_creds_class,
            'instance': credentials
        }


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing project creation workflows.
    
    Returns:
        Dict: Sample project with all required fields.
    """
    return {
        "name": "Test Project",
        "drive_folder_id": "test-folder-123",
        "project_info_spreadsheet_id": "test-info-456",
        "report_spreadsheet_id": "test-report-789",
        "calculations_spreadsheet_id": "test-calc-012"
    }


@pytest.fixture
def sample_specialist_data() -> List[Dict[str, Any]]:
    """Sample specialist data for testing specialist workflows.
    
    Returns:
        List: Sample specialists with required fields.
    """
    return [
        {
            "name": "John Doe",
            "rate": "100",
            "hours": "40",
            "timesheet_id": "timesheet-john-123"
        },
        {
            "name": "Jane Smith", 
            "rate": "120",
            "hours": "35",
            "timesheet_id": "timesheet-jane-456"
        }
    ]
