from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

_ALLOWED_WORKSPACE_ROLES = {"owner", "admin", "editor", "collaborator", "reviewer", "viewer"}


@dataclass(frozen=True)
class ProductWorkspaceLinks:
    detail: str
    runs: str
    onboarding: str

    def __post_init__(self) -> None:
        for field_name in ("detail", "runs", "onboarding"):
            if not getattr(self, field_name):
                raise ValueError(f"ProductWorkspaceLinks.{field_name} must be non-empty")


@dataclass(frozen=True)
class ProductProviderContinuitySummary:
    provider_binding_count: int = 0
    managed_secret_count: int = 0
    recent_probe_count: int = 0
    latest_provider_binding_id: Optional[str] = None
    latest_managed_secret_ref: Optional[str] = None
    latest_probe_event_id: Optional[str] = None
    latest_provider_activity_at: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in ("provider_binding_count", "managed_secret_count", "recent_probe_count"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductProviderContinuitySummary.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductActivityContinuitySummary:
    recent_run_count: int = 0
    pending_run_count: int = 0
    active_run_count: int = 0
    terminal_failure_run_count: int = 0
    recent_probe_count: int = 0
    failed_probe_count: int = 0
    recent_provider_binding_count: int = 0
    recent_managed_secret_count: int = 0
    recent_onboarding_count: int = 0
    latest_activity_at: Optional[str] = None
    latest_run_id: Optional[str] = None
    latest_probe_event_id: Optional[str] = None
    latest_provider_binding_id: Optional[str] = None
    latest_managed_secret_ref: Optional[str] = None
    latest_onboarding_state_id: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in (
            "recent_run_count",
            "pending_run_count",
            "active_run_count",
            "terminal_failure_run_count",
            "recent_probe_count",
            "failed_probe_count",
            "recent_provider_binding_count",
            "recent_managed_secret_count",
            "recent_onboarding_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductActivityContinuitySummary.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductWorkspaceSummaryView:
    workspace_id: str
    title: str
    role: str
    updated_at: str
    created_at: Optional[str] = None
    last_run_id: Optional[str] = None
    last_result_status: Optional[str] = None
    recovery_state: Optional[str] = None
    latest_error_family: Optional[str] = None
    orphan_review_required: bool = False
    worker_attempt_number: int = 0
    archived: bool = False
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    links: ProductWorkspaceLinks = field(default_factory=lambda: ProductWorkspaceLinks(
        detail='/placeholder/workspace',
        runs='/placeholder/runs',
        onboarding='/placeholder/onboarding',
    ))

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError('ProductWorkspaceSummaryView.workspace_id must be non-empty')
        if not self.title:
            raise ValueError('ProductWorkspaceSummaryView.title must be non-empty')
        if self.role not in _ALLOWED_WORKSPACE_ROLES:
            raise ValueError(f'Unsupported ProductWorkspaceSummaryView.role: {self.role}')
        if not self.updated_at:
            raise ValueError('ProductWorkspaceSummaryView.updated_at must be non-empty')
        if self.worker_attempt_number < 0:
            raise ValueError('ProductWorkspaceSummaryView.worker_attempt_number must be >= 0')


@dataclass(frozen=True)
class ProductWorkspaceListResponse:
    returned_count: int
    workspaces: tuple[ProductWorkspaceSummaryView, ...] = ()
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.returned_count < 0:
            raise ValueError('ProductWorkspaceListResponse.returned_count must be >= 0')


__all__ = [
    "ProductWorkspaceLinks",
    "ProductProviderContinuitySummary",
    "ProductActivityContinuitySummary",
    "ProductWorkspaceSummaryView",
    "ProductWorkspaceListResponse",
]
