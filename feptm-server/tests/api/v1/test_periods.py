"""Tests for period API endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from feptm.models.payment_period import ClosePeriodResponse


def _response():
    return ClosePeriodResponse(
        project_id="test-project-id",
        period_name="January 2026",
        entries_updated=10,
        specialists_processed=3,
        report_archived=True,
        calculations_archived=True,
    )


@patch("feptm.api.v1.periods.get_timesheet_project_service")
def test_close_payment_period_success(mock_get_service, client: TestClient):
    mock_service = MagicMock()
    mock_service.close_period.return_value = _response()
    mock_get_service.return_value = mock_service

    response = client.put(
        "/api/periods",
        json={
            "project_id": "test-project-id",
            "period_name": "January 2026",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "test-project-id"
    assert data["period_name"] == "January 2026"
    assert data["entries_updated"] == 10
    assert data["report_archived"] is True
    assert data["calculations_archived"] is True


@patch("feptm.api.v1.periods.get_timesheet_project_service")
def test_close_payment_period_no_entries(mock_get_service, client: TestClient):
    mock_service = MagicMock()
    mock_service.close_period.return_value = ClosePeriodResponse(
        project_id="test",
        period_name="Q1",
        entries_updated=0,
        specialists_processed=2,
        report_archived=False,
        calculations_archived=False,
    )
    mock_get_service.return_value = mock_service

    response = client.put(
        "/api/periods",
        json={
            "project_id": "test",
            "period_name": "Q1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["entries_updated"] == 0
    assert data["report_archived"] is False
    assert data["calculations_archived"] is False


def test_close_payment_period_empty_period_name(client: TestClient):
    response = client.put(
        "/api/periods",
        json={
            "project_id": "test",
            "period_name": "",
        },
    )
    assert response.status_code == 422


def test_close_payment_period_missing_fields(client: TestClient):
    response = client.put(
        "/api/periods",
        json={"project_id": "test"},
    )
    assert response.status_code == 422


@patch("feptm.api.v1.periods.get_timesheet_project_service")
def test_close_payment_period_service_error(mock_get_service, client: TestClient):
    mock_service = MagicMock()
    mock_service.close_period.side_effect = Exception("GSheet error")
    mock_get_service.return_value = mock_service

    response = client.put(
        "/api/periods",
        json={
            "project_id": "test",
            "period_name": "Q1",
        },
    )
    assert response.status_code == 500
