"""
Pytest configuration and shared fixtures for backend tests.

This module provides:
- TestClient fixture for API testing
- Fresh activities database fixture to ensure test isolation
"""

import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
from src.app import app, activities


@pytest.fixture
def client():
    """
    Provides a TestClient instance for testing the FastAPI application.
    
    Returns:
        TestClient: An HTTP client for making requests to the test app.
    """
    return TestClient(app)


@pytest.fixture
def fresh_activities(monkeypatch):
    """
    Provides a fresh copy of the activities database for each test.
    
    This fixture deep-copies the original activities dictionary before each test
    and patches the app's activities to use the copy. This ensures that:
    - Tests do not interfere with each other
    - Modifications to participant lists don't persist between tests
    - Each test starts with a known, consistent state
    
    Args:
        monkeypatch: pytest's monkeypatch fixture for modifying module state
    
    Yields:
        dict: A deep copy of the activities database
    """
    original_activities = deepcopy(activities)
    monkeypatch.setattr("src.app.activities", original_activities)
    yield original_activities
