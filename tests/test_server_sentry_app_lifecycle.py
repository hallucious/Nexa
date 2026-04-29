from __future__ import annotations

import json
from types import SimpleNamespace

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.sentry_observability_runtime import (
    SENTRY_APP_STATE_KEY,
    SENTRY_CAPTURED_REASON,
    SENTRY_DISABLED_REASON,
    SENTRY_INITIALIZED_REASON,
    SENTRY_NOT_INITIALIZED_REASON,
    capture_sentry_exception_for_app,
    install_sentry_observability_on_app,
    read_sentry_observability_app_state,
)


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
        return "event-lifecycle-001"


def test_install_sentry_observability_on_app_stores_disabled_dsn_free_state() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=False,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="local",
    )

    result = install_sentry_observability_on_app(app, config, sdk_module=fake_sdk)
    state = read_sentry_observability_app_state(app)

    assert result.enabled is False
    assert result.initialized is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert state == result.as_payload()
    assert state["dsn_configured"] is True
    assert "dsn" not in state
    assert "examplePublicKey" not in json.dumps(state, sort_keys=True)
    assert fake_sdk.init_kwargs is None


def test_install_sentry_observability_on_app_initializes_and_stores_safe_state() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="production",
        sentry_release="nexa-release-002",
        sentry_traces_sample_rate=0.2,
    )

    result = install_sentry_observability_on_app(app, config, sdk_module=fake_sdk)
    state = getattr(app.state, SENTRY_APP_STATE_KEY)

    assert result.initialized is True
    assert result.reason == SENTRY_INITIALIZED_REASON
    assert state["enabled"] is True
    assert state["initialized"] is True
    assert state["environment"] == "production"
    assert state["sample_rate"] == 0.2
    assert "dsn" not in state
    assert fake_sdk.init_kwargs is not None
    assert fake_sdk.init_kwargs["send_default_pii"] is False


def test_capture_sentry_exception_for_app_refuses_before_initialized_runtime_state() -> None:
    app = _FakeApp()
    setattr(
        app.state,
        SENTRY_APP_STATE_KEY,
        {
            "enabled": True,
            "initialized": False,
            "reason": "sentry_sdk_missing",
            "dsn_configured": True,
            "environment": "production",
            "sample_rate": 0.0,
        },
    )
    fake_sdk = _FakeSentrySdk()

    result = capture_sentry_exception_for_app(
        app=app,
        sdk_module=fake_sdk,
        exc=RuntimeError("should not be captured sk-secret"),
        context={"token": "sk-context-secret"},
    )

    assert result.enabled is True
    assert result.captured is False
    assert result.reason == SENTRY_NOT_INITIALIZED_REASON
    assert fake_sdk.captured_events == []


def test_capture_sentry_exception_for_app_emits_scrubbed_event_after_installation() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="production",
    )
    install_sentry_observability_on_app(app, config, sdk_module=fake_sdk)

    result = capture_sentry_exception_for_app(
        app=app,
        sdk_module=fake_sdk,
        exc=RuntimeError("provider failed with sk-runtime-secret"),
        context={
            "run_id": "run-001",
            "request": {
                "headers": {
                    "Authorization": "Bearer sk-header-secret",
                    "User-Agent": "pytest-client",
                },
                "body": {"contract_text": "raw confidential contract text"},
            },
        },
    )

    assert result.enabled is True
    assert result.captured is True
    assert result.reason == SENTRY_CAPTURED_REASON
    assert result.event_id == "event-lifecycle-001"
    assert len(fake_sdk.captured_events) == 1
    event = fake_sdk.captured_events[0]
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in event_text
    assert "sk-header-secret" not in event_text
    assert "raw confidential contract text" not in event_text
    assert event["extra"]["run_id"] == "run-001"
    assert event["extra"]["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert event["extra"]["request"]["headers"]["user-agent"] == "pytest-client"
    assert event["extra"]["request"]["body"] == REDACTED_VALUE
    assert event["extra"]["sentry_runtime"]["initialized"] is True
    assert "dsn" not in event["extra"]["sentry_runtime"]


def test_capture_sentry_exception_for_app_without_state_is_safe_noop() -> None:
    app = _FakeApp()
    fake_sdk = _FakeSentrySdk()

    result = capture_sentry_exception_for_app(
        app=app,
        sdk_module=fake_sdk,
        exc=RuntimeError("contains sk-secret"),
        context={"token": "sk-context-secret"},
    )

    assert result.enabled is False
    assert result.captured is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert fake_sdk.captured_events == []
