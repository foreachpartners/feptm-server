"""Tests for row formatting and formula copying functionality."""

from unittest.mock import MagicMock

import pytest

from feptm.timesheets.project_service import TimesheetProjectService
from feptm.services.google_sheets_service import GoogleSheetsService


@pytest.fixture
def mock_google_sheets_service():
    """Create a mock GoogleSheetsService."""
    mock_service = MagicMock(spec=GoogleSheetsService)
    mock_service.is_initialized.return_value = True
    return mock_service


def test_copy_row_formatting(mock_google_sheets_service):
    """Test that both formulas and formatting are copied correctly."""
    # Setup test data
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "Current Period"
    source_row = 2
    target_row = 3

    # Mock getting spreadsheet info
    mock_google_sheets_service.sheets_service.spreadsheets().get().execute.return_value = {
        "sheets": [
            {
                "properties": {
                    "title": "Current Period",
                    "sheetId": 123
                }
            }
        ]
    }

    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)

    # Call method
    service._copy_row_formatting(spreadsheet_id, sheet_name, source_row, target_row)

    # Verify batch update was called with both formula and format requests
    mock_google_sheets_service.batch_update.assert_called_once()
    batch_update_args = mock_google_sheets_service.batch_update.call_args[1]
    requests = batch_update_args["requests"]

    # Should have exactly two requests - one for formulas and one for formatting
    assert len(requests) == 2

    # First request should be for formulas
    assert requests[0]["copyPaste"]["pasteType"] == "PASTE_FORMULA"

    # Second request should be for formatting
    assert requests[1]["copyPaste"]["pasteType"] == "PASTE_FORMAT"

    # Both requests should have same source and destination
    for request in requests:
        source = request["copyPaste"]["source"]
        dest = request["copyPaste"]["destination"]
        assert source["startRowIndex"] == source_row - 1
        assert dest["startRowIndex"] == target_row - 1


def test_insert_position_first_specialist(mock_google_sheets_service):
    """Test that first specialist position is handled correctly."""
    # Setup test data
    values = [
        ["Specialist", "Role", "Hours", "Rate"],  # Header row
        ["", "", "", ""],  # Empty data row
        ["", "Total", "", ""]  # Total row
    ]
    headers = values[0]

    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)

    # Call method
    insert_row = service._find_insert_position_for_specialist(values, headers)

    # First specialist should use row 1 (index starts from 0, header is row 0)
    assert insert_row == 1


def test_insert_position_subsequent_specialist(mock_google_sheets_service):
    """Test that subsequent specialist positions are handled correctly."""
    # Setup test data
    values = [
        ["Specialist", "Role", "Hours", "Rate"],  # Header row
        ["John Doe", "Developer", "40", "100"],  # Existing specialist
        ["", "Total", "", ""]  # Total row
    ]
    headers = values[0]

    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)

    # Call method
    insert_row = service._find_insert_position_for_specialist(values, headers)

    # For subsequent specialists, should insert before total row
    assert insert_row == 2


def test_insert_and_update_first_specialist(mock_google_sheets_service):
    """Test that no row is inserted for first specialist."""
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "Current Period"
    insert_row = 1
    update_data = ["John Doe", "Developer", "=SUM(A1:A2)", "100"]
    headers = ["Specialist", "Role", "Hours", "Rate"]

    # Mock sheet data
    sheet = {"properties": {"sheetId": 123}}

    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)

    # Call method
    service._insert_and_update_specialist_row(
        spreadsheet_id, sheet_name, sheet, insert_row, update_data, headers
    )

    # Verify batch update was NOT called (no row insertion for first specialist)
    mock_google_sheets_service.batch_update.assert_not_called()

    # Verify update_range was called to update the data
    mock_google_sheets_service.update_range.assert_called_once()
    update_args = mock_google_sheets_service.update_range.call_args[1]
    assert update_args["range_name"] == f"{sheet_name}!A2:D2"  # row 2 (1-based)
    assert update_args["values"] == [update_data]


def test_insert_and_update_subsequent_specialist(mock_google_sheets_service):
    """Test that row is inserted for subsequent specialists."""
    spreadsheet_id = "test-spreadsheet-id"
    sheet_name = "Current Period"
    insert_row = 2  # After first specialist
    update_data = ["Jane Doe", "Designer", "=SUM(A1:A2)", "120"]
    headers = ["Specialist", "Role", "Hours", "Rate"]

    # Mock sheet data
    sheet = {"properties": {"sheetId": 123}}

    # Create service instance
    service = TimesheetProjectService(mock_google_sheets_service)

    # Call method
    service._insert_and_update_specialist_row(
        spreadsheet_id, sheet_name, sheet, insert_row, update_data, headers
    )

    # Verify batch update was called to insert row
    mock_google_sheets_service.batch_update.assert_called_once()
    batch_args = mock_google_sheets_service.batch_update.call_args[1]
    request = batch_args["requests"][0]
    assert request["insertDimension"]["range"]["startIndex"] == insert_row

    # Verify update_range was called to update the data
    mock_google_sheets_service.update_range.assert_called_once()
    update_args = mock_google_sheets_service.update_range.call_args[1]
    assert update_args["range_name"] == f"{sheet_name}!A3:D3"  # row 3 (1-based)
    assert update_args["values"] == [update_data]
