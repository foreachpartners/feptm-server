"""Tests for project API endpoints."""

from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from feptm.models.project import Project, ProjectMetaResponse


@patch("feptm.api.v1.projects.TimesheetProjectService")
@patch("feptm.api.v1.projects.settings")
def test_create_project_success(mock_settings, mock_timesheet_service, client):
    """Test successful project creation."""
    # Setup mock settings
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-template-id"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Setup mock timesheet service
    mock_service_instance = MagicMock()
    mock_timesheet_service.return_value = mock_service_instance
    
    # Setup mock response data
    now = datetime.now(UTC)
    mock_response = {
        "drive_folder_id": "mocked-folder-id",
        "drive_folder_url": "https://drive.google.com/drive/folders/mocked-folder-id",
        "project_info_spreadsheet_id": "mocked-info-sheet-id",
        "project_info_spreadsheet_url": "https://docs.google.com/spreadsheets/d/mocked-info-sheet-id",
        "report_spreadsheet_id": "mocked-report-id",
        "report_spreadsheet_url": "https://docs.google.com/spreadsheets/d/mocked-report-id",
        "calculations_spreadsheet_id": "mocked-calc-id",
        "calculations_spreadsheet_url": "https://docs.google.com/spreadsheets/d/mocked-calc-id"
    }
    mock_service_instance.create_project.return_value = mock_response
    
    # Prepare request data
    request_data = {
        "project_name": "Test API Project"
    }
    
    # Call API
    response = client.post("/api/projects/create", json=request_data)
    
    # Assert response
    assert response.status_code == 200
    
    # Verify returned data
    response_data = response.json()
    assert response_data["drive_folder_id"] == "mocked-folder-id"
    assert response_data["drive_folder_url"] == "https://drive.google.com/drive/folders/mocked-folder-id"
    assert response_data["project_info_spreadsheet_id"] == "mocked-info-sheet-id"
    assert response_data["project_info_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/mocked-info-sheet-id"
    assert response_data["report_spreadsheet_id"] == "mocked-report-id"
    assert response_data["report_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/mocked-report-id"
    assert response_data["calculations_spreadsheet_id"] == "mocked-calc-id"
    assert response_data["calculations_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/mocked-calc-id"
    
    # Verify service was called correctly
    mock_service_instance.create_project.assert_called_once()
    project_arg = mock_service_instance.create_project.call_args[0][0]
    assert isinstance(project_arg, Project)
    assert project_arg.name == "Test API Project"


@patch("feptm.api.v1.projects.TimesheetProjectService")
@patch("feptm.api.v1.projects.settings")
def test_create_project_missing_template_id(mock_settings, mock_timesheet_service, client):
    """Test project creation fails when template ID is missing."""
    # Setup missing template ID
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = None
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Setup mock service
    mock_service_instance = MagicMock()
    mock_timesheet_service.return_value = mock_service_instance
    
    # Prepare request data
    request_data = {
        "project_name": "Test Missing Template Project"
    }
    
    # Call API
    response = client.post("/api/projects/create", json=request_data)
    
    # Assert response
    assert response.status_code == 500
    assert "GOOGLE_PROJECT_INFO_TEMPLATE_ID not configured" in response.json()["detail"]
    
    # Verify service was not called
    mock_service_instance.create_project.assert_not_called()


@patch("feptm.api.v1.projects.TimesheetProjectService")
@patch("feptm.api.v1.projects.settings")
def test_create_project_service_error(mock_settings, mock_timesheet_service, client):
    """Test project creation fails when service throws an error."""
    # Setup mock settings
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-template-id"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Setup mock service to raise an exception
    mock_service_instance = MagicMock()
    mock_timesheet_service.return_value = mock_service_instance
    mock_service_instance.create_project.side_effect = Exception("Service error")
    
    # Prepare request data
    request_data = {
        "project_name": "Test Service Error Project"
    }
    
    # Call API
    response = client.post("/api/projects/create", json=request_data)
    
    # Assert response
    assert response.status_code == 500
    assert "Failed to create project: Service error" in response.json()["detail"]
    
    # Verify service was called
    mock_service_instance.create_project.assert_called_once()
    project_arg = mock_service_instance.create_project.call_args[0][0]
    assert isinstance(project_arg, Project)
    assert project_arg.name == "Test Service Error Project" 