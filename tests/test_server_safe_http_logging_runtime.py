from __future__ import annotations

import json

import pytest

from src.server.observability_payload_guard import ObservabilityPayloadLeakError, REDACTED_VALUE
from src.server.safe_http_logging_runtime import (
    HTTP_ACCESS_LOG_EVENT_TYPE,
    assert_http_access_log_event_safe,
    build_http_access_log_event,
    emit_http_access_log,
)


def test_build_http_access_log_event_uses_narrow_no_body_schema() -> None:
    event = build_http_access_log_event(
        method="post",
        path="/api/runs?api_key=sk-query-secret",
        status_code=202,
        duration_ms=37.8,
        request_id="req-001",
        route_template="/api/runs",
        extra={
            "request_body": "raw confidential request body",
            "response_body": "raw confidential response body",
            "authorization": "Bearer sk-header-secret",
            "safe_family": "run_submission",
        },
    )

    serialized = json.dumps(event, sort_keys=True)
    assert event["event_type"] == HTTP_ACCESS_LOG_EVENT_TYPE
    assert event["method"] == "POST"
    assert event["path"] == "/api/runs?api_key=sk-query-secret"
    assert event["status_code"] == 202
    assert event["duration_ms"] == 37
    assert event["request_id"] == "req-001"
    assert event["route_template"] == "/api/runs"
    assert "raw confidential request body" not in serialized
    assert "raw confidential response body" not in serialized
    assert "sk-header-secret" not in serialized
    assert event["extra"]["request_body"] == REDACTED_VALUE
    assert event["extra"]["response_body"] == REDACTED_VALUE
    assert event["extra"]["authorization"] == REDACTED_VALUE
    assert event["extra"]["safe_family"] == "run_submission"


def test_http_access_log_event_safe_assertion_rejects_unexpected_raw_fields() -> None:
    unsafe = {
        "event_type": HTTP_ACCESS_LOG_EVENT_TYPE,
        "method": "POST",
        "path": "/api/runs",
        "status_code": 200,
        "duration_ms": 10,
        "request_body": "raw confidential body",
    }

    with pytest.raises(ValueError, match="unexpected HTTP access log fields"):
        assert_http_access_log_event_safe(unsafe)

    sanitized_with_bad_extra = {
        "event_type": HTTP_ACCESS_LOG_EVENT_TYPE,
        "method": "POST",
        "path": "/api/runs",
        "status_code": 200,
        "duration_ms": 10,
        "extra": {"request_body": "raw confidential body"},
    }
    with pytest.raises(ObservabilityPayloadLeakError):
        assert_http_access_log_event_safe(sanitized_with_bad_extra, forbidden_markers=["raw confidential body"])


def test_emit_http_access_log_writes_sanitized_event_and_suppresses_writer_errors() -> None:
    events: list[dict] = []

    event = emit_http_access_log(
        events.append,
        method="get",
        path="/api/workspaces/ws-001/uploads/presign",
        status_code=429,
        duration_ms=5,
        request_id="req-002",
        extra={"api_key": "sk-extra-secret", "safe_count": 2},
    )

    assert event is not None
    assert len(events) == 1
    written = events[0]
    serialized = json.dumps(written, sort_keys=True)
    assert "sk-extra-secret" not in serialized
    assert written["extra"]["api_key"] == REDACTED_VALUE
    assert written["extra"]["safe_count"] == 2

    def _failing_writer(_event):
        raise RuntimeError("log sink unavailable")

    suppressed = emit_http_access_log(
        _failing_writer,
        method="get",
        path="/health",
        status_code=200,
        duration_ms=1,
    )
    assert suppressed is not None
    assert suppressed["path"] == "/health"
