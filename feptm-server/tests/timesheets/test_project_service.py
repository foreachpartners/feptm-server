"""Tests for project storage and facade."""

from unittest.mock import MagicMock

import pytest

from feptm.models.project import Project
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
