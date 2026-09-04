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


MOCK_CARD_DATA = {
    "name": "Acme",
    "drive_folder_id": "folder-1",
    "project_id": "info-id",
    "info_spreadsheet_id": "info-id",
    "report_spreadsheet_id": "report-id",
    "calculations_spreadsheet_id": "calc-id",
    "timesheets": [],
}


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_success_no_timesheets(
    mock_get_service, client: TestClient
):
    mock_service = MagicMock()
    mock_service.get_project_card.return_value = MOCK_CARD_DATA
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/folder-1/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Acme"
    assert data["drive_folder_id"] == "folder-1"
    assert data["project_id"] == "info-id"
    assert data["timesheets"] == []
    assert data["tables"]["project_info"]["spreadsheet_id"] == "info-id"
    assert data["tables"]["project_info"]["url"] == (
        "https://docs.google.com/spreadsheets/d/info-id"
    )
    assert data["tables"]["general_expenses"]["spreadsheet_id"] == "report-id"
    assert data["tables"]["payment_distribution"]["spreadsheet_id"] == "calc-id"
    assert data["tables"]["project_info"]["label"] == "Project info / Team"
    assert data["tables"]["general_expenses"]["label"] == "General Expenses"
    assert data["tables"]["payment_distribution"]["label"] == "Payment Distribution"


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_timesheets_sorted_case_insensitive(
    mock_get_service, client: TestClient
):
    card_data = {
        **MOCK_CARD_DATA,
        "timesheets": [
            {"name": "Time Tracking for alice. Project Acme", "id": "ts-alice"},
            {"name": "Time Tracking for Bob. Project Acme", "id": "ts-bob"},
        ],
    }
    mock_service = MagicMock()
    mock_service.get_project_card.return_value = card_data
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/folder-1/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["timesheets"]) == 2
    assert data["timesheets"][0]["name"] == "Time Tracking for alice. Project Acme"
    assert data["timesheets"][1]["name"] == "Time Tracking for Bob. Project Acme"


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_timesheet_not_in_team(
    mock_get_service, client: TestClient
):
    card_data = {
        **MOCK_CARD_DATA,
        "timesheets": [
            {"name": "Time Tracking for Ghost. Project Acme", "id": "ts-ghost"},
        ],
    }
    mock_service = MagicMock()
    mock_service.get_project_card.return_value = card_data
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/folder-1/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["timesheets"]) == 1
    assert data["timesheets"][0]["name"] == "Time Tracking for Ghost. Project Acme"
    assert data["timesheets"][0]["spreadsheet_id"] == "ts-ghost"
    assert data["timesheets"][0]["url"] == (
        "https://docs.google.com/spreadsheets/d/ts-ghost"
    )


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_folder_not_found(
    mock_get_service, client: TestClient
):
    from feptm.core.exceptions import ProjectFolderNotFoundError

    mock_service = MagicMock()
    mock_service.get_project_card.side_effect = ProjectFolderNotFoundError(
        "bad-folder"
    )
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/bad-folder/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project folder not found."


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_missing_spreadsheet(
    mock_get_service, client: TestClient
):
    from feptm.core.exceptions import ProjectSpreadsheetNotFoundError

    mock_service = MagicMock()
    mock_service.get_project_card.side_effect = ProjectSpreadsheetNotFoundError(
        "Acme - General Expenses"
    )
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/folder-1/")

    assert response.status_code == 404
    assert "Acme - General Expenses" in response.json()["detail"]


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_no_side_effects(
    mock_get_service, client: TestClient
):
    mock_service = MagicMock()
    mock_service.get_project_card.return_value = MOCK_CARD_DATA
    mock_get_service.return_value = mock_service

    client.get("/api/projects/folder-1/")

    mock_service.create_project.assert_not_called()
    mock_service.sync_project_specialists.assert_not_called()
    mock_service.sync_project_rates.assert_not_called()
    mock_service.close_period.assert_not_called()


@patch("feptm.api.v1.projects.get_timesheet_project_service")
def test_get_project_card_project_id_matches_sync(
    mock_get_service, client: TestClient
):
    card_data = {
        **MOCK_CARD_DATA,
        "project_id": "sync-target-id",
        "info_spreadsheet_id": "sync-target-id",
    }
    mock_service = MagicMock()
    mock_service.get_project_card.return_value = card_data
    mock_get_service.return_value = mock_service

    response = client.get("/api/projects/folder-1/")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "sync-target-id"
    assert data["project_id"] == data["tables"]["project_info"]["spreadsheet_id"]
