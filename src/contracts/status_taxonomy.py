from __future__ import annotations

from enum import Enum


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


class ExecutionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    PARTIAL = "partial"


class StreamingStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    STARTED = "started"
    CHUNKING = "chunking"
    COMPLETED = "completed"
    FALLBACK = "fallback"
    SKIPPED = "skipped"
    FAILED = "failed"


class DeliveryStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    PENDING = "pending"
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class GovernanceStatus(str, Enum):
    WITHIN_QUOTA = "within_quota"
    NEAR_QUOTA = "near_quota"
    OVER_QUOTA_BLOCKED = "over_quota_blocked"
    INPUT_SAFE = "input_safe"
    INPUT_WARNING = "input_warning"
    INPUT_BLOCKED = "input_blocked"
    CONFIRMATION_REQUIRED = "confirmation_required"


LAUNCH_STATUSES = tuple(item.value for item in LaunchStatus)
EXECUTION_STATUSES = tuple(item.value for item in ExecutionStatus)
STREAMING_STATUSES = tuple(item.value for item in StreamingStatus)
DELIVERY_STATUSES = tuple(item.value for item in DeliveryStatus)
GOVERNANCE_STATUSES = tuple(item.value for item in GovernanceStatus)
