"""Tests for project storage and facade."""

from unittest.mock import MagicMock, patch

import pytest

from feptm.models.project import Project
from feptm.storage.config_storage import ConfigStorage
from feptm.storage.project_storage import ProjectStorage
from feptm.timesheets.project_service import TimesheetProjectService


@pytest.fixture
def mock_sheets():
    mock = MagicMock()
    mock.is_initialized.return_value = True
    mock.sheets_service = MagicMock()
    mock.drive_service = MagicMock()
    mock.find_column_index.side_effect = (
        lambda headers, names: next(
            (i for i, h in enumerate(headers)
             if h.strip().lower() in (n.lower() for n in names)),
            None,
        )
    )
    return mock


@pytest.fixture
def project_storage(mock_sheets):
    return ProjectStorage(mock_sheets)


@pytest.fixture
def project_service(mock_sheets):
    from feptm.storage.protocols import ProjectStorageProtocol, SpecialistStorageProtocol, FormulaProviderProtocol
    ps = ProjectStorage(mock_sheets)
    ss = MagicMock(spec=SpecialistStorageProtocol)
    fp = MagicMock(spec=FormulaProviderProtocol)
    fp.get_formula.return_value = "=MOCK()"
    fp.get_import_timesheet_formula.return_value = '=IMPORTRANGE("x";"Sheet1!A:Z")'
    return TimesheetProjectService(
        project_storage=ps,
        specialist_storage=ss,
        formula_provider=fp,
        timesheet_template_id="ts-template-id",
    )


