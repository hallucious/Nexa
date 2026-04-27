"""PostgreSQL store for run_submissions.

run_submissions is a short-lived Category C operational truth table.
It bridges accepted run requests and the Redis queue transport,
providing durability so Redis-loss recovery can reconcile orphaned jobs.

Allowed submission_status progression:
  submitted → queued → claimed → running → completed | failed | lost_redis
  failed | lost_redis → requeued → queued → claimed → ...

Terminal statuses: completed, failed, lost_redis

Strict transition guards:
  - mark_completed  : only from 'running'
  - mark_failed     : only from 'claimed' or 'running'
  - mark_lost_redis : only from non-terminal states
                      ('submitted', 'queued', 'requeued', 'claimed', 'running')
  - mark_requeued   : only from 'failed' or 'lost_redis'
  - mark_completed / mark_failed must NOT transition from 'lost_redis'

All mark_* transition methods return bool:
  True  → row was found and transition applied (rowcount >= 1)
  False → no matching row (already in wrong/terminal state, or not found)

SUBSTRATE NOTE (Batch 2A scope):
  This store is production-ready as a data layer.
  Full worker lifecycle requires arq on_startup/on_shutdown hooks that inject
  submission_store and engine_bridge into worker ctx — pending Batch 2H.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4

_ALLOWED_SUBMISSION_STATUSES = {
    "submitted",
    "queued",
    "requeued",
    "claimed",
    "running",
    "completed",
    "failed",
    "lost_redis",
}

_TERMINAL_STATUSES = frozenset({"completed", "failed", "lost_redis"})

# Default TTL for terminal rows before cleanup removes them (seconds).
_DEFAULT_TERMINAL_TTL_S: int = 60 * 60 * 48  # 48 hours

try:  # pragma: no cover - optional dependency
    from sqlalchemy import text
    from sqlalchemy.engine import Engine
except ModuleNotFoundError:  # pragma: no cover
    Engine = Any  # type: ignore[misc,assignment]
    text = None  # type: ignore[assignment]


def _require_sqlalchemy() -> None:
    if text is None:
        raise ModuleNotFoundError("sqlalchemy is required for PostgresRunSubmissionStore")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_iso(*, ttl_s: int = _DEFAULT_TERMINAL_TTL_S) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=ttl_s)).isoformat()


def _row_dict(row: Any) -> dict[str, Any]:
    mapping = getattr(row, "_mapping", row)
    return {str(key): value for key, value in dict(mapping).items()}


def _fetch_one(engine: Engine, sql: str, params: Mapping[str, Any]) -> dict[str, Any] | None:
    _require_sqlalchemy()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        row = result.fetchone()
        return _row_dict(row) if row is not None else None


def _execute_rowcount(engine: Engine, sql: str, params: Mapping[str, Any]) -> int:
    """Execute a DML statement and return the number of affected rows."""
    _require_sqlalchemy()
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        return result.rowcount or 0


class PostgresRunSubmissionStore:
    """Postgres-backed store for run_submissions rows."""

    def __init__(self, engine: Engine) -> None:
        _require_sqlalchemy()
        self._engine = engine

    # ------------------------------------------------------------------ #
    # Write: insert
    # ------------------------------------------------------------------ #

    def insert_submission(
        self,
        *,
        run_id: str,
        workspace_id: str,
        run_request_id: str,
        submitter_user_ref: str,
        target_type: str,
        target_ref: str,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
        priority: str = "normal",
        mode: str = "standard",
        queue_name: Optional[str] = None,
        ttl_s: int = _DEFAULT_TERMINAL_TTL_S,
    ) -> str:
        """Insert a new run_submissions row in 'submitted' status.

        Returns the submission_id of the inserted (or existing) row.

        Idempotency: if run_request_id already exists (UNIQUE constraint),
        returns the existing submission_id rather than raising a unique-constraint
        error. This makes the insert step safe to retry without double-submission.

        This must be called before the job is enqueued to Redis
        (durable-first contract, spec §4.1).
        """
        if not run_id.strip():
            raise ValueError("run_id must be non-empty")
        if not workspace_id.strip():
            raise ValueError("workspace_id must be non-empty")
        if not run_request_id.strip():
            raise ValueError("run_request_id must be non-empty")
        if not submitter_user_ref.strip():
            raise ValueError("submitter_user_ref must be non-empty")

        submission_id = f"sub_{uuid4().hex}"
        now = _now_iso()

        _require_sqlalchemy()
        with self._engine.begin() as conn:
            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO run_submissions (
                            submission_id, run_id, workspace_id, run_request_id,
                            submitter_user_ref, target_type, target_ref,
                            provider_id, model_id, priority, mode,
                            submission_status, queue_name,
                            submitted_at, created_at, updated_at
                        ) VALUES (
                            :submission_id, :run_id, :workspace_id, :run_request_id,
                            :submitter_user_ref, :target_type, :target_ref,
                            :provider_id, :model_id, :priority, :mode,
                            'submitted', :queue_name,
                            :submitted_at, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "submission_id": submission_id,
                        "run_id": run_id,
                        "workspace_id": workspace_id,
                        "run_request_id": run_request_id,
                        "submitter_user_ref": submitter_user_ref,
                        "target_type": target_type,
                        "target_ref": target_ref,
                        "provider_id": provider_id,
                        "model_id": model_id,
                        "priority": priority,
                        "mode": mode,
                        "queue_name": queue_name,
                        "submitted_at": now,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                exc_str = str(exc).lower()
                if "unique" in exc_str or "duplicate" in exc_str or "uq_run_submissions" in exc_str:
                    existing = _fetch_one(
                        self._engine,
                        "SELECT submission_id FROM run_submissions WHERE run_request_id = :req_id LIMIT 1",
                        {"req_id": run_request_id},
                    )
                    if existing:
                        return str(existing["submission_id"])
                raise

        return submission_id

    # ------------------------------------------------------------------ #
    # Write: status transitions (all return bool)
    # ------------------------------------------------------------------ #

    def mark_queued(self, *, run_id: str, queue_job_id: str, queue_name: str) -> bool:
        """Transition to 'queued' after successful Redis enqueue.

        Guard: only from 'submitted' or 'requeued'.
        """
        now = _now_iso()
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'queued',
                queue_job_id = :queue_job_id,
                queue_name = :queue_name,
                queued_at = :queued_at,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status IN ('submitted', 'requeued')
            """,
            {
                "run_id": run_id,
                "queue_job_id": queue_job_id,
                "queue_name": queue_name,
                "queued_at": now,
                "updated_at": now,
            },
        ) > 0

    def mark_claimed(self, *, run_id: str) -> bool:
        """Worker atomically claims the submission.

        Guard: only from 'queued'.
        Returns True if the claim succeeded (exclusive claim secured).
        Returns False if another worker already claimed/running/terminal,
        or if the row is not found.

        CALLERS MUST check the return value and abort execution if False.
        This is the primary concurrent-worker exclusion mechanism.
        """
        now = _now_iso()
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'claimed',
                claimed_at = :claimed_at,
                worker_attempt_number = worker_attempt_number + 1,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status = 'queued'
            """,
            {"run_id": run_id, "claimed_at": now, "updated_at": now},
        ) > 0

    def mark_running(self, *, run_id: str) -> bool:
        """Worker transitions to 'running' after claim.

        Guard: only from 'claimed'.
        """
        now = _now_iso()
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'running',
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status = 'claimed'
            """,
            {"run_id": run_id, "updated_at": now},
        ) > 0

    def mark_completed(self, *, run_id: str, ttl_s: int = _DEFAULT_TERMINAL_TTL_S) -> bool:
        """Worker marks submission as completed (terminal success).

        Guard: ONLY from 'running'.
        Does NOT transition from 'lost_redis', 'failed', 'claimed', or 'submitted'.
        """
        now = _now_iso()
        expires = _expires_iso(ttl_s=ttl_s)
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'completed',
                terminal_at = :terminal_at,
                expires_at = :expires_at,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status = 'running'
            """,
            {"run_id": run_id, "terminal_at": now, "expires_at": expires, "updated_at": now},
        ) > 0

    def mark_failed(
        self, *, run_id: str, failure_reason: str, ttl_s: int = _DEFAULT_TERMINAL_TTL_S
    ) -> bool:
        """Worker marks submission as failed (terminal failure).

        Guard: only from 'claimed' or 'running'.
        Does NOT transition from 'completed', 'lost_redis', or 'submitted'.
        """
        now = _now_iso()
        expires = _expires_iso(ttl_s=ttl_s)
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'failed',
                failure_reason = :failure_reason,
                terminal_at = :terminal_at,
                expires_at = :expires_at,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status IN ('claimed', 'running')
            """,
            {
                "run_id": run_id,
                "failure_reason": failure_reason,
                "terminal_at": now,
                "expires_at": expires,
                "updated_at": now,
            },
        ) > 0

    def mark_lost_redis(self, *, run_id: str, ttl_s: int = _DEFAULT_TERMINAL_TTL_S) -> bool:
        """Reconciliation marks submission as lost_redis.

        Guard: only from active states ('submitted', 'queued', 'requeued', 'claimed', 'running').
        Does NOT transition from 'completed' or 'failed'.
        """
        now = _now_iso()
        expires = _expires_iso(ttl_s=ttl_s)
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'lost_redis',
                terminal_at = :terminal_at,
                expires_at = :expires_at,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status IN ('submitted', 'queued', 'requeued', 'claimed', 'running')
            """,
            {"run_id": run_id, "terminal_at": now, "expires_at": expires, "updated_at": now},
        ) > 0

    def mark_requeued(self, *, run_id: str, queue_job_id: str) -> bool:
        """Admin/recovery re-enqueues a failed or lost_redis submission.

        Guard: only from 'failed' or 'lost_redis'.
        Does NOT transition from 'completed', 'running', 'submitted', or 'queued'.
        """
        now = _now_iso()
        return _execute_rowcount(
            self._engine,
            """
            UPDATE run_submissions
            SET submission_status = 'requeued',
                queue_job_id = :queue_job_id,
                queued_at = :queued_at,
                terminal_at = NULL,
                expires_at = NULL,
                failure_reason = NULL,
                updated_at = :updated_at
            WHERE run_id = :run_id
              AND submission_status IN ('failed', 'lost_redis')
            """,
            {"run_id": run_id, "queue_job_id": queue_job_id, "queued_at": now, "updated_at": now},
        ) > 0

    # ------------------------------------------------------------------ #
    # Read operations
    # ------------------------------------------------------------------ #

    def get_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self._engine,
            "SELECT * FROM run_submissions WHERE run_id = :run_id LIMIT 1",
            {"run_id": run_id},
        )

    def get_by_submission_id(self, submission_id: str) -> dict[str, Any] | None:
        return _fetch_one(
            self._engine,
            "SELECT * FROM run_submissions WHERE submission_id = :sid LIMIT 1",
            {"sid": submission_id},
        )

    def get_by_run_request_id(self, run_request_id: str) -> dict[str, Any] | None:
        """Return the submission row for a given run_request_id, or None."""
        return _fetch_one(
            self._engine,
            "SELECT * FROM run_submissions WHERE run_request_id = :req_id LIMIT 1",
            {"req_id": run_request_id},
        )

    def list_orphaned_submissions(self, *, older_than_s: int = 300) -> Sequence[dict[str, Any]]:
        """Return submissions stuck in non-terminal states beyond the age threshold."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=older_than_s)).isoformat()
        _require_sqlalchemy()
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT * FROM run_submissions
                    WHERE submission_status IN ('submitted', 'queued', 'requeued', 'claimed', 'running')
                      AND updated_at < :cutoff
                    ORDER BY submitted_at ASC
                    """
                ),
                {"cutoff": cutoff},
            )
            return [_row_dict(row) for row in result.fetchall()]

    def list_expired_terminal_submissions(self) -> Sequence[dict[str, Any]]:
        """Return terminal rows whose expires_at has passed (cleanup candidates)."""
        now = _now_iso()
        _require_sqlalchemy()
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT * FROM run_submissions
                    WHERE submission_status IN ('completed', 'failed', 'lost_redis')
                      AND expires_at IS NOT NULL
                      AND expires_at < :now
                    ORDER BY terminal_at ASC
                    """
                ),
                {"now": now},
            )
            return [_row_dict(row) for row in result.fetchall()]

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def delete_expired_terminal_submissions(self) -> int:
        """Delete terminal rows past their expires_at TTL. Returns deleted count."""
        now = _now_iso()
        _require_sqlalchemy()
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM run_submissions
                    WHERE submission_status IN ('completed', 'failed', 'lost_redis')
                      AND expires_at IS NOT NULL
                      AND expires_at < :now
                    """
                ),
                {"now": now},
            )
            return result.rowcount or 0
