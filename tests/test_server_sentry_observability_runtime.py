from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.sentry_observability_runtime import (
    SENTRY_CAPTURE_FAILED_REASON,
    SENTRY_CAPTURED_REASON,
    SENTRY_DISABLED_REASON,
    SENTRY_DSN_MISSING_REASON,
    SENTRY_INITIALIZED_REASON,
    build_sentry_exception_event,
    capture_sentry_exception,
    capture_sentry_exception_from_config,
    initialize_sentry_from_config,
    initialize_sentry_observability,
    scrub_sentry_event,
)


class _FakeSentrySdk:
    def __init__(self) -> None:
        self.init_kwargs = None
        self.captured_events = []

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "event-001"


class _FailingCaptureSentrySdk:
    def capture_event(self, event):
        raise RuntimeError("sentry unavailable")


def test_sentry_scrubber_removes_request_body_headers_cookies_and_user_pii() -> None:
    event = {
        "request": {
            "url": "https://app.nexa.example/api/runs?api_key=sk-query-secret",
            "query_string": "api_key=sk-query-secret",
            "headers": {
                "Authorization": "Bearer sk-header-secret",
                "Cookie": "session=secret-cookie",
                "User-Agent": "pytest-client",
            },
            "data": {"contract_text": "raw confidential document text"},
            "cookies": {"session": "secret-cookie"},
        },
        "user": {
            "id": "raw-user-id",
            "email": "person@example.com",
            "ip_address": "203.0.113.9",
        },
        "extra": {"provider_token": "sk-extra-secret", "safe_count": 3},
        "exception": {"values": [{"value": "RuntimeError with sk-runtime-secret"}]},
    }

    scrubbed = scrub_sentry_event(event)

    assert scrubbed is not None
    assert scrubbed["request"]["query_string"] == REDACTED_VALUE
    assert scrubbed["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert scrubbed["request"]["headers"]["cookie"] == REDACTED_VALUE
    assert scrubbed["request"]["headers"]["user-agent"] == "pytest-client"
    assert scrubbed["request"]["data"] == REDACTED_VALUE
    assert scrubbed["request"]["cookies"] == REDACTED_VALUE
    assert scrubbed["user"]["id"] == REDACTED_VALUE
    assert scrubbed["user"]["email"] == REDACTED_VALUE
    assert scrubbed["user"]["ip_address"] == REDACTED_VALUE
    assert scrubbed["extra"]["provider_token"] == REDACTED_VALUE

    serialized = json.dumps(scrubbed, sort_keys=True)
    assert "raw confidential document text" not in serialized
    assert "sk-query-secret" not in serialized
    assert "sk-header-secret" not in serialized
    assert "sk-runtime-secret" not in serialized
    assert "person@example.com" not in serialized


def test_sentry_initialization_returns_disabled_without_calling_sdk() -> None:
    fake_sdk = _FakeSentrySdk()

    result = initialize_sentry_observability(
        enabled=False,
        dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        environment="test",
        sdk_module=fake_sdk,
    )

    assert result.enabled is False
    assert result.initialized is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert fake_sdk.init_kwargs is None


def test_sentry_initialization_requires_dsn_before_calling_sdk() -> None:
    fake_sdk = _FakeSentrySdk()

    result = initialize_sentry_observability(
        enabled=True,
        dsn=None,
        environment="test",
        sdk_module=fake_sdk,
    )

    assert result.enabled is True
    assert result.initialized is False
    assert result.reason == SENTRY_DSN_MISSING_REASON
    assert fake_sdk.init_kwargs is None


def test_sentry_initialization_installs_privacy_safe_before_send_hook() -> None:
    fake_sdk = _FakeSentrySdk()

    result = initialize_sentry_observability(
        enabled=True,
        dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        environment="production",
        release="nexa-test-release",
        traces_sample_rate=0.25,
        sdk_module=fake_sdk,
    )

    assert result.initialized is True
    assert result.reason == SENTRY_INITIALIZED_REASON
    assert fake_sdk.init_kwargs is not None
    assert fake_sdk.init_kwargs["send_default_pii"] is False
    assert fake_sdk.init_kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
    assert fake_sdk.init_kwargs["environment"] == "production"
    assert fake_sdk.init_kwargs["release"] == "nexa-test-release"
    assert fake_sdk.init_kwargs["traces_sample_rate"] == 0.25

    before_send = fake_sdk.init_kwargs["before_send"]
    scrubbed = before_send({"request": {"headers": {"Authorization": "Bearer sk-secret"}}}, None)
    assert scrubbed["request"]["headers"]["authorization"] == REDACTED_VALUE


def test_sentry_capture_exception_emits_scrubbed_event_without_raw_secret_content() -> None:
    fake_sdk = _FakeSentrySdk()

    result = capture_sentry_exception(
        enabled=True,
        sdk_module=fake_sdk,
        exc=RuntimeError("provider failed with sk-runtime-secret"),
        context={
            "run_id": "run-001",
            "worker_token": "sk-worker-secret",
            "request": {
                "headers": {
                    "Authorization": "Bearer sk-header-secret",
                    "User-Agent": "pytest-client",
                },
                "data": {"contract_text": "raw confidential contract text"},
            },
        },
    )

    assert result.enabled is True
    assert result.captured is True
    assert result.reason == SENTRY_CAPTURED_REASON
    assert result.event_id == "event-001"
    assert len(fake_sdk.captured_events) == 1
    captured = fake_sdk.captured_events[0]
    captured_text = json.dumps(captured, sort_keys=True)
    assert "sk-runtime-secret" not in captured_text
    assert "sk-worker-secret" not in captured_text
    assert "sk-header-secret" not in captured_text
    assert "raw confidential contract text" not in captured_text
    assert captured["extra"]["run_id"] == "run-001"
    assert captured["extra"]["worker_token"] == REDACTED_VALUE
    assert captured["extra"]["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert captured["extra"]["request"]["headers"]["user-agent"] == "pytest-client"
    assert captured["extra"]["request"]["data"] == REDACTED_VALUE


def test_sentry_capture_exception_returns_disabled_without_calling_sdk() -> None:
    fake_sdk = _FakeSentrySdk()

    result = capture_sentry_exception(
        enabled=False,
        sdk_module=fake_sdk,
        exc=RuntimeError("should not be captured"),
        context={"token": "sk-secret"},
    )

    assert result.enabled is False
    assert result.captured is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert fake_sdk.captured_events == []


def test_sentry_capture_exception_suppresses_sdk_failures() -> None:
    result = capture_sentry_exception(
        enabled=True,
        sdk_module=_FailingCaptureSentrySdk(),
        exc=RuntimeError("capture failed"),
        context={"safe": "value"},
    )

    assert result.enabled is True
    assert result.captured is False
    assert result.reason == SENTRY_CAPTURE_FAILED_REASON


def test_initialize_sentry_from_fastapi_config_uses_config_fields() -> None:
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        sentry_environment="staging",
        sentry_release="nexa-release-001",
        sentry_traces_sample_rate=0.5,
    )

    result = initialize_sentry_from_config(config, sdk_module=fake_sdk)

    assert result.initialized is True
    assert result.reason == SENTRY_INITIALIZED_REASON
    assert fake_sdk.init_kwargs is not None
    assert fake_sdk.init_kwargs["environment"] == "staging"
    assert fake_sdk.init_kwargs["release"] == "nexa-release-001"
    assert fake_sdk.init_kwargs["traces_sample_rate"] == 0.5
    assert fake_sdk.init_kwargs["send_default_pii"] is False


def test_build_sentry_exception_event_is_scrubbed_before_sdk_boundary() -> None:
    event = build_sentry_exception_event(
        exc=RuntimeError("exception message contains sk-runtime-secret"),
        context={
            "workspace_id": "ws-001",
            "api_key": "sk-context-secret",
            "request": {
                "query_string": "token=sk-query-secret",
                "headers": {"Authorization": "Bearer sk-header-secret", "User-Agent": "pytest-client"},
                "json": {"prompt": "raw confidential user content"},
            },
        },
    )

    assert event is not None
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in event_text
    assert "sk-context-secret" not in event_text
    assert "sk-query-secret" not in event_text
    assert "sk-header-secret" not in event_text
    assert "raw confidential user content" not in event_text
    assert event["extra"]["workspace_id"] == "ws-001"
    assert event["extra"]["api_key"] == REDACTED_VALUE
    assert event["extra"]["request"]["headers"]["authorization"] == REDACTED_VALUE
    assert event["extra"]["request"]["headers"]["user-agent"] == "pytest-client"
    assert event["extra"]["request"]["json"] == REDACTED_VALUE


def test_capture_sentry_exception_from_fastapi_config_respects_disabled_default() -> None:
    fake_sdk = _FakeSentrySdk()
    result = capture_sentry_exception_from_config(
        config=FastApiBindingConfig(),
        sdk_module=fake_sdk,
        exc=RuntimeError("contains sk-secret"),
        context={"token": "sk-context-secret"},
    )

    assert result.enabled is False
    assert result.captured is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert fake_sdk.captured_events == []


def test_capture_sentry_exception_from_fastapi_config_captures_when_enabled() -> None:
    fake_sdk = _FakeSentrySdk()
    config = FastApiBindingConfig(
        sentry_enabled=True,
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    )

    result = capture_sentry_exception_from_config(
        config=config,
        sdk_module=fake_sdk,
        exc=RuntimeError("contains sk-secret"),
        context={"run_id": "run-001"},
    )

    assert result.enabled is True
    assert result.captured is True
    assert result.reason == SENTRY_CAPTURED_REASON
    assert result.event_id == "event-001"
    assert fake_sdk.captured_events[0]["extra"]["run_id"] == "run-001"
