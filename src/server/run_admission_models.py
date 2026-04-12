from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary


ProductLaunchStatus = Literal["accepted", "rejected"]
ProductFailureFamily = Literal["product_rejection", "engine_rejection"]
ProductRunStatusFamily = Literal[
    "pending",
    "active",
    "terminal_success",
    "terminal_failure",
    "terminal_partial",
    "unknown",
]

_ALLOWED_PRODUCT_TARGET_TYPES = {"approved_snapshot", "commit_snapshot", "working_save"}
_ALLOWED_PRODUCT_FAILURE_FAMILIES = {"product_rejection", "engine_rejection"}
_ALLOWED_PRODUCT_RUN_STATUS_FAMILIES = {
    "pending",
    "active",
    "terminal_success",
    "terminal_failure",
    "terminal_partial",
    "unknown",
}
_ALLOWED_PRIORITIES = {"low", "normal", "high"}
_ALLOWED_MODES = {"standard", "test", "dry_run"}


@dataclass(frozen=True)
class ProductExecutionTarget:
    target_type: str
    target_ref: str

    def __post_init__(self) -> None:
        normalized_target_type = self.target_type.strip().lower()
        object.__setattr__(self, "target_type", normalized_target_type)
        if normalized_target_type not in _ALLOWED_PRODUCT_TARGET_TYPES:
            raise ValueError(f"Unsupported ProductExecutionTarget.target_type: {normalized_target_type}")
        if not self.target_ref:
            raise ValueError("ProductExecutionTarget.target_ref must be non-empty")


@dataclass(frozen=True)
class ProductLaunchOptions:
    mode: str = "standard"
    priority: str = "normal"
    allow_working_save_execution: bool = False

    def __post_init__(self) -> None:
        normalized_mode = self.mode.strip().lower()
        normalized_priority = self.priority.strip().lower()
        object.__setattr__(self, "mode", normalized_mode)
        object.__setattr__(self, "priority", normalized_priority)
        if normalized_mode not in _ALLOWED_MODES:
            raise ValueError(f"Unsupported ProductLaunchOptions.mode: {normalized_mode}")
        if normalized_priority not in _ALLOWED_PRIORITIES:
            raise ValueError(f"Unsupported ProductLaunchOptions.priority: {normalized_priority}")


@dataclass(frozen=True)
class ProductClientContext:
    source: Optional[str] = None
    request_id: Optional[str] = None
    correlation_token: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in ("source", "request_id", "correlation_token"):
            value = getattr(self, field_name)
            if value is not None and not str(value).strip():
                raise ValueError(f"ProductClientContext.{field_name} must be non-empty when provided")


@dataclass(frozen=True)
class ProductRunLaunchRequest:
    workspace_id: str
    execution_target: ProductExecutionTarget
    input_payload: Any = None
    launch_options: ProductLaunchOptions = field(default_factory=ProductLaunchOptions)
    client_context: ProductClientContext = field(default_factory=ProductClientContext)

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductRunLaunchRequest.workspace_id must be non-empty")


@dataclass(frozen=True)
class ProductAdmissionPolicy:
    allow_working_save_execution: bool = False
    workspace_launch_enabled: bool = True
    workspace_suspended: bool = False
    quota_available: bool = True


@dataclass(frozen=True)
class ExecutionTargetCatalogEntry:
    workspace_id: str
    target_ref: str
    source: Any
    target_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ExecutionTargetCatalogEntry.workspace_id must be non-empty")
        if not self.target_ref:
            raise ValueError("ExecutionTargetCatalogEntry.target_ref must be non-empty")
        if self.target_type is not None and self.target_type.strip().lower() not in _ALLOWED_PRODUCT_TARGET_TYPES:
            raise ValueError(f"Unsupported ExecutionTargetCatalogEntry.target_type: {self.target_type}")


@dataclass(frozen=True)
class ResolvedExecutionTarget:
    workspace_id: str
    requested_target_type: str
    requested_target_ref: str
    resolved_target_type: str
    resolved_target_ref: str
    storage_role: str
    source_payload: Any


