from __future__ import annotations

import json
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from src.server import FastApiBindingConfig, FastApiRouteDependencies, create_fastapi_app
from src.server.fastapi_sentry_autowire import install_fastapi_sentry_autowire
from src.server.sentry_observability_runtime import SENTRY_APP_STATE_KEY, SENTRY_CAPTURED_REASON


class _FakeSentrySdkModule:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.captured_events: list[dict] = []

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "autowire-event-001"


def test_fastapi_binding_build_app_autowires_sentry_state_when_enabled(monkeypatch) -> None:
    fake_sdk = _FakeSentrySdkModule()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)
    install_fastapi_sentry_autowire()

    app = create_fastapi_app(
        dependencies=FastApiRouteDependencies(),
        config=FastApiBindingConfig(
            sentry_enabled=True,
            sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            sentry_environment="production",
            sentry_release="nexa-autowire-test",
            sentry_traces_sample_rate=0.1,
        ),
    )

    state = getattr(app.state, SENTRY_APP_STATE_KEY)
    assert state["enabled"] is True
    assert state["initialized"] is True
    assert state["environment"] == "production"
    assert state["sample_rate"] == 0.1
    assert "dsn" not in state
    assert fake_sdk.init_kwargs is not None
    assert fake_sdk.init_kwargs["release"] == "nexa-autowire-test"
    assert fake_sdk.init_kwargs["send_default_pii"] is False


def test_fastapi_binding_build_app_sentry_middleware_captures_unhandled_exception(monkeypatch) -> None:
    fake_sdk = _FakeSentrySdkModule()
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)
    install_fastapi_sentry_autowire()

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

    @app.get("/autowire-boom")
    async def _autowire_boom():
        raise RuntimeError("autowire handler failed with sk-runtime-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/autowire-boom?api_key=sk-query-secret",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
            "X-Nexa-Request-Id": "req-autowire-001",
        },
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["request_id"] == "req-autowire-001"
    assert payload["observability"]["captured"] is True
    assert payload["observability"]["reason"] == SENTRY_CAPTURED_REASON
    assert "sk-runtime-secret" not in response.text
    assert "sk-header-secret" not in response.text
    assert "sk-query-secret" not in response.text

    assert len(fake_sdk.captured_events) == 1
    event = fake_sdk.captured_events[0]
    serialized = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "secret-cookie" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-session-secret" not in serialized
    assert event["extra"]["request_id"] == "req-autowire-001"
    assert event["extra"]["request"]["headers"]["authorization"] == "<redacted>"
    assert event["extra"]["request"]["headers"]["cookie"] == "<redacted>"
    assert event["extra"]["request"]["headers"]["user-agent"] == "pytest-client"
    assert event["extra"]["request"]["query_params"]["api_key"] == "<redacted>"
    assert event["extra"]["session"]["session_token"] == "<redacted>"
