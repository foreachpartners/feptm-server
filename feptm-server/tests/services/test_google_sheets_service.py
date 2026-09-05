"""Tests for Google Sheets Service."""

from unittest.mock import patch, MagicMock, ANY
from typing import Dict, List, Any

import pytest

from feptm.services.google_sheets_service import GoogleSheetsService


# Test data for Google Sheets API responses - stored in same file as tests
SAMPLE_SHEET_METADATA = {
    "properties": {
        "title": "Test Sheet",
        "sheetId": 123,
        "gridProperties": {"rowCount": 1000, "columnCount": 26}
    }
}

SAMPLE_SPREADSHEET_WITH_SHEETS = {
    "spreadsheetId": "test-spreadsheet-id",
    "sheets": [
        {"properties": {"title": "Sheet1", "sheetId": 0}},
        {"properties": {"title": "Project info", "sheetId": 1}},
        {"properties": {"title": "Summary", "sheetId": 2}}
    ]
}

SAMPLE_SHEET_VALUES_WITH_HEADERS = [
    ["Name", "Hours", "Rate", "Total"],
    ["John Doe", "40", "100", "4000"],
    ["Jane Smith", "35", "120", "4200"],
    ["", "", "", ""]  # Empty row
]

SAMPLE_BATCH_UPDATE_REQUESTS = [
    {
        "updateCells": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "Updated"}}]}],
            "fields": "userEnteredValue"
        }
    }
]

ERROR_RESPONSES = {
    "not_found": {
        "error": {
            "code": 404,
            "message": "Requested entity was not found.",
            "status": "NOT_FOUND"
        }
    },
    "permission_denied": {
        "error": {
            "code": 403,
            "message": "The caller does not have permission",
            "status": "PERMISSION_DENIED"
        }
    }
}


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
         patch("feptm.services.google_sheets_service.GoogleSheetsService._get_credentials") as mock_get_creds:
        
        # Configure settings
        mock_settings.GOOGLE_CREDENTIALS_FILE = "test-credentials.json"
        mock_settings.GOOGLE_TOKEN_FILE = "test-token.json"
        mock_settings.GOOGLE_API_TIMEOUT = 30
        
        # Mock credentials
        credentials = MagicMock()
        mock_get_creds.return_value = credentials
        
        # Mock services
        mock_sheets_service = MagicMock()
        mock_drive_service = MagicMock()
        
        # Create service instance
        service = GoogleSheetsService()
        
        # Mock _get_services to return our mock services
        service._get_services = MagicMock(return_value=(mock_drive_service, mock_sheets_service))
        
        yield service


def test_is_initialized(mock_google_sheets_service):
    """Test is_initialized method."""
    # Should return True since credentials are loaded
    assert mock_google_sheets_service.is_initialized() is True
    
    # Test when credentials are None
    mock_google_sheets_service._credentials = None
    assert mock_google_sheets_service.is_initialized() is False


def test_get_sheet_by_name_found(mock_google_sheets_service):
    """Test getting a sheet by name when sheet exists."""
    # Arrange
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "Project info"
    
    # Mock spreadsheets().get() response
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    get_mock = MagicMock()
    spreadsheets_resource.get.return_value = get_mock
    get_mock.execute.return_value = SAMPLE_SPREADSHEET_WITH_SHEETS
    
    # Act
    result = mock_google_sheets_service.get_sheet_by_name(spreadsheet_id, sheet_name)
    
    # Assert
    assert result is not None
    assert result["properties"]["title"] == "Project info"
    assert result["properties"]["sheetId"] == 1
    
    # Verify API call
    spreadsheets_resource.get.assert_called_once_with(spreadsheetId=spreadsheet_id)


def test_get_sheet_by_name_not_found(mock_google_sheets_service):
    """Test getting a sheet by name when sheet does not exist."""
    # Arrange
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "NonExistent"
    
    # Mock spreadsheets().get() response
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    get_mock = MagicMock()
    spreadsheets_resource.get.return_value = get_mock
    get_mock.execute.return_value = SAMPLE_SPREADSHEET_WITH_SHEETS
    
    # Act
    result = mock_google_sheets_service.get_sheet_by_name(spreadsheet_id, sheet_name)
    
    # Assert
    assert result is None


def test_update_range_success(mock_google_sheets_service):
    """Test updating a range with values."""
    # Arrange
    spreadsheet_id = "test-spreadsheet-id"
    range_name = "Sheet1!A1:C3"
    values = [
        ["Header1", "Header2", "Header3"],
        ["Value1", "Value2", "Value3"],
        ["Value4", "Value5", "Value6"]
    ]
    
    # Mock spreadsheets().values().update() response
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    values_resource = MagicMock()
    spreadsheets_resource.values.return_value = values_resource
    
    update_mock = MagicMock()
    values_resource.update.return_value = update_mock
    update_mock.execute.return_value = {
        "spreadsheetId": spreadsheet_id,
        "updatedRows": 3,
        "updatedColumns": 3,
        "updatedCells": 9
    }
    
    # Act
    result = mock_google_sheets_service.update_range(
        spreadsheet_id, range_name, values, "USER_ENTERED"
    )
    
    # Assert
    assert result["updatedRows"] == 3
    assert result["updatedColumns"] == 3
    assert result["updatedCells"] == 9
    
    # Verify API call
    values_resource.update.assert_called_once_with(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={"values": values}
    )


