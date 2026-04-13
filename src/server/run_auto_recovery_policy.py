from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
import uuid

from src.server.pricing_resolver import score_cost_ratio
from src.server.provider_health_models import AutoRecoveryFallbackCandidate, AutoRecoveryProviderHealthSignal

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
    fallback_provider_key: Optional[str] = None


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


def _append_action_log(updated_row: dict[str, Any], *, action: str, timestamp: str | None, before_row: Mapping[str, Any], after_row: Mapping[str, Any], actor_user_id: str = SYSTEM_AUTO_RECOVERY_ACTOR, extra_after_state: Mapping[str, Any] | None = None) -> None:
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
            **dict(extra_after_state or {}),
        },
    })
    updated_row["action_log"] = entries


def _resolve_current_provider_key(run_record_row: Mapping[str, Any], provider_health: AutoRecoveryProviderHealthSignal | None) -> str | None:
    provider_key = str((provider_health.provider_key if provider_health is not None else None) or run_record_row.get("provider_key") or "").strip().lower()
    return provider_key or None


def _fallback_health_score(status: str) -> float:
    normalized = str(status or "").strip().lower()
    if normalized == "healthy":
        return 1.0
    if normalized == "degraded":
        return 0.5
    return 0.0


def _fallback_candidate_breakdown(candidate: AutoRecoveryFallbackCandidate) -> dict[str, float | str | bool]:
    health_score = _fallback_health_score(candidate.status)
    cost_score = score_cost_ratio(candidate.cost_ratio)
    priority_score = float(candidate.priority_weight)
    final_score = (0.6 * health_score) + (0.3 * cost_score) + (0.1 * priority_score)
    return {
        "provider": candidate.provider_key,
        "health_score": health_score,
        "cost_score": cost_score,
        "priority_score": priority_score,
        "final_score": final_score,
        "selected": False,
    }


def _fallback_candidate_score(candidate: AutoRecoveryFallbackCandidate) -> tuple[float, float, float, str]:
    breakdown = _fallback_candidate_breakdown(candidate)
    normalized_cost = float(candidate.cost_ratio) if candidate.cost_ratio is not None else 1.0
    return (float(breakdown["final_score"]), float(breakdown["health_score"]) + float(breakdown["priority_score"]), -normalized_cost, candidate.provider_key)


def _select_fallback_candidate(
    run_record_row: Mapping[str, Any],
    *,
    provider_health: AutoRecoveryProviderHealthSignal | None = None,
    fallback_candidates: Sequence[AutoRecoveryFallbackCandidate] | None = None,
) -> AutoRecoveryFallbackCandidate | None:
    current_provider_key = _resolve_current_provider_key(run_record_row, provider_health)
    if not fallback_candidates:
        return None
    normalized_candidates = tuple(
        candidate
        for candidate in fallback_candidates
        if _fallback_health_score(candidate.status) > 0 and candidate.provider_key.strip().lower() != current_provider_key
    )
    if not normalized_candidates:
        return None
    return max(normalized_candidates, key=_fallback_candidate_score)


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
    fallback_candidates: Sequence[AutoRecoveryFallbackCandidate] | None = None,
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
    resolved_fallback_candidate = _select_fallback_candidate(
        run_record_row,
        provider_health=resolved_provider_health,
        fallback_candidates=fallback_candidates,
    )
    scoring_trace = []
    if fallback_candidates:
        current_provider_key = _resolve_current_provider_key(run_record_row, resolved_provider_health)
        normalized_candidates = tuple(
            candidate
            for candidate in fallback_candidates
            if _fallback_health_score(candidate.status) > 0 and candidate.provider_key.strip().lower() != current_provider_key
        )
        for candidate in normalized_candidates:
            breakdown = dict(_fallback_candidate_breakdown(candidate))
            if resolved_fallback_candidate is not None and candidate.provider_key == resolved_fallback_candidate.provider_key:
                breakdown["selected"] = True
            scoring_trace.append(breakdown)
    backoff_ready = _backoff_ready(run_record_row, now_dt, provider_health=resolved_provider_health)
    provider_is_down = resolved_provider_health.status == "down"
    terminal_or_stuck = status == "failed" or is_stuck
    can_auto_retry = is_infra_failure and not provider_is_down and auto_retry_count < auto_retry_limit and backoff_ready and terminal_or_stuck
    can_auto_fallback = is_infra_failure and not orphan_review_required and terminal_or_stuck and resolved_fallback_candidate is not None and (provider_is_down or auto_retry_count >= auto_retry_limit)
    should_escalate_review = is_infra_failure and not orphan_review_required and terminal_or_stuck and not can_auto_fallback and (provider_is_down or auto_retry_count >= auto_retry_limit)

    if not can_auto_retry and not can_auto_fallback and not should_escalate_review:
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

    if can_auto_fallback and resolved_fallback_candidate is not None:
        new_queue_job_id = queue_job_id_factory() if queue_job_id_factory is not None else f"job_{uuid.uuid4().hex}"
        updated_row["status"] = "queued"
        updated_row["status_family"] = _status_family_for_status("queued")
        updated_row["queue_job_id"] = new_queue_job_id
        updated_row["claimed_by_worker_ref"] = None
        updated_row["lease_expires_at"] = None
        updated_row["orphan_review_required"] = False
        updated_row["worker_attempt_number"] = worker_attempt_number + 1
        updated_row["auto_retry_count"] = auto_retry_count + 1
        updated_row["fallback_provider_key"] = resolved_fallback_candidate.provider_key
        _append_action_log(
            updated_row,
            action="fallback_scoring_evaluated",
            timestamp=now_iso,
            before_row=run_record_row,
            after_row=updated_row,
            extra_after_state={
                "selected_provider_key": resolved_fallback_candidate.provider_key,
                "scoring_trace": scoring_trace,
            },
        )
        _append_action_log(
            updated_row,
            action="auto_fallback_retry",
            timestamp=now_iso,
            before_row=run_record_row,
            after_row=updated_row,
            extra_after_state={
                "fallback_provider_key": resolved_fallback_candidate.provider_key,
                "fallback_provider_status": resolved_fallback_candidate.status,
                "fallback_reason_code": resolved_fallback_candidate.reason_code,
                "fallback_from_provider": _resolve_current_provider_key(run_record_row, resolved_provider_health),
                "fallback_to_provider": resolved_fallback_candidate.provider_key,
                "fallback_reason": "provider_down" if provider_is_down else "retry_exhausted",
            },
        )
        return AutoRecoveryOutcome(
            applied=True,
            action="auto_fallback_retry",
            updated_run_record=updated_row,
            fallback_provider_key=resolved_fallback_candidate.provider_key,
        )

    updated_row["status"] = "failed"
    updated_row["status_family"] = _status_family_for_status("failed")
    updated_row["claimed_by_worker_ref"] = None
    updated_row["lease_expires_at"] = None
    updated_row["orphan_review_required"] = True
    updated_row["queue_job_id"] = str(updated_row.get("queue_job_id") or "").strip() or None
    _append_action_log(updated_row, action="auto_mark_review_required", timestamp=now_iso, before_row=run_record_row, after_row=updated_row)
    return AutoRecoveryOutcome(applied=True, action="auto_mark_review_required", updated_run_record=updated_row)