class TestProjectStorage:

    def test_update_project_info_sheet(self, project_storage, mock_sheets):
        project = Project(
            name="Test Project",
            drive_folder_id="test-folder-id",
            project_info_spreadsheet_id="test-info-id",
            report_spreadsheet_id="test-report-id",
            calculations_spreadsheet_id="test-calc-id",
        )
        project_storage.update_project_info_sheet("test-spreadsheet-id", project)

        mock_sheets.update_sheet_data.assert_called_once()
        call_args = mock_sheets.update_sheet_data.call_args[1]
        assert call_args["spreadsheet_id"] == "test-spreadsheet-id"
        assert call_args["sheet_name"] == "Project info"
        data = call_args["data"]
        assert data[0] == ["Project Information", ""]
        assert data[1] == ["Field", "Value"]
        assert data[2] == ["Project ID", project.project_info_spreadsheet_id]
        assert data[3] == ["Name", project.name]

    def test_update_project_info_sheet_error(self, project_storage, mock_sheets):
        mock_sheets.update_sheet_data.side_effect = Exception("API Error")
        project = Project(name="Test Project")
        with pytest.raises(Exception):
            project_storage.update_project_info_sheet("test-id", project)

    def test_create_from_template(self, project_storage, mock_sheets):
        mock_response = {"spreadsheet_id": "new-id", "spreadsheet_url": "https://..."}
        mock_sheets.ensure_spreadsheet_from_template.return_value = mock_response
        result = project_storage._create_from_template("tmpl-id", "Title", "folder-id")
        assert result == mock_response
        mock_sheets.ensure_spreadsheet_from_template.assert_called_once_with(
            template_id="tmpl-id", new_title="Title", folder_id="folder-id"
        )

    def test_create_from_template_missing_template(self, project_storage):
        with pytest.raises(Exception, match="Template ID is not configured"):
            project_storage._create_from_template("", "Title", "folder-id")

    def test_create_project_success(self, project_storage, mock_sheets):
        mock_sheets.get_file.return_value = {"name": "Parent", "id": "parent-id"}
        mock_sheets.create_drive_folder.return_value = {
            "folder_id": "new-folder-id",
            "folder_url": "https://drive.google.com/drive/folders/new-folder-id",
        }
        mock_sheets.ensure_spreadsheet_from_template.side_effect = [
            {"spreadsheet_id": "info-id", "spreadsheet_url": "https://..."},
            {"spreadsheet_id": "report-id", "spreadsheet_url": "https://..."},
            {"spreadsheet_id": "calc-id", "spreadsheet_url": "https://..."},
        ]

        result = project_storage.create_project(
            "New Project",
            template_ids={"info": "it", "report": "rt", "calculations": "ct"},
            parent_folder_id="parent-folder-id",
        )

        assert result["drive_folder_id"] == "new-folder-id"
        assert result["info_spreadsheet_id"] == "info-id"
        assert result["report_spreadsheet_id"] == "report-id"
        assert result["calculations_spreadsheet_id"] == "calc-id"
        mock_sheets.get_file.assert_called_once_with("parent-folder-id")
        mock_sheets.create_drive_folder.assert_called_once_with("New Project", "parent-folder-id")

    def test_create_project_no_parent_folder(self, project_storage, mock_sheets):
        mock_sheets.create_drive_folder.return_value = {
            "folder_id": "root-folder-id",
            "folder_url": "https://...",
        }
        mock_sheets.ensure_spreadsheet_from_template.side_effect = [
            {"spreadsheet_id": f"{k}-id", "spreadsheet_url": "https://..."}
            for k in ["info", "report", "calculations"]
        ]

        result = project_storage.create_project(
            "No Parent",
            template_ids={"info": "it", "report": "rt", "calculations": "ct"},
            parent_folder_id=None,
        )
        assert result["drive_folder_id"] == "root-folder-id"
        mock_sheets.create_drive_folder.assert_called_once_with("No Parent")

    def test_create_project_service_not_initialized(self, project_storage, mock_sheets):
        mock_sheets.is_initialized.return_value = False
        with pytest.raises(Exception, match="Google services are not initialized"):
            project_storage.create_project("Test", {"info": "x"}, parent_folder_id=None)

    def test_create_project_parent_folder_error(self, project_storage, mock_sheets):
        mock_sheets.get_file.side_effect = Exception("Folder not found")
        with pytest.raises(Exception, match="Parent folder with ID invalid-id not found"):
            project_storage.create_project(
                "Test",
                template_ids={"info": "x", "report": "y", "calculations": "z"},
                parent_folder_id="invalid-id",
            )

    def test_create_project_cleanup_on_error(self, project_storage, mock_sheets):
        mock_sheets.create_drive_folder.return_value = {
            "folder_id": "new-folder-id",
            "folder_url": "https://...",
        }
        mock_sheets.ensure_spreadsheet_from_template.side_effect = Exception("Template error")

        with pytest.raises(Exception):
            project_storage.create_project(
                "Cleanup Test",
                template_ids={"info": "x", "report": "y", "calculations": "z"},
                parent_folder_id=None,
            )
        mock_sheets.delete_file.assert_called_once_with("new-folder-id")

    def test_copy_row_formatting_uses_paste_formula_and_paste_format(self, project_storage, mock_sheets):
        mock_sheets.sheets_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [
                {"properties": {"title": "Current period", "sheetId": 100}},
            ]
        }

        project_storage._copy_row_formatting(
            "spreadsheet-id", "Current period", source_row=3, target_row=5
        )

        mock_sheets.batch_update.assert_called_once()
        call_args = mock_sheets.batch_update.call_args[1]
        assert call_args["spreadsheet_id"] == "spreadsheet-id"

        requests = call_args["requests"]
        assert len(requests) == 2

        request_types = [r["copyPaste"]["pasteType"] for r in requests]
        assert "PASTE_FORMULA" in request_types
        assert "PASTE_FORMAT" in request_types

    def test_get_import_timesheet_formula_replaces_specialist_spreadsheet_id(self, mock_sheets):
        mock_sheets.is_initialized.return_value = True
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Formulas"}}
        mock_sheets.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Formula Name", "Formula"],
                ["Import specialist timesheet", '=IMPORTRANGE("SpecialistSpreadsheetID";"Sheet1!A:Z")'],
            ]
        }

        config = ConfigStorage(mock_sheets, "config-sheet-id")
        result = config.get_import_timesheet_formula("real-timesheet-123")

        assert '=IMPORTRANGE("https://docs.google.com/spreadsheets/d/real-timesheet-123";"Sheet1!A:Z")' == result

    def test_get_import_timesheet_formula_no_double_wrap_for_url_input(self, mock_sheets):
        mock_sheets.is_initialized.return_value = True
        mock_sheets.get_sheet_by_name.return_value = {"properties": {"title": "Formulas"}}
        mock_sheets.sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [
                ["Formula Name", "Formula"],
                ["Import specialist timesheet", '=IMPORTRANGE("SpecialistSpreadsheetID";"Sheet1!A:Z")'],
            ]
        }

        config = ConfigStorage(mock_sheets, "config-sheet-id")
        url_input = "https://docs.google.com/spreadsheets/d/1xSx-Uoi-kQQOrg"
        result = config.get_import_timesheet_formula(url_input)

        expected = f'=IMPORTRANGE("{url_input}";"Sheet1!A:Z")'
        assert expected == result

    def test_add_specialist_to_report_updates_formula_when_tab_exists(self, project_storage, mock_sheets):
        from feptm.models.specialist import Specialist

        mock_sheets.sheets_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "John Doe"}}],
        }

        spec = Specialist(name="John Doe", role="Dev", timesheet="ts-id")
        formula = '=IMPORTRANGE("ts-id";"Sheet1!A:Z")'

        project_storage.add_specialist_to_report("spreadsheet-id", spec, formula)

        mock_sheets.batch_update.assert_not_called()
        mock_sheets.update_range.assert_called_once_with(
            spreadsheet_id="spreadsheet-id",
            range_name="John Doe!A1",
            values=[[formula]],
            value_input_option="USER_ENTERED",
        )

    def test_add_specialist_to_report_creates_tab_and_writes_formula_when_absent(self, project_storage, mock_sheets):
        from feptm.models.specialist import Specialist

        mock_sheets.sheets_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [],
        }

        spec = Specialist(name="John Doe", role="Dev", timesheet="ts-id")
        formula = '=IMPORTRANGE("ts-id";"Sheet1!A:Z")'

        project_storage.add_specialist_to_report("spreadsheet-id", spec, formula)

        mock_sheets.batch_update.assert_called_once_with(
            spreadsheet_id="spreadsheet-id",
            requests=[{"addSheet": {"properties": {"title": "John Doe"}}}],
        )
        mock_sheets.update_range.assert_called_once_with(
            spreadsheet_id="spreadsheet-id",
            range_name="John Doe!A1",
            values=[[formula]],
            value_input_option="USER_ENTERED",
        )

    def test_archive_current_period_writes_period_column(self, project_storage, mock_sheets):
        from datetime import datetime, timezone

        from feptm.models.specialist import Specialist

        sp = Specialist(
            name="John", role="Dev", timesheet="ts-1",
            internal_rate="100", external_rate="120",
        )
        headers = ["Specialist", "Hours Worked", "Total Cost (USD)"]
        cp_values = [
            ["Specialist", "Hours Worked", "Total Cost (USD)"],
            ["John", "", ""],
        ]
        sheet_dict = {"properties": {"sheetId": 1}}
        cp_data = (cp_values, headers, sheet_dict)

        project_storage._list_sheet_titles = MagicMock(return_value=[])
        project_storage._read_current_period = MagicMock(return_value=cp_data)
        project_storage._sum_period_hours = MagicMock(return_value=10.0)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 31, tzinfo=timezone.utc)

        result = project_storage.archive_current_period(
            "spreadsheet-id", "Aug 2026", [sp], start, end,
        )

        assert result is True
        project_storage._sum_period_hours.assert_called_once_with(
            "ts-1", start, end, "Aug 2026"
        )

        update_call = mock_sheets.update_range.call_args
        values = update_call[1]["values"]

        assert len(values) == 3
        assert "Period" in values[0]
        period_idx = values[0].index("Period")
        cost_idx = values[0].index("Total Cost (USD)")
        hours_idx = values[0].index("Hours Worked")

        assert values[1][period_idx] == "Aug 2026"
        assert values[1][cost_idx] == 1200.0

        assert values[2][0] == ""
        assert values[2][hours_idx] == 10.0
        assert values[2][cost_idx] == 1200.0
        assert values[2][period_idx] == "Aug 2026"

    def test_archive_current_period_excludes_empty_timesheet(self, project_storage, mock_sheets):
        from datetime import datetime, timezone

        from feptm.models.specialist import Specialist

        sp_no_ts = Specialist(
            name="Jane", role="QA", timesheet="",
            internal_rate="80", external_rate="100",
        )
        sp_with_ts = Specialist(
            name="John", role="Dev", timesheet="ts-1",
            internal_rate="100", external_rate="120",
        )
        headers = ["Specialist", "Hours Worked", "Total Cost (USD)"]
        cp_values = [
            ["Specialist", "Hours Worked", "Total Cost (USD)"],
            ["Jane", "", ""],
            ["John", "", ""],
        ]
        sheet_dict = {"properties": {"sheetId": 1}}
        cp_data = (cp_values, headers, sheet_dict)

        project_storage._list_sheet_titles = MagicMock(return_value=[])
        project_storage._read_current_period = MagicMock(return_value=cp_data)
        project_storage._sum_period_hours = MagicMock(return_value=10.0)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 31, tzinfo=timezone.utc)

        result = project_storage.archive_current_period(
            "spreadsheet-id", "Aug 2026", [sp_no_ts, sp_with_ts], start, end,
        )

        assert result is True
        update_call = mock_sheets.update_range.call_args
        values = update_call[1]["values"]

        assert len(values) == 3
        assert "Jane" not in [row[0] for row in values[1:]]
        assert values[1][0] == "John"
        assert values[2][0] == ""

    def test_archive_current_period_excludes_zero_hours(self, project_storage, mock_sheets):
        from datetime import datetime, timezone

        from feptm.models.specialist import Specialist

        sp_zero = Specialist(
            name="Anna", role="Dev", timesheet="ts-1",
            internal_rate="100", external_rate="120",
        )
        sp_has_hours = Specialist(
            name="John", role="Dev", timesheet="ts-2",
            internal_rate="100", external_rate="120",
        )
        headers = ["Specialist", "Hours Worked", "Total Cost (USD)"]
        cp_values = [
            ["Specialist", "Hours Worked", "Total Cost (USD)"],
            ["Anna", "", ""],
            ["John", "", ""],
        ]
        sheet_dict = {"properties": {"sheetId": 1}}
        cp_data = (cp_values, headers, sheet_dict)

        project_storage._list_sheet_titles = MagicMock(return_value=[])
        project_storage._read_current_period = MagicMock(return_value=cp_data)

        def sum_hours(ts_id, s, e, p):
            return 0.0 if ts_id == "ts-1" else 10.0
        project_storage._sum_period_hours = MagicMock(side_effect=sum_hours)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 31, tzinfo=timezone.utc)

        result = project_storage.archive_current_period(
            "spreadsheet-id", "Aug 2026", [sp_zero, sp_has_hours], start, end,
        )

        assert result is True
        update_call = mock_sheets.update_range.call_args
        values = update_call[1]["values"]

        assert len(values) == 3
        assert "Anna" not in [row[0] for row in values[1:]]
        assert values[1][0] == "John"
        assert values[2][0] == ""


