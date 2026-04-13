from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
import uuid

from src.server.provider_health_models import AutoRecoveryProviderHealthSignal

QueueJobIdFactory = Callable[[], str]

SYSTEM_AUTO_RECOVERY_ACTOR = "system:auto-recovery"
DEFAULT_AUTO_RETRY_LIMIT = 2
DEFAULT_AUTO_RETRY_BASE_BACKOFF_SECONDS = 300
MAX_AUTO_RETRY_BACKOFF_SECONDS = 3600
_INFRA_FAILURE_FAMILY = "worker_infrastructure_failure"
_ACTIVE_STATUSES = {"starting", "running"}
_DEGRADED_PROVIDER_BACKOFF_MULTIPLIER = 2


@dataclass(frozen=True)
class AutoRecoveryOutcome:
    applied: bool
    action: Optional[str] = None
    updated_run_record: Optional[dict[str, Any]] = None
    reason: Optional[str] = None


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _status_family_for_status(status: str | None) -> str:
    normalized = str(status or '').strip().lower()
    if normalized in {'queued', 'starting'}:
        return 'pending'
    if normalized in {'running', 'paused'}:
        return 'active'
    if normalized == 'completed':
        return 'terminal_success'
    if normalized in {'failed', 'cancelled'}:
        return 'terminal_failure'
    if normalized == 'partial':
        return 'terminal_partial'
    return 'unknown'


def _append_action_log(updated_row: dict[str, Any], *, action: str, timestamp: str | None, before_row: Mapping[str, Any], after_row: Mapping[str, Any], actor_user_id: str = SYSTEM_AUTO_RECOVERY_ACTOR) -> None:
    existing = updated_row.get("action_log")
    entries = list(existing) if isinstance(existing, Sequence) and not isinstance(existing, (str, bytes, bytearray)) else []
    entries.append({
        "event_id": f"act_{uuid.uuid4().hex}",
        "action": action,
        "actor_user_id": actor_user_id,
        "timestamp": timestamp or "",
        "before_state": {
            "status": str(before_row.get("status") or ""),
            "status_family": str(before_row.get("status_family") or ""),
            "queue_job_id": before_row.get("queue_job_id"),
            "worker_attempt_number": _coerce_int(before_row.get("worker_attempt_number") or 0),
            "auto_retry_count": _coerce_int(before_row.get("auto_retry_count") or 0),
            "orphan_review_required": bool(before_row.get("orphan_review_required")),
            "latest_error_family": before_row.get("latest_error_family"),
        },
        "after_state": {
            "status": str(after_row.get("status") or ""),
            "status_family": str(after_row.get("status_family") or ""),
            "queue_job_id": after_row.get("queue_job_id"),
            "worker_attempt_number": _coerce_int(after_row.get("worker_attempt_number") or 0),
            "auto_retry_count": _coerce_int(after_row.get("auto_retry_count") or 0),
            "orphan_review_required": bool(after_row.get("orphan_review_required")),
            "latest_error_family": after_row.get("latest_error_family"),
        },
    })
    updated_row["action_log"] = entries


def _current_backoff_seconds(run_record_row: Mapping[str, Any], *, provider_health: AutoRecoveryProviderHealthSignal | None = None) -> int:
    base = max(1, _coerce_int(run_record_row.get("auto_retry_base_backoff_seconds"), DEFAULT_AUTO_RETRY_BASE_BACKOFF_SECONDS))
    retry_count = max(0, _coerce_int(run_record_row.get("auto_retry_count"), 0))
    backoff = base * (2 ** retry_count)
    if provider_health is not None and provider_health.status == "degraded":
        backoff *= _DEGRADED_PROVIDER_BACKOFF_MULTIPLIER
    return min(backoff, MAX_AUTO_RETRY_BACKOFF_SECONDS)


def _backoff_ready(run_record_row: Mapping[str, Any], now_dt: datetime, *, provider_health: AutoRecoveryProviderHealthSignal | None = None) -> bool:
    last_attempt_at = _parse_iso(run_record_row.get("last_auto_recovery_at"))
    if last_attempt_at is None:
        return True
    return now_dt >= (last_attempt_at + timedelta(seconds=_current_backoff_seconds(run_record_row, provider_health=provider_health)))


