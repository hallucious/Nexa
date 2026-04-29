from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional
from uuid import uuid4

from src.server.edge_observability_runtime import REDACTED_VALUE
from src.server.queue.worker_functions import execute_queued_run
from src.server.sentry_observability_runtime import SENTRY_CAPTURED_REASON


class _TrackingStore:
    def __init__(self) -> None:
        self.claimed: list[str] = []
        self.running_calls: list[str] = []
        self.completed: list[str] = []
        self.failed: list[dict[str, str]] = []

    def mark_claimed(self, *, run_id: str) -> bool:
        self.claimed.append(run_id)
        return True

    def mark_running(self, *, run_id: str) -> bool:
        self.running_calls.append(run_id)
        return True

    def mark_completed(self, *, run_id: str, ttl_s: int = 172800) -> bool:
        self.completed.append(run_id)
        return True

    def mark_failed(self, *, run_id: str, failure_reason: str, ttl_s: int = 172800) -> bool:
        self.failed.append({"run_id": run_id, "failure_reason": failure_reason})
        return True


class _ClaimRaisingStore(_TrackingStore):
    def mark_claimed(self, *, run_id: str) -> bool:
        raise RuntimeError("claim failed with sk-claim-secret")


class _FakeEngineBridge:
    def __init__(self, *, raise_exc: Optional[Exception] = None) -> None:
        self._raise = raise_exc
        self.calls: list[dict[str, Any]] = []

    def execute(self, *, run_id: str, workspace_id: str, target_type: str, target_ref: str, mode: str) -> Dict[str, Any]:
        self.calls.append({"run_id": run_id})
        if self._raise:
            raise self._raise
        return {"trace_id": f"trace_{run_id}", "status": "ok"}


class _FakeSentrySdk:
    def __init__(self) -> None:
        self.captured_events: list[dict] = []

    def capture_event(self, event):
        self.captured_events.append(dict(event))
        return "worker-runtime-event-001"


def _payload(run_id: str = "run_worker", workspace_id: str = "ws_worker") -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "run_request_id": f"req_{uuid4().hex[:6]}",
        "target_type": "commit_snapshot",
        "target_ref": "snap",
        "provider_id": None,
        "model_id": None,
        "mode": "standard",
        "api_key": "sk-payload-secret",
    }


def test_worker_engine_exception_captures_sentry_without_changing_failure_result() -> None:
    fake_sdk = _FakeSentrySdk()
    store = _TrackingStore()
    ctx = {
        "submission_store": store,
        "engine_bridge": _FakeEngineBridge(raise_exc=RuntimeError("engine failed with sk-runtime-secret")),
        "sentry_enabled": True,
        "sentry_sdk": fake_sdk,
    }

    result = asyncio.run(execute_queued_run(ctx, _payload("run_worker_crash")))

    assert result["status"] == "failed"
    assert "engine_execution_error" in result["failure_reason"]
    assert store.failed[0]["run_id"] == "run_worker_crash"
    assert len(fake_sdk.captured_events) == 1
    event = fake_sdk.captured_events[0]
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in event_text
    assert "sk-payload-secret" not in event_text
    assert event["extra"]["worker"]["run_id"] == "run_worker_crash"
    assert event["extra"]["worker"]["stage"] == "engine_execution"
    assert event["extra"]["job_payload"]["api_key"] == REDACTED_VALUE


def test_worker_claim_error_captures_sentry_before_abort() -> None:
    fake_sdk = _FakeSentrySdk()
    ctx = {
        "submission_store": _ClaimRaisingStore(),
        "engine_bridge": _FakeEngineBridge(),
        "sentry_enabled": True,
        "sentry_sdk": fake_sdk,
    }

    result = asyncio.run(execute_queued_run(ctx, _payload("run_claim_error")))

    assert result["status"] == "aborted"
    assert "claim_error" in result["reason"]
    assert len(fake_sdk.captured_events) == 1
    event_text = json.dumps(fake_sdk.captured_events[0], sort_keys=True)
    assert "sk-claim-secret" not in event_text
    assert "sk-payload-secret" not in event_text
    assert fake_sdk.captured_events[0]["extra"]["worker"]["stage"] == "mark_claimed"


def test_worker_sentry_capture_failure_is_suppressed() -> None:
    class _FailingSentrySdk:
        def capture_event(self, event):
            raise RuntimeError("sentry unavailable")

    store = _TrackingStore()
    ctx = {
        "submission_store": store,
        "engine_bridge": _FakeEngineBridge(raise_exc=RuntimeError("engine failed")),
        "sentry_enabled": True,
        "sentry_sdk": _FailingSentrySdk(),
    }

    result = asyncio.run(execute_queued_run(ctx, _payload("run_capture_suppressed")))

    assert result["status"] == "failed"
    assert store.failed[0]["run_id"] == "run_capture_suppressed"
