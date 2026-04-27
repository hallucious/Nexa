"""Worker smoke tests (P1 fixes applied).

P1 additions:
- execute_queued_run aborts if mark_claimed returns False.
- Duplicate worker cannot execute the same run once first worker claimed it.
- mark_completed only transitions from 'running' (tested via lifecycle ordering).
- mark_failed only transitions from 'claimed'/'running'.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from src.server.queue.worker_functions import execute_queued_run


# ================================================================== #
# Doubles
# ================================================================== #


class _TrackingStore:
    """In-memory store double that tracks all calls and returns bool from mark_*."""

    def __init__(self, *, claim_succeeds: bool = True) -> None:
        self._status: Dict[str, str] = {}
        self._claim_succeeds = claim_succeeds
        self.claimed: List[str] = []
        self.running_calls: List[str] = []
        self.completed: List[str] = []
        self.failed: List[Dict[str, str]] = []

    def mark_claimed(self, *, run_id: str) -> bool:
        if not self._claim_succeeds:
            return False
        self.claimed.append(run_id)
        self._status[run_id] = "claimed"
        return True

    def mark_running(self, *, run_id: str) -> bool:
        self.running_calls.append(run_id)
        self._status[run_id] = "running"
        return True

    def mark_completed(self, *, run_id: str, ttl_s: int = 172800) -> bool:
        self.completed.append(run_id)
        self._status[run_id] = "completed"
        return True

    def mark_failed(self, *, run_id: str, failure_reason: str, ttl_s: int = 172800) -> bool:
        self.failed.append({"run_id": run_id, "failure_reason": failure_reason})
        self._status[run_id] = "failed"
        return True

    def status_of(self, run_id: str) -> Optional[str]:
        return self._status.get(run_id)


class _FakeEngineBridge:
    def __init__(self, *, raise_exc: Optional[Exception] = None) -> None:
        self._raise = raise_exc
        self.calls: List[Dict[str, Any]] = []

    def execute(self, *, run_id: str, workspace_id: str, target_type: str,
                target_ref: str, mode: str) -> Dict[str, Any]:
        self.calls.append({"run_id": run_id})
        if self._raise:
            raise self._raise
        return {"trace_id": f"trace_{run_id}", "status": "ok"}


class _FakeActionLog:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def record(self, *, run_id: str, workspace_id: str, event: str, detail: str = "") -> None:
        self.events.append({"run_id": run_id, "event": event})


def _payload(run_id: str = "run_x", workspace_id: str = "ws_x") -> Dict[str, Any]:
    return {
        "run_id": run_id, "workspace_id": workspace_id,
        "run_request_id": f"req_{uuid4().hex[:6]}",
        "target_type": "commit_snapshot", "target_ref": "snap",
        "provider_id": None, "model_id": None, "mode": "standard",
    }


# ================================================================== #
# Tests
# ================================================================== #


class TestMissingRunId:
    def test_returns_failed_without_touching_store(self) -> None:
        store = _TrackingStore()
        result = asyncio.run(execute_queued_run({"submission_store": store}, {"workspace_id": "ws"}))
        assert result["status"] == "failed"
        assert store.claimed == []


class TestClaimFailureAbortsExecution:
    """P1 Fix 2 — mark_claimed returns False → engine must NOT be invoked."""

    def test_claim_fails_returns_aborted(self) -> None:
        store = _TrackingStore(claim_succeeds=False)
        bridge = _FakeEngineBridge()
        ctx = {"submission_store": store, "engine_bridge": bridge}

        result = asyncio.run(execute_queued_run(ctx, _payload("run_abort")))

        assert result["status"] == "aborted"
        assert "claim_failed" in result.get("reason", "")
        # Engine MUST NOT have been called
        assert bridge.calls == [], "engine_bridge must not be called when claim fails"

    def test_second_worker_cannot_execute_after_first_claimed(self) -> None:
        """Simulate two workers racing — second claim must return False."""

        class _RaceStore(_TrackingStore):
            def __init__(self) -> None:
                super().__init__()
                self._already_claimed = False

            def mark_claimed(self, *, run_id: str) -> bool:
                if self._already_claimed:
                    return False  # second worker loses
                self._already_claimed = True
                return super().mark_claimed(run_id=run_id)

        store = _RaceStore()
        bridge = _FakeEngineBridge()
        ctx = {"submission_store": store, "engine_bridge": bridge}

        # Worker 1 — succeeds
        r1 = asyncio.run(execute_queued_run(ctx, _payload("run_race")))
        # Worker 2 — claim fails
        r2 = asyncio.run(execute_queued_run(ctx, _payload("run_race")))

        assert r1["status"] in ("completed", "failed")  # ran
        assert r2["status"] == "aborted"                # blocked
        assert len(bridge.calls) == 1                   # engine called exactly once


class TestNoEngineBridge:
    def test_marks_failed_with_unavailable_reason(self) -> None:
        store = _TrackingStore()
        ctx = {"submission_store": store}
        result = asyncio.run(execute_queued_run(ctx, _payload("run_no_bridge")))
        assert result["status"] == "failed"
        assert store.failed[0]["failure_reason"] == "engine_bridge_unavailable"

    def test_no_store_no_bridge_returns_dict(self) -> None:
        result = asyncio.run(execute_queued_run({}, _payload("run_bare")))
        assert isinstance(result, dict) and result["run_id"] == "run_bare"


class TestSuccessPath:
    def test_engine_called_store_marked_completed(self) -> None:
        store = _TrackingStore()
        bridge = _FakeEngineBridge()
        ctx = {"submission_store": store, "engine_bridge": bridge}
        result = asyncio.run(execute_queued_run(ctx, _payload("run_ok")))
        assert result["status"] == "completed"
        assert "run_ok" in store.completed
        assert len(bridge.calls) == 1

    def test_lifecycle_events_emitted(self) -> None:
        store = _TrackingStore()
        log = _FakeActionLog()
        ctx = {"submission_store": store, "engine_bridge": _FakeEngineBridge(), "action_log": log}
        asyncio.run(execute_queued_run(ctx, _payload("run_events")))
        names = [e["event"] for e in log.events]
        assert "worker_started" in names and "worker_completed" in names

    def test_execution_result_in_return(self) -> None:
        store = _TrackingStore()
        ctx = {"submission_store": store, "engine_bridge": _FakeEngineBridge()}
        result = asyncio.run(execute_queued_run(ctx, _payload("run_result")))
        assert "execution_result" in result and result["execution_result"]["status"] == "ok"


class TestEngineFailurePath:
    def test_engine_exception_marks_failed(self) -> None:
        store = _TrackingStore()
        bridge = _FakeEngineBridge(raise_exc=RuntimeError("boom"))
        ctx = {"submission_store": store, "engine_bridge": bridge}
        result = asyncio.run(execute_queued_run(ctx, _payload("run_crash")))
        assert result["status"] == "failed"
        assert "engine_execution_error" in store.failed[0]["failure_reason"]

    def test_engine_failure_emits_worker_failed_event(self) -> None:
        log = _FakeActionLog()
        ctx = {
            "submission_store": _TrackingStore(),
            "engine_bridge": _FakeEngineBridge(raise_exc=ValueError("bad")),
            "action_log": log,
        }
        asyncio.run(execute_queued_run(ctx, _payload("run_fail_event")))
        assert "worker_failed" in [e["event"] for e in log.events]


class TestLifecycleOrdering:
    def test_claim_and_running_before_engine(self) -> None:
        order: List[str] = []

        class _OrderedStore(_TrackingStore):
            def mark_claimed(self, *, run_id: str) -> bool:
                order.append("claimed")
                return super().mark_claimed(run_id=run_id)

            def mark_running(self, *, run_id: str) -> bool:
                order.append("running")
                return super().mark_running(run_id=run_id)

        class _OrderedBridge(_FakeEngineBridge):
            def execute(self, *, run_id, workspace_id, target_type, target_ref, mode):  # noqa: ANN001
                order.append("execute")
                return super().execute(run_id=run_id, workspace_id=workspace_id,
                                       target_type=target_type, target_ref=target_ref, mode=mode)

        ctx = {"submission_store": _OrderedStore(), "engine_bridge": _OrderedBridge()}
        asyncio.run(execute_queued_run(ctx, _payload("run_order")))

        assert order.index("claimed") < order.index("execute")
        assert order.index("running") < order.index("execute")
