from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal

from src.server.run_read_models import ProductExecutionTargetView, ProductResultSummaryView, ProductRunControlActionsView, ProductRunRecoveryView
from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary

RunListReadFailureFamily = Literal["product_read_failure", "workspace_not_found", "invalid_cursor"]
_ALLOWED_FAILURE_FAMILIES = {"product_read_failure", "workspace_not_found", "invalid_cursor"}
_ALLOWED_STATUS_FAMILIES = {
    "pending",
    "active",
    "terminal_success",
    "terminal_failure",
    "terminal_partial",
    "unknown",
}


@dataclass(frozen=True)
class ProductRunListLinks:
    status: str
    result: str
    trace: str
    artifacts: str

    def __post_init__(self) -> None:
        for field_name in ("status", "result", "trace", "artifacts"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductRunListLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProductRunListItemView:
    run_id: str
    workspace_id: str
    execution_target: ProductExecutionTargetView
    status: str
    status_family: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    requested_by_user_id: Optional[str] = None
    result_state: Optional[str] = None
    latest_error_family: Optional[str] = None
    trace_available: bool = False
    artifact_count: int = 0
    result_summary: Optional[ProductResultSummaryView] = None
    recovery: Optional[ProductRunRecoveryView] = None
    actions: Optional[ProductRunControlActionsView] = None
    links: ProductRunListLinks = field(default_factory=lambda: ProductRunListLinks(
        status="/placeholder/status",
        result="/placeholder/result",
        trace="/placeholder/trace",
        artifacts="/placeholder/artifacts",
    ))

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("ProductRunListItemView.run_id must be non-empty")
        if not self.workspace_id:
            raise ValueError("ProductRunListItemView.workspace_id must be non-empty")
        if not self.status:
            raise ValueError("ProductRunListItemView.status must be non-empty")
        if self.status_family not in _ALLOWED_STATUS_FAMILIES:
            raise ValueError(f"Unsupported ProductRunListItemView.status_family: {self.status_family}")
        if not self.created_at:
            raise ValueError("ProductRunListItemView.created_at must be non-empty")
        if not self.updated_at:
            raise ValueError("ProductRunListItemView.updated_at must be non-empty")
        if self.artifact_count < 0:
            raise ValueError("ProductRunListItemView.artifact_count must be >= 0")


@dataclass(frozen=True)
class ProductRunListAppliedFilters:
    status_family: Optional[str] = None
    requested_by_user_id: Optional[str] = None
    limit: int = 20
    cursor: Optional[str] = None

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("ProductRunListAppliedFilters.limit must be > 0")


@dataclass(frozen=True)
class ProductWorkspaceRunListResponse:
    workspace_id: str
    returned_count: int
    total_visible_count: int
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    runs: tuple[ProductRunListItemView, ...] = ()
    next_cursor: Optional[str] = None
    applied_filters: ProductRunListAppliedFilters = field(default_factory=ProductRunListAppliedFilters)
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceRunListResponse.workspace_id must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductWorkspaceRunListResponse.returned_count must be >= 0")
        if self.total_visible_count < 0:
            raise ValueError("ProductWorkspaceRunListResponse.total_visible_count must be >= 0")


@dataclass(frozen=True)
class ProductRunListRejectedResponse:
    failure_family: RunListReadFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None

    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_FAILURE_FAMILIES:
            raise ValueError(f"Unsupported ProductRunListRejectedResponse.failure_family: {self.failure_family}")
        if not self.reason_code:
            raise ValueError("ProductRunListRejectedResponse.reason_code must be non-empty")
        if not self.message:
            raise ValueError("ProductRunListRejectedResponse.message must be non-empty")

@dataclass(frozen=True)
class RunListReadOutcome:
    response: Optional[ProductWorkspaceRunListResponse] = None
    rejected: Optional[ProductRunListRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
