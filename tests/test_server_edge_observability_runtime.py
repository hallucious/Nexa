from __future__ import annotations

import json

from src.server.edge_observability_runtime import (
    EDGE_EXCEPTION_REASON,
    REDACTED_VALUE,
    edge_exception_event,
    emit_edge_observation,
    redact_headers,
    redact_mapping,
    request_observation_context,
)


def test_edge_observability_redacts_sensitive_keys_without_over_redacting_key_substrings() -> None:
    redacted = redact_mapping(
        {
            "api_key": "sk-query-secret",
            "monkey": "banana",
            "keyboard_layout": "dvorak",
            "nested": {
                "public_key": "ssh-public-key-like-value",
                "ordinary": "safe-value",
            },
        }
    )

    assert redacted["api_key"] == REDACTED_VALUE
    assert redacted["nested"]["public_key"] == REDACTED_VALUE
    assert redacted["monkey"] == "banana"
    assert redacted["keyboard_layout"] == "dvorak"
    assert redacted["nested"]["ordinary"] == "safe-value"


def test_edge_observability_redacts_nested_secret_scalars_and_collections() -> None:
    redacted = redact_mapping(
        {
            "filters": [
                {"token": "user-token-value"},
                {"note": "contains sk-hidden-value"},
                "Bearer direct-secret",
            ],
            "safe_count": 3,
        }
    )

    assert redacted["filters"] == [
        {"token": REDACTED_VALUE},
        {"note": REDACTED_VALUE},
        REDACTED_VALUE,
    ]
    assert redacted["safe_count"] == 3


def test_edge_observability_headers_emit_only_safe_or_redacted_values() -> None:
    redacted = redact_headers(
        {
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-001",
            "X-Forwarded-For": "203.0.113.9",
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
        }
    )

    assert redacted["user-agent"] == "pytest-client"
    assert redacted["x-nexa-request-id"] == "req-001"
    assert redacted["authorization"] == REDACTED_VALUE
    assert redacted["cookie"] == REDACTED_VALUE
    assert "x-forwarded-for" not in redacted


def test_edge_exception_event_never_serializes_exception_message_content() -> None:
    request_context = request_observation_context(
        method="post",
        path="/api/runs",
        headers={"Authorization": "Bearer sk-header-secret"},
        query_params={"api_key": "sk-query-secret", "safe": "value"},
        session_claims={"sub": "user-owner", "roles": ["editor"]},
        request_id="req-001",
    )

    event = edge_exception_event(
        request_context=request_context,
        exc=RuntimeError("provider secret sk-runtime-secret should not leak"),
    )

    assert event["error_type"] == "RuntimeError"
    assert event["reason"] == EDGE_EXCEPTION_REASON
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in event_text
    assert "sk-query-secret" not in event_text
    assert "sk-header-secret" not in event_text
    assert event["request"]["query_params"]["api_key"] == REDACTED_VALUE
    assert event["request"]["headers"]["authorization"] == REDACTED_VALUE


def test_emit_edge_observation_suppresses_writer_failures() -> None:
    def _writer(_event):
        raise RuntimeError("writer unavailable")

    emit_edge_observation(_writer, {"event_type": "edge.http_request_completed"})
