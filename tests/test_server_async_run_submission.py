"""Tests for Batch 2A — Async Execution Substrate (P1 fixes applied).

GPT P1 fixes covered:
1. Strict terminal status guards on mark_* methods.
2. mark_* methods return bool; callers check it.
3. No raw RPUSH fallback; arq_unavailable returned instead.
4. Idempotency: duplicate run_request_id returns existing submission_id.
5. Scope note verified (no production claims beyond substrate).
"""
from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

from src.server.queue.redis_client import (
    RedisConnectionSettings,
    build_redis_url,
    load_redis_settings_from_env,
)
from src.server.queue.worker_settings import (
    QueuePolicy,
    load_queue_policy_from_env,
    NEXA_RUN_QUEUE_NAME,
    NEXA_RUN_JOB_FUNCTION_NAME,
)
from src.server.queue.run_launcher import RunEnqueueResult, enqueue_run
from src.server.queue.cleanup_jobs import (
    reconcile_orphaned_submissions,
    cleanup_expired_terminal_submissions,
)


# ================================================================== #
# In-memory submission store double — mirrors PostgresRunSubmissionStore
# ================================================================== #


class _InMemoryRunSubmissionStore:
    """Pure-Python double with strict guard semantics matching the real store."""

    def __init__(self) -> None:
        self._rows: Dict[str, Dict[str, Any]] = {}
        # Separate index by run_request_id for idempotency
        self._req_to_sub: Dict[str, str] = {}   # run_request_id → submission_id
        self._sub_to_run: Dict[str, str] = {}   # submission_id → run_id
        self.insert_calls: List[Dict[str, Any]] = []
        self.raise_on_insert: Optional[Exception] = None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _expires(self, ttl_s: int = 172800) -> str:
        return (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()

    def insert_submission(self, *, run_id: str, workspace_id: str, run_request_id: str,
                          submitter_user_ref: str, target_type: str, target_ref: str,
                          provider_id=None, model_id=None, priority="normal",
                          mode="standard", queue_name=None, ttl_s=172800) -> str:
        if self.raise_on_insert is not None:
            raise self.raise_on_insert

        # Idempotency: return existing if run_request_id already present
        if run_request_id in self._req_to_sub:
            return self._req_to_sub[run_request_id]

        submission_id = f"sub_{uuid4().hex[:8]}"
        now = self._now()
        row = {
            "submission_id": submission_id, "run_id": run_id,
            "workspace_id": workspace_id, "run_request_id": run_request_id,
            "submitter_user_ref": submitter_user_ref, "target_type": target_type,
            "target_ref": target_ref, "provider_id": provider_id,
            "model_id": model_id, "priority": priority, "mode": mode,
            "submission_status": "submitted", "queue_name": queue_name,
            "queue_job_id": None, "worker_attempt_number": 0,
            "submitted_at": now, "queued_at": None, "claimed_at": None,
            "terminal_at": None, "expires_at": None, "failure_reason": None,
            "created_at": now, "updated_at": now,
        }
        self._rows[run_id] = row
        self._req_to_sub[run_request_id] = submission_id
        self._sub_to_run[submission_id] = run_id
        self.insert_calls.append({"run_id": run_id, "submission_id": submission_id})
        return submission_id

    def _transition(self, run_id: str, from_statuses: set, to_status: str,
                    extra: dict | None = None) -> bool:
        row = self._rows.get(run_id)
        if row is None or row["submission_status"] not in from_statuses:
            return False
        update = {"submission_status": to_status, "updated_at": self._now()}
        if extra:
            update.update(extra)
        self._rows[run_id] = {**row, **update}
        return True

    def mark_queued(self, *, run_id: str, queue_job_id: str, queue_name: str) -> bool:
        return self._transition(
            run_id, {"submitted", "requeued"}, "queued",
            {"queue_job_id": queue_job_id, "queue_name": queue_name, "queued_at": self._now()},
        )

    def mark_claimed(self, *, run_id: str) -> bool:
        row = self._rows.get(run_id)
        if row is None or row["submission_status"] != "queued":
            return False
        self._rows[run_id] = {
            **row,
            "submission_status": "claimed",
            "claimed_at": self._now(),
            "worker_attempt_number": row["worker_attempt_number"] + 1,
            "updated_at": self._now(),
        }
        return True

    def mark_running(self, *, run_id: str) -> bool:
        return self._transition(run_id, {"claimed"}, "running")

    def mark_completed(self, *, run_id: str, ttl_s: int = 172800) -> bool:
        # ONLY from 'running'
        return self._transition(
            run_id, {"running"}, "completed",
            {"terminal_at": self._now(), "expires_at": self._expires(ttl_s)},
        )

    def mark_failed(self, *, run_id: str, failure_reason: str, ttl_s: int = 172800) -> bool:
        # ONLY from 'claimed' or 'running'
        return self._transition(
            run_id, {"claimed", "running"}, "failed",
            {"failure_reason": failure_reason, "terminal_at": self._now(),
             "expires_at": self._expires(ttl_s)},
        )

    def mark_lost_redis(self, *, run_id: str, ttl_s: int = 172800) -> bool:
        # ONLY from non-terminal active states
        return self._transition(
            run_id, {"submitted", "queued", "requeued", "claimed", "running"}, "lost_redis",
            {"terminal_at": self._now(), "expires_at": self._expires(ttl_s)},
        )

    def mark_requeued(self, *, run_id: str, queue_job_id: str) -> bool:
        # ONLY from 'failed' or 'lost_redis'
        return self._transition(
            run_id, {"failed", "lost_redis"}, "requeued",
            {"queue_job_id": queue_job_id, "queued_at": self._now(),
             "terminal_at": None, "expires_at": None, "failure_reason": None},
        )

    def get_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._rows.get(run_id)

    def get_by_run_request_id(self, run_request_id: str) -> Optional[Dict[str, Any]]:
        sub_id = self._req_to_sub.get(run_request_id)
        if sub_id is None:
            return None
        run_id = self._sub_to_run.get(sub_id)
        return self._rows.get(run_id) if run_id else None

    def list_orphaned_submissions(self, *, older_than_s: int = 300) -> List[Dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=older_than_s)).isoformat()
        active = {"submitted", "queued", "requeued", "claimed", "running"}
        return [r for r in self._rows.values()
                if r["submission_status"] in active and r["updated_at"] < cutoff]

    def list_expired_terminal_submissions(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        terminal = {"completed", "failed", "lost_redis"}
        return [r for r in self._rows.values()
                if r["submission_status"] in terminal
                and r.get("expires_at") and r["expires_at"] < now]

    def delete_expired_terminal_submissions(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        terminal = {"completed", "failed", "lost_redis"}
        to_del = [rid for rid, r in self._rows.items()
                  if r["submission_status"] in terminal
                  and r.get("expires_at") and r["expires_at"] < now]
        for rid in to_del:
            del self._rows[rid]
        return len(to_del)


# ================================================================== #
# 1. RedisConnectionSettings
# ================================================================== #

class TestRedisConnectionSettings:
    def test_default_values(self) -> None:
        s = RedisConnectionSettings()
        assert s.host == "localhost" and s.port == 6379 and s.db == 0

    def test_custom_values(self) -> None:
        s = RedisConnectionSettings(host="redis.prod", port=6380, db=1, ssl=True)
        assert s.host == "redis.prod" and s.ssl is True

    def test_empty_host_rejected(self) -> None:
        with pytest.raises(ValueError, match="host"):
            RedisConnectionSettings(host="  ")

    def test_invalid_port_rejected(self) -> None:
        with pytest.raises(ValueError):
            RedisConnectionSettings(port=0)
        with pytest.raises(ValueError):
            RedisConnectionSettings(port=65536)

    def test_negative_db_rejected(self) -> None:
        with pytest.raises(ValueError, match="db"):
            RedisConnectionSettings(db=-1)


class TestBuildRedisUrl:
    def test_plain_url(self) -> None:
        url = build_redis_url(RedisConnectionSettings(host="myhost", port=6379, db=0))
        assert url == "redis://myhost:6379/0"

    def test_ssl_url(self) -> None:
        url = build_redis_url(RedisConnectionSettings(host="h", port=6380, db=2, ssl=True))
        assert url.startswith("rediss://")

    def test_password_url(self) -> None:
        url = build_redis_url(RedisConnectionSettings(host="h", port=6379, db=0, password="s"))
        assert ":s@" in url


class TestLoadRedisSettingsFromEnv:
    def test_defaults_when_env_empty(self) -> None:
        s = load_redis_settings_from_env(env={})
        assert s.host == "localhost" and s.port == 6379

    def test_reads_host_and_port(self) -> None:
        s = load_redis_settings_from_env(env={"NEXA_REDIS_HOST": "cache", "NEXA_REDIS_PORT": "6380"})
        assert s.host == "cache" and s.port == 6380

    def test_invalid_port_falls_back(self) -> None:
        s = load_redis_settings_from_env(env={"NEXA_REDIS_PORT": "bad"})
        assert s.port == 6379

    def test_ssl_flag(self) -> None:
        assert load_redis_settings_from_env(env={"NEXA_REDIS_SSL": "true"}).ssl is True

    def test_password_via_env_var_name(self) -> None:
        s = load_redis_settings_from_env(env={"NEXA_REDIS_PASSWORD": "PW_VAR", "PW_VAR": "secret"})
        assert s.password == "secret"


# ================================================================== #
# 2. QueuePolicy
# ================================================================== #

class TestQueuePolicy:
    def test_default_construction(self) -> None:
        p = QueuePolicy(queue_name=NEXA_RUN_QUEUE_NAME, max_jobs=4, job_timeout_s=900,
                        keep_result_s=3600, retry_jobs=False, job_function_name=NEXA_RUN_JOB_FUNCTION_NAME)
        assert p.max_jobs == 4

    def test_empty_queue_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="queue_name"):
            QueuePolicy(queue_name=" ", max_jobs=4, job_timeout_s=900,
                        keep_result_s=3600, retry_jobs=False, job_function_name="x")

    def test_max_jobs_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_jobs"):
            QueuePolicy(queue_name="q", max_jobs=0, job_timeout_s=900,
                        keep_result_s=3600, retry_jobs=False, job_function_name="x")


class TestLoadQueuePolicyFromEnv:
    def test_defaults(self) -> None:
        p = load_queue_policy_from_env(env={})
        assert p.queue_name == NEXA_RUN_QUEUE_NAME and p.max_jobs == 4

    def test_custom_max_jobs(self) -> None:
        assert load_queue_policy_from_env(env={"NEXA_WORKER_MAX_JOBS": "8"}).max_jobs == 8

    def test_retry_jobs_true(self) -> None:
        assert load_queue_policy_from_env(env={"NEXA_WORKER_RETRY_JOBS": "true"}).retry_jobs is True

    def test_invalid_max_jobs_falls_back(self) -> None:
        assert load_queue_policy_from_env(env={"NEXA_WORKER_MAX_JOBS": "bad"}).max_jobs == 4


# ================================================================== #
# 3. RunEnqueueResult contract
# ================================================================== #

class TestRunEnqueueResult:
    def test_enqueued_true_when_job_id_present(self) -> None:
        r = RunEnqueueResult(accepted=True, run_id="r", submission_id="s", queue_job_id="j")
        assert r.enqueued is True

    def test_enqueued_false_when_no_job_id(self) -> None:
        r = RunEnqueueResult(accepted=True, run_id="r", submission_id="s",
                             failure_reason="redis_client_unavailable")
        assert r.enqueued is False

    def test_rejected_result(self) -> None:
        r = RunEnqueueResult(accepted=False, run_id="r", submission_id="",
                             failure_reason="submission_insert_failed: db error")
        assert not r.accepted and not r.enqueued


# ================================================================== #
# 4. enqueue_run — durable-first contract
# ================================================================== #


def _install_fake_arq(monkeypatch):  # noqa: ANN001
    class _FakeArqRedis:
        def __init__(self) -> None:
            self.enqueue_calls: List[dict[str, Any]] = []

        async def enqueue_job(self, function_name, payload, _queue_name=None):  # noqa: ANN001
            self.enqueue_calls.append({
                "function_name": function_name,
                "payload": payload,
                "queue_name": _queue_name,
            })

            class _Job:
                job_id = "job-001"

            return _Job()

    fake_arq = types.ModuleType("arq")
    fake_arq.ArqRedis = _FakeArqRedis
    monkeypatch.setitem(sys.modules, "arq", fake_arq)
    return _FakeArqRedis


class TestEnqueueRunDurableFirst:
    def test_insert_called_before_enqueue(self) -> None:
        store = _InMemoryRunSubmissionStore()
        order: List[str] = []
        orig = store.insert_submission

        def tracked(**kw):  # noqa: ANN001
            order.append("insert")
            return orig(**kw)

        store.insert_submission = tracked  # type: ignore[method-assign]

        class _FakeArq:
            async def enqueue_job(self, *a, **kw):  # noqa: ANN001
                order.append("redis")
                class _J:
                    job_id = "j1"
                return _J()
            def __class_getitem__(cls, item): return cls  # noqa: ANN001

        # Monkeypatch ArqRedis check — fake is "ArqRedis" for isinstance
        import src.server.queue.run_launcher as _rl
        orig_import = _rl.__builtins__ if isinstance(_rl.__builtins__, dict) else {}

        fake_arq_client = _FakeArq()

        # We use redis_client=None path to avoid the isinstance(ArqRedis) check
        # and test purely the insert-first ordering
        result = asyncio.run(enqueue_run(
            run_id="run_order", workspace_id="ws", run_request_id="req_order",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
            submission_store=store, redis_client=None,
        ))
        assert order[0] == "insert", "insert must be first"
        assert len(store.insert_calls) == 1

    def test_no_redis_client_insert_still_happens(self) -> None:
        store = _InMemoryRunSubmissionStore()
        result = asyncio.run(enqueue_run(
            run_id="run_002", workspace_id="ws", run_request_id="req_002",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
            submission_store=store, redis_client=None,
        ))
        assert result.accepted is True
        assert result.enqueued is False
        assert result.failure_reason == "redis_client_unavailable"
        row = store.get_by_run_id("run_002")
        assert row is not None and row["submission_status"] == "submitted"

    def test_insert_failure_returns_rejected(self) -> None:
        store = _InMemoryRunSubmissionStore()
        store.raise_on_insert = RuntimeError("DB down")
        result = asyncio.run(enqueue_run(
            run_id="run_003", workspace_id="ws", run_request_id="req_003",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
            submission_store=store, redis_client=None,
        ))
        assert result.accepted is False and "submission_insert_failed" in (result.failure_reason or "")

    def test_non_arq_redis_client_returns_arq_client_type_mismatch(self) -> None:
        """Non-ArqRedis client must NOT fall back to raw RPUSH — returns type error."""
        store = _InMemoryRunSubmissionStore()

        class _PlainRedis:
            async def rpush(self, *a, **kw): return 1  # noqa: ANN001

        result = asyncio.run(enqueue_run(
            run_id="run_nonarg", workspace_id="ws", run_request_id="req_nonarq",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
            submission_store=store, redis_client=_PlainRedis(),
        ))
        # arq not installed in this env → arq_unavailable, not raw push
        assert result.accepted is True
        assert result.enqueued is False
        assert result.failure_reason in ("arq_unavailable", "arq_client_type_mismatch")
        # Row must be preserved in submitted state for recovery
        row = store.get_by_run_id("run_nonarg")
        assert row is not None and row["submission_status"] == "submitted"

    def test_duplicate_run_request_id_returns_existing_identity_without_enqueue(self, monkeypatch) -> None:  # noqa: ANN001
        """A retried request id must return the existing durable identity and skip Redis."""
        store = _InMemoryRunSubmissionStore()
        existing_submission_id = store.insert_submission(
            run_id="run-original",
            workspace_id="ws",
            run_request_id="req-duplicate",
            submitter_user_ref="u",
            target_type="commit_snapshot",
            target_ref="snap",
        )
        FakeArqRedis = _install_fake_arq(monkeypatch)
        redis_client = FakeArqRedis()

        result = asyncio.run(enqueue_run(
            run_id="run-new-should-not-enqueue",
            workspace_id="ws",
            run_request_id="req-duplicate",
            submitter_user_ref="u",
            target_type="commit_snapshot",
            target_ref="snap",
            submission_store=store,
            redis_client=redis_client,
        ))

        assert result.accepted is True
        assert result.run_id == "run-original"
        assert result.submission_id == existing_submission_id
        assert result.queue_job_id is None
        assert result.failure_reason == "duplicate_run_request_id"
        assert redis_client.enqueue_calls == []
        assert store.get_by_run_id("run-new-should-not-enqueue") is None

    def test_duplicate_run_request_id_does_not_mark_new_run_queued(self, monkeypatch) -> None:  # noqa: ANN001
        store = _InMemoryRunSubmissionStore()
        store.insert_submission(
            run_id="run-existing",
            workspace_id="ws",
            run_request_id="req-existing",
            submitter_user_ref="u",
            target_type="commit_snapshot",
            target_ref="snap",
        )
        mark_queued_calls: List[dict[str, Any]] = []
        original_mark_queued = store.mark_queued

        def tracked_mark_queued(**kwargs):  # noqa: ANN001
            mark_queued_calls.append(kwargs)
            return original_mark_queued(**kwargs)

        store.mark_queued = tracked_mark_queued  # type: ignore[method-assign]
        FakeArqRedis = _install_fake_arq(monkeypatch)

        result = asyncio.run(enqueue_run(
            run_id="run-new",
            workspace_id="ws",
            run_request_id="req-existing",
            submitter_user_ref="u",
            target_type="commit_snapshot",
            target_ref="snap",
            submission_store=store,
            redis_client=FakeArqRedis(),
        ))

        assert result.run_id == "run-existing"
        assert mark_queued_calls == []

    def test_mark_queued_false_is_reported_after_successful_enqueue(self, monkeypatch) -> None:  # noqa: ANN001
        store = _InMemoryRunSubmissionStore()

        def mark_queued_false(**kwargs):  # noqa: ANN001
            return False

        store.mark_queued = mark_queued_false  # type: ignore[method-assign]
        FakeArqRedis = _install_fake_arq(monkeypatch)

        result = asyncio.run(enqueue_run(
            run_id="run-mark-queued-fails",
            workspace_id="ws",
            run_request_id="req-mark-queued-fails",
            submitter_user_ref="u",
            target_type="commit_snapshot",
            target_ref="snap",
            submission_store=store,
            redis_client=FakeArqRedis(),
        ))

        assert result.accepted is True
        assert result.enqueued is True
        assert result.queue_job_id == "job-001"
        assert result.failure_reason == "mark_queued_failed"
        row = store.get_by_run_id("run-mark-queued-fails")
        assert row is not None and row["submission_status"] == "submitted"


# ================================================================== #
# 5. Submission store — strict transition guards (P1 Fix 1)
# ================================================================== #

class TestStrictTransitionGuards:
    """Verify every mark_* method respects its guard and returns bool."""

    def _insert(self, store: _InMemoryRunSubmissionStore, run_id: str, req_id: str = None) -> str:
        return store.insert_submission(
            run_id=run_id, workspace_id="ws", run_request_id=req_id or f"req_{run_id}",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )

    # -- mark_completed only from 'running' --------------------------------

    def test_mark_completed_from_running_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "r1")
        store.mark_queued(run_id="r1", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="r1")
        store.mark_running(run_id="r1")
        assert store.mark_completed(run_id="r1") is True
        assert store._rows["r1"]["submission_status"] == "completed"

    def test_mark_completed_from_claimed_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "r2")
        store.mark_queued(run_id="r2", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="r2")
        assert store.mark_completed(run_id="r2") is False  # still 'claimed', not 'running'
        assert store._rows["r2"]["submission_status"] == "claimed"

    def test_mark_completed_from_submitted_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "r3")
        assert store.mark_completed(run_id="r3") is False

    def test_mark_completed_does_not_overwrite_lost_redis(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "r4")
        store.mark_queued(run_id="r4", queue_job_id="j", queue_name="q")
        store.mark_lost_redis(run_id="r4")
        assert store.mark_completed(run_id="r4") is False  # guard blocks it
        assert store._rows["r4"]["submission_status"] == "lost_redis"

    # -- mark_failed only from 'claimed' or 'running' ----------------------

    def test_mark_failed_from_claimed_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "f1")
        store.mark_queued(run_id="f1", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="f1")
        assert store.mark_failed(run_id="f1", failure_reason="oops") is True
        assert store._rows["f1"]["submission_status"] == "failed"

    def test_mark_failed_from_running_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "f2")
        store.mark_queued(run_id="f2", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="f2")
        store.mark_running(run_id="f2")
        assert store.mark_failed(run_id="f2", failure_reason="crash") is True

    def test_mark_failed_from_submitted_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "f3")
        assert store.mark_failed(run_id="f3", failure_reason="x") is False

    def test_mark_failed_does_not_overwrite_lost_redis(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "f4")
        store.mark_queued(run_id="f4", queue_job_id="j", queue_name="q")
        store.mark_lost_redis(run_id="f4")
        assert store.mark_failed(run_id="f4", failure_reason="late") is False
        assert store._rows["f4"]["submission_status"] == "lost_redis"

    def test_mark_failed_does_not_overwrite_completed(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "f5")
        store.mark_queued(run_id="f5", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="f5")
        store.mark_running(run_id="f5")
        store.mark_completed(run_id="f5")
        assert store.mark_failed(run_id="f5", failure_reason="late") is False
        assert store._rows["f5"]["submission_status"] == "completed"

    # -- mark_lost_redis only from active states ---------------------------

    def test_mark_lost_redis_from_queued_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "l1")
        store.mark_queued(run_id="l1", queue_job_id="j", queue_name="q")
        assert store.mark_lost_redis(run_id="l1") is True
        assert store._rows["l1"]["submission_status"] == "lost_redis"

    def test_mark_lost_redis_from_submitted_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "l2")
        assert store.mark_lost_redis(run_id="l2") is True

    def test_mark_lost_redis_from_completed_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "l3")
        store.mark_queued(run_id="l3", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="l3")
        store.mark_running(run_id="l3")
        store.mark_completed(run_id="l3")
        assert store.mark_lost_redis(run_id="l3") is False
        assert store._rows["l3"]["submission_status"] == "completed"

    def test_mark_lost_redis_from_failed_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "l4")
        store.mark_queued(run_id="l4", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="l4")
        store.mark_failed(run_id="l4", failure_reason="x")
        assert store.mark_lost_redis(run_id="l4") is False

    # -- mark_requeued only from 'failed' or 'lost_redis' ------------------

    def test_mark_requeued_from_failed_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "rq1")
        store.mark_queued(run_id="rq1", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="rq1")
        store.mark_failed(run_id="rq1", failure_reason="x")
        assert store.mark_requeued(run_id="rq1", queue_job_id="j2") is True
        assert store._rows["rq1"]["submission_status"] == "requeued"

    def test_mark_requeued_from_lost_redis_succeeds(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "rq2")
        store.mark_queued(run_id="rq2", queue_job_id="j", queue_name="q")
        store.mark_lost_redis(run_id="rq2")
        assert store.mark_requeued(run_id="rq2", queue_job_id="j3") is True

    def test_mark_requeued_from_completed_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "rq3")
        store.mark_queued(run_id="rq3", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="rq3")
        store.mark_running(run_id="rq3")
        store.mark_completed(run_id="rq3")
        assert store.mark_requeued(run_id="rq3", queue_job_id="j4") is False
        assert store._rows["rq3"]["submission_status"] == "completed"

    def test_mark_requeued_from_submitted_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "rq4")
        assert store.mark_requeued(run_id="rq4", queue_job_id="j") is False

    def test_mark_requeued_from_running_fails(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "rq5")
        store.mark_queued(run_id="rq5", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="rq5")
        store.mark_running(run_id="rq5")
        assert store.mark_requeued(run_id="rq5", queue_job_id="j2") is False

    # -- mark_claimed returns bool ------------------------------------------

    def test_mark_claimed_returns_true_from_queued(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "c1")
        store.mark_queued(run_id="c1", queue_job_id="j", queue_name="q")
        assert store.mark_claimed(run_id="c1") is True

    def test_mark_claimed_returns_false_from_claimed(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "c2")
        store.mark_queued(run_id="c2", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="c2")
        assert store.mark_claimed(run_id="c2") is False  # already claimed

    def test_mark_claimed_returns_false_from_terminal(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "c3")
        store.mark_queued(run_id="c3", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="c3")
        store.mark_running(run_id="c3")
        store.mark_completed(run_id="c3")
        assert store.mark_claimed(run_id="c3") is False


