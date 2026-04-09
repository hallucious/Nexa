from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence
import uuid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@dataclass(frozen=True)
class DestinationCapability:
    destination_type: str
    destination_ref: str
    supports_text: bool
    supports_structured_payload: bool
    supports_attachments: bool
    supports_idempotency_key: bool
    supports_retry: bool
    max_payload_policy: Optional[Dict[str, Any]] = None
    auth_mode: str = 'unknown'

    @staticmethod
    def from_raw(raw: Mapping[str, Any]) -> 'DestinationCapability':
        return DestinationCapability(
            destination_type=str(raw.get('destination_type') or 'other'),
            destination_ref=str(raw.get('destination_ref') or ''),
            supports_text=bool(raw.get('supports_text', True)),
            supports_structured_payload=bool(raw.get('supports_structured_payload', False)),
            supports_attachments=bool(raw.get('supports_attachments', False)),
            supports_idempotency_key=bool(raw.get('supports_idempotency_key', False)),
            supports_retry=bool(raw.get('supports_retry', False)),
            max_payload_policy=dict(raw.get('max_payload_policy') or {}),
            auth_mode=str(raw.get('auth_mode') or 'unknown'),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'destination_type': self.destination_type,
            'destination_ref': self.destination_ref,
            'supports_text': self.supports_text,
            'supports_structured_payload': self.supports_structured_payload,
            'supports_attachments': self.supports_attachments,
            'supports_idempotency_key': self.supports_idempotency_key,
            'supports_retry': self.supports_retry,
            'max_payload_policy': dict(self.max_payload_policy or {}),
            'auth_mode': self.auth_mode,
        }


@dataclass(frozen=True)
class DeliveryPlan:
    delivery_plan_id: str
    run_ref: str
    destination_ref: str
    destination_type: str
    selected_output_ref: Optional[str] = None
    selected_artifact_ref: Optional[str] = None
    payload_projection_mode: str = 'final_output'
    title_template: Optional[str] = None
    body_template: Optional[str] = None
    attachment_refs: tuple[str, ...] = ()
    requires_confirmation: bool = False
    safety_scope: Optional[Dict[str, Any]] = None
    quota_scope: Optional[Dict[str, Any]] = None
    simulate_failure_reason_code: Optional[str] = None

    @staticmethod
    def from_raw(raw: Mapping[str, Any], *, run_ref: str) -> 'DeliveryPlan':
        return DeliveryPlan(
            delivery_plan_id=str(raw.get('delivery_plan_id') or str(uuid.uuid4())),
            run_ref=run_ref,
            destination_ref=str(raw.get('destination_ref') or ''),
            destination_type=str(raw.get('destination_type') or 'other'),
            selected_output_ref=(str(raw.get('selected_output_ref')) if raw.get('selected_output_ref') is not None else None),
            selected_artifact_ref=(str(raw.get('selected_artifact_ref')) if raw.get('selected_artifact_ref') is not None else None),
            payload_projection_mode=str(raw.get('payload_projection_mode') or 'final_output'),
            title_template=(str(raw.get('title_template')) if raw.get('title_template') is not None else None),
            body_template=(str(raw.get('body_template')) if raw.get('body_template') is not None else None),
            attachment_refs=tuple(str(item) for item in raw.get('attachment_refs', []) or []),
            requires_confirmation=bool(raw.get('requires_confirmation', False)),
            safety_scope=dict(raw.get('safety_scope') or {}),
            quota_scope=dict(raw.get('quota_scope') or {}),
            simulate_failure_reason_code=(str(raw.get('simulate_failure_reason_code')) if raw.get('simulate_failure_reason_code') is not None else None),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'delivery_plan_id': self.delivery_plan_id,
            'run_ref': self.run_ref,
            'destination_ref': self.destination_ref,
            'destination_type': self.destination_type,
            'selected_output_ref': self.selected_output_ref,
            'selected_artifact_ref': self.selected_artifact_ref,
            'payload_projection_mode': self.payload_projection_mode,
            'title_template': self.title_template,
            'body_template': self.body_template,
            'attachment_refs': list(self.attachment_refs),
            'requires_confirmation': self.requires_confirmation,
            'safety_scope': dict(self.safety_scope or {}),
            'quota_scope': dict(self.quota_scope or {}),
            'simulate_failure_reason_code': self.simulate_failure_reason_code,
        }


@dataclass(frozen=True)
class DeliveryAttempt:
    attempt_id: str
    delivery_plan_ref: str
    run_ref: str
    destination_ref: str
    started_at: str
    completed_at: Optional[str]
    status: str
    idempotency_key: Optional[str]
    response_summary: Optional[Dict[str, Any]]
    failure_reason_code: Optional[str]
    retry_eligible: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            'attempt_id': self.attempt_id,
            'delivery_plan_ref': self.delivery_plan_ref,
            'run_ref': self.run_ref,
            'destination_ref': self.destination_ref,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status,
            'idempotency_key': self.idempotency_key,
            'response_summary': dict(self.response_summary or {}),
            'failure_reason_code': self.failure_reason_code,
            'retry_eligible': self.retry_eligible,
        }


@dataclass(frozen=True)
class DeliveryRecord:
    run_ref: str
    destination_ref: str
    destination_type: str
    selected_output_ref: Optional[str]
    selected_artifact_ref: Optional[str]
    latest_status: str
    attempt_refs: tuple[str, ...]
    delivered_at: Optional[str]
    delivery_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'run_ref': self.run_ref,
            'destination_ref': self.destination_ref,
            'destination_type': self.destination_type,
            'selected_output_ref': self.selected_output_ref,
            'selected_artifact_ref': self.selected_artifact_ref,
            'latest_status': self.latest_status,
            'attempt_refs': list(self.attempt_refs),
            'delivered_at': self.delivered_at,
            'delivery_summary': dict(self.delivery_summary or {}),
        }


