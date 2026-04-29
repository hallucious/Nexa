from __future__ import annotations

import json

import pytest

from src.server.edge_observability_runtime import emit_edge_observation
from src.server.observability_payload_guard import (
    REDACTED_VALUE,
    ObservabilityPayloadLeakError,
    assert_observability_payload_safe,
    sanitize_observability_payload,
)


def test_sanitize_observability_payload_removes_bodies_documents_prompts_outputs_and_credentials() -> None:
    payload = {
        "event_type": "edge.http_request_completed",
        "request_id": "req-001",
        "request_body": {"contract_text": "raw confidential contract text"},
        "response_body": "raw response with sk-response-secret",
        "document_text": "raw extracted document text",
        "rendered_prompt": "prompt containing user contract",
        "provider_raw_output": "model output with secret",
        "headers": {"authorization": "Bearer sk-header-secret", "user-agent": "pytest-client"},
        "nested": [{"api_key": "sk-nested-secret", "safe_count": 3}],
    }

    sanitized = sanitize_observability_payload(payload)

    serialized = json.dumps(sanitized, sort_keys=True)
    assert "raw confidential contract text" not in serialized
    assert "raw response" not in serialized
    assert "raw extracted document text" not in serialized
    assert "prompt containing user contract" not in serialized
    assert "model output" not in serialized
    assert "sk-header-secret" not in serialized
    assert "sk-nested-secret" not in serialized
    assert sanitized["request_body"] == REDACTED_VALUE
    assert sanitized["response_body"] == REDACTED_VALUE
    assert sanitized["document_text"] == REDACTED_VALUE
    assert sanitized["rendered_prompt"] == REDACTED_VALUE
    assert sanitized["provider_raw_output"] == REDACTED_VALUE
    assert sanitized["headers"]["authorization"] == REDACTED_VALUE
    assert sanitized["headers"]["user-agent"] == "pytest-client"
    assert sanitized["nested"][0]["api_key"] == REDACTED_VALUE
    assert sanitized["nested"][0]["safe_count"] == 3


def test_sanitize_observability_payload_removes_context_path_and_contract_result_content() -> None:
    payload = {
        "working_context": {
            "input": {"text": "raw uploaded contract body"},
            "prompt": {"main": {"rendered": "prompt rendered with contract terms"}},
            "provider": {"openai": {"output": "provider answer with clause text"}},
        },
        "contract_review_result": {
            "clauses": [
                {
                    "clause_id": "c_001",
                    "text": "raw clause text",
                    "plain_text": "plain explanation of raw clause",
                    "why_it_matters": "why raw clause matters",
                }
            ],
            "pre_signature_questions": [
                {"question": "raw question about the contract"}
            ],
        },
        "safe_count": 3,
    }

    sanitized = sanitize_observability_payload(payload)
    serialized = json.dumps(sanitized, sort_keys=True)

    assert "raw uploaded contract body" not in serialized
    assert "prompt rendered with contract terms" not in serialized
    assert "provider answer with clause text" not in serialized
    assert "raw clause text" not in serialized
    assert "plain explanation" not in serialized
    assert "why raw clause matters" not in serialized
    assert "raw question about the contract" not in serialized
    assert sanitized["working_context"]["input"]["text"] == REDACTED_VALUE
    assert sanitized["working_context"]["prompt"]["main"]["rendered"] == REDACTED_VALUE
    assert sanitized["working_context"]["provider"]["openai"]["output"] == REDACTED_VALUE
    assert sanitized["contract_review_result"]["clauses"][0]["text"] == REDACTED_VALUE
    assert sanitized["contract_review_result"]["clauses"][0]["plain_text"] == REDACTED_VALUE
    assert sanitized["contract_review_result"]["clauses"][0]["why_it_matters"] == REDACTED_VALUE
    assert sanitized["contract_review_result"]["pre_signature_questions"][0]["question"] == REDACTED_VALUE
    assert sanitized["safe_count"] == 3


def test_assert_observability_payload_safe_rejects_raw_forbidden_fields_and_markers() -> None:
    with pytest.raises(ObservabilityPayloadLeakError, match="unsafe observability field"):
        assert_observability_payload_safe({"request_body": "raw confidential body"})

    with pytest.raises(ObservabilityPayloadLeakError, match="unsafe observability field"):
        assert_observability_payload_safe({"input": {"text": "raw confidential body"}})

    with pytest.raises(ObservabilityPayloadLeakError, match="unsafe observability marker"):
        assert_observability_payload_safe({"safe": "raw confidential body"}, forbidden_markers=["raw confidential body"])

    assert_observability_payload_safe({"request_body": REDACTED_VALUE, "input": {"text": REDACTED_VALUE}, "safe": "value"})


def test_emit_edge_observation_sanitizes_payload_before_writer_boundary() -> None:
    events: list[dict] = []

    emit_edge_observation(
        events.append,
        {
            "event_type": "edge.http_request_completed",
            "request": {
                "method": "POST",
                "path": "/api/runs",
                "request_body": {"contract_text": "raw confidential body"},
                "query_params": {"api_key": "sk-query-secret", "safe": "value"},
            },
            "response_body": "raw response body",
            "input": {"text": "raw input text"},
        },
    )

    assert len(events) == 1
    event = events[0]
    serialized = json.dumps(event, sort_keys=True)
    assert "raw confidential body" not in serialized
    assert "raw response body" not in serialized
    assert "raw input text" not in serialized
    assert "sk-query-secret" not in serialized
    assert event["request"]["request_body"] == REDACTED_VALUE
    assert event["request"]["query_params"]["api_key"] == REDACTED_VALUE
    assert event["request"]["query_params"]["safe"] == "value"
    assert event["response_body"] == REDACTED_VALUE
    assert event["input"]["text"] == REDACTED_VALUE


def test_emit_edge_observation_suppresses_guard_or_writer_failures() -> None:
    def _bad_writer(_event):
        raise RuntimeError("writer failed with sk-secret")

    emit_edge_observation(_bad_writer, {"request_body": "raw body"})
