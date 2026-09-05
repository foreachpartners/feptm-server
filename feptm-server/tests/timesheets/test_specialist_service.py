"""Tests for specialist storage and facade."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from feptm.models.context import TimesheetContext
from feptm.models.specialist import Specialist
from feptm.storage.specialist_storage import SpecialistStorage
from feptm.timesheets.specialist_service import SpecialistService
from feptm.timesheets.config_service import DateFormat

SAMPLE_HEADERS = [
    "Name", "Role", "Project", "Internal Rate", "External Rate",
    "Date", "Timesheet",
]

SAMPLE_VALUES = [
    ["Name", "Role", "Project", "Internal Rate", "External Rate", "Date", "Timesheet"],
    ["John Doe", "Lead Developer", "Project Alpha", "100", "120", "Jan 15, 2024", "timesheet-john-123"],
    ["Jane Smith", "Senior Designer", "Project Beta", "90", "110", "Jan 20, 2024", ""],
    ["Bob Wilson", "Junior Developer", "Project Gamma", "70", "90", "Feb 01, 2024", "timesheet-bob-456"],
]

TIMESHEET_CONTEXT = TimesheetContext(
    folder_id="test-folder-123",
    project_name="Test Project",
)

TIMESHEET_RESULT = {
    "spreadsheet_id": "new-timesheet-id-789",
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/new-timesheet-id-789",
}


@pytest.fixture
def mock_sheets():
    mock = MagicMock()
    mock.is_initialized.return_value = True
    mock.sheets_service = MagicMock()
    mock.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
    mock.find_column_index.side_effect = lambda headers, names: (
        next((i for i, h in enumerate(headers) if h.strip().lower() in (n.lower() for n in names)), None)
    )
    mock.column_index_to_letter.side_effect = lambda idx: chr(ord("A") + idx)
    return mock


@pytest.fixture
def specialist_storage(mock_sheets):
    return SpecialistStorage(mock_sheets)


@pytest.fixture
def specialist_service(mock_sheets):
    return SpecialistService(
        specialist_storage=SpecialistStorage(mock_sheets),
        timesheet_template_id="ts-template-id",
    )


class TestSpecialistStorage:

    def test_list_from_sheet_success(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)

        specialists, existing = specialist_storage.list_from_sheet("test-id", "Team")

        assert len(specialists) == 3
        assert existing == 2
        assert specialists[0].name == "John Doe"
        assert specialists[0].timesheet == "timesheet-john-123"
        assert specialists[1].timesheet is None
        mock_sheets.get_sheet_data_with_headers.assert_called_once()

    def test_list_from_sheet_not_found(self, specialist_storage, mock_sheets):
        mock_sheets.get_sheet_by_name.return_value = None

        specialists, existing = specialist_storage.list_from_sheet("test-id", "Team")
        assert specialists == []
        assert existing == 0

    def test_list_from_sheet_no_data(self, specialist_storage, mock_sheets):
        mock_sheets.get_sheet_data_with_headers.return_value = (
            [SAMPLE_HEADERS], SAMPLE_HEADERS
        )

        specialists, existing = specialist_storage.list_from_sheet("test-id", "Team")
        assert specialists == []

    def test_parse_row_extracts_timesheet_id_from_url(self, specialist_storage, mock_sheets):
        headers = SAMPLE_HEADERS
        data = [
            headers,
            ["John Doe", "Lead Developer", "Project Alpha", "100", "120",
             "Jan 15, 2024", "https://docs.google.com/spreadsheets/d/abcd1234/edit"],
        ]
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)

        specialists, _ = specialist_storage.list_from_sheet("test-id", "Team")

        assert len(specialists) == 1
        assert specialists[0].timesheet == "abcd1234"

    def test_parse_row_preserves_plain_timesheet_id(self, specialist_storage, mock_sheets):
        headers = SAMPLE_HEADERS
        data = [
            headers,
            ["John Doe", "Lead Developer", "Project Alpha", "100", "120",
             "Jan 15, 2024", "plain-id-123"],
        ]
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)

        specialists, _ = specialist_storage.list_from_sheet("test-id", "Team")

        assert len(specialists) == 1
        assert specialists[0].timesheet == "plain-id-123"

    def test_create_timesheet_success(self, specialist_storage, mock_sheets):
        mock_sheets.find_file_in_folder.return_value = None
        mock_sheets.ensure_spreadsheet_from_template.return_value = TIMESHEET_RESULT

        spec = Specialist(name="John", role="Dev")
        result = specialist_storage.create_timesheet(spec, TIMESHEET_CONTEXT, "tmpl-id")

        assert result == TIMESHEET_RESULT
        assert spec.timesheet == "new-timesheet-id-789"
        mock_sheets.ensure_spreadsheet_from_template.assert_called_once()

    def test_create_timesheet_missing_template(self, specialist_storage):
        spec = Specialist(name="John", role="Dev")
        with pytest.raises(Exception, match="Timesheet template ID not configured"):
            specialist_storage.create_timesheet(spec, TIMESHEET_CONTEXT, "")

    def test_create_timesheet_reuses_existing_drive_file(self, specialist_storage, mock_sheets):
        mock_sheets.find_file_in_folder.return_value = "existing-timesheet-id"

        spec = Specialist(name="John", role="Dev")
        result = specialist_storage.create_timesheet(spec, TIMESHEET_CONTEXT, "tmpl-id")

        assert result["spreadsheet_id"] == "existing-timesheet-id"
        assert spec.timesheet == "existing-timesheet-id"
        mock_sheets.ensure_spreadsheet_from_template.assert_not_called()

    def test_create_timesheet_creates_new_when_none_found(self, specialist_storage, mock_sheets):
        mock_sheets.find_file_in_folder.return_value = None
        mock_sheets.ensure_spreadsheet_from_template.return_value = TIMESHEET_RESULT

        spec = Specialist(name="John", role="Dev")
        result = specialist_storage.create_timesheet(spec, TIMESHEET_CONTEXT, "tmpl-id")

        assert result == TIMESHEET_RESULT
        assert spec.timesheet == "new-timesheet-id-789"
        mock_sheets.ensure_spreadsheet_from_template.assert_called_once()

    def test_update_timesheet_ids(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        spec = Specialist(name="John Doe", role="Lead Developer", timesheet="new-ts-id", row_index=2)
        result = specialist_storage.update_timesheet_ids("test-id", "Team", [spec])

        assert result is True
        mock_sheets.batch_update.assert_called_once()

    def test_update_timesheet_ids_no_double_wrap_for_url_input(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        spec = Specialist(
            name="John Doe", role="Lead Developer",
            timesheet="https://docs.google.com/spreadsheets/d/already-a-url",
            row_index=2,
        )
        result = specialist_storage.update_timesheet_ids("test-id", "Team", [spec])

        assert result is True
        call_args = mock_sheets.batch_update.call_args[0]
        requests = call_args[1]
        assert len(requests) == 1
        cell_value = requests[0]["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]["stringValue"]
        assert cell_value == "https://docs.google.com/spreadsheets/d/already-a-url"

    def test_update_timesheet_ids_no_updates(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        spec = Specialist(name="John", role="Dev")  # no timesheet
        result = specialist_storage.update_timesheet_ids("test-id", "Team", [spec])
        assert result is True

    def test_parse_rows_sets_row_index(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)

        specialists, _ = specialist_storage.list_from_sheet("test-id", "Team")

        assert specialists[0].row_index == 2
        assert specialists[1].row_index == 3
        assert specialists[2].row_index == 4

    def test_prepare_updates_uses_row_index(self, specialist_storage, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        sp1 = Specialist(name="John Doe", role="Dev", timesheet="ts-a", row_index=2)
        sp2 = Specialist(name="Jane Smith", role="Designer", timesheet="ts-b", row_index=3)

        result = specialist_storage.update_timesheet_ids("test-id", "Team", [sp1, sp2])

        assert result is True
        assert mock_sheets.batch_update.call_count == 1
        call_args = mock_sheets.batch_update.call_args[0]
        requests = call_args[1]
        assert len(requests) == 2
        assert requests[0]["updateCells"]["range"]["startRowIndex"] == 1
        assert requests[1]["updateCells"]["range"]["startRowIndex"] == 2

    def test_prepare_updates_duplicate_names_correct_rows(self, specialist_storage, mock_sheets):
        headers = ["Name", "Role", "Project", "Internal Rate", "External Rate", "Date", "Timesheet"]
        data = [
            headers,
            ["John Smith", "Dev", "", "100", "120", "", ""],
            ["John Smith", "QA", "", "80", "100", "", ""],
        ]
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        sp1 = Specialist(name="John Smith", role="Dev", timesheet="ts-dev", row_index=2)
        sp2 = Specialist(name="John Smith", role="QA", timesheet="ts-qa", row_index=3)

        result = specialist_storage.update_timesheet_ids("test-id", "Team", [sp1, sp2])

        assert result is True
        assert mock_sheets.batch_update.call_count == 1
        call_args = mock_sheets.batch_update.call_args[0]
        requests = call_args[1]
        assert len(requests) == 2
        assert requests[0]["updateCells"]["range"]["startRowIndex"] == 1
        assert requests[1]["updateCells"]["range"]["startRowIndex"] == 2


class TestSpecialistServiceFacade:

    def test_sync_specialists(self, specialist_service, mock_sheets):
        data = SAMPLE_VALUES
        headers = SAMPLE_HEADERS
        mock_sheets.get_sheet_data_with_headers.return_value = (data, headers)
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Team", "sheetId": 123}}
        mock_sheets.ensure_spreadsheet_from_template.return_value = TIMESHEET_RESULT
        mock_sheets.find_specialist_row_index.return_value = 1
        mock_sheets.find_column_index.side_effect = lambda h, names: (
            next((i for i, hh in enumerate(h) if hh.strip().lower() in (n.lower() for n in names)), None)
        )

        specialists, new_count = specialist_service.sync_specialists(
            "test-id", TIMESHEET_CONTEXT
        )

        assert len(specialists) == 3
        assert new_count == 1
        mock_sheets.batch_update.assert_called()

    def test_sync_no_specialists(self, specialist_service, mock_sheets):
        mock_sheets.get_sheet_by_name.return_value = None

        specialists, new_count = specialist_service.sync_specialists("test-id", TIMESHEET_CONTEXT)
        assert specialists == []
        assert new_count == 0

    def test_sync_error_handling(self, specialist_service, mock_sheets):
        mock_sheets.get_sheet_by_name.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            specialist_service.sync_specialists("test-id", TIMESHEET_CONTEXT)
