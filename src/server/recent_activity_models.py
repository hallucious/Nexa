from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from src.server.workspace_onboarding_models import ProductActivityContinuitySummary, ProductProviderContinuitySummary
from src.server.run_read_models import ProductSourceArtifactView

RecentActivityFailureFamily = Literal["product_read_failure"]
_ALLOWED_RECENT_ACTIVITY_FAILURE_FAMILIES = {"product_read_failure"}
_ALLOWED_ACTIVITY_TYPES = {
    "workspace_created",
    "workspace_updated",
    "onboarding_updated",
    "run_queued",
    "run_running",
    "run_completed",
    "run_failed",
    "run_updated",
    "provider_probe_reachable",
    "provider_probe_warning",
    "provider_probe_failed",
    "provider_binding_updated",
    "managed_secret_updated",
}
_ALLOWED_HISTORY_SUMMARY_SCOPES = {"account", "workspace"}


@dataclass(frozen=True)
class ProductRecentActivityLinks:
    workspace: Optional[str] = None
    onboarding: Optional[str] = None
    run_status: Optional[str] = None
    run_result: Optional[str] = None
    provider_binding: Optional[str] = None
    provider_health: Optional[str] = None
    provider_probe_history: Optional[str] = None
    managed_secret: Optional[str] = None


@dataclass(frozen=True)
class ProductRecentActivityItemView:
    activity_id: str
    activity_type: str
    occurred_at: str
    workspace_id: str
    workspace_title: str
    run_id: Optional[str] = None
    source_artifact: Optional[ProductSourceArtifactView] = None
    status: Optional[str] = None
    status_family: Optional[str] = None
    summary: Optional[str] = None
    actor_user_id: Optional[str] = None
    recovery_state: Optional[str] = None
    latest_error_family: Optional[str] = None
    orphan_review_required: bool = False
    worker_attempt_number: int = 0
    links: ProductRecentActivityLinks = field(default_factory=ProductRecentActivityLinks)

    def __post_init__(self) -> None:
        if not self.activity_id:
            raise ValueError('ProductRecentActivityItemView.activity_id must be non-empty')
        if self.activity_type not in _ALLOWED_ACTIVITY_TYPES:
            raise ValueError(f'Unsupported ProductRecentActivityItemView.activity_type: {self.activity_type}')
        if not self.occurred_at:
            raise ValueError('ProductRecentActivityItemView.occurred_at must be non-empty')
        if not self.workspace_id:
            raise ValueError('ProductRecentActivityItemView.workspace_id must be non-empty')
        if not self.workspace_title:
            raise ValueError('ProductRecentActivityItemView.workspace_title must be non-empty')
        if self.worker_attempt_number < 0:
            raise ValueError('ProductRecentActivityItemView.worker_attempt_number must be >= 0')


@dataclass(frozen=True)
class ProductRecentActivityAppliedFilters:
    workspace_id: Optional[str] = None
    cursor: Optional[str] = None
    limit: int = 20

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError('ProductRecentActivityAppliedFilters.limit must be > 0')


@dataclass(frozen=True)
class ProductRecentActivityResponse:
    returned_count: int
    total_visible_count: int
    activities: tuple[ProductRecentActivityItemView, ...] = ()
    applied_filters: ProductRecentActivityAppliedFilters = field(default_factory=ProductRecentActivityAppliedFilters)
    next_cursor: Optional[str] = None
    latest_activity_at: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.returned_count < 0:
            raise ValueError('ProductRecentActivityResponse.returned_count must be >= 0')
        if self.total_visible_count < 0:
            raise ValueError('ProductRecentActivityResponse.total_visible_count must be >= 0')


@dataclass(frozen=True)
class ProductHistorySummaryResponse:
    scope: str
    workspace_id: Optional[str] = None
    visible_workspace_count: int = 0
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    total_visible_runs: int = 0
    pending_runs: int = 0
    active_runs: int = 0
    terminal_success_runs: int = 0
    terminal_failure_runs: int = 0
    recent_workspace_count: int = 0
    recent_share_history_count: int = 0
    recent_probe_count: int = 0
    failed_probe_count: int = 0
    recent_provider_binding_count: int = 0
    recent_managed_secret_count: int = 0
    recent_onboarding_count: int = 0
    latest_activity_at: Optional[str] = None
    latest_workspace_id: Optional[str] = None
    latest_share_id: Optional[str] = None
    latest_run_id: Optional[str] = None
    latest_probe_event_id: Optional[str] = None
    latest_provider_binding_id: Optional[str] = None
    latest_managed_secret_ref: Optional[str] = None
    latest_onboarding_state_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.scope not in _ALLOWED_HISTORY_SUMMARY_SCOPES:
            raise ValueError(f'Unsupported ProductHistorySummaryResponse.scope: {self.scope}')
        for field_name in (
            'visible_workspace_count',
            'total_visible_runs',
            'pending_runs',
            'active_runs',
            'terminal_success_runs',
            'terminal_failure_runs',
            'recent_workspace_count',
            'recent_share_history_count',
            'recent_probe_count',
            'failed_probe_count',
            'recent_provider_binding_count',
            'recent_managed_secret_count',
            'recent_onboarding_count',
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f'ProductHistorySummaryResponse.{field_name} must be >= 0')


@dataclass(frozen=True)
class ProductRecentActivityRejectedResponse:
    failure_family: RecentActivityFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None
    workspace_title: Optional[str] = None
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_RECENT_ACTIVITY_FAILURE_FAMILIES:
            raise ValueError(f'Unsupported ProductRecentActivityRejectedResponse.failure_family: {self.failure_family}')
        if not self.reason_code:
            raise ValueError('ProductRecentActivityRejectedResponse.reason_code must be non-empty')
        if not self.message:
            raise ValueError('ProductRecentActivityRejectedResponse.message must be non-empty')


@dataclass(frozen=True)
class RecentActivityReadOutcome:
    response: Optional[ProductRecentActivityResponse] = None
    rejected: Optional[ProductRecentActivityRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class HistorySummaryReadOutcome:
    response: Optional[ProductHistorySummaryResponse] = None
    rejected: Optional[ProductRecentActivityRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None