def apply_auto_recovery(
    run_record_row: Mapping[str, Any],
    *,
    now_iso: str,
    queue_job_id_factory: Optional[QueueJobIdFactory] = None,
    provider_health: AutoRecoveryProviderHealthSignal | None = None,
) -> AutoRecoveryOutcome:
    now_dt = _parse_iso(now_iso)
    if now_dt is None:
        raise ValueError("apply_auto_recovery requires a valid now_iso timestamp")

    status = str(run_record_row.get("status") or "").strip().lower()
    latest_error_family = str(run_record_row.get("latest_error_family") or "").strip() or None
    auto_retry_count = _coerce_int(run_record_row.get("auto_retry_count"), 0)
    auto_retry_limit = _coerce_int(run_record_row.get("auto_retry_limit"), DEFAULT_AUTO_RETRY_LIMIT)
    worker_attempt_number = _coerce_int(run_record_row.get("worker_attempt_number"), 0)
    lease_expires_at = _parse_iso(run_record_row.get("lease_expires_at"))
    claimed_by_worker_ref = str(run_record_row.get("claimed_by_worker_ref") or "").strip() or None
    orphan_review_required = bool(run_record_row.get("orphan_review_required"))

    is_stuck = bool(claimed_by_worker_ref and lease_expires_at is not None and lease_expires_at < now_dt and status in _ACTIVE_STATUSES)
    is_infra_failure = latest_error_family == _INFRA_FAILURE_FAMILY
    resolved_provider_health = provider_health or AutoRecoveryProviderHealthSignal()
    backoff_ready = _backoff_ready(run_record_row, now_dt, provider_health=resolved_provider_health)
    provider_is_down = resolved_provider_health.status == "down"
    can_auto_retry = is_infra_failure and not provider_is_down and auto_retry_count < auto_retry_limit and backoff_ready and (status == "failed" or is_stuck)
    should_escalate_review = is_infra_failure and not orphan_review_required and (status == "failed" or is_stuck) and (provider_is_down or auto_retry_count >= auto_retry_limit)

    if not can_auto_retry and not should_escalate_review:
        return AutoRecoveryOutcome(applied=False, reason="no_auto_recovery_needed" if backoff_ready else "backoff_active")

    updated_row = deepcopy(dict(run_record_row))
    updated_row["updated_at"] = now_iso
    updated_row["auto_retry_count"] = auto_retry_count
    updated_row["auto_retry_limit"] = auto_retry_limit
    updated_row["auto_retry_base_backoff_seconds"] = max(1, _coerce_int(updated_row.get("auto_retry_base_backoff_seconds"), DEFAULT_AUTO_RETRY_BASE_BACKOFF_SECONDS))
    updated_row["last_auto_recovery_at"] = now_iso

    if can_auto_retry:
        new_queue_job_id = queue_job_id_factory() if queue_job_id_factory is not None else f"job_{uuid.uuid4().hex}"
        updated_row["status"] = "queued"
        updated_row["status_family"] = _status_family_for_status("queued")
        updated_row["queue_job_id"] = new_queue_job_id
        updated_row["claimed_by_worker_ref"] = None
        updated_row["lease_expires_at"] = None
        updated_row["orphan_review_required"] = False
        updated_row["worker_attempt_number"] = worker_attempt_number + 1
        updated_row["auto_retry_count"] = auto_retry_count + 1
        if resolved_provider_health.status == "degraded":
            current_base_backoff = max(1, _coerce_int(updated_row.get("auto_retry_base_backoff_seconds"), DEFAULT_AUTO_RETRY_BASE_BACKOFF_SECONDS))
            updated_row["auto_retry_base_backoff_seconds"] = min(current_base_backoff * _DEGRADED_PROVIDER_BACKOFF_MULTIPLIER, MAX_AUTO_RETRY_BACKOFF_SECONDS)
        _append_action_log(updated_row, action="auto_retry", timestamp=now_iso, before_row=run_record_row, after_row=updated_row)
        return AutoRecoveryOutcome(applied=True, action="auto_retry", updated_run_record=updated_row)

    updated_row["status"] = "failed"
    updated_row["status_family"] = _status_family_for_status("failed")
    updated_row["claimed_by_worker_ref"] = None
    updated_row["lease_expires_at"] = None
    updated_row["orphan_review_required"] = True
    updated_row["queue_job_id"] = str(updated_row.get("queue_job_id") or "").strip() or None
    _append_action_log(updated_row, action="auto_mark_review_required", timestamp=now_iso, before_row=run_record_row, after_row=updated_row)
    return AutoRecoveryOutcome(applied=True, action="auto_mark_review_required", updated_run_record=updated_row)