def test_batch_update_success(mock_google_sheets_service):
    """Test batch update with multiple requests."""
    # Arrange
    spreadsheet_id = "test-spreadsheet-id"
    requests = SAMPLE_BATCH_UPDATE_REQUESTS
    
    # Mock spreadsheets().batchUpdate() response
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    batch_update_mock = MagicMock()
    spreadsheets_resource.batchUpdate.return_value = batch_update_mock
    batch_update_mock.execute.return_value = {
        "spreadsheetId": spreadsheet_id,
        "replies": [{"updateCells": {"updatedRows": 1}}]
    }
    
    # Act
    result = mock_google_sheets_service.batch_update(spreadsheet_id, requests)
    
    # Assert
    assert result["spreadsheetId"] == spreadsheet_id
    assert "replies" in result
    
    # Verify API call
    spreadsheets_resource.batchUpdate.assert_called_once_with(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests}
    )


def test_find_column_index_found(mock_google_sheets_service):
    """Test finding column index when columns exist."""
    # Arrange
    headers = ["Name", "Hours", "Rate", "Total", "Notes"]
    column_names = ["Rate", "Total"]
    
    # Act
    result = mock_google_sheets_service.find_column_index(headers, column_names)
    
    # Assert
    assert result == 2  # "Rate" is at index 2


def test_find_column_index_not_found(mock_google_sheets_service):
    """Test finding column index when columns don't exist."""
    # Arrange
    headers = ["Name", "Hours", "Rate"]
    column_names = ["NonExistent", "AlsoMissing"]
    
    # Act
    result = mock_google_sheets_service.find_column_index(headers, column_names)
    
    # Assert
    assert result is None


def test_get_sheet_data_with_headers_success(mock_google_sheets_service):
    """Test getting sheet data with headers."""
    # Arrange
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "TestSheet"
    range_format = "{sheet_name}!A:D"
    
    # Mock spreadsheets().values().get() response
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    values_resource = MagicMock()
    spreadsheets_resource.values.return_value = values_resource
    
    get_mock = MagicMock()
    values_resource.get.return_value = get_mock
    get_mock.execute.return_value = {
        "values": SAMPLE_SHEET_VALUES_WITH_HEADERS
    }
    
    # Act
    values, headers = mock_google_sheets_service.get_sheet_data_with_headers(
        spreadsheet_id, sheet_name, range_format
    )
    
    # Assert
    assert headers == ["Name", "Hours", "Rate", "Total"]
    assert len(values) == 4  # Including header row
    assert values[0] == ["Name", "Hours", "Rate", "Total"]
    assert values[1] == ["John Doe", "40", "100", "4000"]
    
    # Verify API calls - check that the correct range was requested
    values_resource.get.assert_called_once_with(
        spreadsheetId=spreadsheet_id,
        range="TestSheet!A:D",
        valueRenderOption="UNFORMATTED_VALUE",
    )


@pytest.mark.parametrize("column_letter,expected_index", [
    ("A", 0),
    ("B", 1),
    ("Z", 25),
    ("AA", 26),
    ("AB", 27),
    ("AZ", 51)
])
def test_column_letter_to_index(mock_google_sheets_service, column_letter: str, expected_index: int):
    """Test converting column letters to indices."""
    result = mock_google_sheets_service.column_letter_to_index(column_letter)
    assert result == expected_index


@pytest.mark.parametrize("column_index,expected_letter", [
    (0, "A"),
    (1, "B"),
    (25, "Z"),
    (26, "AA"),
    (27, "AB"),
    (51, "AZ")
])
def test_column_index_to_letter(mock_google_sheets_service, column_index: int, expected_letter: str):
    """Test converting column indices to letters."""
    result = mock_google_sheets_service.column_index_to_letter(column_index)
    assert result == expected_letter


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


def test_error_handling_http_error(mock_google_sheets_service):
    """Test handling HTTP errors from Google API."""
    from googleapiclient.errors import HttpError
    
    # Mock HttpError response
    http_error = HttpError(
        resp=MagicMock(status=404),
        content=b'{"error": {"code": 404, "message": "Not found"}}'
    )
    
    # Mock sheets_service.spreadsheets().values().get() to raise HttpError
    spreadsheets_resource = MagicMock()
    mock_google_sheets_service.sheets_service.spreadsheets.return_value = spreadsheets_resource
    
    values_resource = MagicMock()
    spreadsheets_resource.values.return_value = values_resource
    
    get_mock = MagicMock()
    values_resource.get.return_value = get_mock
    get_mock.execute.side_effect = http_error
    
    # Test that HttpError is properly handled and re-raised as Exception
    with pytest.raises(Exception) as exc_info:
        mock_google_sheets_service.get_sheet_data_with_headers(
            "test-id", "Test Sheet", "{sheet_name}!A:D"
        )
    
    # Verify error is caught and wrapped
    assert "Failed to get sheet data" in str(exc_info.value) 