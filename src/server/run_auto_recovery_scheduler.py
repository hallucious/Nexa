from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from src.server.provider_health_models import AutoRecoveryFallbackCandidate, AutoRecoveryProviderHealthSignal
from src.server.run_auto_recovery_policy import AutoRecoveryOutcome, AutoRecoveryScoringPolicy, apply_auto_recovery

RunRecordWriter = Callable[[Mapping[str, Any]], Any]
QueueJobIdFactory = Callable[[], str]
ProviderHealthResolver = Callable[[Mapping[str, Any]], AutoRecoveryProviderHealthSignal | None]
WorkspaceProviderHealthSignalsResolver = Callable[[Mapping[str, Any]], Mapping[str, AutoRecoveryProviderHealthSignal] | Sequence[AutoRecoveryProviderHealthSignal] | None]
WorkspaceProviderBindingRowsResolver = Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]] | None]
FallbackCandidatesResolver = Callable[[Mapping[str, Any], AutoRecoveryProviderHealthSignal | None], Sequence[AutoRecoveryFallbackCandidate] | None]
WorkspaceScoringPolicyResolver = Callable[[Mapping[str, Any]], Mapping[str, Any] | AutoRecoveryScoringPolicy | None]


def _normalize_provider_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_provider_health_map(
    value: Mapping[str, AutoRecoveryProviderHealthSignal] | Sequence[AutoRecoveryProviderHealthSignal] | None,
) -> dict[str, AutoRecoveryProviderHealthSignal]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        result: dict[str, AutoRecoveryProviderHealthSignal] = {}
        for provider_key, signal in value.items():
            normalized_key = _normalize_provider_key(provider_key)
            if normalized_key and isinstance(signal, AutoRecoveryProviderHealthSignal):
                result[normalized_key] = signal
        return result
    result: dict[str, AutoRecoveryProviderHealthSignal] = {}
    for signal in value:
        if not isinstance(signal, AutoRecoveryProviderHealthSignal):
            continue
        normalized_key = _normalize_provider_key(signal.provider_key)
        if normalized_key:
            result[normalized_key] = signal
    return result


def _fallback_candidates_from_workspace_bindings(
    run_row: Mapping[str, Any],
    *,
    provider_health: AutoRecoveryProviderHealthSignal | None,
    binding_rows: Sequence[Mapping[str, Any]] | None,
    workspace_provider_health_signals: Mapping[str, AutoRecoveryProviderHealthSignal] | Sequence[AutoRecoveryProviderHealthSignal] | None = None,
) -> tuple[AutoRecoveryFallbackCandidate, ...] | None:
    if not binding_rows:
        return None
    workspace_id = str(run_row.get("workspace_id") or "").strip()
    current_provider_key = _normalize_provider_key((provider_health.provider_key if provider_health is not None else None) or run_row.get("provider_key"))
    health_map = _normalize_provider_health_map(workspace_provider_health_signals)
    candidates: list[AutoRecoveryFallbackCandidate] = []
    seen_provider_keys: set[str] = set()
    for row in binding_rows:
        if not isinstance(row, Mapping):
            continue
        row_workspace_id = str(row.get("workspace_id") or "").strip()
        if workspace_id and row_workspace_id and row_workspace_id != workspace_id:
            continue
        provider_key = _normalize_provider_key(row.get("provider_key"))
        if not provider_key or provider_key in seen_provider_keys or provider_key == current_provider_key:
            continue
        enabled = row.get("enabled")
        if enabled is False:
            continue
        signal = health_map.get(provider_key)
        status = signal.status if signal is not None else "healthy"
        reason_code = signal.reason_code if signal is not None else "workspace.binding.available"
        provider_family = str(row.get("provider_family") or "").strip() or None
        raw_priority_weight = row.get("fallback_priority_weight", row.get("priority_weight", 0.0))
        try:
            priority_weight = float(raw_priority_weight)
        except (TypeError, ValueError):
            priority_weight = 0.0
        raw_cost_ratio = row.get("fallback_cost_ratio", row.get("cost_ratio", row.get("provider_cost_ratio")))
        try:
            cost_ratio = float(raw_cost_ratio) if raw_cost_ratio is not None else None
        except (TypeError, ValueError):
            cost_ratio = None
        candidates.append(
            AutoRecoveryFallbackCandidate(
                provider_key=provider_key,
                status=status,
                provider_family=provider_family,
                reason_code=reason_code,
                cost_ratio=cost_ratio,
                priority_weight=priority_weight,
            )
        )
        seen_provider_keys.add(provider_key)
    return tuple(candidates) if candidates else None


@dataclass(frozen=True)
class AutoRecoverySchedulerStats:
    scanned_count: int
    eligible_count: int
    applied_count: int
    auto_retry_count: int
    auto_mark_review_required_count: int
    auto_fallback_retry_count: int
    skipped_count: int


