"""Tests for project storage and facade."""

from unittest.mock import MagicMock

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

    def test_sync_resolves_display_names_on_collision(self, project_service):
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

        project_service.sync_project_rates("test-project-id")

        assert sp1.display_name == "John Smith (2)"
        assert sp2.display_name == "John Smith (3)"

    def test_sync_no_collision_preserves_name(self, project_service):
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
        )
        sp2 = Specialist(
            name="Jane", role="QA", timesheet="ts-2", row_index=3,
        )
        project_service._specialists.list_from_sheet = MagicMock(
            return_value=([sp1, sp2], 2)
        )

        mock_add = MagicMock()
        mock_update = MagicMock()
        project_service._projects.add_specialist_to_report = mock_add
        project_service._projects.sync_rates_to_current_period = mock_update

        project_service.sync_project_rates("test-project-id")

        assert sp1.display_name == "John"
        assert sp2.display_name == "Jane"

    def test_sync_duplicate_names_passes_display_name_to_storage(self, project_service):
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
        project_service._projects.sync_rates_to_current_period = mock_update

        project_service.sync_project_rates("test-project-id")

        assert mock_add.call_count == 2
        assert mock_add.call_args_list[0][0][1].display_name == "Sam (2)"
        assert mock_add.call_args_list[1][0][1].display_name == "Sam (3)"

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
