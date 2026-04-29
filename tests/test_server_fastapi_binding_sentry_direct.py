from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from src.server.fastapi_binding import create_fastapi_app
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies


class _FakeSentrySdkModule:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.captured_events: list[dict] = []

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "direct-fastapi-event-001"


def test_create_fastapi_app_directly_initializes_sentry_and_captures_through_edge_middleware(monkeypatch) -> None:
    fake_sdk = _FakeSentrySdkModule()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(
            session_claims_resolver=lambda _request: {"sub": "raw-user-id", "session_token": "sk-session-secret"},
        ),
        config=FastApiBindingConfig(
            sentry_enabled=True,
            sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            sentry_environment="production",
        ),
    )

    @app.get("/direct-boom")
    async def _direct_boom():
        raise RuntimeError("direct handler failed with sk-runtime-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/direct-boom?api_key=sk-query-secret",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-direct-001",
        },
    )

    assert fake_sdk.init_kwargs is not None
    assert fake_sdk.init_kwargs["send_default_pii"] is False
    assert response.status_code == 500
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["reason"] == "edge_exception_captured"
    assert payload["request_id"] == "req-direct-001"
    assert "observability" not in payload

    response_text = response.text
    assert "sk-runtime-secret" not in response_text
    assert "sk-header-secret" not in response_text
    assert "sk-query-secret" not in response_text

    assert len(fake_sdk.captured_events) == 1
    event = fake_sdk.captured_events[0]
    serialized = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-session-secret" not in serialized
    assert event["extra"]["request_id"] == "req-direct-001"
    assert event["extra"]["request"]["headers"]["authorization"] == "<redacted>"
    assert event["extra"]["request"]["headers"]["cookie"] == "<redacted>"
    assert event["extra"]["request"]["headers"]["user-agent"] == "pytest-client"
    assert event["extra"]["request"]["query_params"]["api_key"] == "<redacted>"
    assert event["extra"]["session"]["session_token"] == "<redacted>"


def test_create_fastapi_app_sentry_disabled_keeps_normal_edge_exception_payload(monkeypatch) -> None:
    fake_sdk = _FakeSentrySdkModule()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(),
        config=FastApiBindingConfig(sentry_enabled=False),
    )

    @app.get("/direct-disabled-boom")
    async def _direct_disabled_boom():
        raise RuntimeError("disabled handler failed with sk-runtime-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/direct-disabled-boom",
        headers={"X-Nexa-Request-Id": "req-direct-disabled-001"},
    )

    assert fake_sdk.init_kwargs is None
    assert fake_sdk.captured_events == []
    assert response.status_code == 500
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["reason"] == "edge_exception_captured"
    assert payload["request_id"] == "req-direct-disabled-001"
    assert "sk-runtime-secret" not in response.text
