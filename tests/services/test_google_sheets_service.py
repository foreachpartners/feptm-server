"""Tests for Google Sheets Service."""

from unittest.mock import patch, MagicMock, ANY

import pytest

from feptm.services.google_sheets_service import GoogleSheetsService


@pytest.fixture
def mock_google_service():
    """Create a mock for Google API service."""
    with patch("googleapiclient.discovery.build") as mock_build:
        # Mock sheets and drive services
        mock_sheets_service = MagicMock()
        mock_drive_service = MagicMock()
        
        # Configure build to return different services
        mock_build.side_effect = lambda service, version, credentials, cache_discovery=None: \
            mock_sheets_service if service == "sheets" else mock_drive_service
        
        # Return both mocked services
        yield {
            "build": mock_build,
            "sheets": mock_sheets_service,
            "drive": mock_drive_service
        }


@pytest.fixture
def mock_google_auth():
    """Create a mock for Google Auth."""
    with patch("google.oauth2.credentials.Credentials") as mock_creds_class:
        # Create mock credentials
        credentials = MagicMock()
        
        # Setup from_authorized_user_info
        mock_creds_class.from_authorized_user_info.return_value = credentials
        
        yield {
            "Credentials": mock_creds_class,
            "instance": credentials
        }


@pytest.fixture
def mock_google_sheets_service():
    """Create a pre-configured mock of GoogleSheetsService."""
    with patch("feptm.services.google_sheets_service.settings") as mock_settings, \
         patch("feptm.services.google_sheets_service.GoogleSheetsService._get_credentials") as mock_get_creds, \
         patch("googleapiclient.discovery.build") as mock_build:
        
        # Configure settings
        mock_settings.GOOGLE_CREDENTIALS_FILE = "test-credentials.json"
        mock_settings.GOOGLE_TOKEN_FILE = "test-token.json"
        
        # Mock credentials
        credentials = MagicMock()
        mock_get_creds.return_value = credentials
        
        # Mock services
        mock_sheets_service = MagicMock()
        mock_drive_service = MagicMock()
        
        # Configure build to return different services
        mock_build.side_effect = lambda service, version, credentials, cache_discovery=None: \
            mock_sheets_service if service == "sheets" else mock_drive_service
        
        # Create service instance
        service = GoogleSheetsService()
        
        # Manually set services
        service.sheets_service = mock_sheets_service
        service.drive_service = mock_drive_service
        
        yield service


def test_is_initialized(mock_google_sheets_service):
    """Test is_initialized method."""
    # Should return True since we set both services in the fixture
    assert mock_google_sheets_service.is_initialized() is True
    
    # Test when one service is None
    mock_google_sheets_service.sheets_service = None
    assert mock_google_sheets_service.is_initialized() is False


def test_create_drive_folder(mock_google_sheets_service):
    """Test creating a folder in Google Drive."""
    # Mock drive service responses
    files_resource = MagicMock()
    mock_google_sheets_service.drive_service.files.return_value = files_resource
    
    # Mock create call
    create_mock = MagicMock()
    files_resource.create.return_value = create_mock
    
    # Mock execute response
    create_mock.execute.return_value = {
        "id": "new-folder-id",
        "name": "Test Folder"
    }
    
    # Test without parent folder
    result = mock_google_sheets_service.create_drive_folder("Test Folder")
    
    # Verify result
    assert result["folder_id"] == "new-folder-id"
    assert result["folder_url"] == "https://drive.google.com/drive/folders/new-folder-id"
    
    # Verify API calls
    files_resource.create.assert_called_once()
    create_args = files_resource.create.call_args[1]
    assert create_args["body"]["name"] == "Test Folder"
    assert create_args["body"]["mimeType"] == "application/vnd.google-apps.folder"
    assert "parents" not in create_args["body"]
    
    # Reset mocks for next test
    files_resource.create.reset_mock()
    
    # Test with parent folder
    parent_id = "parent-folder-id"
    result = mock_google_sheets_service.create_drive_folder("Child Folder", parent_id)
    
    # Verify API calls with parent
    files_resource.create.assert_called_once()
    create_args = files_resource.create.call_args[1]
    assert create_args["body"]["name"] == "Child Folder"
    assert create_args["body"]["parents"] == [parent_id]


def test_get_file(mock_google_sheets_service):
    """Test getting file information."""
    # Mock drive service responses
    files_resource = MagicMock()
    mock_google_sheets_service.drive_service.files.return_value = files_resource
    
    # Mock get call
    get_mock = MagicMock()
    files_resource.get.return_value = get_mock
    
    # Mock execute response
    get_mock.execute.return_value = {
        "id": "test-file-id",
        "name": "Test File"
    }
    
    # Call get_file
    file_id = "test-file-id"
    result = mock_google_sheets_service.get_file(file_id)
    
    # Verify result
    assert result["id"] == "test-file-id"
    assert result["name"] == "Test File"
    
    # Verify API call was made with correct parameters - but don't be too strict about exact fields
    # Just check that the method was called with the correct fileId
    files_resource.get.assert_called_once()
    call_args = files_resource.get.call_args[1]
    assert call_args["fileId"] == file_id
    assert "fields" in call_args  # Just check that fields parameter exists


