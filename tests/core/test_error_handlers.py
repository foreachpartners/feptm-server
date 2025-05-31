"""Tests for error handling."""

import pytest
from fastapi.testclient import TestClient

from feptm.core.exceptions import FEPTMError, ResourceNotFoundError, ValidationError
from feptm.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_custom_error_handling(client):
    """Test handling of application-specific errors."""

    @app.get("/test/error")
    def raise_error():
        raise FEPTMError(
            message="Test error",
            code="test_error",
            details={"test": "value"},
        )

    response = client.get("/test/error")
    assert response.status_code == 500

    data = response.json()
    assert data["error"]["code"] == "test_error"
    assert data["error"]["message"] == "Test error"
    assert data["error"]["details"] == {"test": "value"}


def test_validation_error_handling(client):
    """Test handling of validation errors."""

    @app.get("/test/validation")
    def raise_validation_error():
        raise ValidationError(
            message="Invalid input",
            field="test_field",
            value="invalid",
        )

    response = client.get("/test/validation")
    assert response.status_code == 500

    data = response.json()
    assert data["error"]["code"] == "validation_error"
    assert "Invalid input" in data["error"]["message"]
    assert data["error"]["details"]["field"] == "test_field"


def test_not_found_error_handling(client):
    """Test handling of not found errors."""

    @app.get("/test/not-found")
    def raise_not_found():
        raise ResourceNotFoundError(
            resource_type="Test",
            resource_id="123",
        )

    response = client.get("/test/not-found")
    assert response.status_code == 500

    data = response.json()
    assert data["error"]["code"] == "not_found"
    assert "not found" in data["error"]["message"].lower()
    assert data["error"]["details"]["resource_type"] == "Test"
    assert data["error"]["details"]["resource_id"] == "123"
