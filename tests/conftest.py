"""Common test fixtures and configuration."""

import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath("src"))

from feptm.api.router import router

# Create a test app that uses the router
test_app = FastAPI()
test_app.include_router(router, prefix="/api")


@pytest.fixture
def client() -> TestClient:
    """Create a test client for FastAPI application.

    Returns:
        TestClient: A FastAPI test client for testing endpoints.
    """
    return TestClient(test_app)


@pytest.fixture
def mock_pygsheets_client() -> MagicMock:
    """Mock pygsheets client for testing.

    Returns:
        MagicMock: Configured pygsheets client mock.
    """
    mock_gc = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()

    # Configure mock spreadsheet
    mock_spreadsheet.id = "test-spreadsheet-id"
    mock_spreadsheet.worksheet_by_title.return_value = mock_worksheet
    mock_spreadsheet.add_worksheet.return_value = mock_worksheet

    # Configure mock worksheet
    mock_worksheet.get_values.return_value = []
    mock_worksheet.update_values.return_value = None
    mock_worksheet.update_value.return_value = None
    mock_worksheet.cell.return_value = MagicMock(formula="", value="")

    # Configure mock client
    mock_gc.open_by_key.return_value = mock_spreadsheet
    mock_gc.create.return_value = mock_spreadsheet
    mock_gc.copy.return_value = mock_spreadsheet
    mock_gc.drive = MagicMock()

    return mock_gc


@pytest.fixture
def mock_pygsheets_client_wrapper(mock_pygsheets_client: MagicMock) -> MagicMock:
    """Mock PygSheetsClient wrapper.

    Args:
        mock_pygsheets_client: Mock pygsheets client

    Returns:
        MagicMock: Configured PygSheetsClient mock
    """
    with patch("feptm.adapters.google.auth.authorize_pygsheets") as mock_auth:
        mock_auth.return_value = mock_pygsheets_client
        yield mock_pygsheets_client


@pytest.fixture
def mock_project_repository() -> MagicMock:
    """Mock ProjectRepository for testing.

    Returns:
        MagicMock: Configured ProjectRepository mock.
    """
    mock_repo = MagicMock()
    mock_repo.create.return_value = "test-project-id"
    mock_repo.get_by_id.return_value = MagicMock(
        name="Test Project",
        created=MagicMock(),
        team=[],
    )
    mock_repo.save.return_value = None
    return mock_repo


@pytest.fixture
def mock_specialist_repository() -> MagicMock:
    """Mock SpecialistRepository for testing.

    Returns:
        MagicMock: Configured SpecialistRepository mock.
    """
    mock_repo = MagicMock()
    mock_repo.create_timesheet.return_value = "test-timesheet-id"
    mock_repo.get_by_project.return_value = []
    mock_repo.update_team_sheet.return_value = None
    return mock_repo


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing.

    Returns:
        Dict: Sample project with all required fields.
    """
    return {
        "name": "Test Project",
        "project_id": "test-project-id-123",
    }


@pytest.fixture
def sample_specialist_data() -> List[Dict[str, Any]]:
    """Sample specialist data for testing.

    Returns:
        List: Sample specialists with required fields.
    """
    return [
        {
            "name": "John Doe",
            "role": "Developer",
            "internal_rate": "12",
            "external_rate": "14",
            "start_date": "2025-01-01",
            "timesheet_id": "timesheet-john-123",
        },
        {
            "name": "Jane Smith",
            "role": "QA",
            "internal_rate": "15",
            "external_rate": "20",
            "start_date": "2025-01-01",
            "timesheet_id": "timesheet-jane-456",
        },
    ]