class TestSerialToDate:

    def test_accepts_dd_mm_yyyy(self):
        from feptm.storage.project_storage import _serial_to_date

        result = _serial_to_date("01.02.2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 1

    def test_rejects_yyyy_mm_dd(self):
        from feptm.storage.project_storage import _serial_to_date

        assert _serial_to_date("2026-02-01") is None

    def test_rejects_mm_dd_yyyy(self):
        from feptm.storage.project_storage import _serial_to_date

        assert _serial_to_date("02/01/2026") is None

    def test_accepts_numeric_serial(self):
        from feptm.storage.project_storage import _serial_to_date

        result = _serial_to_date(46054)   # 2026-02-01
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 1

    def test_rejects_empty(self):
        from feptm.storage.project_storage import _serial_to_date

        assert _serial_to_date("") is None
        assert _serial_to_date(None) is None


class TestParseDecimal:

    def test_returns_none_for_empty_string(self):
        from decimal import Decimal

        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal([""], 0, "John", "internal_rate")
        assert result is None

    def test_returns_none_for_whitespace(self):
        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["   "], 0, "John", "internal_rate")
        assert result is None

    def test_returns_none_for_invalid_string(self):
        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["abc"], 0, "John", "internal_rate")
        assert result is None

    def test_returns_zero_for_explicit_zero(self):
        from decimal import Decimal

        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["0"], 0, "John", "internal_rate")
        assert result is not None
        assert result == Decimal("0")

    def test_returns_decimal_for_valid_number(self):
        from decimal import Decimal

        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["100.50"], 0, "John", "internal_rate")
        assert result is not None
        assert result == Decimal("100.50")

    def test_returns_decimal_for_comma_format(self):
        from decimal import Decimal

        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["100,50"], 0, "John", "internal_rate")
        assert result is not None
        assert result == Decimal("100.50")

    def test_returns_none_for_missing_index(self):
        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["100"], None, "John", "internal_rate")
        assert result is None

    def test_returns_none_for_index_out_of_range(self):
        from feptm.storage.specialist_storage import _parse_decimal

        result = _parse_decimal(["100"], 5, "John", "internal_rate")
        assert result is None


