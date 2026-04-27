"""Run launcher — enqueues admitted runs to the Redis/arq queue.

Submission contract (enforced in order, spec §4.1):
1. run_submissions INSERT to Postgres (durable) — BEFORE Redis.
2. arq job enqueued to Redis (transport).
3. run_submissions UPDATE to 'queued'.

If arq is not installed or the redis_client is not an ArqRedis instance,
the row is kept in 'submitted' status and the result exposes
failure_reason='arq_unavailable'. The submitted row remains available for
orphan recovery. Raw RPUSH is NOT used as a production fallback.

SUBSTRATE NOTE (Batch 2A scope):
  Not yet wired into run_admission.py HTTP path.
  The run_admission synchronous path remains unchanged.
  Async wiring is pending Batch 2H green gate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from src.server.queue.worker_settings import NEXA_RUN_JOB_FUNCTION_NAME, NEXA_RUN_QUEUE_NAME

logger = logging.getLogger(__name__)

_RUN_ID_KEY = "run_id"
_WORKSPACE_ID_KEY = "workspace_id"
_RUN_REQUEST_ID_KEY = "run_request_id"
_TARGET_TYPE_KEY = "target_type"
_TARGET_REF_KEY = "target_ref"
_PROVIDER_ID_KEY = "provider_id"
_MODEL_ID_KEY = "model_id"
_MODE_KEY = "mode"


@dataclass(frozen=True)
class RunEnqueueResult:
    """Result of a run enqueue attempt."""

    accepted: bool
    run_id: str
    submission_id: str
    queue_job_id: Optional[str] = None
    queue_name: Optional[str] = None
    failure_reason: Optional[str] = None

    @property
    def enqueued(self) -> bool:
        return self.accepted and self.queue_job_id is not None


def _existing_submission_result(row: Any, *, reason: str = "duplicate_run_request_id") -> RunEnqueueResult:
    """Build a RunEnqueueResult from an existing durable submission row."""
    return RunEnqueueResult(
        accepted=True,
        run_id=str(row.get("run_id", "")),
        submission_id=str(row.get("submission_id", "")),
        queue_job_id=row.get("queue_job_id"),
        queue_name=row.get("queue_name"),
        failure_reason=reason,
    )


def _get_existing_submission_by_request_id(
    submission_store: Any, run_request_id: str
) -> Optional[dict[str, Any]]:
    """Return an existing submission for run_request_id when the store supports it."""
    get_by_run_request_id = getattr(submission_store, "get_by_run_request_id", None)
    if get_by_run_request_id is None:
        return None
    row = get_by_run_request_id(run_request_id)
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(getattr(row, "_mapping", row))


async def enqueue_run(
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
    submission_store: Any,
    queue_name: str = NEXA_RUN_QUEUE_NAME,
    redis_client: Any = None,
) -> RunEnqueueResult:
    """Enqueue a run following the durable-first submission contract.

    Parameters
    ----------
    submission_store:
        Instance of PostgresRunSubmissionStore (Any to avoid mandatory import).
    redis_client:
        An arq ArqRedis client. None in environments without Redis — the row
        is inserted but enqueue is skipped with failure_reason='redis_client_unavailable'.
    """
    existing_submission = _get_existing_submission_by_request_id(
        submission_store, run_request_id
    )
    if existing_submission is not None:
        logger.info(
            "run_launcher: duplicate run_request_id=%s resolved to existing run_id=%s submission_id=%s",
            run_request_id,
            existing_submission.get("run_id"),
            existing_submission.get("submission_id"),
        )
        return _existing_submission_result(existing_submission)

    # Step 1 — insert durable submission record BEFORE touching Redis.
    try:
        submission_id = submission_store.insert_submission(
            run_id=run_id,
            workspace_id=workspace_id,
            run_request_id=run_request_id,
            submitter_user_ref=submitter_user_ref,
            target_type=target_type,
            target_ref=target_ref,
            provider_id=provider_id,
            model_id=model_id,
            priority=priority,
            mode=mode,
            queue_name=queue_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "run_launcher: failed to insert run_submissions row for run_id=%s: %s",
            run_id,
            exc,
        )
        return RunEnqueueResult(
            accepted=False,
            run_id=run_id,
            submission_id="",
            failure_reason=f"submission_insert_failed: {exc}",
        )

    post_insert_submission = _get_existing_submission_by_request_id(
        submission_store, run_request_id
    )
    if (
        post_insert_submission is not None
        and str(post_insert_submission.get("run_id", "")) != run_id
    ):
        logger.warning(
            "run_launcher: duplicate run_request_id=%s resolved after insert to existing run_id=%s; "
            "skipping enqueue for requested run_id=%s",
            run_request_id,
            post_insert_submission.get("run_id"),
            run_id,
        )
        return _existing_submission_result(post_insert_submission)

    # Step 2 — enqueue to Redis via arq.
    if redis_client is None:
        logger.warning(
            "run_launcher: no redis_client provided; run_id=%s stays in 'submitted'",
            run_id,
        )
        return RunEnqueueResult(
            accepted=True,
            run_id=run_id,
            submission_id=submission_id,
            queue_job_id=None,
            failure_reason="redis_client_unavailable",
        )

    # arq is required in production. If not present, keep the submitted row
    # and return arq_unavailable — do NOT fall back to raw RPUSH.
    try:
        from arq import ArqRedis  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        logger.error(
            "run_launcher: arq is not installed; run_id=%s stays in 'submitted'",
            run_id,
        )
        return RunEnqueueResult(
            accepted=True,
            run_id=run_id,
            submission_id=submission_id,
            queue_job_id=None,
            failure_reason="arq_unavailable",
        )

    if not isinstance(redis_client, ArqRedis):
        logger.error(
            "run_launcher: redis_client is not an ArqRedis instance (%s); "
            "run_id=%s stays in 'submitted'",
            type(redis_client).__name__,
            run_id,
        )
        return RunEnqueueResult(
            accepted=True,
            run_id=run_id,
            submission_id=submission_id,
            queue_job_id=None,
            failure_reason="arq_client_type_mismatch",
        )

    job_payload = {
        _RUN_ID_KEY: run_id,
        _WORKSPACE_ID_KEY: workspace_id,
        _RUN_REQUEST_ID_KEY: run_request_id,
        _TARGET_TYPE_KEY: target_type,
        _TARGET_REF_KEY: target_ref,
        _PROVIDER_ID_KEY: provider_id,
        _MODEL_ID_KEY: model_id,
        _MODE_KEY: mode,
    }

    try:
        job = await redis_client.enqueue_job(
            NEXA_RUN_JOB_FUNCTION_NAME,
            job_payload,
            _queue_name=queue_name,
        )
        queue_job_id: Optional[str] = job.job_id if job is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "run_launcher: arq enqueue failed for run_id=%s: %s",
            run_id,
            exc,
        )
        return RunEnqueueResult(
            accepted=True,
            run_id=run_id,
            submission_id=submission_id,
            queue_job_id=None,
            failure_reason=f"redis_enqueue_failed: {exc}",
        )

    # Step 3 — update submission row to 'queued'.
    try:
        queued_marked = submission_store.mark_queued(
            run_id=run_id,
            queue_job_id=queue_job_id or "",
            queue_name=queue_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "run_launcher: mark_queued failed for run_id=%s: %s (row stays submitted; recovery possible)",
            run_id,
            exc,
        )
        queued_marked = False

    if queued_marked is not True:
        logger.warning(
            "run_launcher: arq enqueue succeeded but mark_queued did not transition run_id=%s; "
            "durable row may need reconciliation",
            run_id,
        )
        return RunEnqueueResult(
            accepted=True,
            run_id=run_id,
            submission_id=submission_id,
            queue_job_id=queue_job_id,
            queue_name=queue_name,
            failure_reason="mark_queued_failed",
        )

    logger.info(
        "run_launcher: enqueued run_id=%s submission_id=%s queue_job_id=%s",
        run_id,
        submission_id,
        queue_job_id,
    )
    return RunEnqueueResult(
        accepted=True,
        run_id=run_id,
        submission_id=submission_id,
        queue_job_id=queue_job_id,
        queue_name=queue_name,
    )
