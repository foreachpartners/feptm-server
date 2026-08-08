"""Tests for project API endpoints."""

from typing import Dict, Any
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from fastapi import status

from feptm.models.project import Project
from feptm.models.specialist import Specialist


# Test data for API endpoints - stored in same file as tests
VALID_PROJECT_CREATE_REQUEST = {
    "project_name": "Test Project API"
}

INVALID_PROJECT_CREATE_REQUEST = {
    "project_name": ""  # Empty name
}

VALID_PROJECT_SYNC_REQUEST = {
    "project_id": "test-project-spreadsheet-id-123"
}

INVALID_PROJECT_SYNC_REQUEST = {
    "project_id": ""  # Empty project ID
}

MOCK_PROJECT_CREATION_RESULT = {
    "drive_folder_id": "test-folder-api-123",
    "drive_folder_url": "https://drive.google.com/drive/folders/test-folder-api-123",
    "project_info_spreadsheet_id": "test-info-api-456",
    "project_info_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-info-api-456",
    "report_spreadsheet_id": "test-report-api-789",
    "report_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-report-api-789",
    "calculations_spreadsheet_id": "test-calc-api-012",
    "calculations_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-calc-api-012"
}

MOCK_SYNC_SPECIALISTS_RESULT = [
    Specialist(
        name="John Doe API",
        role="Lead Developer",
        project="Test Project API",
        internal_rate=100.0,
        external_rate=120.0,
        date=datetime(2024, 1, 15),
        timesheet="timesheet-john-api-123"
    ),
    Specialist(
        name="Jane Smith API",
        role="Senior Designer", 
        project="Test Project API",
        internal_rate=90.0,
        external_rate=110.0,
        date=datetime(2024, 1, 20),
        timesheet="timesheet-jane-api-456"
    )
]

API_ERROR_RESPONSES = {
    "missing_template_id": {
        "detail": "GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured. Please set this value in the environment variables."
    },
    "service_not_initialized": {
        "detail": "Failed to create project: Google services are not initialized. Please check your credentials and scopes."
    },
    "invalid_project_name": {
        "detail": "validation error for ProjectCreateRequest"
    }
}


@pytest.fixture
def mock_settings():
    """Mock settings for API tests."""
    with patch('feptm.api.v1.projects.settings') as mock_settings:
        # Configure valid settings by default
        mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "test-info-template-123"
        mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "test-report-template-456"
        mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "test-calc-template-789"
        mock_settings.GOOGLE_TIMESHEET_TEMPLATE_ID = "test-timesheet-template-012"
        yield mock_settings


@pytest.fixture
def mock_timesheet_project_service():
    """Mock TimesheetProjectService for API tests."""
    with patch('feptm.api.v1.projects.TimesheetProjectService') as mock_service_class:
        mock_service_instance = MagicMock()
        mock_service_class.return_value = mock_service_instance
        
        # Set up default successful responses
        mock_service_instance.create_project.return_value = MOCK_PROJECT_CREATION_RESULT
        mock_service_instance.sync_project_specialists.return_value = (
            MOCK_SYNC_SPECIALISTS_RESULT,
            2,  # total_count
            2   # created_count
        )
        
        yield mock_service_instance


@pytest.fixture  
def mock_google_sheets_service_instance():
    """Mock google_sheets_service instance for API tests."""
    with patch('feptm.api.v1.projects.google_sheets_service') as mock_service:
        mock_service.is_initialized.return_value = True
        yield mock_service


# Async API endpoint tests (using asyncio_mode = "auto" from pyproject.toml)

