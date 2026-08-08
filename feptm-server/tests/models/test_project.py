"""Tests for project models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from feptm.models.project import Project, ProjectMetaResponse


def test_project_model_creation():
    project = Project(name="Test Project")
    assert project.name == "Test Project"
    assert project.drive_folder_id is None
    assert project.project_info_spreadsheet_id is None
    assert project.report_spreadsheet_id is None
    assert project.calculations_spreadsheet_id is None
    assert isinstance(project.created, datetime)
    assert isinstance(project.modified, datetime)


def test_project_model_creation_with_all_fields():
    now = datetime.now(UTC)
    project = Project(
        name="Full Project",
        drive_folder_id="folder-id-123",
        project_info_spreadsheet_id="sheet-id-123",
        report_spreadsheet_id="report-id-123",
        calculations_spreadsheet_id="calc-id-123",
        created=now,
        modified=now,
    )
    assert project.name == "Full Project"
    assert project.drive_folder_id == "folder-id-123"
    assert project.project_info_spreadsheet_id == "sheet-id-123"
    assert project.report_spreadsheet_id == "report-id-123"
    assert project.calculations_spreadsheet_id == "calc-id-123"
    assert project.created == now
    assert project.modified == now


def test_project_model_no_computed_fields():
    """URL computation moved to UrlPattern; models are plain data."""
    project = Project(
        name="Test",
        drive_folder_id="folder-id-456",
        project_info_spreadsheet_id="sheet-id-456",
    )
    assert project.drive_folder_id == "folder-id-456"
    assert not hasattr(project, "drive_folder_url")


def test_project_model_missing_required_fields():
    with pytest.raises(ValidationError):
        Project()


def test_project_meta_response_model():
    now = datetime.now(UTC)
    response = ProjectMetaResponse(
        created=now,
        modified=now,
        drive_folder_id="folder-id-789",
        drive_folder_url="https://drive.google.com/drive/folders/folder-id-789",
        project_info_spreadsheet_id="sheet-id-789",
        project_info_spreadsheet_url="https://docs.google.com/spreadsheets/d/sheet-id-789",
        report_spreadsheet_id="report-id-789",
        report_spreadsheet_url="https://docs.google.com/spreadsheets/d/report-id-789",
        calculations_spreadsheet_id="calc-id-789",
        calculations_spreadsheet_url="https://docs.google.com/spreadsheets/d/calc-id-789",
    )
    assert response.created == now
    assert response.drive_folder_id == "folder-id-789"


def test_project_meta_response_missing_required_fields():
    with pytest.raises(ValidationError):
        ProjectMetaResponse()
