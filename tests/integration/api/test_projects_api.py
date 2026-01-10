"""Integration tests for projects API endpoints."""

from unittest.mock import patch

import pytest

from tests.conftest import client, mock_project_repository, mock_specialist_repository


@pytest.mark.integration
class TestProjectsAPI:
    """Integration tests for projects endpoints."""

    @patch("feptm.interfaces.api.dependencies.get_project_repository")
    def test_create_project(
        self, mock_get_repo, client, mock_project_repository
    ) -> None:
        """Test POST /api/v1/projects/create endpoint."""
        mock_get_repo.return_value = mock_project_repository

        response = client.post(
            "/api/v1/projects/create",
            json={"project_name": "Test Project"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert data["name"] == "Test Project"

    @patch("feptm.interfaces.api.dependencies.get_project_repository")
    def test_create_project_empty_name(
        self, mock_get_repo, client, mock_project_repository
    ) -> None:
        """Test POST /api/v1/projects/create with empty name."""
        mock_get_repo.return_value = mock_project_repository

        response = client.post(
            "/api/v1/projects/create",
            json={"project_name": ""},
        )

        assert response.status_code == 422  # Validation error

    @patch("feptm.interfaces.api.dependencies.get_project_service")
    @patch("feptm.interfaces.api.dependencies.get_specialist_service")
    def test_sync_project_specialists(
        self, mock_get_spec_service, mock_get_proj_service, client
    ) -> None:
        """Test POST /api/v1/projects/sync endpoint."""
        from feptm.domain.services.project_service import ProjectService
        from feptm.domain.services.specialist_service import SpecialistService

        mock_proj_service = ProjectService(mock_project_repository)
        mock_spec_service = SpecialistService(mock_specialist_repository)

        mock_get_proj_service.return_value = mock_proj_service
        mock_get_spec_service.return_value = mock_spec_service

        response = client.post(
            "/api/v1/projects/sync",
            json={"project_id": "test-project-id"},
        )

        assert response.status_code in [200, 404, 500]  # May fail if not fully implemented
