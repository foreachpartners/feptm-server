"""Common test fixtures and configuration."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.abspath("src"))

from feptm.api.router import router

# Create a test app that uses the router
test_app = FastAPI()
test_app.include_router(router, prefix="/api")


@pytest.fixture
def client():
    """Create a test client for FastAPI application.
    
    Returns:
        TestClient: A FastAPI test client.
    """
    return TestClient(test_app)