@dataclass(frozen=True)
class RunRecordProjection:
    run_id: str
    workspace_id: str
    launch_request_id: str
    execution_target_type: str
    execution_target_ref: str
    status: str
    status_family: ProductRunStatusFamily
    result_state: Optional[str]
    latest_error_family: Optional[str]
    requested_by_user_id: Optional[str]
    auth_context_ref: Optional[str]
    trace_available: bool
    artifact_count: int
    trace_event_count: int
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    updated_at: str

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("RunRecordProjection.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("RunRecordProjection.workspace_id must be non-empty")
        if not self.launch_request_id:
            raise ValueError("RunRecordProjection.launch_request_id must be non-empty")
        if not self.execution_target_type:
            raise ValueError("RunRecordProjection.execution_target_type must be non-empty")
        if not self.execution_target_ref:
            raise ValueError("RunRecordProjection.execution_target_ref must be non-empty")
        if not self.status:
            raise ValueError("RunRecordProjection.status must be non-empty")
        if self.status_family not in _ALLOWED_PRODUCT_RUN_STATUS_FAMILIES:
            raise ValueError(f"Unsupported RunRecordProjection.status_family: {self.status_family}")
        if self.artifact_count < 0:
            raise ValueError("RunRecordProjection.artifact_count must be >= 0")
        if self.trace_event_count < 0:
            raise ValueError("RunRecordProjection.trace_event_count must be >= 0")
        for field_name in ("created_at", "updated_at"):
            if not getattr(self, field_name):
                raise ValueError(f"RunRecordProjection.{field_name} must be non-empty")

    def to_row(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "launch_request_id": self.launch_request_id,
            "execution_target_type": self.execution_target_type,
            "execution_target_ref": self.execution_target_ref,
            "status": self.status,
            "status_family": self.status_family,
            "result_state": self.result_state,
            "latest_error_family": self.latest_error_family,
            "requested_by_user_id": self.requested_by_user_id,
            "auth_context_ref": self.auth_context_ref,
            "trace_available": self.trace_available,
            "artifact_count": self.artifact_count,
            "trace_event_count": self.trace_event_count,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ProductRunLaunchLinks:
    run_status: str
    run_result: str


@dataclass(frozen=True)
class ProductRunLaunchAcceptedResponse:
    status: ProductLaunchStatus
    run_id: str
    workspace_id: str
    execution_target: ProductExecutionTarget
    initial_run_status: str
    links: ProductRunLaunchLinks
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if self.status != "accepted":
            raise ValueError("ProductRunLaunchAcceptedResponse.status must be 'accepted'")
        if not self.run_id:
            raise ValueError("ProductRunLaunchAcceptedResponse.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunLaunchAcceptedResponse.workspace_id must be non-empty")
        if not self.initial_run_status:
            raise ValueError("ProductRunLaunchAcceptedResponse.initial_run_status must be non-empty")


@dataclass(frozen=True)
class ProductRunLaunchRejectedResponse:
    status: ProductLaunchStatus
    failure_family: ProductFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    blocking_findings: list[dict[str, Any]] = field(default_factory=list)
    engine_error_code: Optional[str] = None
    engine_message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status != "rejected":
            raise ValueError("ProductRunLaunchRejectedResponse.status must be 'rejected'")
        if self.failure_family not in _ALLOWED_PRODUCT_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductRunLaunchRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductRunLaunchRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductRunLaunchRejectedResponse.message must be non-empty")


@dataclass(frozen=True)
class RunAdmissionOutcome:
    accepted_response: Optional[ProductRunLaunchAcceptedResponse] = None
    rejected_response: Optional[ProductRunLaunchRejectedResponse] = None
    engine_request: Any = None
    engine_response: Any = None
    run_record: Optional[RunRecordProjection] = None
    resolved_target: Optional[ResolvedExecutionTarget] = None

    @property
    def accepted(self) -> bool:
        return self.accepted_response is not None
