from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.fastapi_edge_middleware import OTEL_HTTP_SERVER_EVENT_TYPE


def test_fastapi_edge_emits_safe_otel_http_span_projection() -> None:
    spans: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(
            otel_span_writer=spans.append,
            session_claims_resolver=lambda _request: {"sub": "raw-user-id", "session_token": "sk-session-secret"},
        ),
        config=FastApiBindingConfig(otel_enabled=True, otel_service_name="nexa-api", otel_environment="test"),
    )

    @app.get("/otel-ok")
    async def _otel_ok():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/otel-ok?api_key=sk-query-secret",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-otel-edge-001",
        },
    )

    assert response.status_code == 200
    assert len(spans) == 1
    span = spans[0]
    serialized = json.dumps(span, sort_keys=True)
    assert "sk-query-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "sk-session-secret" not in serialized
    assert span["event_type"] == OTEL_HTTP_SERVER_EVENT_TYPE
    assert span["name"] == "http.server"
    assert span["attributes"]["span.kind"] == "server"
    assert span["attributes"]["http.request.method"] == "GET"
    assert span["attributes"]["url.path"] == "/otel-ok"
    assert span["attributes"]["http.response.status_code"] == 200
    assert span["attributes"]["nexa.request_id"] == "req-otel-edge-001"
    assert span["attributes"]["http.request.headers"]["authorization"] == "<redacted>"
    assert span["attributes"]["http.request.headers"]["cookie"] == "<redacted>"
    assert span["attributes"]["http.request.headers"]["user-agent"] == "pytest-client"
    assert span["attributes"]["http.request.query"]["api_key"] == "<redacted>"
    assert span["attributes"]["nexa.session"]["session_token"] == "<redacted>"
    assert span["attributes"]["nexa.edge_outcome"] == "completed"
    assert span["attributes"]["nexa.otel_service_name"] == "nexa-api"
    assert span["attributes"]["nexa.otel_environment"] == "test"


def test_fastapi_edge_otel_projection_adds_scrubbed_exception_event() -> None:
    spans: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(otel_span_writer=spans.append),
        config=FastApiBindingConfig(otel_enabled=True, edge_exception_capture_enabled=True),
    )

    @app.get("/otel-boom")
    async def _otel_boom():
        raise RuntimeError("provider failed with sk-runtime-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/otel-boom?token=sk-query-secret", headers={"X-Nexa-Request-Id": "req-otel-edge-002"})

    assert response.status_code == 500
    assert len(spans) == 1
    span = spans[0]
    serialized = json.dumps(span, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-query-secret" not in serialized
    assert span["attributes"]["http.response.status_code"] == 500
    assert span["attributes"]["nexa.edge_outcome"] == "exception"
    assert span["events"][0]["name"] == "exception"
    assert span["events"][0]["attributes"]["exception.message"] == "<redacted>"


def test_fastapi_edge_otel_disabled_does_not_emit_spans() -> None:
    spans: list[dict] = []
    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(otel_span_writer=spans.append),
        config=FastApiBindingConfig(otel_enabled=False),
    )

    @app.get("/otel-disabled")
    async def _otel_disabled():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/otel-disabled")

    assert response.status_code == 200
    assert spans == []


def test_fastapi_edge_otel_writer_failure_is_suppressed() -> None:
    def _failing_writer(_event):
        raise RuntimeError("writer unavailable")

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(otel_span_writer=_failing_writer),
        config=FastApiBindingConfig(otel_enabled=True),
    )

    @app.get("/otel-writer-fails")
    async def _otel_writer_fails():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/otel-writer-fails")

    assert response.status_code == 200