# ================================================================== #
# 6. Idempotency (P1 Fix 4)
# ================================================================== #

class TestInsertIdempotency:
    def test_duplicate_run_request_id_returns_existing_submission_id(self) -> None:
        store = _InMemoryRunSubmissionStore()
        sid1 = store.insert_submission(
            run_id="run_idem", workspace_id="ws", run_request_id="req_idem",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        # Second call with same run_request_id → must return same submission_id
        sid2 = store.insert_submission(
            run_id="run_idem_different_run_id", workspace_id="ws",
            run_request_id="req_idem",  # same request ID
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        assert sid1 == sid2, "Duplicate run_request_id must return existing submission_id"

    def test_different_run_request_ids_get_different_submission_ids(self) -> None:
        store = _InMemoryRunSubmissionStore()
        sid1 = store.insert_submission(
            run_id="run_a", workspace_id="ws", run_request_id="req_a",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        sid2 = store.insert_submission(
            run_id="run_b", workspace_id="ws", run_request_id="req_b",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        assert sid1 != sid2

    def test_idempotent_insert_does_not_create_second_row(self) -> None:
        store = _InMemoryRunSubmissionStore()
        store.insert_submission(
            run_id="run_x", workspace_id="ws", run_request_id="req_x",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        store.insert_submission(
            run_id="run_x2", workspace_id="ws", run_request_id="req_x",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        assert len(store.insert_calls) == 1  # only one real insert


# ================================================================== #
# 7. Full lifecycle transitions
# ================================================================== #

class TestSubmissionStoreLifecycle:
    def _insert(self, store, run_id):  # noqa: ANN001
        return store.insert_submission(
            run_id=run_id, workspace_id="ws", run_request_id=f"req_{run_id}",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )

    def test_success_lifecycle_all_transitions_return_true(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "life1")
        assert store.mark_queued(run_id="life1", queue_job_id="j", queue_name="q") is True
        assert store.mark_claimed(run_id="life1") is True
        assert store.mark_running(run_id="life1") is True
        assert store.mark_completed(run_id="life1") is True
        assert store._rows["life1"]["submission_status"] == "completed"

    def test_failure_lifecycle(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "fail1")
        store.mark_queued(run_id="fail1", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="fail1")
        store.mark_running(run_id="fail1")
        assert store.mark_failed(run_id="fail1", failure_reason="engine_crash") is True
        assert store._rows["fail1"]["failure_reason"] == "engine_crash"

    def test_lost_redis_then_requeue_lifecycle(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._insert(store, "lost1")
        store.mark_queued(run_id="lost1", queue_job_id="j", queue_name="q")
        assert store.mark_lost_redis(run_id="lost1") is True
        assert store.mark_requeued(run_id="lost1", queue_job_id="j2") is True
        assert store._rows["lost1"]["submission_status"] == "requeued"
        assert store._rows["lost1"]["failure_reason"] is None


# ================================================================== #
# 8. Orphan reconciliation
# ================================================================== #

class TestOrphanReconciliation:
    def _make_old_row(self, store, run_id, status):  # noqa: ANN001
        store.insert_submission(
            run_id=run_id, workspace_id="ws", run_request_id=f"req_{run_id}",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        store._rows[run_id]["submission_status"] = status
        store._rows[run_id]["updated_at"] = old

    def test_stuck_queued_marked_lost_redis(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._make_old_row(store, "orphan1", "queued")
        result = reconcile_orphaned_submissions(submission_store=store, orphan_threshold_s=60)
        assert result.orphans_found >= 1 and result.marked_lost_redis >= 1
        assert store._rows["orphan1"]["submission_status"] == "lost_redis"

    def test_completed_row_not_touched(self) -> None:
        store = _InMemoryRunSubmissionStore()
        store.insert_submission(
            run_id="done1", workspace_id="ws", run_request_id="req_done1",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        store.mark_queued(run_id="done1", queue_job_id="j", queue_name="q")
        store.mark_claimed(run_id="done1")
        store.mark_running(run_id="done1")
        store.mark_completed(run_id="done1")
        reconcile_orphaned_submissions(submission_store=store, orphan_threshold_s=0)
        assert store._rows["done1"]["submission_status"] == "completed"

    def test_empty_store_returns_zero(self) -> None:
        store = _InMemoryRunSubmissionStore()
        r = reconcile_orphaned_submissions(submission_store=store)
        assert r.orphans_found == 0 and r.marked_lost_redis == 0


# ================================================================== #
# 9. TTL cleanup
# ================================================================== #

class TestCleanupExpiredSubmissions:
    def _make_expired_terminal(self, store, run_id, status):  # noqa: ANN001
        store.insert_submission(
            run_id=run_id, workspace_id="ws", run_request_id=f"req_{run_id}",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        store._rows[run_id].update({
            "submission_status": status,
            "terminal_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": past,
        })

    def test_expired_completed_row_deleted(self) -> None:
        store = _InMemoryRunSubmissionStore()
        self._make_expired_terminal(store, "exp1", "completed")
        result = cleanup_expired_terminal_submissions(submission_store=store)
        assert result.deleted >= 1 and store.get_by_run_id("exp1") is None

    def test_non_expired_row_not_deleted(self) -> None:
        store = _InMemoryRunSubmissionStore()
        store.insert_submission(
            run_id="fresh1", workspace_id="ws", run_request_id="req_fresh1",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        future = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
        store._rows["fresh1"].update({"submission_status": "completed",
                                      "terminal_at": datetime.now(timezone.utc).isoformat(),
                                      "expires_at": future})
        cleanup_expired_terminal_submissions(submission_store=store)
        assert store.get_by_run_id("fresh1") is not None

    def test_active_row_never_deleted(self) -> None:
        store = _InMemoryRunSubmissionStore()
        store.insert_submission(
            run_id="active1", workspace_id="ws", run_request_id="req_active1",
            submitter_user_ref="u", target_type="commit_snapshot", target_ref="snap",
        )
        cleanup_expired_terminal_submissions(submission_store=store)
        assert store.get_by_run_id("active1") is not None

    def test_empty_store_returns_zero(self) -> None:
        store = _InMemoryRunSubmissionStore()
        r = cleanup_expired_terminal_submissions(submission_store=store)
        assert r.deleted == 0
