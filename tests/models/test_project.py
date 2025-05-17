"""Tests for project models."""

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from feptm.models.project import Project, ProjectMetaResponse


def test_project_model_creation():
    """Test Project model creation with valid data."""
    # Test data
    project_data = {
        "name": "Test Project"
    }
    
    # Create project instance
    project = Project(**project_data)
    
    # Assert fields
    assert project.name == "Test Project"
    assert project.drive_folder_id is None
    assert project.project_info_spreadsheet_id is None
    assert project.report_spreadsheet_id is None
    assert project.calculations_spreadsheet_id is None
    assert isinstance(project.created, datetime)
    assert isinstance(project.modified, datetime)


def test_project_model_creation_with_all_fields():
    """Test Project model creation with all fields."""
    # Test data with all fields
    now = datetime.now(UTC)
    project_data = {
        "name": "Full Project",
        "drive_folder_id": "folder-id-123",
        "project_info_spreadsheet_id": "sheet-id-123",
        "report_spreadsheet_id": "report-id-123",
        "calculations_spreadsheet_id": "calc-id-123",
        "created": now,
        "modified": now
    }
    
    # Create project instance
    project = Project(**project_data)
    
    # Assert fields
    assert project.name == "Full Project"
    assert project.drive_folder_id == "folder-id-123"
    assert project.project_info_spreadsheet_id == "sheet-id-123"
    assert project.report_spreadsheet_id == "report-id-123"
    assert project.calculations_spreadsheet_id == "calc-id-123"
    assert project.created == now
    assert project.modified == now


def test_project_model_computed_fields():
    """Test computed fields in Project model."""
    # Test data
    project_data = {
        "name": "Computed Fields Project",
        "drive_folder_id": "folder-id-456",
        "project_info_spreadsheet_id": "sheet-id-456",
        "report_spreadsheet_id": "report-id-456",
        "calculations_spreadsheet_id": "calc-id-456"
    }
    
    # Create project instance
    project = Project(**project_data)
    
    # Assert computed fields
    assert project.drive_folder_url == "https://drive.google.com/drive/folders/folder-id-456"
    assert project.project_info_spreadsheet_url == "https://docs.google.com/spreadsheets/d/sheet-id-456"
    assert project.report_spreadsheet_url == "https://docs.google.com/spreadsheets/d/report-id-456"
    assert project.calculations_spreadsheet_url == "https://docs.google.com/spreadsheets/d/calc-id-456"


def test_project_model_missing_required_fields():
    """Test Project model fails with missing required fields."""
    # Test data with missing required field (name)
    project_data = {}
    
    # Assert validation error
    with pytest.raises(ValidationError):
        Project(**project_data)


def test_project_meta_response_model():
    """Test ProjectMetaResponse model."""
    # Test data
    now = datetime.now(UTC)
    response_data = {
        "created": now,
        "modified": now,
        "drive_folder_id": "folder-id-789",
        "drive_folder_url": "https://drive.google.com/drive/folders/folder-id-789",
        "project_info_spreadsheet_id": "sheet-id-789",
        "project_info_spreadsheet_url": "https://docs.google.com/spreadsheets/d/sheet-id-789",
        "report_spreadsheet_id": "report-id-789",
        "report_spreadsheet_url": "https://docs.google.com/spreadsheets/d/report-id-789",
        "calculations_spreadsheet_id": "calc-id-789",
        "calculations_spreadsheet_url": "https://docs.google.com/spreadsheets/d/calc-id-789"
    }
    
    # Create response instance
    response = ProjectMetaResponse(**response_data)
    
    # Assert fields
    assert response.created == now
    assert response.modified == now
    assert response.drive_folder_id == "folder-id-789"
    assert response.drive_folder_url == "https://drive.google.com/drive/folders/folder-id-789"
    assert response.project_info_spreadsheet_id == "sheet-id-789"
    assert response.project_info_spreadsheet_url == "https://docs.google.com/spreadsheets/d/sheet-id-789"
    assert response.report_spreadsheet_id == "report-id-789"
    assert response.report_spreadsheet_url == "https://docs.google.com/spreadsheets/d/report-id-789"
    assert response.calculations_spreadsheet_id == "calc-id-789"
    assert response.calculations_spreadsheet_url == "https://docs.google.com/spreadsheets/d/calc-id-789"


def test_project_meta_response_missing_required_fields():
    """Test ProjectMetaResponse model fails with missing required fields."""
    # Test data with missing required fields
    response_data = {
        # Missing created and modified fields
    }
    
    # Assert validation error
    with pytest.raises(ValidationError):
        ProjectMetaResponse(**response_data) 