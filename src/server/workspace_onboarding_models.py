from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

WorkspaceReadFailureFamily = Literal["product_read_failure", "workspace_not_found"]
WorkspaceWriteFailureFamily = Literal["product_write_failure"]
OnboardingFailureFamily = Literal["product_read_failure", "product_write_failure"]

_ALLOWED_WORKSPACE_READ_FAILURE_FAMILIES = {"product_read_failure", "workspace_not_found"}
_ALLOWED_WORKSPACE_WRITE_FAILURE_FAMILIES = {"product_write_failure"}
_ALLOWED_ONBOARDING_FAILURE_FAMILIES = {"product_read_failure", "product_write_failure"}
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


@dataclass(frozen=True)
class ProductWorkspaceDetailResponse:
    workspace_id: str
    title: str
    role: str
    owner_user_id: Optional[str]
    updated_at: str
    created_at: Optional[str] = None
    description: Optional[str] = None
    collaborator_count: int = 0
    last_run_id: Optional[str] = None
    last_result_status: Optional[str] = None
    continuity_source: Optional[str] = None
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
            raise ValueError('ProductWorkspaceDetailResponse.workspace_id must be non-empty')
        if not self.title:
            raise ValueError('ProductWorkspaceDetailResponse.title must be non-empty')
        if self.role not in _ALLOWED_WORKSPACE_ROLES:
            raise ValueError(f'Unsupported ProductWorkspaceDetailResponse.role: {self.role}')
        if self.collaborator_count < 0:
            raise ValueError('ProductWorkspaceDetailResponse.collaborator_count must be >= 0')
        if not self.updated_at:
            raise ValueError('ProductWorkspaceDetailResponse.updated_at must be non-empty')


@dataclass(frozen=True)
class ProductWorkspaceListResponse:
    returned_count: int
    workspaces: tuple[ProductWorkspaceSummaryView, ...] = ()
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.returned_count < 0:
            raise ValueError('ProductWorkspaceListResponse.returned_count must be >= 0')


@dataclass(frozen=True)
class ProductWorkspaceCreateRequest:
    title: str
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError('ProductWorkspaceCreateRequest.title must be non-empty')


@dataclass(frozen=True)
class ProductWorkspaceWriteAcceptedResponse:
    status: str
    workspace: ProductWorkspaceDetailResponse
    owner_membership_id: str
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError('ProductWorkspaceWriteAcceptedResponse.status must be non-empty')
        if not self.owner_membership_id:
            raise ValueError('ProductWorkspaceWriteAcceptedResponse.owner_membership_id must be non-empty')


@dataclass(frozen=True)
class ProductWorkspaceReadRejectedResponse:
    failure_family: WorkspaceReadFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_WORKSPACE_READ_FAILURE_FAMILIES:
            raise ValueError(f'Unsupported ProductWorkspaceReadRejectedResponse.failure_family: {self.failure_family}')
        if not self.reason_code:
            raise ValueError('ProductWorkspaceReadRejectedResponse.reason_code must be non-empty')
        if not self.message:
            raise ValueError('ProductWorkspaceReadRejectedResponse.message must be non-empty')


@dataclass(frozen=True)
class ProductWorkspaceWriteRejectedResponse:
    failure_family: WorkspaceWriteFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_WORKSPACE_WRITE_FAILURE_FAMILIES:
            raise ValueError(f'Unsupported ProductWorkspaceWriteRejectedResponse.failure_family: {self.failure_family}')
        if not self.reason_code:
            raise ValueError('ProductWorkspaceWriteRejectedResponse.reason_code must be non-empty')
        if not self.message:
            raise ValueError('ProductWorkspaceWriteRejectedResponse.message must be non-empty')


