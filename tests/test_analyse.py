"""Unit tests for the POST /api/v1/analyse-ad endpoint (app/routes.py).

All tests patch `app.services.predict_conversion` to avoid the real model's
2-4 second sleep and to control the return value / raised exception.
The TestClient and mock are set up locally in this file because conftest.py
does not exist yet (created in Task 7.1).
"""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from app.main import app

MOCK_RESULT = {
    "impulse_score": 0.75,
    "trust_score": 0.5,
    "conversion_probability": 0.6,
    "model_version": "v1.0-mock",
}

ANALYSE_URL = "/api/v1/analyse-ad"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_ad_copy():
    """POST valid payload → HTTP 200, success: true, all four prediction fields
    present with correct types, non-empty request_id."""
    with patch("app.services.predict_conversion", return_value=MOCK_RESULT):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={"ad_copy": "Buy our amazing product today!"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["request_id"] != ""

    data = body["data"]
    assert isinstance(data["impulse_score"], float)
    assert isinstance(data["trust_score"], float)
    assert isinstance(data["conversion_probability"], float)
    assert isinstance(data["model_version"], str)


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


def test_missing_ad_copy():
    """POST {} → HTTP 422 (missing required field)."""
    with patch("app.services.predict_conversion", return_value=MOCK_RESULT):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={})

    assert response.status_code == 422


def test_empty_ad_copy():
    """POST {"ad_copy": ""} → HTTP 422 (min_length=1 violated)."""
    with patch("app.services.predict_conversion", return_value=MOCK_RESULT):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={"ad_copy": ""})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Business-logic errors
# ---------------------------------------------------------------------------


def test_short_ad_copy():
    """POST {"ad_copy": "short"} → HTTP 400, success: false, non-empty request_id.

    The real model raises ValueError for strings < 10 chars.  Since we patch
    predict_conversion, we make the patch raise ValueError so the service maps
    it to HTTPException(400).
    """
    with patch(
        "app.services.predict_conversion",
        side_effect=ValueError("Input text must be at least 10 characters for analysis."),
    ):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={"ad_copy": "short"})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["request_id"] != ""


def test_runtime_error():
    """POST {"ad_copy": "force_runtime_error trigger"} → HTTP 500, success: false,
    non-empty request_id."""
    with patch(
        "app.services.predict_conversion",
        side_effect=RuntimeError("Simulated model runtime failure."),
    ):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={"ad_copy": "force_runtime_error trigger"})

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["request_id"] != ""


# ---------------------------------------------------------------------------
# Unexpected / bare Exception
# ---------------------------------------------------------------------------


def test_unexpected_error():
    """Patch AdAnalyserService.analyse_ad to raise a bare Exception → HTTP 500,
    body does NOT contain a stack trace."""
    async_mock = AsyncMock(side_effect=Exception("boom"))

    with patch("app.services.AdAnalyserService.analyse_ad", async_mock):
        with TestClient(app) as client:
            response = client.post(ANALYSE_URL, json={"ad_copy": "Some valid ad copy here"})

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    # Ensure no raw traceback / exception detail leaks into the response body
    response_text = response.text
    assert "Traceback" not in response_text
    assert "boom" not in response_text
