from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary
from src.server.run_action_log_models import ProductRunLastActionView

ReadFailureFamily = Literal["product_read_failure", "run_not_found"]
ResultReadState = Literal["not_ready", "ready_success", "ready_partial", "ready_failure"]
StatusFamily = Literal[
    "pending",
    "active",
    "terminal_success",
    "terminal_failure",
    "terminal_partial",
    "unknown",
]

_ALLOWED_READ_FAILURE_FAMILIES = {"product_read_failure", "run_not_found"}
_ALLOWED_RESULT_READ_STATES = {"not_ready", "ready_success", "ready_partial", "ready_failure"}

RecoveryState = Literal["healthy", "leased", "retry_pending", "manual_review_required", "failed"]

_ALLOWED_RECOVERY_STATES = {"healthy", "leased", "retry_pending", "manual_review_required", "failed"}

_ALLOWED_STATUS_FAMILIES = {
    "pending",
    "active",
    "terminal_success",
    "terminal_failure",
    "terminal_partial",
    "unknown",
}


@dataclass(frozen=True)
class ProductExecutionTargetView:
    target_type: str
    target_ref: str

    def __post_init__(self) -> None:
        if not self.target_type:
            raise ValueError("ProductExecutionTargetView.target_type must be non-empty")
        if not self.target_ref:
            raise ValueError("ProductExecutionTargetView.target_ref must be non-empty")


@dataclass(frozen=True)
class ProductEngineSignalView:
    severity: str
    code: str
    message: str

    def __post_init__(self) -> None:
        if not self.severity:
            raise ValueError("ProductEngineSignalView.severity must be non-empty")
        if not self.code:
            raise ValueError("ProductEngineSignalView.code must be non-empty")
        if not self.message:
            raise ValueError("ProductEngineSignalView.message must be non-empty")


@dataclass(frozen=True)
class ProductRunProgressView:
    percent: Optional[int] = None
    active_node_id: Optional[str] = None
    active_node_label: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        if self.percent is not None and not 0 <= self.percent <= 100:
            raise ValueError("ProductRunProgressView.percent must be between 0 and 100 when provided")


@dataclass(frozen=True)
class ProductRunLinks:
    result: str
    trace: str
    artifacts: str

    def __post_init__(self) -> None:
        for field_name in ("result", "trace", "artifacts"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductRunLinks.{field_name} must be non-empty")




@dataclass(frozen=True)
class ProductRunControlActionsView:
    can_retry: bool = False
    can_force_reset: bool = False
    can_mark_reviewed: bool = False

@dataclass(frozen=True)
class ProductRunRecoveryView:
    recovery_state: RecoveryState
    worker_attempt_number: int = 0
    queue_job_id: Optional[str] = None
    claimed_by_worker_ref: Optional[str] = None
    lease_expires_at: Optional[str] = None
    orphan_review_required: bool = False
    latest_error_family: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        if self.recovery_state not in _ALLOWED_RECOVERY_STATES:
            raise ValueError(f"Unsupported ProductRunRecoveryView.recovery_state: {self.recovery_state}")
        if self.worker_attempt_number < 0:
            raise ValueError("ProductRunRecoveryView.worker_attempt_number must be >= 0")


@dataclass(frozen=True)
class ProductRunStatusResponse:
    run_id: str
    workspace_id: str
    execution_target: ProductExecutionTargetView
    status: str
    status_family: StatusFamily
    created_at: str
    started_at: Optional[str]
    updated_at: str
    completed_at: Optional[str] = None
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    progress: Optional[ProductRunProgressView] = None
    latest_engine_signal: Optional[ProductEngineSignalView] = None
    recovery: Optional[ProductRunRecoveryView] = None
    actions: Optional[ProductRunControlActionsView] = None
    last_action: Optional[ProductRunLastActionView] = None
    links: ProductRunLinks = field(default_factory=lambda: ProductRunLinks(result="/placeholder/result", trace="/placeholder/trace", artifacts="/placeholder/artifacts"))
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunStatusResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunStatusResponse.workspace_id must be non-empty")
        if not self.status:
            raise ValueError("ProductRunStatusResponse.status must be non-empty")
        if self.status_family not in _ALLOWED_STATUS_FAMILIES:
            raise ValueError(f"Unsupported ProductRunStatusResponse.status_family: {self.status_family}")
        if not self.created_at:
            raise ValueError("ProductRunStatusResponse.created_at must be non-empty")
        if not self.updated_at:
            raise ValueError("ProductRunStatusResponse.updated_at must be non-empty")


@dataclass(frozen=True)
class ProductResultSummaryView:
    title: str
    description: str

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("ProductResultSummaryView.title must be non-empty")
        if not self.description:
            raise ValueError("ProductResultSummaryView.description must be non-empty")


@dataclass(frozen=True)
class ProductFinalOutputView:
    output_key: str
    value_preview: str
    value_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.output_key:
            raise ValueError("ProductFinalOutputView.output_key must be non-empty")
        if self.value_preview is None:
            raise ValueError("ProductFinalOutputView.value_preview must not be None")


@dataclass(frozen=True)
class ProductArtifactRefView:
    artifact_id: str
    kind: str
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("ProductArtifactRefView.artifact_id must be non-empty")
        if not self.kind:
            raise ValueError("ProductArtifactRefView.kind must be non-empty")


@dataclass(frozen=True)
class ProductTraceRefView:
    run_id: str
    endpoint: str

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductTraceRefView.run_id must be non-empty")
        if not self.endpoint:
            raise ValueError("ProductTraceRefView.endpoint must be non-empty")


@dataclass(frozen=True)
class ProductRunResultResponse:
    run_id: str
    workspace_id: str
    result_state: ResultReadState
    final_status: Optional[str]
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    result_summary: Optional[ProductResultSummaryView] = None
    final_output: Optional[ProductFinalOutputView] = None
    artifact_refs: tuple[ProductArtifactRefView, ...] = ()
    trace_ref: Optional[ProductTraceRefView] = None
    recovery: Optional[ProductRunRecoveryView] = None
    actions: Optional[ProductRunControlActionsView] = None
    last_action: Optional[ProductRunLastActionView] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    updated_at: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunResultResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunResultResponse.workspace_id must be non-empty")
        if self.result_state not in _ALLOWED_RESULT_READ_STATES:
            raise ValueError(f"Unsupported ProductRunResultResponse.result_state: {self.result_state}")
        if not isinstance(self.metrics, dict):
            raise TypeError("ProductRunResultResponse.metrics must be a dict")
        if self.result_state != "not_ready" and self.final_status is None:
            raise ValueError("ProductRunResultResponse.final_status must be set when result is ready")


@dataclass(frozen=True)
class ProductRunReadRejectedResponse:
    failure_family: ReadFailureFamily
    reason_code: str
    message: str
    run_id: Optional[str] = None
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_READ_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductRunReadRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductRunReadRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductRunReadRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class RunStatusReadOutcome:
    response: Optional[ProductRunStatusResponse] = None
    rejected: Optional[ProductRunReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class RunResultReadOutcome:
    response: Optional[ProductRunResultResponse] = None
    rejected: Optional[ProductRunReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