class TestProjectServiceFacade:

    def test_create_project(self, project_service, mock_sheets):
        mock_sheets.create_drive_folder.return_value = {
            "folder_id": "folder-id",
            "folder_url": "https://...",
        }
        mock_sheets.ensure_spreadsheet_from_template.side_effect = [
            {"spreadsheet_id": f"{k}-id", "spreadsheet_url": "https://..."}
            for k in ["info", "report", "calculations"]
        ]

        result = project_service.create_project(
            "Test Project",
            template_ids={"info": "it", "report": "rt", "calculations": "ct"},
        )

        assert result["drive_folder_id"] == "folder-id"
        assert result["info_spreadsheet_id"] == "info-id"
        mock_sheets.update_sheet_data.assert_called_once()

    def test_sync_project_rates_success(self, project_service):
        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            project_info_spreadsheet_id="info-id",
            report_spreadsheet_id="report-id",
            calculations_spreadsheet_id="calc-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp1 = Specialist(
            name="John", role="Dev", internal_rate="100",
            external_rate="120", timesheet="ts-1",
        )
        sp2 = Specialist(
            name="Jane", role="QA", internal_rate="90",
            external_rate="110", timesheet="ts-2",
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 2
        assert len(specialists) == 2
        assert mock_add.call_count == 4
        assert mock_update.call_count == 4

    def test_sync_project_rates_empty_sheet(self, project_service):
        project_service._projects.get_project_metadata = MagicMock(
            return_value=Project(name="Empty")
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([], 0)
        )

        specialists, updated = project_service.sync_project_rates("empty-id")

        assert updated == 0
        assert specialists == []

    def test_sync_project_rates_auto_creates_timesheets(self, project_service):
        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test", drive_folder_id="folder-id",
            report_spreadsheet_id="r-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp = Specialist(
            name="Bob", role="Dev", internal_rate="50",
            external_rate="60", timesheet=None,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 0)
        )

        mock_create = MagicMock()
        mock_write = MagicMock()
        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._specialists.create_timesheet = mock_create
        project_service._specialists.update_timesheet_ids = mock_write
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        specialists, updated = project_service.sync_project_rates("test-id")

        assert updated == 0
        assert len(specialists) == 1
        mock_create.assert_called_once()
        mock_write.assert_called_once()
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_sync_rates_aborts_on_duplicate_names(self, project_service):

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            project_info_spreadsheet_id="info-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp1 = Specialist(
            name="John Smith", role="Dev", internal_rate="100",
            external_rate="120", timesheet="ts-1", row_index=2,
        )
        sp2 = Specialist(
            name="John Smith", role="QA", internal_rate="80",
            external_rate="100", timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            result = project_service.sync_project_rates("test-project-id")

        assert result == ([], 0)
        mock_log.error.assert_called_once()
        assert "Duplicate specialist names" in mock_log.error.call_args[0][0]
        assert "John Smith" in mock_log.error.call_args[0][1]
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_sync_aborts_on_invalid_dates(self, project_service):
        from unittest.mock import patch

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            project_info_spreadsheet_id="info-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp = Specialist(
            name="John", role="Dev", timesheet="ts-1",
            row_index=2, date=None,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 1)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.update_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            result = project_service.sync_project_specialists("test-project-id")

        assert result == ([], 0, 0)
        mock_log.error.assert_called_once()
        assert "invalid dates" in mock_log.error.call_args[0][0]
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_sync_no_collision_proceeds_normally(self, project_service):
        from decimal import Decimal

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp1 = Specialist(
            name="John", role="Dev", timesheet="ts-1", row_index=2,
            internal_rate=Decimal("100"), external_rate=Decimal("120"),
        )
        sp2 = Specialist(
            name="Jane", role="QA", timesheet="ts-2", row_index=3,
            internal_rate=Decimal("80"), external_rate=Decimal("100"),
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            result = project_service.sync_project_rates("test-project-id")

        assert result[1] == 2
        mock_log.error.assert_not_called()
        assert mock_add.call_count == 2
        assert mock_update.call_count == 2

    def test_sync_aborts_on_duplicate_names(self, project_service):

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            project_info_spreadsheet_id="info-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp1 = Specialist(
            name="Sam", role="Dev", timesheet="ts-1", row_index=2,
        )
        sp2 = Specialist(
            name="Sam", role="QA", timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.update_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            result = project_service.sync_project_specialists("test-project-id")

        assert result == ([], 0, 0)
        mock_log.error.assert_called_once()
        assert "Duplicate specialist names" in mock_log.error.call_args[0][0]
        assert "Sam" in mock_log.error.call_args[0][1]
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_close_period_matching_entries(self, project_service):
        from datetime import datetime, timezone

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
            calculations_spreadsheet_id="calc-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )
        sp = Specialist(
            name="John", role="Dev", timesheet="ts-1", row_index=2,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 1)
        )
        project_service._projects.close_period_in_timesheet = MagicMock(
            return_value=5
        )
        project_service._projects.archive_current_period = MagicMock(
            return_value=True
        )
        project_service._projects.protect_archived_sheet = MagicMock()
        project_service._projects.remove_stale_specialists = MagicMock(
            return_value=0
        )

        result = project_service.close_period(
            "test-id",
            "January 2026",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

        assert result.entries_updated == 5
        assert result.specialists_processed == 1
        assert result.report_archived is True
        assert result.calculations_archived is True
        assert project_service._projects.archive_current_period.call_count == 2
        assert project_service._projects.protect_archived_sheet.call_count == 2
        assert project_service._projects.remove_stale_specialists.call_count == 2
        project_service._projects.remove_stale_specialists.assert_any_call(
            "report-id", {"John"}
        )

    def test_close_period_no_matching_entries(self, project_service):
        from datetime import datetime, timezone

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )
        sp = Specialist(
            name="John", role="Dev", timesheet="ts-1", row_index=2,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 1)
        )
        project_service._projects.close_period_in_timesheet = MagicMock(
            return_value=0
        )
        project_service._projects.archive_current_period = MagicMock()
        project_service._projects.protect_archived_sheet = MagicMock()
        project_service._projects.remove_stale_specialists = MagicMock(
            return_value=0
        )

        result = project_service.close_period(
            "test-id",
            "Q2",
            datetime(2026, 4, 1, tzinfo=timezone.utc),
            datetime(2026, 6, 30, tzinfo=timezone.utc),
        )

        assert result.entries_updated == 0
        assert result.specialists_processed == 1
        assert result.report_archived is False
        assert result.calculations_archived is False
        project_service._projects.archive_current_period.assert_not_called()
        project_service._projects.protect_archived_sheet.assert_not_called()
        project_service._projects.remove_stale_specialists.assert_called_once_with(
            "report-id", {"John"}
        )

    def test_close_period_no_timesheet_specialists(self, project_service):
        from datetime import datetime, timezone

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test",
            drive_folder_id="folder-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )
        sp = Specialist(
            name="Jane", role="QA", timesheet=None, row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 1)
        )
        project_service._projects.close_period_in_timesheet = MagicMock()
        project_service._projects.archive_current_period = MagicMock()

        result = project_service.close_period(
            "test-id",
            "Q1",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert result.entries_updated == 0
        assert result.specialists_processed == 0
        project_service._projects.close_period_in_timesheet.assert_not_called()
        project_service._projects.archive_current_period.assert_not_called()

    def test_close_period_none_report_calculations(self, project_service):
        from datetime import datetime, timezone

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test",
            drive_folder_id="folder-id",
            report_spreadsheet_id=None,
            calculations_spreadsheet_id=None,
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )
        sp = Specialist(
            name="John", role="Dev", timesheet="ts-1", row_index=2,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp], 1)
        )
        project_service._projects.close_period_in_timesheet = MagicMock(
            return_value=3
        )
        project_service._projects.archive_current_period = MagicMock()
        project_service._projects.protect_archived_sheet = MagicMock()

        result = project_service.close_period(
            "test-id",
            "Q1",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 3, 31, tzinfo=timezone.utc),
        )

        assert result.entries_updated == 3
        assert result.report_archived is False
        assert result.calculations_archived is False
        project_service._projects.archive_current_period.assert_not_called()

    def test_sync_rates_invalid_rate_logs_error_and_skips(self, project_service):
        from decimal import Decimal

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp_valid = Specialist(
            name="John", role="Dev", internal_rate=Decimal("100"),
            external_rate=Decimal("120"), timesheet="ts-1", row_index=2,
        )
        sp_invalid = Specialist(
            name="Jane", role="QA", internal_rate=None,
            external_rate=Decimal("80"), timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp_valid, sp_invalid], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 1
        assert len(specialists) == 2
        mock_log.error.assert_called_once()
        error_args = mock_log.error.call_args[0]
        assert "Invalid rate for specialist '%s'" in error_args[0]
        assert "Jane" in error_args[1]
        assert "internal_rate='<empty>'" in error_args[0]
        assert "is not a valid number" in error_args[0]
        assert "Previous rate retained" in error_args[0]
        assert mock_add.call_count == 1
        assert mock_update.call_count == 1

    def test_sync_rates_both_rates_invalid(self, project_service):
        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp_invalid = Specialist(
            name="Jane", role="QA", internal_rate=None,
            external_rate=None, timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp_invalid], 1)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 0
        assert len(specialists) == 1
        assert mock_log.error.call_count == 2
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_sync_rates_one_rate_invalid(self, project_service):
        from decimal import Decimal

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp_invalid = Specialist(
            name="Jane", role="QA", internal_rate=Decimal("80"),
            external_rate=None, timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp_invalid], 1)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 0
        assert len(specialists) == 1
        mock_log.error.assert_called_once()
        error_args = mock_log.error.call_args[0]
        assert "external_rate='<empty>'" in error_args[0]
        assert "Jane" in error_args[1]
        mock_add.assert_not_called()
        mock_update.assert_not_called()

    def test_sync_rates_all_valid_no_error(self, project_service):
        from decimal import Decimal

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
            calculations_spreadsheet_id="calc-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp1 = Specialist(
            name="John", role="Dev", internal_rate=Decimal("100"),
            external_rate=Decimal("120"), timesheet="ts-1", row_index=2,
        )
        sp2 = Specialist(
            name="Jane", role="QA", internal_rate=Decimal("80"),
            external_rate=Decimal("100"), timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 2
        assert len(specialists) == 2
        mock_log.error.assert_not_called()
        assert mock_add.call_count == 4
        assert mock_update.call_count == 4

    def test_sync_rates_negative_rate_logs_error_and_skips(self, project_service):
        from decimal import Decimal

        from feptm.models.project import Project
        from feptm.models.specialist import Specialist

        project = Project(
            name="Test Project",
            drive_folder_id="folder-id",
            report_spreadsheet_id="report-id",
        )
        project_service._projects.get_project_metadata = MagicMock(
            return_value=project
        )

        sp_valid = Specialist(
            name="John", role="Dev", internal_rate=Decimal("100"),
            external_rate=Decimal("120"), timesheet="ts-1", row_index=2,
        )
        sp_negative = Specialist(
            name="Jane", role="QA", internal_rate=Decimal("-50"),
            external_rate=Decimal("80"), timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp_valid, sp_negative], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        with patch("feptm.timesheets.project_service.log") as mock_log:
            specialists, updated = project_service.sync_project_rates("test-project-id")

        assert updated == 1
        assert len(specialists) == 2
        mock_log.error.assert_called_once()
        error_args = mock_log.error.call_args[0]
        assert "Invalid rate for specialist '%s'" in error_args[0]
        assert "Jane" in error_args[1]
        assert "must be non-negative" in error_args[0]
        assert "Previous rate retained" in error_args[0]
        assert mock_add.call_count == 1
        assert mock_update.call_count == 1
