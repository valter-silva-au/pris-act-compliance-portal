"""Pytest configuration and fixtures for the WA PRIS Act Compliance Portal."""

import pytest
from fastapi.testclient import TestClient
from src.app.main import app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.

    Yields:
        TestClient: A test client for making requests to the application
    """
    with TestClient(app) as test_client:
        yield test_client
