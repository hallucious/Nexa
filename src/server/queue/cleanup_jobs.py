"""Cleanup and orphan recovery jobs for the Nexa async queue substrate.

This module handles:
1. Orphan detection — submissions stuck in non-terminal states longer than
   the configured threshold are marked as lost_redis.
2. TTL cleanup — expired terminal submissions are deleted.

These jobs are designed to run periodically (e.g. via arq cron or a scheduler).
They are idempotent and safe to run multiple times.

From the spec (async_execution_and_run_state_spec.md §9):
- Redis loss recovery reconciles against run_submissions.
- Orphan reprocessing updates stuck rows, does not silently discard them.
- Cleanup only removes terminal rows whose expires_at has passed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Threshold in seconds before a non-terminal submission is considered orphaned.
_DEFAULT_ORPHAN_THRESHOLD_S: int = 300  # 5 minutes


@dataclass(frozen=True)
class OrphanReconciliationResult:
    """Summary of a single orphan reconciliation run."""

    orphans_found: int = 0
    marked_lost_redis: int = 0
    errors: int = 0


@dataclass(frozen=True)
class CleanupResult:
    """Summary of a single TTL cleanup run."""

    expired_found: int = 0
    deleted: int = 0
    errors: int = 0


def reconcile_orphaned_submissions(
    *,
    submission_store: Any,
    orphan_threshold_s: int = _DEFAULT_ORPHAN_THRESHOLD_S,
) -> OrphanReconciliationResult:
    """Mark stuck submissions as lost_redis.

    Submissions that have been in a non-terminal, non-running state for longer
    than orphan_threshold_s are considered to have lost their Redis transport
    and are marked as lost_redis.

    This is the primary Redis-loss recovery path.
    """
    try:
        orphans = submission_store.list_orphaned_submissions(
            older_than_s=orphan_threshold_s,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("reconcile_orphaned_submissions: list_orphaned_submissions failed: %s", exc)
        return OrphanReconciliationResult(errors=1)

    if not orphans:
        return OrphanReconciliationResult()

    marked = 0
    errors = 0
    for row in orphans:
        run_id = row.get("run_id", "")
        if not run_id:
            errors += 1
            continue
        try:
            submission_store.mark_lost_redis(run_id=run_id)
            marked += 1
            logger.info(
                "reconcile_orphaned_submissions: marked lost_redis run_id=%s status_was=%s",
                run_id,
                row.get("submission_status", "unknown"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "reconcile_orphaned_submissions: mark_lost_redis failed for run_id=%s: %s",
                run_id,
                exc,
            )
            errors += 1

    return OrphanReconciliationResult(
        orphans_found=len(orphans),
        marked_lost_redis=marked,
        errors=errors,
    )


def cleanup_expired_terminal_submissions(
    *,
    submission_store: Any,
) -> CleanupResult:
    """Delete terminal run_submissions rows whose expires_at TTL has passed.

    Only deletes rows whose submission_status is completed, failed, or lost_redis
    AND whose expires_at is in the past. Active rows are never touched.
    """
    try:
        expired_rows = submission_store.list_expired_terminal_submissions()
    except Exception as exc:  # noqa: BLE001
        logger.error("cleanup_expired_terminal_submissions: list_expired failed: %s", exc)
        return CleanupResult(errors=1)

    if not expired_rows:
        return CleanupResult()

    try:
        deleted = submission_store.delete_expired_terminal_submissions()
        logger.info(
            "cleanup_expired_terminal_submissions: deleted %d expired terminal rows",
            deleted,
        )
        return CleanupResult(expired_found=len(expired_rows), deleted=deleted)
    except Exception as exc:  # noqa: BLE001
        logger.error("cleanup_expired_terminal_submissions: delete failed: %s", exc)
        return CleanupResult(expired_found=len(expired_rows), errors=1)


# ------------------------------------------------------------------ #
# arq cron job wrappers
# ------------------------------------------------------------------ #

async def cron_reconcile_orphans(ctx: dict[str, Any]) -> dict[str, Any]:
    """arq cron job wrapper for orphan reconciliation."""
    submission_store: Optional[Any] = ctx.get("submission_store")
    if submission_store is None:
        logger.warning("cron_reconcile_orphans: submission_store not in ctx; skipping")
        return {"skipped": True, "reason": "no_submission_store"}

    result = reconcile_orphaned_submissions(submission_store=submission_store)
    return {
        "orphans_found": result.orphans_found,
        "marked_lost_redis": result.marked_lost_redis,
        "errors": result.errors,
    }


async def cron_cleanup_expired(ctx: dict[str, Any]) -> dict[str, Any]:
    """arq cron job wrapper for TTL cleanup."""
    submission_store: Optional[Any] = ctx.get("submission_store")
    if submission_store is None:
        logger.warning("cron_cleanup_expired: submission_store not in ctx; skipping")
        return {"skipped": True, "reason": "no_submission_store"}

    result = cleanup_expired_terminal_submissions(submission_store=submission_store)
    return {
        "expired_found": result.expired_found,
        "deleted": result.deleted,
        "errors": result.errors,
    }
