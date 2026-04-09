from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LaunchStatus(str, Enum):
    CREATED = "created"
    REQUESTED = "requested"
    READY = "ready"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    SAFETY_BLOCKED = "safety_blocked"
    QUOTA_BLOCKED = "quota_blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"
    LAUNCH_CANCELLED = "launch_cancelled"
    STARTED = "started"
    RESUMED = "resumed"
    FAILED = "failed"


class SafetyStatus(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"
    UNKNOWN = "unknown"


class QuotaStatus(str, Enum):
    WITHIN_LIMIT = "within_limit"
    NEAR_LIMIT = "near_limit"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    QUEUED = "queued"
    UNKNOWN = "unknown"


class StreamingStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    STARTED = "started"
    CHUNKING = "chunking"
    COMPLETED = "completed"
    FALLBACK = "fallback"
    SKIPPED = "skipped"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"


class DeliveryStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    PENDING = "pending"
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class GovernanceStatus(str, Enum):
    WITHIN_QUOTA = "within_quota"
    NEAR_QUOTA = "near_quota"
    OVER_QUOTA_BLOCKED = "over_quota_blocked"
    INPUT_SAFE = "input_safe"
    INPUT_WARNING = "input_warning"
    INPUT_BLOCKED = "input_blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"


@dataclass(frozen=True)
class ReasonCodeRecord:
    code: str
    subsystem: str
    severity: str
    family: str
    human_summary: str
    recommended_next_action: Optional[str] = None


_REASON_CODE_REGISTRY: dict[str, ReasonCodeRecord] = {
    "safety.credential.exposed_secret_pattern": ReasonCodeRecord(
        code="safety.credential.exposed_secret_pattern",
        subsystem="safety",
        severity="blocking",
        family="safety_status",
        human_summary="Input appears to contain a credential or API secret.",
        recommended_next_action="Remove the secret before launch.",
    ),
    "safety.personal.detected_personal_data_warning": ReasonCodeRecord(
        code="safety.personal.detected_personal_data_warning",
        subsystem="safety",
        severity="warning",
        family="safety_status",
        human_summary="Input appears to contain personal contact information.",
        recommended_next_action="Confirm that provider submission is intended.",
    ),
    "safety.policy.confirmation_required_sensitive_input": ReasonCodeRecord(
        code="safety.policy.confirmation_required_sensitive_input",
        subsystem="safety",
        severity="warning",
        family="safety_status",
        human_summary="Input looks sensitive for unattended automation or external delivery.",
        recommended_next_action="Require explicit confirmation before unattended launch.",
    ),
    "safety.confidential.detected_confidential_data_warning": ReasonCodeRecord(
        code="safety.confidential.detected_confidential_data_warning",
        subsystem="safety",
        severity="warning",
        family="safety_status",
        human_summary="Input is marked as confidential or internal-only.",
        recommended_next_action="Confirm that this content may leave the workspace.",
    ),
    "safety.external.review_recommended": ReasonCodeRecord(
        code="safety.external.review_recommended",
        subsystem="safety",
        severity="info",
        family="safety_status",
        human_summary="External file or URL input should be reviewed before provider submission.",
        recommended_next_action="Review the external source and confirm it is expected.",
    ),
    "quota.run.count_limit_exceeded": ReasonCodeRecord(
        code="quota.run.count_limit_exceeded",
        subsystem="quota",
        severity="blocking",
        family="quota_status",
        human_summary="Run count quota would be exceeded.",
        recommended_next_action="Wait for quota reset or increase the run-count limit.",
    ),
    "quota.cost.estimated_limit_exceeded": ReasonCodeRecord(
        code="quota.cost.estimated_limit_exceeded",
        subsystem="quota",
        severity="blocking",
        family="quota_status",
        human_summary="Estimated cost quota would be exceeded.",
        recommended_next_action="Lower estimated usage or increase the cost limit.",
    ),
    "quota.streaming.minutes_limit_exceeded": ReasonCodeRecord(
        code="quota.streaming.minutes_limit_exceeded",
        subsystem="quota",
        severity="blocking",
        family="quota_status",
        human_summary="Streaming minutes quota would be exceeded.",
        recommended_next_action="Shorten streaming duration or increase the streaming limit.",
    ),
    "quota.delivery.action_limit_exceeded": ReasonCodeRecord(
        code="quota.delivery.action_limit_exceeded",
        subsystem="quota",
        severity="blocking",
        family="quota_status",
        human_summary="Delivery action quota would be exceeded.",
        recommended_next_action="Wait for quota reset or reduce delivery attempts.",
    ),
    "quota.automation.launch_limit_exceeded": ReasonCodeRecord(
        code="quota.automation.launch_limit_exceeded",
        subsystem="quota",
        severity="blocking",
        family="quota_status",
        human_summary="Automation launch quota would be exceeded.",
        recommended_next_action="Wait for quota reset or reduce automation frequency.",
    ),
    "quota.policy.near_limit_warning": ReasonCodeRecord(
        code="quota.policy.near_limit_warning",
        subsystem="quota",
        severity="warning",
        family="quota_status",
        human_summary="Quota usage is near the configured threshold.",
        recommended_next_action="Review projected usage before continuing.",
    ),
    "delivery.destination.mismatch": ReasonCodeRecord(
        code="delivery.destination.mismatch",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Delivery destination does not match the declared capability.",
        recommended_next_action="Use a matching destination capability and plan.",
    ),
    "delivery.destination.authorization_blocked": ReasonCodeRecord(
        code="delivery.destination.authorization_blocked",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Delivery was blocked because authorization is not available.",
        recommended_next_action="Authorize the destination before delivery.",
    ),
    "delivery.destination.confirmation_required": ReasonCodeRecord(
        code="delivery.destination.confirmation_required",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Delivery requires explicit confirmation before sending.",
        recommended_next_action="Confirm the outbound delivery action.",
    ),
    "delivery.payload.artifact_not_found": ReasonCodeRecord(
        code="delivery.payload.artifact_not_found",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Selected artifact was not found for delivery.",
        recommended_next_action="Choose a valid artifact reference.",
    ),
    "delivery.payload.output_ref_required": ReasonCodeRecord(
        code="delivery.payload.output_ref_required",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Delivery requires an explicit selected output reference.",
        recommended_next_action="Select the output that should be delivered.",
    ),
    "delivery.payload.output_not_found": ReasonCodeRecord(
        code="delivery.payload.output_not_found",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Selected output was not found for delivery.",
        recommended_next_action="Choose a valid output reference.",
    ),
    "delivery.payload.unsupported_projection": ReasonCodeRecord(
        code="delivery.payload.unsupported_projection",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Delivery projection mode is not supported.",
        recommended_next_action="Use a supported payload projection mode.",
    ),
    "delivery.payload.text_unsupported": ReasonCodeRecord(
        code="delivery.payload.text_unsupported",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Destination does not accept text payloads.",
        recommended_next_action="Choose a destination that supports text payloads.",
    ),
    "delivery.payload.structured_payload_unsupported": ReasonCodeRecord(
        code="delivery.payload.structured_payload_unsupported",
        subsystem="delivery",
        severity="blocking",
        family="delivery_status",
        human_summary="Destination does not accept structured payloads.",
        recommended_next_action="Change projection mode or choose a compatible destination.",
    ),
}


def lookup_reason_code_record(code: str) -> Optional[ReasonCodeRecord]:
    return _REASON_CODE_REGISTRY.get(code)


def is_canonical_reason_code(code: str) -> bool:
    return code in _REASON_CODE_REGISTRY


def register_reason_code(record: ReasonCodeRecord) -> None:
    _REASON_CODE_REGISTRY[record.code] = record


LAUNCH_STATUSES = tuple(item.value for item in LaunchStatus)
SAFETY_STATUSES = tuple(item.value for item in SafetyStatus)
QUOTA_STATUSES = tuple(item.value for item in QuotaStatus)
EXECUTION_STATUSES = tuple(item.value for item in ExecutionStatus)
STREAMING_STATUSES = tuple(item.value for item in StreamingStatus)
DELIVERY_STATUSES = tuple(item.value for item in DeliveryStatus)
GOVERNANCE_STATUSES = tuple(item.value for item in GovernanceStatus)
CANONICAL_REASON_CODES = tuple(sorted(_REASON_CODE_REGISTRY))


__all__ = [
    "LaunchStatus",
    "SafetyStatus",
    "QuotaStatus",
    "ExecutionStatus",
    "StreamingStatus",
    "DeliveryStatus",
    "GovernanceStatus",
    "ReasonCodeRecord",
    "lookup_reason_code_record",
    "is_canonical_reason_code",
    "register_reason_code",
    "LAUNCH_STATUSES",
    "SAFETY_STATUSES",
    "QUOTA_STATUSES",
    "EXECUTION_STATUSES",
    "STREAMING_STATUSES",
    "DELIVERY_STATUSES",
    "GOVERNANCE_STATUSES",
    "CANONICAL_REASON_CODES",
]
