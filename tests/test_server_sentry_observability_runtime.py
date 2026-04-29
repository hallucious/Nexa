from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.sentry_observability_runtime import (
    SENTRY_DISABLED_REASON,
    SENTRY_DSN_MISSING_REASON,
    SENTRY_INITIALIZED_REASON,
    initialize_sentry_observability,
    scrub_sentry_event,
)


class _FakeSentrySdk:
    def __init__(self) -> None:
        self.init_kwargs = None

    def init(self, **kwargs):
        self.init_kwargs = dict(kwargs)


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
