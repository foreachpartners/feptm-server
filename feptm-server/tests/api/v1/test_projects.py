"""Tests for project API endpoints."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

MOCK_CREATE_RESULT = {
    "drive_folder_id": "test-folder-id",
    "drive_folder_url": "https://drive.google.com/drive/folders/test-folder-id",
    "info_spreadsheet_id": "test-info-id",
    "info_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-info-id",
    "report_spreadsheet_id": "test-report-id",
    "report_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-report-id",
    "calculations_spreadsheet_id": "test-calc-id",
    "calculations_spreadsheet_url": "https://docs.google.com/spreadsheets/d/test-calc-id",
}

MOCK_SYNC_RESULT = ([], 5, 2)


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_create_project_success(mock_get_service, mock_settings, client: TestClient):
    mock_service = MagicMock()
    mock_service.create_project.return_value = MOCK_CREATE_RESULT
    mock_get_service.return_value = mock_service

    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "info-tmpl"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "report-tmpl"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "calc-tmpl"
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = None

    response = client.post(
        "/api/projects/create", json={"project_name": "Test Project"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["drive_folder_id"] == "test-folder-id"
    assert data["project_info_spreadsheet_id"] == "test-info-id"


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_create_project_missing_config(
    mock_get_service, mock_settings, client: TestClient
):
    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = None
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = None
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = None

    response = client.post("/api/projects/create", json={"project_name": "Test"})

    assert response.status_code == 500


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_create_project_service_error(
    mock_get_service, mock_settings, client: TestClient
):
    mock_service = MagicMock()
    mock_service.create_project.side_effect = Exception("Service failure")
    mock_get_service.return_value = mock_service

    mock_settings.GOOGLE_PROJECT_INFO_TEMPLATE_ID = "x"
    mock_settings.GOOGLE_PROJECT_REPORT_TEMPLATE_ID = "y"
    mock_settings.GOOGLE_PROJECT_CALCULATIONS_TEMPLATE_ID = "z"
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = None

    response = client.post("/api/projects/create", json={"project_name": "Test"})
    assert response.status_code == 500


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_sync_project_specialists_success(
    mock_get_service, mock_settings, client: TestClient
):
    mock_service = MagicMock()
    mock_service.sync_project_specialists.return_value = MOCK_SYNC_RESULT
    mock_get_service.return_value = mock_service

    mock_settings.GOOGLE_TIMESHEET_TEMPLATE_ID = "ts-tmpl"

    response = client.post("/api/projects/sync", json={"project_id": "test-project-id"})

    assert response.status_code == 200
    data = response.json()
    assert data["specialists_found"] == 5
    assert data["specialists_created"] == 2


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_sync_missing_template_config(
    mock_get_service, mock_settings, client: TestClient
):
    mock_settings.GOOGLE_TIMESHEET_TEMPLATE_ID = None

    response = client.post("/api/projects/sync", json={"project_id": "test-id"})
    assert response.status_code == 500


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_sync_service_error(mock_get_service, mock_settings, client: TestClient):
    mock_service = MagicMock()
    mock_service.sync_project_specialists.side_effect = Exception("Sync failure")
    mock_get_service.return_value = mock_service

    mock_settings.GOOGLE_TIMESHEET_TEMPLATE_ID = "ts-tmpl"

    response = client.post("/api/projects/sync", json={"project_id": "test-id"})
    assert response.status_code == 500


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_sync_project_rates_success(mock_get_service, client: TestClient):
    from feptm.models.specialist import Specialist

    sp = Specialist(
        name="John", role="Dev", internal_rate="100",
        external_rate="120", timesheet="ts-1",
    )
    mock_service = MagicMock()
    mock_service.sync_project_rates.return_value = ([sp], 1)
    mock_get_service.return_value = mock_service

    response = client.post(
        "/api/projects/sync-rates", json={"project_id": "test-project-id"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["specialists_updated"] == 1
    assert data["project_id"] == "test-project-id"
    assert len(data["specialists"]) == 1
    assert data["specialists"][0]["name"] == "John"
    assert data["specialists"][0]["internal_rate"] == "100"
    assert data["specialists"][0]["external_rate"] == "120"


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_sync_project_rates_service_error(
    mock_get_service, client: TestClient,
):
    mock_service = MagicMock()
    mock_service.sync_project_rates.side_effect = Exception("Rate sync failure")
    mock_get_service.return_value = mock_service

    response = client.post(
        "/api/projects/sync-rates", json={"project_id": "test-id"}
    )
    assert response.status_code == 500


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_list_projects_success(mock_get_service, mock_settings, client: TestClient):
    mock_service = MagicMock()
    mock_service.list_projects.return_value = [
        {"name": "Alpha", "id": "folder-a"},
        {"name": "Beta", "id": "folder-b"},
    ]
    mock_get_service.return_value = mock_service
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = "parent-folder"

    response = client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert len(data["projects"]) == 2
    assert data["projects"][0]["name"] == "Alpha"
    assert data["projects"][0]["drive_folder_id"] == "folder-a"
    assert data["projects"][1]["name"] == "Beta"


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_list_projects_empty(mock_get_service, mock_settings, client: TestClient):
    mock_service = MagicMock()
    mock_service.list_projects.return_value = []
    mock_get_service.return_value = mock_service
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = "parent-folder"

    response = client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == []


@patch("feptm.api.v1.projects.settings")
def test_list_projects_missing_config(mock_settings, client: TestClient):
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = None

    response = client.get("/api/projects")

    assert response.status_code == 500


@patch("feptm.api.v1.projects.settings")
@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_list_projects_service_error(mock_get_service, mock_settings, client: TestClient):
    mock_service = MagicMock()
    mock_service.list_projects.side_effect = Exception("Drive failure")
    mock_get_service.return_value = mock_service
    mock_settings.GOOGLE_PROJECTS_FOLDER_ID = "parent-folder"

    response = client.get("/api/projects")

    assert response.status_code == 500
