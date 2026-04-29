from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.safe_http_logging_runtime import HTTP_ACCESS_LOG_EVENT_TYPE


def test_fastapi_edge_emits_narrow_http_access_log_without_request_data() -> None:
    logs: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(http_access_log_writer=logs.append),
        config=FastApiBindingConfig(),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/api/runs/run-http-log?api_key=sk-query-secret",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-http-log-001",
        },
    )

    assert response.status_code in {401, 404, 405}
    assert len(logs) == 1
    event = logs[0]
    serialized = json.dumps(event, sort_keys=True)
    assert event["event_type"] == HTTP_ACCESS_LOG_EVENT_TYPE
    assert event["method"] == "GET"
    assert event["path"] == "/api/runs/run-http-log"
    assert event["status_code"] == response.status_code
    assert event["request_id"] == "req-http-log-001"
    assert "headers" not in event
    assert "query_params" not in event
    assert "request_body" not in event
    assert "response_body" not in event
    assert "sk-query-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized


def test_fastapi_edge_http_access_log_records_rate_limit_without_leaking_secrets() -> None:
    logs: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(http_access_log_writer=logs.append),
        config=FastApiBindingConfig(
            rate_limit_enabled=True,
            rate_limit_requests_per_window=1,
            rate_limit_window_seconds=60,
        ),
    )

    client = TestClient(app, raise_server_exceptions=False)
    first = client.get("/api/runs/run-http-log-limit?token=sk-query-secret", headers={"X-Nexa-Request-Id": "req-http-log-1"})
    second = client.get("/api/runs/run-http-log-limit?token=sk-query-secret", headers={"X-Nexa-Request-Id": "req-http-log-2"})

    assert first.status_code in {401, 404, 405}
    assert second.status_code == 429
    assert len(logs) == 2
    rate_limited_event = logs[-1]
    serialized = json.dumps(rate_limited_event, sort_keys=True)
    assert rate_limited_event["event_type"] == HTTP_ACCESS_LOG_EVENT_TYPE
    assert rate_limited_event["status_code"] == 429
    assert rate_limited_event["request_id"] == "req-http-log-2"
    assert rate_limited_event["extra"]["edge_outcome"] == "rate_limited"
    assert "sk-query-secret" not in serialized


def test_fastapi_edge_http_access_log_writer_failure_is_suppressed() -> None:
    def _failing_writer(_event: dict) -> None:
        raise RuntimeError("log sink unavailable")

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(http_access_log_writer=_failing_writer),
        config=FastApiBindingConfig(),
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/runs/run-http-log-failure", headers={"X-Nexa-Request-Id": "req-http-log-failure"})

    assert response.status_code in {401, 404, 405}
    assert response.headers["x-nexa-request-id"] == "req-http-log-failure"
