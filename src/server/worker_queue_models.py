from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

QueueJobState = Literal["queued", "claimed", "completed", "abandoned"]
WorkerFailureFamily = Literal["worker_infrastructure_failure", "engine_execution_failure", "engine_partial_result"]

_ALLOWED_QUEUE_JOB_STATES = {"queued", "claimed", "completed", "abandoned"}
_ALLOWED_WORKER_FAILURE_FAMILIES = {
    "worker_infrastructure_failure",
    "engine_execution_failure",
    "engine_partial_result",
}


@dataclass(frozen=True)
class WorkerLeasePolicy:
    lease_duration_s: int = 60
    heartbeat_extension_s: int = 60
    max_worker_attempts: int = 3
    requeue_orphans: bool = True

    def __post_init__(self) -> None:
        if self.lease_duration_s <= 0:
            raise ValueError("WorkerLeasePolicy.lease_duration_s must be > 0")
        if self.heartbeat_extension_s <= 0:
            raise ValueError("WorkerLeasePolicy.heartbeat_extension_s must be > 0")
        if self.max_worker_attempts <= 0:
            raise ValueError("WorkerLeasePolicy.max_worker_attempts must be > 0")


@dataclass(frozen=True)
class QueueJobProjection:
    queue_job_id: str
    run_id: str
    workspace_id: str
    run_request_id: str
    queue_state: QueueJobState
    queue_name: str
    priority: str
    enqueued_at: str
    available_at: str
    created_at: str
    updated_at: str
    claimed_by_worker_ref: Optional[str] = None
    claimed_at: Optional[str] = None
    lease_expires_at: Optional[str] = None
    last_heartbeat_at: Optional[str] = None
    worker_attempt_number: int = 0

    def __post_init__(self) -> None:
        if not self.queue_job_id:
            raise ValueError("QueueJobProjection.queue_job_id must be non-empty")
        if not self.run_id:
            raise ValueError("QueueJobProjection.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("QueueJobProjection.workspace_id must be non-empty")
        if not self.run_request_id:
            raise ValueError("QueueJobProjection.run_request_id must be non-empty")
        if self.queue_state not in _ALLOWED_QUEUE_JOB_STATES:
            raise ValueError(f"Unsupported QueueJobProjection.queue_state: {self.queue_state}")
        if not self.queue_name:
            raise ValueError("QueueJobProjection.queue_name must be non-empty")
        if not self.priority:
            raise ValueError("QueueJobProjection.priority must be non-empty")
        if self.worker_attempt_number < 0:
            raise ValueError("QueueJobProjection.worker_attempt_number must be >= 0")
        for field_name in ("enqueued_at", "available_at", "created_at", "updated_at"):
            if not getattr(self, field_name):
                raise ValueError(f"QueueJobProjection.{field_name} must be non-empty")

    def to_row(self) -> dict[str, Any]:
        return {
            "queue_job_id": self.queue_job_id,
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "run_request_id": self.run_request_id,
            "queue_state": self.queue_state,
            "queue_name": self.queue_name,
            "priority": self.priority,
            "enqueued_at": self.enqueued_at,
            "available_at": self.available_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "claimed_by_worker_ref": self.claimed_by_worker_ref,
            "claimed_at": self.claimed_at,
            "lease_expires_at": self.lease_expires_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "worker_attempt_number": self.worker_attempt_number,
        }


@dataclass(frozen=True)
class WorkerClaim:
    worker_ref: str
    queue_job: QueueJobProjection
    run_record_row: dict[str, Any]
    engine_request: Any
    lease_policy: WorkerLeasePolicy

    def __post_init__(self) -> None:
        if not self.worker_ref:
            raise ValueError("WorkerClaim.worker_ref must be non-empty")
        if self.queue_job.queue_state != "claimed":
            raise ValueError("WorkerClaim requires a claimed queue_job")
        if not isinstance(self.run_record_row, dict):
            raise TypeError("WorkerClaim.run_record_row must be a dict")


@dataclass(frozen=True)
class QueueSubmission:
    queue_job: QueueJobProjection
    run_record_row: dict[str, Any]
    engine_request: Any

    def __post_init__(self) -> None:
        if self.queue_job.queue_state != "queued":
            raise ValueError("QueueSubmission requires a queued queue_job")
        if not isinstance(self.run_record_row, dict):
            raise TypeError("QueueSubmission.run_record_row must be a dict")


@dataclass(frozen=True)
class WorkerOrphanReview:
    run_id: str
    queue_job_id: str
    is_orphaned: bool
    reason_code: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("WorkerOrphanReview.run_id must be non-empty")
        if not self.queue_job_id:
            raise ValueError("WorkerOrphanReview.queue_job_id must be non-empty")
        if self.is_orphaned and not self.reason_code:
            raise ValueError("WorkerOrphanReview.reason_code must be set when orphaned")


@dataclass(frozen=True)
class WorkerProjectionBundle:
    run_record_row: dict[str, Any]
    queue_job_row: dict[str, Any]
    result_row: Optional[dict[str, Any]] = None
    artifact_rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    trace_rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    failure_family: Optional[WorkerFailureFamily] = None

    def __post_init__(self) -> None:
        if not isinstance(self.run_record_row, dict):
            raise TypeError("WorkerProjectionBundle.run_record_row must be a dict")
        if not isinstance(self.queue_job_row, dict):
            raise TypeError("WorkerProjectionBundle.queue_job_row must be a dict")
        if self.failure_family is not None and self.failure_family not in _ALLOWED_WORKER_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported WorkerProjectionBundle.failure_family: {self.failure_family}")
