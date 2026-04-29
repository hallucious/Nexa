from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.otel_observability_runtime import (
    OTEL_DISABLED_REASON,
    OTEL_INITIALIZED_REASON,
    OTEL_SDK_MISSING_REASON,
    build_otel_exception_event,
    build_otel_http_server_attributes,
    build_otel_safe_attributes,
    build_otel_worker_attributes,
    initialize_otel_observability,
)


class _FakeOtelTraceSdk:
    def __init__(self) -> None:
        self.provider_read = False

    def get_tracer_provider(self):
        self.provider_read = True
        return object()


class _FailingOtelTraceSdk:
    def get_tracer_provider(self):
        raise RuntimeError("otel unavailable")


def test_build_otel_safe_attributes_redacts_sql_bodies_and_credentials() -> None:
    attributes = build_otel_safe_attributes(
        {
            "db.statement": "select * from users where token='sk-sql-secret'",
            "request_body": {"contract_text": "raw confidential contract"},
            "api_key": "sk-api-secret",
            "authorization": "Bearer sk-header-secret",
            "safe_count": 3,
            "nested": {"worker_token": "sk-worker-secret", "safe": "value"},
        }
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "select * from users" not in serialized
    assert "raw confidential contract" not in serialized
    assert "sk-api-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "sk-worker-secret" not in serialized
    assert attributes["db.statement"] == REDACTED_VALUE
    assert attributes["request_body"] == REDACTED_VALUE
    assert attributes["api_key"] == REDACTED_VALUE
    assert attributes["authorization"] == REDACTED_VALUE
    assert attributes["safe_count"] == 3
    assert attributes["nested"]["worker_token"] == REDACTED_VALUE
    assert attributes["nested"]["safe"] == "value"


def test_build_otel_safe_attributes_redacts_context_paths_and_contract_outputs() -> None:
    attributes = build_otel_safe_attributes(
        {
            "input": {"text": "raw uploaded contract text"},
            "prompt": {"main": {"rendered": "rendered prompt with raw text"}},
            "provider": {"anthropic": {"output": "provider output with raw clause"}},
            "contract_review_result": {
                "clauses": [
                    {
                        "text": "raw clause",
                        "plain_text": "plain clause explanation",
                        "why_it_matters": "raw reason",
                    }
                ],
                "pre_signature_questions": [{"question": "raw contract question"}],
            },
            "safe": "value",
        }
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "raw uploaded contract text" not in serialized
    assert "rendered prompt with raw text" not in serialized
    assert "provider output with raw clause" not in serialized
    assert "raw clause" not in serialized
    assert "plain clause explanation" not in serialized
    assert "raw reason" not in serialized
    assert "raw contract question" not in serialized
    assert attributes["input"]["text"] == REDACTED_VALUE
    assert attributes["prompt"]["main"]["rendered"] == REDACTED_VALUE
    assert attributes["provider"]["anthropic"]["output"] == REDACTED_VALUE
    assert attributes["contract_review_result"]["clauses"][0]["plain_text"] == REDACTED_VALUE
    assert attributes["contract_review_result"]["pre_signature_questions"][0]["question"] == REDACTED_VALUE
    assert attributes["safe"] == "value"


def test_build_otel_http_server_attributes_scrubs_request_boundary() -> None:
    attributes = build_otel_http_server_attributes(
        method="post",
        path="/api/runs",
        status_code=500,
        request_id="req-otel-001",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Forwarded-For": "203.0.113.9",
        },
        query_params={"api_key": "sk-query-secret", "safe": "value"},
        session_claims={"sub": "raw-user-id", "session_token": "sk-session-secret", "roles": ["editor"]},
        extra={"raw_sql": "select secret from table", "safe_flag": True},
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "203.0.113.9" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-session-secret" not in serialized
    assert "select secret" not in serialized
    assert attributes["span.kind"] == "server"
    assert attributes["http.request.method"] == "POST"
    assert attributes["url.path"] == "/api/runs"
    assert attributes["http.response.status_code"] == 500
    assert attributes["nexa.request_id"] == "req-otel-001"
    assert attributes["http.request.headers"]["authorization"] == REDACTED_VALUE
    assert attributes["http.request.headers"]["cookie"] == REDACTED_VALUE
    assert attributes["http.request.headers"]["user-agent"] == "pytest-client"
    assert "x-forwarded-for" not in attributes["http.request.headers"]
    assert attributes["http.request.query"]["api_key"] == REDACTED_VALUE
    assert attributes["http.request.query"]["safe"] == "value"
    assert attributes["nexa.session"]["session_token"] == REDACTED_VALUE
    assert attributes["raw_sql"] == REDACTED_VALUE
    assert attributes["safe_flag"] is True


def test_build_otel_worker_attributes_scrubs_payload() -> None:
    attributes = build_otel_worker_attributes(
        job_name="execute_queued_run",
        run_id="run-001",
        workspace_id="ws-001",
        payload={"api_key": "sk-payload-secret", "target_ref": "snapshot-001"},
        extra={"worker_token": "sk-worker-secret", "safe_count": 2},
    )

    serialized = json.dumps(attributes, sort_keys=True)
    assert "sk-payload-secret" not in serialized
    assert "sk-worker-secret" not in serialized
    assert attributes["span.kind"] == "worker"
    assert attributes["messaging.operation.name"] == "execute_queued_run"
    assert attributes["nexa.run_id"] == "run-001"
    assert attributes["nexa.workspace_id"] == "ws-001"
    assert attributes["nexa.worker.payload"]["api_key"] == REDACTED_VALUE
    assert attributes["nexa.worker.payload"]["target_ref"] == "snapshot-001"
    assert attributes["worker_token"] == REDACTED_VALUE
    assert attributes["safe_count"] == 2


def test_build_otel_exception_event_redacts_exception_message_and_attributes() -> None:
    event = build_otel_exception_event(
        exc=RuntimeError("provider failed with sk-runtime-secret"),
        attributes={"request_body": "raw confidential body", "safe": "value"},
    )

    serialized = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "raw confidential body" not in serialized
    assert event["name"] == "exception"
    assert event["attributes"]["exception.type"] == "RuntimeError"
    assert event["attributes"]["exception.message"] == REDACTED_VALUE
    assert event["attributes"]["request_body"] == REDACTED_VALUE
    assert event["attributes"]["safe"] == "value"


def test_build_otel_exception_event_redacts_non_secret_document_exception_message() -> None:
    event = build_otel_exception_event(
        exc=RuntimeError("parser failed on raw uploaded contract text"),
        attributes={"safe": "value"},
    )

    serialized = json.dumps(event, sort_keys=True)
    assert "raw uploaded contract text" not in serialized
    assert event["attributes"]["exception.message"] == REDACTED_VALUE
    assert event["attributes"]["safe"] == "value"


def test_initialize_otel_observability_disabled_and_missing_sdk_are_safe_noop() -> None:
    disabled = initialize_otel_observability(enabled=False, exporter_endpoint="http://collector:4317")
    assert disabled.enabled is False
    assert disabled.initialized is False
    assert disabled.reason == OTEL_DISABLED_REASON
    assert disabled.exporter_endpoint_configured is True
    assert "collector" not in json.dumps(disabled.as_payload(), sort_keys=True)

    missing = initialize_otel_observability(enabled=True, service_name="nexa-api", environment="production")
    assert missing.enabled is True
    assert missing.initialized is False
    assert missing.reason in {OTEL_SDK_MISSING_REASON, OTEL_INITIALIZED_REASON}


def test_initialize_otel_observability_with_fake_sdk_records_initialized_posture() -> None:
    fake_sdk = _FakeOtelTraceSdk()

    result = initialize_otel_observability(
        enabled=True,
        service_name="nexa-api",
        environment="staging",
        exporter_endpoint="http://collector:4317",
        sdk_module=fake_sdk,
    )

    assert result.enabled is True
    assert result.initialized is True
    assert result.reason == OTEL_INITIALIZED_REASON
    assert result.service_name == "nexa-api"
    assert result.environment == "staging"
    assert result.exporter_endpoint_configured is True
    assert fake_sdk.provider_read is True
    assert "collector" not in json.dumps(result.as_payload(), sort_keys=True)
