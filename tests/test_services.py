"""Unit tests for AdAnalyserService (app/services.py).

All tests patch `app.services.predict_conversion` to avoid the real model's
2-4 second sleep and to control the return value / raised exception.
Tests use asyncio.run() to drive the async service method without requiring
pytest-asyncio.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas import PredictionData
from app.services import AdAnalyserService

MOCK_RESULT = {
    "impulse_score": 0.75,
    "trust_score": 0.5,
    "conversion_probability": 0.6,
    "model_version": "v1.0-mock",
}


def _make_service() -> AdAnalyserService:
    """Return a service backed by a real (small) thread-pool executor."""
    return AdAnalyserService(executor=ThreadPoolExecutor(max_workers=1))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_analyse_ad_happy_path():
    """Mock returns a valid dict → service returns a PredictionData instance."""
    service = _make_service()

    with patch("app.services.predict_conversion", return_value=MOCK_RESULT):
        result = asyncio.run(service.analyse_ad("Buy our amazing product!", "req-001"))

    assert isinstance(result, PredictionData)
    assert result.impulse_score == 0.75
    assert result.trust_score == 0.5
    assert result.conversion_probability == 0.6
    assert result.model_version == "v1.0-mock"


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def test_analyse_ad_value_error_raises_http_400():
    """ValueError from predict_conversion → HTTPException with status 400."""
    service = _make_service()

    with patch(
        "app.services.predict_conversion", side_effect=ValueError("ad_copy too short")
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.analyse_ad("short", "req-002"))

    assert exc_info.value.status_code == 400
    assert "ad_copy too short" in exc_info.value.detail


def test_analyse_ad_runtime_error_raises_http_500():
    """RuntimeError from predict_conversion → HTTPException with status 500."""
    service = _make_service()

    with patch(
        "app.services.predict_conversion",
        side_effect=RuntimeError("model inference failed"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.analyse_ad("force_runtime_error trigger", "req-003"))

    assert exc_info.value.status_code == 500
    assert "model inference failed" in exc_info.value.detail


def test_analyse_ad_unexpected_exception_raises_http_500_generic():
    """Unexpected Exception → HTTPException with status 500 and generic message."""
    service = _make_service()

    with patch(
        "app.services.predict_conversion",
        side_effect=Exception("something totally unexpected"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.analyse_ad("some ad copy here", "req-004"))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "An unexpected error occurred."


def test_analyse_ad_timeout_raises_http_504():
    """Model call exceeding MODEL_TIMEOUT → HTTPException with status 504."""
    import time
    from app import config as config_module

    service = _make_service()

    # Patch timeout to 0.1s and make predict_conversion sleep longer
    original_timeout = config_module.settings.model_timeout
    config_module.settings.model_timeout = 1  # 1 second timeout

    def slow_predict(ad_text):
        time.sleep(5)  # longer than timeout
        return {}

    try:
        with patch("app.services.predict_conversion", side_effect=slow_predict):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(service.analyse_ad("some long ad copy here", "req-005"))
        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail
    finally:
        config_module.settings.model_timeout = original_timeout