def record_not_attempted_delivery(*, plan: DeliveryPlan) -> DeliveryRecord:
    return DeliveryRecord(
        run_ref=plan.run_ref,
        destination_ref=plan.destination_ref,
        destination_type=plan.destination_type,
        selected_output_ref=plan.selected_output_ref,
        selected_artifact_ref=plan.selected_artifact_ref,
        latest_status='not_attempted',
        attempt_refs=(),
        delivered_at=None,
        delivery_summary={'reason': 'execution_not_completed'},
    )


def _project_payload(*, plan: DeliveryPlan, outputs: Mapping[str, Any], artifacts: Mapping[str, Any]) -> tuple[Any, Optional[str]]:
    if plan.selected_artifact_ref is not None:
        if plan.selected_artifact_ref not in artifacts:
            return None, 'DELIVERY_ARTIFACT_NOT_FOUND'
        selected = artifacts[plan.selected_artifact_ref]
    else:
        if not plan.selected_output_ref:
            return None, 'DELIVERY_OUTPUT_REF_REQUIRED'
        if plan.selected_output_ref not in outputs:
            return None, 'DELIVERY_OUTPUT_NOT_FOUND'
        selected = outputs[plan.selected_output_ref]

    if plan.payload_projection_mode == 'summary':
        return str(selected), None
    if plan.payload_projection_mode in {'final_output', 'artifact_content', 'custom_projection', 'artifact_ref'}:
        return selected, None
    return None, 'DELIVERY_UNSUPPORTED_PROJECTION'


def attempt_delivery(
    *,
    capability: DestinationCapability | Mapping[str, Any],
    plan: DeliveryPlan | Mapping[str, Any],
    outputs: Mapping[str, Any],
    artifacts: Optional[Mapping[str, Any]] = None,
    authorization_allowed: bool = True,
    confirmation_granted: bool = False,
) -> Dict[str, Any]:
    if not isinstance(capability, DestinationCapability):
        capability = DestinationCapability.from_raw(capability)
    if not isinstance(plan, DeliveryPlan):
        plan = DeliveryPlan.from_raw(plan, run_ref=str(plan.get('run_ref') or 'run.unknown'))

    started_at = _utc_now_iso()
    idempotency_key = str(uuid.uuid4()) if capability.supports_idempotency_key else None
    retry_eligible = False

    if capability.destination_ref != plan.destination_ref or capability.destination_type != plan.destination_type:
        failure_reason = 'DELIVERY_DESTINATION_MISMATCH'
        attempt = DeliveryAttempt(
            attempt_id=str(uuid.uuid4()),
            delivery_plan_ref=plan.delivery_plan_id,
            run_ref=plan.run_ref,
            destination_ref=plan.destination_ref,
            started_at=started_at,
            completed_at=_utc_now_iso(),
            status='blocked',
            idempotency_key=idempotency_key,
            response_summary=None,
            failure_reason_code=failure_reason,
            retry_eligible=False,
        )
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'blocked', (attempt.attempt_id,), None, {'reason_code': failure_reason})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': None}

    if not authorization_allowed:
        failure_reason = 'DELIVERY_AUTHORIZATION_BLOCKED'
        attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'blocked', idempotency_key, None, failure_reason, False)
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'blocked', (attempt.attempt_id,), None, {'reason_code': failure_reason})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': None}

    if plan.requires_confirmation and not confirmation_granted:
        failure_reason = 'DELIVERY_CONFIRMATION_REQUIRED'
        attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'blocked', idempotency_key, None, failure_reason, False)
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'blocked', (attempt.attempt_id,), None, {'reason_code': failure_reason})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': None}

    payload, projection_error = _project_payload(plan=plan, outputs=outputs, artifacts=artifacts or {})
    if projection_error is not None:
        attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'blocked', idempotency_key, None, projection_error, False)
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'blocked', (attempt.attempt_id,), None, {'reason_code': projection_error})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': None}

    if isinstance(payload, str):
        if not capability.supports_text:
            projection_error = 'DELIVERY_TEXT_UNSUPPORTED'
        else:
            projection_error = None
    else:
        if not capability.supports_structured_payload:
            projection_error = 'DELIVERY_STRUCTURED_PAYLOAD_UNSUPPORTED'
        else:
            projection_error = None

    if projection_error is not None:
        attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'blocked', idempotency_key, None, projection_error, False)
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'blocked', (attempt.attempt_id,), None, {'reason_code': projection_error})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': None}

    if plan.simulate_failure_reason_code:
        retry_eligible = capability.supports_retry
        attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'failed', idempotency_key, None, plan.simulate_failure_reason_code, retry_eligible)
        record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'failed', (attempt.attempt_id,), None, {'reason_code': plan.simulate_failure_reason_code})
        return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': payload}

    response_summary = {
        'destination_ref': capability.destination_ref,
        'destination_type': capability.destination_type,
        'auth_mode': capability.auth_mode,
        'payload_kind': 'text' if isinstance(payload, str) else 'structured',
    }
    attempt = DeliveryAttempt(str(uuid.uuid4()), plan.delivery_plan_id, plan.run_ref, plan.destination_ref, started_at, _utc_now_iso(), 'succeeded', idempotency_key, response_summary, None, retry_eligible)
    record = DeliveryRecord(plan.run_ref, plan.destination_ref, plan.destination_type, plan.selected_output_ref, plan.selected_artifact_ref, 'succeeded', (attempt.attempt_id,), attempt.completed_at, response_summary)
    return {'attempt': attempt.to_dict(), 'record': record.to_dict(), 'payload': payload}
