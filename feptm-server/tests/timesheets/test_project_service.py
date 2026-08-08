"""Tests for TimesheetProjectService."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from feptm.models.project import Project
from feptm.timesheets.project_service import TimesheetProjectService
from feptm.services.google_sheets_service import GoogleSheetsService
from feptm.core.config import settings


@pytest.fixture
def mock_google_sheets_service():
    """Create a mock GoogleSheetsService.
    
    Returns:
        MagicMock: A mock of GoogleSheetsService with predefined behaviors.
    """
    mock_service = MagicMock(spec=GoogleSheetsService)
    mock_service.is_initialized.return_value = True
    return mock_service


@pytest.fixture
def mock_timesheet_project_service(mock_google_sheets_service):
    """Create a mock TimesheetProjectService.
    
    Args:
        mock_google_sheets_service: Mock Google Sheets service
        
    Returns:
        TimesheetProjectService: A TimesheetProjectService with mocked GoogleSheetsService.
    """
    return TimesheetProjectService(mock_google_sheets_service)


def test_update_project_info_sheet(mock_google_sheets_service):
    """Test updating project info sheet."""
    # Setup test data
    spreadsheet_id = "test-spreadsheet-id"
    project = Project(
        name="Test Project",
        drive_folder_id="test-folder-id",
        project_info_spreadsheet_id="test-info-id",
        report_spreadsheet_id="test-report-id",
        calculations_spreadsheet_id="test-calc-id"
    )
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method
    service.update_project_info_sheet(spreadsheet_id, project)
    
    # Verify Google Sheets service was called
    mock_google_sheets_service.update_sheet_data.assert_called_once()
    
    # Verify call arguments
    call_args = mock_google_sheets_service.update_sheet_data.call_args[1]
    assert call_args["spreadsheet_id"] == spreadsheet_id
    assert call_args["sheet_name"] == "Project info"
    
    # Verify data content (at least the known fields)
    data = call_args["data"]
    assert len(data) > 0
    assert data[0] == ["Project Information", ""]
    assert data[1] == ["Field", "Value"]
    assert data[2] == ["Project ID", project.project_info_spreadsheet_id]
    assert data[3] == ["Name", project.name]


def test_update_project_info_sheet_error(mock_google_sheets_service):
    """Test error handling when updating project info sheet."""
    # Setup mock to raise exception
    mock_google_sheets_service.update_sheet_data.side_effect = Exception("API Error")
    
    # Setup test data
    spreadsheet_id = "test-spreadsheet-id"
    project = Project(name="Test Project")
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method and expect exception
    with pytest.raises(Exception) as exc_info:
        service.update_project_info_sheet(spreadsheet_id, project)
    
    # Verify exception message
    assert "Failed to update project info sheet" in str(exc_info.value)

    # Verify update_project_info_sheet was called
    mock_google_sheets_service.update_sheet_data.assert_called_once()


def test_create_spreadsheet_from_template(mock_google_sheets_service):
    """Test creating spreadsheet from template."""
    # Setup mock response
    mock_response = {
        "spreadsheet_id": "new-spreadsheet-id",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-spreadsheet-id"
    }
    mock_google_sheets_service.ensure_spreadsheet_from_template.return_value = mock_response
    
    # Setup test data
    template_id = "test-template-id"
    new_title = "New Spreadsheet"
    folder_id = "test-folder-id"
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method
    result = service._create_spreadsheet_from_template(template_id, new_title, folder_id)
    
    # Verify result
    assert result == mock_response
    
    # Verify Google Sheets service was called correctly
    mock_google_sheets_service.ensure_spreadsheet_from_template.assert_called_once_with(
        template_id=template_id,
        new_title=new_title,
        folder_id=folder_id
    )


def test_create_spreadsheet_from_template_missing_template(mock_google_sheets_service):
    """Test error when template ID is missing."""
    # Setup test data
    template_id = None
    new_title = "New Spreadsheet"
    folder_id = "test-folder-id"
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method and expect exception
    with pytest.raises(Exception) as exc_info:
        service._create_spreadsheet_from_template(template_id, new_title, folder_id)
    
    # Verify exception message
    assert "Template ID is not configured" in str(exc_info.value)
    
    # Verify Google Sheets service was not called
    mock_google_sheets_service.ensure_spreadsheet_from_template.assert_not_called()


@patch("feptm.timesheets.project_service.settings")
def test_create_project_success(mock_settings, mock_google_sheets_service):
    """Test successful project creation."""
    # Setup test data
    project = Project(name="New Project")
    
    # Configure mock services
    mock_google_sheets_service.is_initialized.return_value = True
    
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = "parent-folder-id"
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-template-id"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Setup mock responses
    mock_google_sheets_service.get_file.return_value = {"name": "Parent Folder", "id": "parent-folder-id"}
    mock_google_sheets_service.create_drive_folder.return_value = {
        "folder_id": "new-folder-id",
        "folder_url": "https://drive.google.com/drive/folders/new-folder-id"
    }
    
    # Mock template creation responses
    info_template_response = {
        "spreadsheet_id": "new-info-id",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-info-id"
    }
    report_template_response = {
        "spreadsheet_id": "new-report-id",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-report-id"
    }
    calc_template_response = {
        "spreadsheet_id": "new-calc-id",
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-calc-id"
    }
    
    # Configure mock to return different responses for different calls
    mock_google_sheets_service.ensure_spreadsheet_from_template.side_effect = [
        info_template_response,
        report_template_response,
        calc_template_response
    ]
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method
    result = service.create_project(project)
    
    # Verify result
    assert result["drive_folder_id"] == "new-folder-id"
    assert result["drive_folder_url"] == "https://drive.google.com/drive/folders/new-folder-id"
    assert result["project_info_spreadsheet_id"] == "new-info-id"
    assert result["project_info_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/new-info-id"
    assert result["report_spreadsheet_id"] == "new-report-id"
    assert result["report_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/new-report-id"
    assert result["calculations_spreadsheet_id"] == "new-calc-id"
    assert result["calculations_spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/new-calc-id"
    
    # Verify project object was updated
    assert project.drive_folder_id == "new-folder-id"
    assert project.project_info_spreadsheet_id == "new-info-id"
    assert project.report_spreadsheet_id == "new-report-id"
    assert project.calculations_spreadsheet_id == "new-calc-id"
    
    # Verify method calls
    mock_google_sheets_service.get_file.assert_called_once_with("parent-folder-id")
    mock_google_sheets_service.create_drive_folder.assert_called_once_with("New Project", "parent-folder-id")
    
    # Verify update_project_info_sheet was called
    mock_google_sheets_service.update_sheet_data.assert_called_once()


@patch("feptm.timesheets.project_service.settings")
def test_create_project_no_parent_folder(mock_settings, mock_google_sheets_service):
    """Test project creation with no parent folder specified."""
    # Setup test data
    project = Project(name="No Parent Project")
    
    # Configure mock services
    mock_google_sheets_service.is_initialized.return_value = True
    
    # No parent folder ID
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = None
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-template-id"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Setup mock responses
    mock_google_sheets_service.create_drive_folder.return_value = {
        "folder_id": "root-folder-id",
        "folder_url": "https://drive.google.com/drive/folders/root-folder-id"
    }
    
    # Mock template creation responses
    mock_google_sheets_service.ensure_spreadsheet_from_template.side_effect = [
        {"spreadsheet_id": "new-info-id", "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-info-id"},
        {"spreadsheet_id": "new-report-id", "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-report-id"},
        {"spreadsheet_id": "new-calc-id", "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-calc-id"}
    ]
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method
    result = service.create_project(project)
    
    # Verify result
    assert result["drive_folder_id"] == "root-folder-id"
    
    # Verify method calls
    mock_google_sheets_service.get_file.assert_not_called()
    # Called with just the project name (no parent ID)
    mock_google_sheets_service.create_drive_folder.assert_called_once_with("No Parent Project")


@patch("feptm.timesheets.project_service.settings")
def test_create_project_service_not_initialized(mock_settings, mock_google_sheets_service):
    """Test error when Google service is not initialized."""
    # Setup test data
    project = Project(name="Test Project")
    
    # Configure mock service to return not initialized
    mock_google_sheets_service.is_initialized.return_value = False
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method and expect exception
    with pytest.raises(Exception) as exc_info:
        service.create_project(project)
    
    # Verify exception message
    assert "Google services are not initialized" in str(exc_info.value)


@patch("feptm.timesheets.project_service.settings")
def test_create_project_parent_folder_error(mock_settings, mock_google_sheets_service):
    """Test error when parent folder is not accessible."""
    # Setup test data
    project = Project(name="Parent Error Project")
    
    # Configure mock services
    mock_google_sheets_service.is_initialized.return_value = True
    
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = "invalid-folder-id"
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-template-id"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-template-id"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-template-id"
    
    # Configure get_file to raise exception
    mock_google_sheets_service.get_file.side_effect = Exception("Folder not found")
    
    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)
    
    # Call method and expect exception
    with pytest.raises(Exception) as exc_info:
        service.create_project(project)
    
    # Verify exception message
    assert "Parent folder with ID invalid-folder-id not found" in str(exc_info.value)
    
    # Verify method calls
    mock_google_sheets_service.get_file.assert_called_once_with("invalid-folder-id")
    mock_google_sheets_service.create_drive_folder.assert_not_called() 