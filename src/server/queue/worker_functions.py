"""Worker execution functions for the Nexa async queue substrate.

arq job function executed by worker processes.

Design invariants (spec §7):
- Worker claims the submission row BEFORE invoking the engine.
- If mark_claimed returns False, execution is ABORTED — another worker
  already claimed the run, or it was already terminal. No engine invocation.
- Worker writes terminal result via engine_bridge (not directly to store).
- Worker updates submission status at each lifecycle transition.
- Worker must not erase original failure history on retry.

SUBSTRATE NOTE (Batch 2A scope):
  ctx["submission_store"] and ctx["engine_bridge"] are injected by arq
  on_startup hooks, which are not yet implemented (pending Batch 2H).
  Until then, ctx will lack these keys and the worker will handle the
  absence gracefully without panicking.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_RUN_ID_KEY = "run_id"
_WORKSPACE_ID_KEY = "workspace_id"
_RUN_REQUEST_ID_KEY = "run_request_id"
_TARGET_TYPE_KEY = "target_type"
_TARGET_REF_KEY = "target_ref"
_PROVIDER_ID_KEY = "provider_id"
_MODEL_ID_KEY = "model_id"
_MODE_KEY = "mode"


def _extract_job_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Unexpected job payload type: {type(payload)!r}")


async def execute_queued_run(
    ctx: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """arq job function — execute a queued Nexa run.

    Lifecycle:
    1. Extract run identity from payload.
    2. Atomically claim the submission row — ABORT if claim fails (False).
    3. Transition to 'running'.
    4. Invoke engine through approved bridge.
    5. Write terminal status based on engine outcome.
    6. Emit lifecycle events.

    Returns a summary dict stored by arq as the job result.
    """
    job_data = _extract_job_payload(payload)
    run_id: str = job_data.get(_RUN_ID_KEY, "")
    workspace_id: str = job_data.get(_WORKSPACE_ID_KEY, "")
    target_type: str = job_data.get(_TARGET_TYPE_KEY, "")
    target_ref: str = job_data.get(_TARGET_REF_KEY, "")
    mode: str = job_data.get(_MODE_KEY, "standard")

    if not run_id:
        logger.error("execute_queued_run: missing run_id in payload; skipping")
        return {"status": "failed", "reason": "missing_run_id"}

    logger.info(
        "execute_queued_run: start run_id=%s workspace_id=%s target_type=%s",
        run_id,
        workspace_id,
        target_type,
    )

    submission_store: Optional[Any] = ctx.get("submission_store")
    engine_bridge: Optional[Any] = ctx.get("engine_bridge")
    action_log: Optional[Any] = ctx.get("action_log")

    # Step 1 — atomically claim the submission row.
    # mark_claimed returns False if another worker beat us, or the row is
    # already terminal. In that case we MUST NOT invoke the engine.
    if submission_store is not None:
        claimed = False
        try:
            claimed = submission_store.mark_claimed(run_id=run_id)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "execute_queued_run: mark_claimed raised for run_id=%s: %s; aborting",
                run_id,
                exc,
            )
            return {
                "run_id": run_id,
                "workspace_id": workspace_id,
                "status": "aborted",
                "reason": f"claim_error: {exc}",
            }

        if not claimed:
            logger.warning(
                "execute_queued_run: claim failed (already claimed or terminal) "
                "for run_id=%s; aborting to prevent duplicate execution",
                run_id,
            )
            return {
                "run_id": run_id,
                "workspace_id": workspace_id,
                "status": "aborted",
                "reason": "claim_failed_duplicate_or_terminal",
            }

        # Step 2 — transition to running.
        try:
            submission_store.mark_running(run_id=run_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "execute_queued_run: mark_running failed for run_id=%s: %s (non-fatal)",
                run_id,
                exc,
            )

    # Step 3 — emit lifecycle start event.
    _emit_lifecycle_event(
        action_log=action_log,
        run_id=run_id,
        workspace_id=workspace_id,
        event="worker_started",
    )

    # Step 4 — invoke the engine via approved bridge.
    execution_result: Optional[dict[str, Any]] = None
    failure_reason: Optional[str] = None

    try:
        if engine_bridge is not None:
            execution_result = await _invoke_engine_bridge(
                engine_bridge=engine_bridge,
                run_id=run_id,
                workspace_id=workspace_id,
                target_type=target_type,
                target_ref=target_ref,
                mode=mode,
            )
        else:
            failure_reason = "engine_bridge_unavailable"
            logger.error(
                "execute_queued_run: engine_bridge not in worker context for run_id=%s",
                run_id,
            )
    except Exception as exc:  # noqa: BLE001
        failure_reason = f"engine_execution_error: {exc}"
        logger.exception(
            "execute_queued_run: engine execution raised for run_id=%s",
            run_id,
        )

    # Step 5 — transition to terminal status.
    if submission_store is not None:
        try:
            if failure_reason is not None:
                # mark_failed guard: only from 'claimed' or 'running'.
                # If mark_running succeeded, we are in 'running'.
                # If mark_running silently failed, we are still in 'claimed'.
                transitioned = submission_store.mark_failed(
                    run_id=run_id, failure_reason=failure_reason
                )
                if not transitioned:
                    logger.warning(
                        "execute_queued_run: mark_failed returned False for run_id=%s "
                        "(row may already be terminal)",
                        run_id,
                    )
            else:
                transitioned = submission_store.mark_completed(run_id=run_id)
                if not transitioned:
                    logger.warning(
                        "execute_queued_run: mark_completed returned False for run_id=%s "
                        "(row not in 'running' — possible lost_redis race)",
                        run_id,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "execute_queued_run: terminal status update failed for run_id=%s: %s",
                run_id,
                exc,
            )

    # Step 6 — emit lifecycle terminal event.
    terminal_event = "worker_failed" if failure_reason else "worker_completed"
    _emit_lifecycle_event(
        action_log=action_log,
        run_id=run_id,
        workspace_id=workspace_id,
        event=terminal_event,
        detail=failure_reason or "",
    )

    summary: dict[str, Any] = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "status": "failed" if failure_reason else "completed",
        "failure_reason": failure_reason,
    }
    if execution_result is not None:
        summary["execution_result"] = execution_result

    logger.info(
        "execute_queued_run: done run_id=%s status=%s",
        run_id,
        summary["status"],
    )
    return summary


async def _invoke_engine_bridge(
    *,
    engine_bridge: Any,
    run_id: str,
    workspace_id: str,
    target_type: str,
    target_ref: str,
    mode: str,
) -> Optional[dict[str, Any]]:
    """Invoke the engine through the approved server→engine bridge boundary."""
    if hasattr(engine_bridge, "execute_async"):
        result = await engine_bridge.execute_async(
            run_id=run_id,
            workspace_id=workspace_id,
            target_type=target_type,
            target_ref=target_ref,
            mode=mode,
        )
    elif hasattr(engine_bridge, "execute"):
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: engine_bridge.execute(
                run_id=run_id,
                workspace_id=workspace_id,
                target_type=target_type,
                target_ref=target_ref,
                mode=mode,
            ),
        )
    else:
        raise AttributeError(
            f"engine_bridge {type(engine_bridge)!r} has neither execute nor execute_async"
        )

    if result is None:
        return None
    if isinstance(result, dict):
        return result
    try:
        from dataclasses import asdict

        return asdict(result)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return {"raw": str(result)}


def _emit_lifecycle_event(
    *,
    action_log: Optional[Any],
    run_id: str,
    workspace_id: str,
    event: str,
    detail: str = "",
) -> None:
    if action_log is None:
        return
    try:
        if hasattr(action_log, "record"):
            action_log.record(
                run_id=run_id,
                workspace_id=workspace_id,
                event=event,
                detail=detail,
            )
        elif hasattr(action_log, "append"):
            action_log.append(
                {"run_id": run_id, "workspace_id": workspace_id, "event": event, "detail": detail}
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("_emit_lifecycle_event: action_log call failed: %s", exc)