@dataclass(frozen=True)
class WorkspaceListOutcome:
    response: Optional[ProductWorkspaceListResponse] = None
    rejected: Optional[ProductWorkspaceReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class WorkspaceReadOutcome:
    response: Optional[ProductWorkspaceDetailResponse] = None
    rejected: Optional[ProductWorkspaceReadRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class WorkspaceWriteOutcome:
    accepted: Optional[ProductWorkspaceWriteAcceptedResponse] = None
    rejected: Optional[ProductWorkspaceWriteRejectedResponse] = None
    created_workspace_row: Optional[dict[str, Any]] = None
    created_membership_row: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.accepted is not None


@dataclass(frozen=True)
class ProductOnboardingStateView:
    onboarding_state_id: Optional[str]
    user_id: str
    workspace_id: Optional[str]
    first_success_achieved: bool = False
    advanced_surfaces_unlocked: bool = False
    dismissed_guidance_state: dict[str, Any] = field(default_factory=dict)
    current_step: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError('ProductOnboardingStateView.user_id must be non-empty')
        if not isinstance(self.dismissed_guidance_state, dict):
            raise TypeError('ProductOnboardingStateView.dismissed_guidance_state must be a dict')


@dataclass(frozen=True)
class ProductOnboardingLinks:
    self_ref: str
    workspace: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.self_ref:
            raise ValueError('ProductOnboardingLinks.self_ref must be non-empty')


@dataclass(frozen=True)
class ProductOnboardingReadResponse:
    continuity_scope: str
    state: ProductOnboardingStateView
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    links: ProductOnboardingLinks = field(default_factory=lambda: ProductOnboardingLinks('/placeholder/onboarding'))
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.continuity_scope not in {'user', 'workspace'}:
            raise ValueError(f'Unsupported ProductOnboardingReadResponse.continuity_scope: {self.continuity_scope}')


@dataclass(frozen=True)
class ProductOnboardingWriteRequest:
    workspace_id: Optional[str] = None
    first_success_achieved: Optional[bool] = None
    advanced_surfaces_unlocked: Optional[bool] = None
    dismissed_guidance_state: Optional[dict[str, Any]] = None
    current_step: Optional[str] = None

    def __post_init__(self) -> None:
        if self.dismissed_guidance_state is not None and not isinstance(self.dismissed_guidance_state, dict):
            raise TypeError('ProductOnboardingWriteRequest.dismissed_guidance_state must be a dict when provided')
        if all(
            value is None
            for value in (
                self.first_success_achieved,
                self.advanced_surfaces_unlocked,
                self.dismissed_guidance_state,
                self.current_step,
            )
        ):
            raise ValueError('ProductOnboardingWriteRequest must set at least one continuity field')


@dataclass(frozen=True)
class ProductOnboardingWriteAcceptedResponse:
    status: str
    continuity_scope: str
    state: ProductOnboardingStateView
    provider_continuity: Optional[ProductProviderContinuitySummary] = None
    activity_continuity: Optional[ProductActivityContinuitySummary] = None
    links: ProductOnboardingLinks = field(default_factory=lambda: ProductOnboardingLinks('/placeholder/onboarding'))
    was_created: bool = False
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError('ProductOnboardingWriteAcceptedResponse.status must be non-empty')
        if self.continuity_scope not in {'user', 'workspace'}:
            raise ValueError(f'Unsupported ProductOnboardingWriteAcceptedResponse.continuity_scope: {self.continuity_scope}')


@dataclass(frozen=True)
class ProductOnboardingRejectedResponse:
    failure_family: OnboardingFailureFamily
    reason_code: str
    message: str
    workspace_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.failure_family not in _ALLOWED_ONBOARDING_FAILURE_FAMILIES:
            raise ValueError(f'Unsupported ProductOnboardingRejectedResponse.failure_family: {self.failure_family}')
        if not self.reason_code:
            raise ValueError('ProductOnboardingRejectedResponse.reason_code must be non-empty')
        if not self.message:
            raise ValueError('ProductOnboardingRejectedResponse.message must be non-empty')


@dataclass(frozen=True)
class OnboardingReadOutcome:
    response: Optional[ProductOnboardingReadResponse] = None
    rejected: Optional[ProductOnboardingRejectedResponse] = None

    @property
    def ok(self) -> bool:
        return self.response is not None


@dataclass(frozen=True)
class OnboardingWriteOutcome:
    accepted: Optional[ProductOnboardingWriteAcceptedResponse] = None
    rejected: Optional[ProductOnboardingRejectedResponse] = None
    persisted_onboarding_row: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.accepted is not None
