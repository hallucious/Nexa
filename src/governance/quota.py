from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    return float(value)


@dataclass(frozen=True)
class QuotaScope:
    scope_type: str
    scope_ref: str
    parent_scope_refs: tuple[str, ...] = ()

    @staticmethod
    def from_raw(raw: Dict[str, Any]) -> 'QuotaScope':
        return QuotaScope(
            scope_type=str(raw.get('scope_type') or 'workspace'),
            scope_ref=str(raw.get('scope_ref') or 'workspace.default'),
            parent_scope_refs=tuple(str(item) for item in raw.get('parent_scope_refs', []) or []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scope_type': self.scope_type,
            'scope_ref': self.scope_ref,
            'parent_scope_refs': list(self.parent_scope_refs),
        }


@dataclass(frozen=True)
class QuotaPolicy:
    policy_id: str
    scope_ref: str
    period_type: str = 'day'
    max_run_count: Optional[int] = None
    max_estimated_cost: Optional[float] = None
    max_actual_cost: Optional[float] = None
    max_stream_minutes: Optional[float] = None
    max_automation_launches: Optional[int] = None
    max_delivery_actions: Optional[int] = None
    warning_threshold_ratio: Optional[float] = None
    hard_block_enabled: bool = True

    @staticmethod
    def from_raw(raw: Dict[str, Any], *, scope_ref: str) -> 'QuotaPolicy':
        return QuotaPolicy(
            policy_id=str(raw.get('policy_id') or f'quota.{scope_ref}'),
            scope_ref=scope_ref,
            period_type=str(raw.get('period_type') or 'day'),
            max_run_count=raw.get('max_run_count'),
            max_estimated_cost=_coerce_float(raw.get('max_estimated_cost')),
            max_actual_cost=_coerce_float(raw.get('max_actual_cost')),
            max_stream_minutes=_coerce_float(raw.get('max_stream_minutes')),
            max_automation_launches=raw.get('max_automation_launches'),
            max_delivery_actions=raw.get('max_delivery_actions'),
            warning_threshold_ratio=_coerce_float(raw.get('warning_threshold_ratio')),
            hard_block_enabled=bool(raw.get('hard_block_enabled', True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'policy_id': self.policy_id,
            'scope_ref': self.scope_ref,
            'period_type': self.period_type,
            'max_run_count': self.max_run_count,
            'max_estimated_cost': self.max_estimated_cost,
            'max_actual_cost': self.max_actual_cost,
            'max_stream_minutes': self.max_stream_minutes,
            'max_automation_launches': self.max_automation_launches,
            'max_delivery_actions': self.max_delivery_actions,
            'warning_threshold_ratio': self.warning_threshold_ratio,
            'hard_block_enabled': self.hard_block_enabled,
        }


@dataclass(frozen=True)
class QuotaDecision:
    decision_id: str
    scope_ref: str
    requested_action_type: str
    estimated_usage: Optional[Dict[str, Any]]
    overall_status: str
    blocking_reason_code: Optional[str] = None
    warning_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'scope_ref': self.scope_ref,
            'requested_action_type': self.requested_action_type,
            'estimated_usage': dict(self.estimated_usage or {}),
            'overall_status': self.overall_status,
            'blocking_reason_code': self.blocking_reason_code,
            'warning_summary': self.warning_summary,
        }


@dataclass(frozen=True)
class UsageAccountingRecord:
    accounting_id: str
    scope_ref: str
    run_ref: Optional[str]
    action_type: str
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    stream_minutes_used: Optional[float] = None
    delivery_actions_used: Optional[int] = None
    automation_launches_used: Optional[int] = None
    recorded_at: str = _utc_now_iso()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'accounting_id': self.accounting_id,
            'scope_ref': self.scope_ref,
            'run_ref': self.run_ref,
            'action_type': self.action_type,
            'estimated_cost': self.estimated_cost,
            'actual_cost': self.actual_cost,
            'stream_minutes_used': self.stream_minutes_used,
            'delivery_actions_used': self.delivery_actions_used,
            'automation_launches_used': self.automation_launches_used,
            'recorded_at': self.recorded_at,
        }


@dataclass(frozen=True)
class QuotaStateRecord:
    scope_ref: str
    period_ref: str
    consumed_run_count: int = 0
    consumed_estimated_cost: Optional[float] = None
    consumed_actual_cost: Optional[float] = None
    consumed_stream_minutes: Optional[float] = None
    consumed_automation_launches: Optional[int] = None
    consumed_delivery_actions: Optional[int] = None
    remaining_summary: Optional[Dict[str, Any]] = None
    last_updated_at: str = _utc_now_iso()

    @staticmethod
    def from_raw(raw: Dict[str, Any], *, scope_ref: str, period_ref: str) -> 'QuotaStateRecord':
        return QuotaStateRecord(
            scope_ref=scope_ref,
            period_ref=str(raw.get('period_ref') or period_ref),
            consumed_run_count=int(raw.get('consumed_run_count', 0) or 0),
            consumed_estimated_cost=_coerce_float(raw.get('consumed_estimated_cost')),
            consumed_actual_cost=_coerce_float(raw.get('consumed_actual_cost')),
            consumed_stream_minutes=_coerce_float(raw.get('consumed_stream_minutes')),
            consumed_automation_launches=int(raw.get('consumed_automation_launches', 0) or 0),
            consumed_delivery_actions=int(raw.get('consumed_delivery_actions', 0) or 0),
            remaining_summary=dict(raw.get('remaining_summary') or {}),
            last_updated_at=str(raw.get('last_updated_at') or _utc_now_iso()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scope_ref': self.scope_ref,
            'period_ref': self.period_ref,
            'consumed_run_count': self.consumed_run_count,
            'consumed_estimated_cost': self.consumed_estimated_cost,
            'consumed_actual_cost': self.consumed_actual_cost,
            'consumed_stream_minutes': self.consumed_stream_minutes,
            'consumed_automation_launches': self.consumed_automation_launches,
            'consumed_delivery_actions': self.consumed_delivery_actions,
            'remaining_summary': dict(self.remaining_summary or {}),
            'last_updated_at': self.last_updated_at,
        }


def evaluate_quota(
    *,
    scope: QuotaScope,
    policy: QuotaPolicy,
    state_record: QuotaStateRecord,
    requested_action_type: str,
    estimated_usage: Optional[Dict[str, Any]] = None,
) -> QuotaDecision:
    usage = dict(estimated_usage or {})
    decision_status = 'allow'
    block_reason: Optional[str] = None
    warning_summary: Optional[str] = None

    def _set_warning(message: str) -> None:
        nonlocal decision_status, warning_summary
        if decision_status == 'allow':
            decision_status = 'allow_with_warning'
            warning_summary = message

    def _block(reason_code: str) -> None:
        nonlocal decision_status, block_reason
        decision_status = 'blocked' if policy.hard_block_enabled else 'allow_with_warning'
        if decision_status == 'blocked':
            block_reason = reason_code
        else:
            _set_warning(reason_code)

    if requested_action_type in {'run_launch', 'automation_launch'} and policy.max_run_count is not None:
        projected = state_record.consumed_run_count + int(usage.get('run_count', 1) or 1)
        if projected > policy.max_run_count:
            _block('QUOTA_RUN_COUNT_EXCEEDED')
        elif policy.warning_threshold_ratio is not None and projected >= max(1, int(policy.max_run_count * policy.warning_threshold_ratio)):
            _set_warning('run count is near quota limit')

    estimated_cost = _coerce_float(usage.get('estimated_cost'))
    if estimated_cost is not None and policy.max_estimated_cost is not None:
        projected_cost = float(state_record.consumed_estimated_cost or 0.0) + estimated_cost
        if projected_cost > policy.max_estimated_cost:
            _block('QUOTA_ESTIMATED_COST_EXCEEDED')
        elif policy.warning_threshold_ratio is not None and projected_cost >= policy.max_estimated_cost * policy.warning_threshold_ratio:
            _set_warning('estimated cost is near quota limit')

    stream_minutes = _coerce_float(usage.get('stream_minutes'))
    if requested_action_type == 'streaming_continuation' and stream_minutes is not None and policy.max_stream_minutes is not None:
        projected_stream = float(state_record.consumed_stream_minutes or 0.0) + stream_minutes
        if projected_stream > policy.max_stream_minutes:
            _block('QUOTA_STREAM_MINUTES_EXCEEDED')
        elif policy.warning_threshold_ratio is not None and projected_stream >= policy.max_stream_minutes * policy.warning_threshold_ratio:
            _set_warning('streaming minutes are near quota limit')

    delivery_actions = int(usage.get('delivery_actions', 0) or 0)
    if requested_action_type == 'delivery_action' and policy.max_delivery_actions is not None:
        projected_delivery = int(state_record.consumed_delivery_actions or 0) + max(1, delivery_actions)
        if projected_delivery > policy.max_delivery_actions:
            _block('QUOTA_DELIVERY_ACTIONS_EXCEEDED')
        elif policy.warning_threshold_ratio is not None and projected_delivery >= max(1, int(policy.max_delivery_actions * policy.warning_threshold_ratio)):
            _set_warning('delivery actions are near quota limit')

    if requested_action_type == 'automation_launch' and policy.max_automation_launches is not None:
        projected_launches = int(state_record.consumed_automation_launches or 0) + int(usage.get('automation_launches', 1) or 1)
        if projected_launches > policy.max_automation_launches:
            _block('QUOTA_AUTOMATION_LAUNCHES_EXCEEDED')
        elif policy.warning_threshold_ratio is not None and projected_launches >= max(1, int(policy.max_automation_launches * policy.warning_threshold_ratio)):
            _set_warning('automation launches are near quota limit')

    return QuotaDecision(
        decision_id=str(uuid.uuid4()),
        scope_ref=scope.scope_ref,
        requested_action_type=requested_action_type,
        estimated_usage=usage,
        overall_status=decision_status,
        blocking_reason_code=block_reason,
        warning_summary=warning_summary,
    )


def apply_usage_accounting(*, state_record: QuotaStateRecord, accounting: UsageAccountingRecord) -> QuotaStateRecord:
    action_type = accounting.action_type
    run_count = state_record.consumed_run_count + (1 if action_type in {'run_launch', 'automation_launch'} else 0)
    automation_launches = int(state_record.consumed_automation_launches or 0) + int(accounting.automation_launches_used or 0)
    delivery_actions = int(state_record.consumed_delivery_actions or 0) + int(accounting.delivery_actions_used or 0)
    estimated_cost = float(state_record.consumed_estimated_cost or 0.0) + float(accounting.estimated_cost or 0.0)
    actual_cost = float(state_record.consumed_actual_cost or 0.0) + float(accounting.actual_cost or 0.0)
    stream_minutes = float(state_record.consumed_stream_minutes or 0.0) + float(accounting.stream_minutes_used or 0.0)
    return QuotaStateRecord(
        scope_ref=state_record.scope_ref,
        period_ref=state_record.period_ref,
        consumed_run_count=run_count,
        consumed_estimated_cost=estimated_cost,
        consumed_actual_cost=actual_cost,
        consumed_stream_minutes=stream_minutes,
        consumed_automation_launches=automation_launches,
        consumed_delivery_actions=delivery_actions,
        remaining_summary=dict(state_record.remaining_summary or {}),
        last_updated_at=_utc_now_iso(),
    )