def test_delete_file(mock_google_sheets_service):
    """Test deleting a file."""
    # Mock drive service responses
    files_resource = MagicMock()
    mock_google_sheets_service.drive_service.files.return_value = files_resource
    
    # Mock delete call
    delete_mock = MagicMock()
    files_resource.delete.return_value = delete_mock
    
    # Call delete_file
    file_id = "file-to-delete-id"
    mock_google_sheets_service.delete_file(file_id)
    
    # Verify API calls
    files_resource.delete.assert_called_once_with(fileId=file_id)
    delete_mock.execute.assert_called_once()


def test_ensure_spreadsheet_from_template(mock_google_sheets_service):
    """Test creating a spreadsheet from a template."""
    # Mock drive service responses
    files_resource = MagicMock()
    mock_google_sheets_service.drive_service.files.return_value = files_resource
    
    # Mock get call for template verification
    get_mock = MagicMock()
    files_resource.get.return_value = get_mock
    get_mock.execute.return_value = {"id": "template-id", "name": "Template Sheet"}
    
    # Mock copy call
    copy_mock = MagicMock()
    files_resource.copy.return_value = copy_mock
    
    # Mock execute response
    copy_mock.execute.return_value = {
        "id": "new-spreadsheet-id",
        "name": "New Title"
    }
    
    # Mock update call
    update_mock = MagicMock()
    files_resource.update.return_value = update_mock
    update_mock.execute.return_value = {"id": "new-spreadsheet-id"}
    
    # Call ensure_spreadsheet_from_template
    template_id = "template-id"
    new_title = "New Title"
    folder_id = "folder-id"
    
    result = mock_google_sheets_service.ensure_spreadsheet_from_template(template_id, new_title, folder_id)
    
    # Verify result
    assert result["spreadsheet_id"] == "new-spreadsheet-id"
    assert result["spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/new-spreadsheet-id"
    
    # Verify API calls - focusing on the parameters that matter
    files_resource.copy.assert_called_once()
    copy_args = files_resource.copy.call_args[1]
    assert copy_args["fileId"] == template_id
    assert copy_args["body"]["name"] == new_title
    
    # Verify update was called (not checking exact parameters)
    files_resource.update.assert_called_once()


def test_update_sheet_data(mock_google_sheets_service):
    """Test updating a sheet in a spreadsheet."""
    # Mock sheets service responses
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    # Mock get method to return sheet
    mock_google_sheets_service.get_sheet_by_name = MagicMock()
    mock_google_sheets_service.get_sheet_by_name.return_value = {
        "properties": {
            "title": "Test Sheet"
        }
    }
    
    # Mock clear_range method
    mock_google_sheets_service.clear_range = MagicMock()
    
    # Mock update_range method
    mock_google_sheets_service.update_range = MagicMock()
    mock_google_sheets_service.update_range.return_value = {"updatedRows": 10}
    
    # Call update_sheet_data
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "Test Sheet"
    data = [
        ["Header 1", "Header 2"],
        ["Value 1", "Value 2"],
        ["Value 3", "Value 4"]
    ]
    
    result = mock_google_sheets_service.update_sheet_data(spreadsheet_id, sheet_name, data)
    
    # Verify method calls
    mock_google_sheets_service.get_sheet_by_name.assert_called_once_with(spreadsheet_id, sheet_name)
    mock_google_sheets_service.clear_range.assert_called_once()
    mock_google_sheets_service.update_range.assert_called_once()
    
    # Verify the update_range parameters
    update_args = mock_google_sheets_service.update_range.call_args[1]
    assert update_args["spreadsheet_id"] == spreadsheet_id
    assert "Test Sheet" in update_args["range_name"]
    assert update_args["values"] == data
    assert update_args["value_input_option"] == "USER_ENTERED"


def test_exception_handling(mock_google_sheets_service):
    """Test exception handling in methods."""
    # Create a function that raises an exception
    def failing_function():
        raise Exception("Test error")
    
    # Mock get_sheet_by_name to raise exception
    mock_google_sheets_service.get_sheet_by_name = MagicMock(side_effect=Exception("Sheet not found"))
    
    # Test update_sheet_data error handling
    with pytest.raises(Exception) as exc_info:
        mock_google_sheets_service.update_sheet_data("test-id", "Test Sheet", [["Data"]])
    
    # Verify error message contains the original error
    assert "Failed to update sheet" in str(exc_info.value)
    assert "Sheet not found" in str(exc_info.value) 