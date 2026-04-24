"""Property-based tests for the FastAPI Ad Analyser using Hypothesis."""

import uuid

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


# Feature: fastapi-ad-analyser, Property 1: Valid request always produces a well-formed success response
@given(st.text(min_size=10).filter(lambda s: "force_runtime_error" not in s.lower()))
@settings(max_examples=100)
def test_property_1_valid_request_success_response(client, ad_copy):
    """Validates: Requirements 1.2, 1.3, 10.1

    For any non-empty ad_copy string of length >= 10 that does not contain
    "force_runtime_error", a POST to /api/v1/analyse-ad SHALL return HTTP 200
    with success: true, a non-empty UUID request_id, and all four prediction
    fields present with their correct types.
    """
    response = client.post("/api/v1/analyse-ad", json={"ad_copy": ad_copy})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["request_id"] != ""
    # Validate UUID v4 format
    uuid.UUID(body["request_id"], version=4)
    data = body["data"]
    assert isinstance(data["impulse_score"], float)
    assert isinstance(data["trust_score"], float)
    assert isinstance(data["conversion_probability"], float)
    assert isinstance(data["model_version"], str)


# Feature: fastapi-ad-analyser, Property 2: Every response always contains a valid UUID request_id
@given(
    st.one_of(
        st.text(min_size=10).filter(lambda s: "force_runtime_error" not in s.lower()),
        st.text(min_size=1, max_size=9),
        st.just("force_runtime_error trigger"),
    )
)
@settings(max_examples=100)
def test_property_2_every_response_has_valid_uuid_request_id(client, ad_copy):
    """Validates: Requirements 1.3, 3.3, 10.5

    For any request to POST /api/v1/analyse-ad — regardless of whether it
    succeeds, triggers a ValueError, or triggers a RuntimeError — the response
    body SHALL always contain a request_id field that is a non-empty, valid
    UUID v4 string.
    """
    response = client.post("/api/v1/analyse-ad", json={"ad_copy": ad_copy})
    body = response.json()
    assert "request_id" in body
    assert body["request_id"] != ""
    # Validate UUID v4 format — raises ValueError if invalid
    uuid.UUID(body["request_id"], version=4)


# Feature: fastapi-ad-analyser, Property 3: Short ad_copy always produces a well-formed HTTP 400 error response
@given(st.text(min_size=1, max_size=9))
@settings(max_examples=100)
def test_property_3_short_ad_copy_returns_400(client, ad_copy):
    """Validates: Requirements 3.1, 4.3, 10.2

    For any ad_copy string with length between 1 and 9 characters (inclusive),
    a POST to /api/v1/analyse-ad SHALL return HTTP 400 with success: false,
    a non-empty request_id, and an error.message string that is non-empty.
    """
    from unittest.mock import patch

    with patch(
        "app.services.predict_conversion",
        side_effect=ValueError("Input text must be at least 10 characters for analysis."),
    ):
        response = client.post("/api/v1/analyse-ad", json={"ad_copy": ad_copy})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["request_id"] != ""
    assert body["error"]["message"] != ""


# Feature: fastapi-ad-analyser, Property 4: Every request produces INFO log entries containing the request_id
@given(st.text(min_size=10).filter(lambda s: "force_runtime_error" not in s.lower()))
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_property_4_valid_request_produces_info_logs_with_request_id(client, caplog, ad_copy):
    """Validates: Requirements 6.1, 6.2

    For any valid request to POST /api/v1/analyse-ad, the application logger
    SHALL emit at least two INFO-level log entries: one when the request is
    received and one when the prediction is returned, and both entries SHALL
    contain the request_id assigned to that request.

    caplog is not reset between Hypothesis examples, but we filter records by
    the unique request_id from each response, so accumulated records from prior
    examples do not affect the assertion.
    """
    import logging

    with caplog.at_level(logging.INFO, logger="app.routes"):
        response = client.post("/api/v1/analyse-ad", json={"ad_copy": ad_copy})

    assert response.status_code == 200
    body = response.json()
    request_id = body["request_id"]

    # Filter for INFO-level records from app.routes that contain the request_id
    info_records_with_request_id = [
        record
        for record in caplog.records
        if record.levelno == logging.INFO and request_id in record.getMessage()
    ]

    assert len(info_records_with_request_id) >= 2, (
        f"Expected at least 2 INFO log entries containing request_id={request_id!r}, "
        f"but found {len(info_records_with_request_id)}. "
        f"All captured records: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )
