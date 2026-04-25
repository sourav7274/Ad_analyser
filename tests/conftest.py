"""Shared pytest fixtures for the FastAPI Ad Analyser test suite."""

import os
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

# Must be set before app modules are imported so the Settings singleton
# and the rate limiter both pick up the test value.
os.environ["RATE_LIMIT"] = "10000/minute"

from app.main import app  # noqa: E402

MOCK_RESULT = {
    "impulse_score": 0.75,
    "trust_score": 0.5,
    "conversion_probability": 0.6,
    "model_version": "v1.0-mock",
}


@pytest.fixture(scope="session", autouse=True)
def mock_predict_conversion():
    """Patch app.services.predict_conversion for the entire test session.

    Individual tests may override this with their own local patch — local
    patches take precedence over this session-scoped one.
    """
    with patch("app.services.predict_conversion", return_value=MOCK_RESULT) as mock:
        yield mock


@pytest.fixture(scope="session")
def client():
    """Return a TestClient wrapping the FastAPI app.

    Used primarily by property-based tests (Task 8).  The existing example
    tests in test_health.py and test_analyse.py create their own local
    TestClient instances.
    """
    with TestClient(app) as test_client:
        yield test_client
