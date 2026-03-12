"""Tests for the health check endpoint."""

import pytest


def test_health_check(client):
    """
    Test that the health check endpoint returns the expected response.

    Args:
        client: FastAPI test client fixture from conftest.py
    """
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_response_structure(client):
    """
    Test that the health check response has the correct structure.

    Args:
        client: FastAPI test client fixture from conftest.py
    """
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert isinstance(data["status"], str)
    assert data["status"] == "ok"
