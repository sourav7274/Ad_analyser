"""Unit tests for Pydantic schema validation (Requirements 4.1, 4.2)."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalyseRequest,
    AnalyseResponse,
    ErrorDetail,
    ErrorResponse,
    PredictionData,
)


# ---------------------------------------------------------------------------
# AnalyseRequest
# ---------------------------------------------------------------------------


def test_analyse_request_rejects_empty_string():
    """AnalyseRequest must reject an empty ad_copy (min_length=1 constraint)."""
    with pytest.raises(ValidationError):
        AnalyseRequest(ad_copy="")


def test_analyse_request_accepts_single_character():
    """AnalyseRequest must accept a single-character string (passes Pydantic validation)."""
    req = AnalyseRequest(ad_copy="x")
    assert req.ad_copy == "x"


# ---------------------------------------------------------------------------
# AnalyseResponse
# ---------------------------------------------------------------------------


def test_analyse_response_serialises_to_expected_shape():
    """AnalyseResponse must serialise to the expected JSON envelope."""
    data = PredictionData(
        impulse_score=0.75,
        trust_score=0.5,
        conversion_probability=0.6,
        model_version="v1.0-mock",
    )
    response = AnalyseResponse(request_id="abc-123", data=data)
    serialised = response.model_dump()

    assert serialised["success"] is True
    assert serialised["request_id"] == "abc-123"
    assert serialised["data"]["impulse_score"] == 0.75
    assert serialised["data"]["trust_score"] == 0.5
    assert serialised["data"]["conversion_probability"] == 0.6
    assert serialised["data"]["model_version"] == "v1.0-mock"


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------


def test_error_response_serialises_to_expected_shape():
    """ErrorResponse must serialise to the expected JSON envelope."""
    error = ErrorDetail(message="Something went wrong")
    response = ErrorResponse(request_id="xyz-789", error=error)
    serialised = response.model_dump()

    assert serialised["success"] is False
    assert serialised["request_id"] == "xyz-789"
    assert serialised["error"]["message"] == "Something went wrong"