async def test_create_project_success(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test successful project creation via API endpoint."""
    # Arrange - using test data from same file
    request_data = VALID_PROJECT_CREATE_REQUEST
    
    # Act
    response = client.post("/api/projects/create", json=request_data)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    # Verify response structure matches expected data
    assert response_data["drive_folder_id"] == MOCK_PROJECT_CREATION_RESULT["drive_folder_id"]
    assert response_data["project_info_spreadsheet_id"] == MOCK_PROJECT_CREATION_RESULT["project_info_spreadsheet_id"]
    assert response_data["report_spreadsheet_id"] == MOCK_PROJECT_CREATION_RESULT["report_spreadsheet_id"]
    assert response_data["calculations_spreadsheet_id"] == MOCK_PROJECT_CREATION_RESULT["calculations_spreadsheet_id"]
    assert "created" in response_data
    assert "modified" in response_data
    
    # Verify service was called correctly
    mock_timesheet_project_service.create_project.assert_called_once()
    call_args = mock_timesheet_project_service.create_project.call_args[0]
    project_arg = call_args[0]
    assert isinstance(project_arg, Project)
    assert project_arg.name == request_data["project_name"]


async def test_create_project_missing_template_config(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test project creation failure when template ID is not configured."""
    # Arrange - simulate missing template configuration
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = None
    
    # Act
    response = client.post("/api/projects/create", json=VALID_PROJECT_CREATE_REQUEST)
    
    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured" in response_data["detail"]
    
    # Verify service was not called
    mock_timesheet_project_service.create_project.assert_not_called()


async def test_create_project_service_not_initialized(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test project creation failure when Google services are not initialized."""
    # Arrange - simulate service not initialized
    mock_google_sheets_service_instance.is_initialized.return_value = False
    mock_timesheet_project_service.create_project.side_effect = Exception(
        "Google services are not initialized. Please check your credentials and scopes."
    )
    
    # Act
    response = client.post("/api/projects/create", json=VALID_PROJECT_CREATE_REQUEST)
    
    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "Failed to create project" in response_data["detail"]
    assert "Google services are not initialized" in response_data["detail"]


async def test_create_project_invalid_request_data(client: TestClient):
    """Test project creation with invalid request data."""
    # Arrange - using invalid test data
    invalid_requests = [
        {},  # Missing project_name
        {"project_name": ""},  # Empty project_name
        {"wrong_field": "value"}  # Wrong field name
    ]
    
    for invalid_request in invalid_requests:
        # Act
        response = client.post("/api/projects/create", json=invalid_request)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_sync_project_specialists_success(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test successful project specialists synchronization."""
    # Arrange
    request_data = VALID_PROJECT_SYNC_REQUEST
    
    # Act
    response = client.post("/api/projects/sync", json=request_data)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    # Verify response structure
    assert response_data["project_id"] == request_data["project_id"]
    assert response_data["specialists_found"] == 2
    assert response_data["specialists_created"] == 2
    assert len(response_data["specialists"]) == 2
    
    # Verify specialist data
    first_specialist = response_data["specialists"][0]
    assert first_specialist["name"] == MOCK_SYNC_SPECIALISTS_RESULT[0].name
    assert first_specialist["timesheet"] == MOCK_SYNC_SPECIALISTS_RESULT[0].timesheet
    
    # Verify service was called correctly
    mock_timesheet_project_service.sync_project_specialists.assert_called_once_with(
        project_id=request_data["project_id"]
    )


async def test_sync_project_specialists_missing_template_config(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test specialist sync failure when timesheet template is not configured."""
    # Arrange
    mock_settings.GOOGLE_TIMESHEET_TEMPLATE_ID = None
    
    # Act
    response = client.post("/api/projects/sync", json=VALID_PROJECT_SYNC_REQUEST)
    
    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "GOOGLE_TIMESHEET_TEMPLATE_ID not configured" in response_data["detail"]
    
    # Verify service was not called
    mock_timesheet_project_service.sync_project_specialists.assert_not_called()


async def test_sync_project_specialists_service_error(
    client: TestClient,
    mock_settings,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance
):
    """Test specialist sync failure when service raises exception."""
    # Arrange
    mock_timesheet_project_service.sync_project_specialists.side_effect = Exception(
        "Failed to extract project metadata"
    )
    
    # Act
    response = client.post("/api/projects/sync", json=VALID_PROJECT_SYNC_REQUEST)
    
    # Assert
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "Failed to sync project specialists" in response_data["detail"]
    assert "Failed to extract project metadata" in response_data["detail"]


async def test_sync_project_specialists_invalid_request_data(client: TestClient):
    """Test specialist sync with invalid request data."""
    # Arrange - using invalid test data
    invalid_requests = [
        {},  # Missing project_id
        {"project_id": ""},  # Empty project_id
        {"wrong_field": "value"}  # Wrong field name
    ]
    
    for invalid_request in invalid_requests:
        # Act
        response = client.post("/api/projects/sync", json=invalid_request)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("missing_setting,expected_message", [
    ("GOOGLE_PROJECT_INFO_TEMPLATE_ID", "GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured"),
    ("GOOGLE_PROJECT_REPORT_TEMPLATE_ID", "GOOGLE_PROJECT_REPORT_TEMPLATE_ID not configured"),
    ("GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID", "GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID not configured"),
])
async def test_create_project_missing_various_settings(
    client: TestClient,
    mock_timesheet_project_service,
    mock_google_sheets_service_instance,
    missing_setting: str,
    expected_message: str
):
    """Test project creation with various missing settings."""
    # Arrange - mock settings with one missing
    with patch('feptm.api.v1.projects.settings') as mock_settings:
        # Set all settings to valid values first
        mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "valid-id"
        mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "valid-id"
        mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "valid-id"
        
        # Set the specific one to None
        setattr(mock_settings, missing_setting, None)
        
        # Act
        response = client.post("/api/projects/create", json=VALID_PROJECT_CREATE_REQUEST)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert expected_message in response_data["detail"] 