@dataclass(frozen=True)
class AutoRecoveryScheduledUpdate:
    run_id: str
    action: str
    updated_run_record: Mapping[str, Any]


@dataclass(frozen=True)
class AutoRecoverySchedulerOutcome:
    stats: AutoRecoverySchedulerStats
    applied_updates: tuple[AutoRecoveryScheduledUpdate, ...]


class AutoRecoveryScheduler:
    @staticmethod
    def _is_sequence_of_rows(value: Sequence[Mapping[str, Any]] | None) -> tuple[Mapping[str, Any], ...]:
        if not value:
            return ()
        return tuple(row for row in value if isinstance(row, Mapping))

    @classmethod
    def run_batch(
        cls,
        run_rows: Sequence[Mapping[str, Any]] | None,
        *,
        now_iso: str,
        run_record_writer: Optional[RunRecordWriter] = None,
        queue_job_id_factory: Optional[QueueJobIdFactory] = None,
        provider_health_resolver: Optional[ProviderHealthResolver] = None,
        workspace_provider_health_signals_resolver: Optional[WorkspaceProviderHealthSignalsResolver] = None,
        workspace_provider_binding_rows_resolver: Optional[WorkspaceProviderBindingRowsResolver] = None,
        fallback_candidates_resolver: Optional[FallbackCandidatesResolver] = None,
        workspace_scoring_policy_resolver: Optional[WorkspaceScoringPolicyResolver] = None,
        batch_limit: int = 50,
        max_applied_per_batch: Optional[int] = None,
    ) -> AutoRecoverySchedulerOutcome:
        if batch_limit < 0:
            raise ValueError("batch_limit must be non-negative")
        if max_applied_per_batch is not None and max_applied_per_batch < 0:
            raise ValueError("max_applied_per_batch must be non-negative")

        rows = cls._is_sequence_of_rows(run_rows)
        rows = () if batch_limit == 0 else rows[:batch_limit]

        applied_updates: list[AutoRecoveryScheduledUpdate] = []
        eligible_count = 0
        auto_retry_count = 0
        auto_mark_review_required_count = 0
        auto_fallback_retry_count = 0

        for row in rows:
            if max_applied_per_batch is not None and len(applied_updates) >= max_applied_per_batch:
                break
            provider_health = provider_health_resolver(row) if provider_health_resolver is not None else None
            if fallback_candidates_resolver is not None:
                fallback_candidates = fallback_candidates_resolver(row, provider_health)
            else:
                binding_rows = workspace_provider_binding_rows_resolver(row) if workspace_provider_binding_rows_resolver is not None else None
                workspace_provider_health_signals = (
                    workspace_provider_health_signals_resolver(row)
                    if workspace_provider_health_signals_resolver is not None
                    else None
                )
                fallback_candidates = _fallback_candidates_from_workspace_bindings(
                    row,
                    provider_health=provider_health,
                    binding_rows=binding_rows,
                    workspace_provider_health_signals=workspace_provider_health_signals,
                )
            scoring_policy = workspace_scoring_policy_resolver(row) if workspace_scoring_policy_resolver is not None else None
            outcome: AutoRecoveryOutcome = apply_auto_recovery(
                row,
                now_iso=now_iso,
                queue_job_id_factory=queue_job_id_factory,
                provider_health=provider_health,
                fallback_candidates=fallback_candidates,
                scoring_policy=scoring_policy,
            )
            if not outcome.applied or outcome.updated_run_record is None or outcome.action is None:
                continue
            eligible_count += 1
            updated_row = dict(outcome.updated_run_record)
            if run_record_writer is not None:
                run_record_writer(updated_row)
            if outcome.action == "auto_retry":
                auto_retry_count += 1
            elif outcome.action == "auto_mark_review_required":
                auto_mark_review_required_count += 1
            elif outcome.action == "auto_fallback_retry":
                auto_fallback_retry_count += 1
            applied_updates.append(AutoRecoveryScheduledUpdate(
                run_id=str(updated_row.get("run_id") or ""),
                action=outcome.action,
                updated_run_record=updated_row,
            ))

        applied_count = len(applied_updates)
        scanned_count = len(rows)
        skipped_count = scanned_count - applied_count
        return AutoRecoverySchedulerOutcome(
            stats=AutoRecoverySchedulerStats(
                scanned_count=scanned_count,
                eligible_count=eligible_count,
                applied_count=applied_count,
                auto_retry_count=auto_retry_count,
                auto_mark_review_required_count=auto_mark_review_required_count,
                auto_fallback_retry_count=auto_fallback_retry_count,
                skipped_count=skipped_count,
            ),
            applied_updates=tuple(applied_updates),
        )
