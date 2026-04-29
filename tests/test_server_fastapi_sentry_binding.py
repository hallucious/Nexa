from __future__ import annotations

import json
from types import SimpleNamespace

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.fastapi_sentry_binding import (
    build_fastapi_sentry_exception_context,
    capture_fastapi_sentry_exception,
    install_fastapi_sentry_observability,
)
from src.server.sentry_observability_runtime import SENTRY_CAPTURED_REASON, SENTRY_INITIALIZED_REASON


class _FakeApp:
    def __init__(self) -> None:
        self.state = SimpleNamespace()


class _FakeSentrySdk:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.captured_events: list[dict] = []

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "fastapi-event-001"


def test_install_fastapi_sentry_observability_initializes_state_without_dsn() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="production",
        sentry_release="nexa-fastapi-release",
        sentry_traces_sample_rate=0.1,
    )

    result = install_fastapi_sentry_observability(app, config, sdk_module=fake_sdk)

    assert result.initialized is True
    assert result.reason == SENTRY_INITIALIZED_REASON
    assert fake_sdk.init_kwargs is not None
    state_payload = vars(app.state)["nexa_sentry_observability"]
    assert state_payload["initialized"] is True
    assert state_payload["environment"] == "production"
    assert state_payload["sample_rate"] == 0.1
    assert "dsn" not in state_payload
    assert "examplePublicKey" not in json.dumps(state_payload, sort_keys=True)


def test_build_fastapi_sentry_exception_context_is_privacy_safe() -> None:
    context = build_fastapi_sentry_exception_context(
        method="get",
        path="/api/runs/run-001/result",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "User-Agent": "pytest-client",
        },
        query_params={"token": "sk-query-secret", "safe": "value"},
        request_id="req-fastapi-001",
        session_claims={"sub": "raw-user-id", "roles": ["editor"]},
        status_code=500,
        extra={"api_key": "sk-extra-secret"},
    )

    serialized = json.dumps(context, sort_keys=True)
    assert "sk-header-secret" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-extra-secret" not in serialized
    assert context["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert context["request"]["headers"]["user-agent"] == "pytest-client"
    assert context["request"]["query_params"]["token"] == REDACTED_VALUE
    assert context["request"]["query_params"]["safe"] == "value"
    assert context["request_id"] == "req-fastapi-001"
    assert context["api_key"] == REDACTED_VALUE


def test_capture_fastapi_sentry_exception_emits_scrubbed_event() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="production",
    )
    install_fastapi_sentry_observability(app, config, sdk_module=fake_sdk)

    result = capture_fastapi_sentry_exception(
        app=app,
        sdk_module=fake_sdk,
        exc=RuntimeError("handler failed with sk-runtime-secret"),
        method="post",
        path="/api/runs",
        headers={
            "Authorization": "Bearer sk-header-secret",
            "Cookie": "session=secret-cookie",
            "User-Agent": "pytest-client",
        },
        query_params={"api_key": "sk-query-secret"},
        request_id="req-fastapi-002",
        session_claims={"sub": "raw-user-id", "session_token": "sk-session-secret"},
        extra={"request_body": "raw confidential body"},
    )

    assert result.enabled is True
    assert result.captured is True
    assert result.reason == SENTRY_CAPTURED_REASON
    assert result.event_id == "fastapi-event-001"
    assert len(fake_sdk.captured_events) == 1

    captured = fake_sdk.captured_events[0]
    captured_text = json.dumps(captured, sort_keys=True)
    assert "sk-runtime-secret" not in captured_text
    assert "sk-header-secret" not in captured_text
    assert "secret-cookie" not in captured_text
    assert "sk-query-secret" not in captured_text
    assert "sk-session-secret" not in captured_text
    assert "raw confidential body" not in captured_text
    extra = captured["extra"]
    assert extra["request_id"] == "req-fastapi-002"
    assert extra["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert extra["request"]["headers"]["cookie"] == REDACTED_VALUE
    assert extra["request"]["headers"]["user-agent"] == "pytest-client"
    assert extra["request"]["query_params"]["api_key"] == REDACTED_VALUE
    assert extra["request_body"] == REDACTED_VALUE
