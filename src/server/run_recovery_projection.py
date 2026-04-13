from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from src.server.run_action_log_models import (
    ProductRunFallbackAuditView,
    ProductRunFallbackScoringAuditView,
    fallback_audit_from_action_log_event,
    fallback_scoring_audit_from_action_log_event,
)

_RECOVERY_PRIORITY = {
    "manual_review_required": 4,
    "retry_pending": 3,
    "failed": 2,
    "leased": 1,
    "healthy": 0,
}


def _fallback_trace_from_run_row(run_record_row: Mapping[str, Any]) -> tuple[ProductRunFallbackAuditView, ...]:
    action_log = run_record_row.get("action_log")
    if not isinstance(action_log, Sequence) or isinstance(action_log, (str, bytes, bytearray)):
        return ()
    trace: list[ProductRunFallbackAuditView] = []
    for event in action_log:
        if not isinstance(event, Mapping):
            continue
        audit = fallback_audit_from_action_log_event(dict(event))
        if audit is not None:
            trace.append(audit)
    return tuple(trace)






@dataclass(frozen=True)
class RunRecoveryPolicyValidationProjection:
    status: str
    reason: str
    fallback_applied: bool = False


def _policy_validation_from_run_row(run_record_row: Mapping[str, Any]) -> RunRecoveryPolicyValidationProjection | None:
    raw = run_record_row.get("policy_validation")
    if not isinstance(raw, Mapping):
        return None
    status = str(raw.get("status") or "").strip()
    reason = str(raw.get("reason") or "").strip()
    if not status or not reason:
        return None
    return RunRecoveryPolicyValidationProjection(
        status=status,
        reason=reason,
        fallback_applied=bool(raw.get("fallback_applied")),
    )

def _scoring_trace_from_run_row(run_record_row: Mapping[str, Any]) -> tuple[ProductRunFallbackScoringAuditView, ...]:
    action_log = run_record_row.get("action_log")
    if not isinstance(action_log, Sequence) or isinstance(action_log, (str, bytes, bytearray)):
        return ()
    trace: list[ProductRunFallbackScoringAuditView] = []
    for event in action_log:
        if not isinstance(event, Mapping):
            continue
        audit = fallback_scoring_audit_from_action_log_event(dict(event))
        if audit is not None:
            trace.append(audit)
    return tuple(trace)


@dataclass(frozen=True)
class RunRecoveryProjection:
    recovery_state: str
    worker_attempt_number: int = 0
    queue_job_id: Optional[str] = None
    claimed_by_worker_ref: Optional[str] = None
    lease_expires_at: Optional[str] = None
    orphan_review_required: bool = False
    latest_error_family: Optional[str] = None
    summary: Optional[str] = None
    fallback_trace: tuple[ProductRunFallbackAuditView, ...] = field(default_factory=tuple)
    scoring_trace: tuple[ProductRunFallbackScoringAuditView, ...] = field(default_factory=tuple)
    policy_validation: RunRecoveryPolicyValidationProjection | None = None


def recovery_projection_from_run_row(
    run_record_row: Mapping[str, Any],
    *,
    include_healthy_without_signal: bool = False,
) -> RunRecoveryProjection | None:
    queue_job_id = str(run_record_row.get('queue_job_id') or '').strip() or None
    claimed_by_worker_ref = str(run_record_row.get('claimed_by_worker_ref') or '').strip() or None
    lease_expires_at = str(run_record_row.get('lease_expires_at') or '').strip() or None
    latest_error_family = str(run_record_row.get('latest_error_family') or '').strip() or None
    worker_attempt_number = int(run_record_row.get('worker_attempt_number') or 0)
    orphan_review_required = bool(run_record_row.get('orphan_review_required'))
    status = str(run_record_row.get('status') or '').strip().lower()
    fallback_trace = _fallback_trace_from_run_row(run_record_row)
    scoring_trace = _scoring_trace_from_run_row(run_record_row)
    policy_validation = _policy_validation_from_run_row(run_record_row)

    has_recovery_signal = any((
        queue_job_id,
        claimed_by_worker_ref,
        lease_expires_at,
        latest_error_family,
        orphan_review_required,
        worker_attempt_number > 0,
        bool(fallback_trace),
        bool(scoring_trace),
        policy_validation is not None,
    ))
    if not has_recovery_signal and not include_healthy_without_signal:
        return None

    if orphan_review_required:
        recovery_state = 'manual_review_required'
        summary = 'Run continuity requires orphan review before the latest worker state can be trusted.'
    elif latest_error_family == 'worker_infrastructure_failure' and status in {'queued', 'starting', 'running'}:
        recovery_state = 'retry_pending'
        summary = 'Run continuity detected infrastructure failure and is waiting for another worker attempt.'
    elif latest_error_family == 'worker_infrastructure_failure':
        recovery_state = 'failed'
        summary = 'Run continuity failed because the worker infrastructure did not complete the run safely.'
    elif claimed_by_worker_ref and lease_expires_at and status in {'starting', 'running'}:
        recovery_state = 'leased'
        summary = 'Run is currently leased to a worker and the lease window is being tracked.'
    else:
        recovery_state = 'healthy'
        summary = 'Run continuity metadata is present and currently healthy.' if has_recovery_signal else 'Run has no active continuity risk signals.'

    return RunRecoveryProjection(
        recovery_state=recovery_state,
        worker_attempt_number=worker_attempt_number,
        queue_job_id=queue_job_id,
        claimed_by_worker_ref=claimed_by_worker_ref,
        lease_expires_at=lease_expires_at,
        orphan_review_required=orphan_review_required,
        latest_error_family=latest_error_family,
        summary=summary,
        fallback_trace=fallback_trace,
        scoring_trace=scoring_trace,
        policy_validation=policy_validation,
    )


def aggregate_recovery_projection_for_runs(
    run_rows: Sequence[Mapping[str, Any]],
) -> RunRecoveryProjection | None:
    best: RunRecoveryProjection | None = None
    best_priority = -1
    best_updated_at = ''
    for row in run_rows:
        projection = recovery_projection_from_run_row(row, include_healthy_without_signal=True)
        if projection is None:
            continue
        priority = _RECOVERY_PRIORITY.get(projection.recovery_state, 0)
        updated_at = str(row.get('updated_at') or row.get('created_at') or '')
        if priority > best_priority or (priority == best_priority and updated_at > best_updated_at):
            best = projection
            best_priority = priority
            best_updated_at = updated_at
    return best
