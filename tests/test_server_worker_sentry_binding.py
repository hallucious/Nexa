from __future__ import annotations

import json

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.fastapi_binding_models import FastApiBindingConfig
from src.server.worker_sentry_binding import (
    build_worker_sentry_exception_event,
    capture_worker_sentry_exception,
    worker_sentry_enabled,
)
from src.server.sentry_observability_runtime import SENTRY_CAPTURED_REASON, SENTRY_DISABLED_REASON


class _FakeSentrySdk:
    def __init__(self) -> None:
        self.captured_events: list[dict] = []

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "worker-event-001"


def _payload() -> dict:
    return {
        "run_id": "run-worker-001",
        "workspace_id": "ws-worker-001",
        "run_request_id": "req-worker-001",
        "target_type": "commit_snapshot",
        "target_ref": "snap-worker-001",
        "provider_id": "anthropic",
        "model_id": "claude-haiku",
        "mode": "standard",
        "api_key": "sk-payload-secret",
    }


def test_worker_sentry_enabled_accepts_direct_flag_or_config() -> None:
    assert worker_sentry_enabled({"sentry_enabled": True}) is True
    assert worker_sentry_enabled({"sentry_config": FastApiBindingConfig(sentry_enabled=True)}) is True
    assert worker_sentry_enabled({"config": FastApiBindingConfig(sentry_enabled=True)}) is True
    assert worker_sentry_enabled({}) is False


def test_build_worker_sentry_exception_event_scrubs_job_payload_and_failure_reason() -> None:
    event = build_worker_sentry_exception_event(
        exc=RuntimeError("engine failed with sk-runtime-secret"),
        job_payload=_payload(),
        stage="engine_execution",
        failure_reason="engine_execution_error: sk-failure-secret",
        extra={"worker_token": "sk-worker-secret", "safe_count": 3},
    )

    assert event is not None
    serialized = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-payload-secret" not in serialized
    assert "sk-failure-secret" not in serialized
    assert "sk-worker-secret" not in serialized
    assert event["extra"]["worker"]["run_id"] == "run-worker-001"
    assert event["extra"]["worker"]["workspace_id"] == "ws-worker-001"
    assert event["extra"]["worker"]["stage"] == "engine_execution"
    assert event["extra"]["job_payload"]["api_key"] == REDACTED_VALUE
    assert event["extra"]["worker_token"] == REDACTED_VALUE
    assert event["extra"]["safe_count"] == 3


def test_capture_worker_sentry_exception_is_disabled_by_default() -> None:
    fake_sdk = _FakeSentrySdk()

    result = capture_worker_sentry_exception(
        ctx={"sentry_sdk": fake_sdk},
        exc=RuntimeError("contains sk-secret"),
        job_payload=_payload(),
        stage="engine_execution",
    )

    assert result.enabled is False
    assert result.captured is False
    assert result.reason == SENTRY_DISABLED_REASON
    assert fake_sdk.captured_events == []


def test_capture_worker_sentry_exception_emits_scrubbed_event_when_enabled() -> None:
    fake_sdk = _FakeSentrySdk()

    result = capture_worker_sentry_exception(
        ctx={"sentry_enabled": True, "sentry_sdk": fake_sdk},
        exc=RuntimeError("worker failed with sk-runtime-secret"),
        job_payload=_payload(),
        stage="engine_execution",
        failure_reason="engine_execution_error: sk-failure-secret",
    )

    assert result.enabled is True
    assert result.captured is True
    assert result.reason == SENTRY_CAPTURED_REASON
    assert result.event_id == "worker-event-001"
    assert len(fake_sdk.captured_events) == 1
    serialized = json.dumps(fake_sdk.captured_events[0], sort_keys=True)
    assert "sk-runtime-secret" not in serialized
    assert "sk-payload-secret" not in serialized
    assert "sk-failure-secret" not in serialized
    assert fake_sdk.captured_events[0]["extra"]["worker"]["run_id"] == "run-worker-001"
