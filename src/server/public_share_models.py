from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ProductPublicShareLifecycleView:
    stored_state: str
    state: str
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    issued_by_user_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.stored_state:
            raise ValueError("ProductPublicShareLifecycleView.stored_state must be non-empty")
        if not self.state:
            raise ValueError("ProductPublicShareLifecycleView.state must be non-empty")
        if not self.created_at:
            raise ValueError("ProductPublicShareLifecycleView.created_at must be non-empty")
        if not self.updated_at:
            raise ValueError("ProductPublicShareLifecycleView.updated_at must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareManagementView:
    archived: bool = False
    archived_at: Optional[str] = None


@dataclass(frozen=True)
class ProductPublicShareAuditSummaryView:
    event_count: int
    last_event_type: Optional[str] = None
    last_event_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.event_count < 0:
            raise ValueError("ProductPublicShareAuditSummaryView.event_count must be >= 0")


@dataclass(frozen=True)
class ProductPublicShareSourceArtifactView:
    storage_role: str
    canonical_ref: str
    artifact_format_family: str
    source_working_save_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.storage_role:
            raise ValueError("ProductPublicShareSourceArtifactView.storage_role must be non-empty")
        if not self.canonical_ref:
            raise ValueError("ProductPublicShareSourceArtifactView.canonical_ref must be non-empty")
        if not self.artifact_format_family:
            raise ValueError("ProductPublicShareSourceArtifactView.artifact_format_family must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareLinks:
    values: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, value in self.values.items():
            if not key:
                raise ValueError("ProductPublicShareLinks keys must be non-empty")
            if not value:
                raise ValueError("ProductPublicShareLinks values must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareCapabilitySummaryView:
    can_download_artifact: bool = False
    can_import_copy: bool = False
    can_run_artifact: bool = False
    can_checkout_working_copy: bool = False
    can_create_workspace_from_share: bool = False
    create_workspace_supported_modes: tuple[str, ...] = ()
    preferred_create_workspace_mode: Optional[str] = None


@dataclass(frozen=True)
class ProductPublicShareActionAvailabilityView:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, value in self.values.items():
            if not key:
                raise ValueError("ProductPublicShareActionAvailabilityView keys must be non-empty")
            if not isinstance(value, dict):
                raise ValueError("ProductPublicShareActionAvailabilityView values must be dict objects")


@dataclass(frozen=True)
class ProductPublicShareDetailResponse:
    status: str
    share_id: str
    share_path: str
    transport: str
    access_mode: str
    lifecycle: ProductPublicShareLifecycleView
    management: ProductPublicShareManagementView
    audit_summary: ProductPublicShareAuditSummaryView
    source_artifact: ProductPublicShareSourceArtifactView
    share_boundary: dict[str, Any]
    artifact_boundary: dict[str, Any]
    links: ProductPublicShareLinks
    capability_summary: ProductPublicShareCapabilitySummaryView = field(default_factory=ProductPublicShareCapabilitySummaryView)
    action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    title: Optional[str] = None
    summary: Optional[str] = None
    viewer_capabilities: tuple[str, ...] = ()
    operation_capabilities: tuple[str, ...] = ()
    identity: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareDetailResponse.status must be non-empty")
        if not self.share_id:
            raise ValueError("ProductPublicShareDetailResponse.share_id must be non-empty")
        if not self.share_path:
            raise ValueError("ProductPublicShareDetailResponse.share_path must be non-empty")
        if not self.transport:
            raise ValueError("ProductPublicShareDetailResponse.transport must be non-empty")
        if not self.access_mode:
            raise ValueError("ProductPublicShareDetailResponse.access_mode must be non-empty")


@dataclass(frozen=True)
class ProductWorkspaceShellShareCreatedResponse(ProductPublicShareDetailResponse):
    workspace_id: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.workspace_id:
            raise ValueError("ProductWorkspaceShellShareCreatedResponse.workspace_id must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareHistoryEntryView:
    event_id: str
    event_type: str
    timestamp: str
    actor_identity: Optional[str] = None
    stored_lifecycle_state: Optional[str] = None
    effective_lifecycle_state: Optional[str] = None
    detail_payload: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("ProductPublicShareHistoryEntryView.event_id must be non-empty")
        if not self.event_type:
            raise ValueError("ProductPublicShareHistoryEntryView.event_type must be non-empty")
        if not self.timestamp:
            raise ValueError("ProductPublicShareHistoryEntryView.timestamp must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareHistoryResponse:
    status: str
    share_id: str
    share_path: str
    audit_summary: ProductPublicShareAuditSummaryView
    share_boundary: dict[str, Any]
    artifact_boundary: dict[str, Any]
    history: tuple[ProductPublicShareHistoryEntryView, ...] = ()
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareHistoryResponse.status must be non-empty")
        if not self.share_id:
            raise ValueError("ProductPublicShareHistoryResponse.share_id must be non-empty")
        if not self.share_path:
            raise ValueError("ProductPublicShareHistoryResponse.share_path must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareArtifactResponse:
    status: str
    share_id: str
    share_title: Optional[str]
    share_boundary: dict[str, Any]
    artifact_boundary: dict[str, Any]
    artifact: dict[str, Any]
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareArtifactResponse.status must be non-empty")
        if not self.share_id:
            raise ValueError("ProductPublicShareArtifactResponse.share_id must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareMutationResponse(ProductPublicShareDetailResponse):
    action_report: Optional[dict[str, Any]] = None
    governance_summary: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class ProductPublicShareCatalogEntryView:
    share_id: str
    share_path: str
    storage_role: str
    lifecycle_state: str
    title: Optional[str] = None
    summary: Optional[str] = None
    stored_lifecycle_state: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    issued_by_user_ref: Optional[str] = None
    operation_capabilities: tuple[str, ...] = ()
    capability_summary: ProductPublicShareCapabilitySummaryView = field(default_factory=ProductPublicShareCapabilitySummaryView)
    action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    identity: Optional[dict[str, Any]] = None
    is_saved: bool = False
    saved_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.share_id:
            raise ValueError("ProductPublicShareCatalogEntryView.share_id must be non-empty")
        if not self.share_path:
            raise ValueError("ProductPublicShareCatalogEntryView.share_path must be non-empty")
        if not self.storage_role:
            raise ValueError("ProductPublicShareCatalogEntryView.storage_role must be non-empty")
        if not self.lifecycle_state:
            raise ValueError("ProductPublicShareCatalogEntryView.lifecycle_state must be non-empty")


@dataclass(frozen=True)
class ProductRelatedPublicShareEntryView(ProductPublicShareCatalogEntryView):
    match_score: int = 0
    same_issuer: bool = False
    same_storage_role: bool = False
    shared_operations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.match_score < 0:
            raise ValueError("ProductRelatedPublicShareEntryView.match_score must be >= 0")


@dataclass(frozen=True)
class ProductPublicShareCatalogSummaryView:
    filtered_share_count: int
    inventory_share_count: int
    working_save_share_count: int
    commit_snapshot_share_count: int
    checkoutable_share_count: int
    importable_share_count: int
    runnable_share_count: int
    downloadable_share_count: int
    saved_share_count: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "filtered_share_count",
            "inventory_share_count",
            "working_save_share_count",
            "commit_snapshot_share_count",
            "checkoutable_share_count",
            "importable_share_count",
            "runnable_share_count",
            "downloadable_share_count",
            "saved_share_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductPublicShareCatalogSummaryView.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductSavedPublicShareCollectionSummaryView:
    total_saved_count: int
    active_share_count: int
    working_save_share_count: int
    commit_snapshot_share_count: int
    latest_saved_at: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in (
            "total_saved_count",
            "active_share_count",
            "working_save_share_count",
            "commit_snapshot_share_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductSavedPublicShareCollectionSummaryView.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductRelatedPublicShareSummaryView:
    total_related_count: int
    same_issuer_count: int
    same_storage_role_count: int
    shared_operation_match_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "total_related_count",
            "same_issuer_count",
            "same_storage_role_count",
            "shared_operation_match_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductRelatedPublicShareSummaryView.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductPublicShareCompareSummaryView:
    workspace_found: bool
    share_artifact_summary: dict[str, Any]
    workspace_id: Optional[str] = None
    workspace_artifact_summary: Optional[dict[str, Any]] = None
    share_storage_role: Optional[str] = None
    workspace_storage_role: Optional[str] = None
    storage_role_match: bool = False
    canonical_ref_match: bool = False
    artifact_digest_match: bool = False


@dataclass(frozen=True)
class ProductPublicShareCatalogResponse:
    status: str
    returned_count: int
    summary: ProductPublicShareCatalogSummaryView
    inventory_summary: ProductPublicShareCatalogSummaryView
    shares: tuple[ProductPublicShareCatalogEntryView, ...] = ()
    applied_filters: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareCatalogResponse.status must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductPublicShareCatalogResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductPublicShareCatalogSummaryResponse:
    status: str
    summary: ProductPublicShareCatalogSummaryView
    inventory_summary: ProductPublicShareCatalogSummaryView
    applied_filters: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareCatalogSummaryResponse.status must be non-empty")


@dataclass(frozen=True)
class ProductSavedPublicShareCollectionResponse:
    status: str
    saved_by_user_ref: str
    returned_count: int
    summary: ProductSavedPublicShareCollectionSummaryView
    shares: tuple[ProductPublicShareCatalogEntryView, ...] = ()
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductSavedPublicShareCollectionResponse.status must be non-empty")
        if not self.saved_by_user_ref:
            raise ValueError("ProductSavedPublicShareCollectionResponse.saved_by_user_ref must be non-empty")
        if self.returned_count < 0:
            raise ValueError("ProductSavedPublicShareCollectionResponse.returned_count must be >= 0")


@dataclass(frozen=True)
class ProductRelatedPublicShareResponse:
    status: str
    share_id: str
    related_summary: ProductRelatedPublicShareSummaryView
    shares: tuple[ProductRelatedPublicShareEntryView, ...] = ()
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductRelatedPublicShareResponse.status must be non-empty")
        if not self.share_id:
            raise ValueError("ProductRelatedPublicShareResponse.share_id must be non-empty")


@dataclass(frozen=True)
class ProductPublicShareCompareSummaryResponse:
    status: str
    share_id: str
    compare: ProductPublicShareCompareSummaryView
    capability_summary: ProductPublicShareCapabilitySummaryView = field(default_factory=ProductPublicShareCapabilitySummaryView)
    action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity: Optional[dict[str, Any]] = None
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductPublicShareCompareSummaryResponse.status must be non-empty")
        if not self.share_id:
            raise ValueError("ProductPublicShareCompareSummaryResponse.share_id must be non-empty")




@dataclass(frozen=True)
class ProductIssuerPublicShareManagementCapabilityView:
    can_revoke: bool = False
    can_extend_expiration: bool = False
    can_archive: bool = False
    can_unarchive: bool = False
    can_delete: bool = True


@dataclass(frozen=True)
class ProductIssuerPublicShareManagementCapabilitySummaryView:
    total_share_count: int
    revokable_share_count: int
    extendable_share_count: int
    archivable_share_count: int
    unarchivable_share_count: int
    deletable_share_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "total_share_count",
            "revokable_share_count",
            "extendable_share_count",
            "archivable_share_count",
            "unarchivable_share_count",
            "deletable_share_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"ProductIssuerPublicShareManagementCapabilitySummaryView.{field_name} must be >= 0")


@dataclass(frozen=True)
class ProductIssuerPublicShareManagementEntryView:
    share_id: str
    share_path: str
    storage_role: str
    canonical_ref: str
    lifecycle: ProductPublicShareLifecycleView
    management: ProductPublicShareManagementView
    audit_summary: ProductPublicShareAuditSummaryView
    title: Optional[str] = None
    summary: Optional[str] = None
    operation_capabilities: tuple[str, ...] = ()
    management_capability_summary: ProductIssuerPublicShareManagementCapabilityView = field(default_factory=ProductIssuerPublicShareManagementCapabilityView)
    management_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    identity: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.share_id:
            raise ValueError("ProductIssuerPublicShareManagementEntryView.share_id must be non-empty")
        if not self.share_path:
            raise ValueError("ProductIssuerPublicShareManagementEntryView.share_path must be non-empty")
        if not self.storage_role:
            raise ValueError("ProductIssuerPublicShareManagementEntryView.storage_role must be non-empty")
        if not self.canonical_ref:
            raise ValueError("ProductIssuerPublicShareManagementEntryView.canonical_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareSummaryView:
    issuer_user_ref: str
    total_share_count: int
    active_share_count: int
    expired_share_count: int
    revoked_share_count: int
    archived_share_count: int
    working_save_share_count: int
    commit_snapshot_share_count: int
    runnable_share_count: int
    checkoutable_share_count: int
    latest_created_at: Optional[str] = None
    latest_updated_at: Optional[str] = None
    latest_audit_event_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareSummaryView.issuer_user_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareGovernanceSummaryView(ProductIssuerPublicShareSummaryView):
    total_action_report_count: int = 0
    revoke_action_report_count: int = 0
    extend_action_report_count: int = 0
    archive_action_report_count: int = 0
    delete_action_report_count: int = 0
    latest_action_report_at: Optional[str] = None
    recent_action_reports: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ProductIssuerPublicShareListResponse:
    status: str
    issuer_user_ref: str
    summary: ProductIssuerPublicShareSummaryView
    inventory_summary: ProductIssuerPublicShareSummaryView
    governance_summary: ProductIssuerPublicShareGovernanceSummaryView
    management_capability_summary: ProductIssuerPublicShareManagementCapabilitySummaryView
    bulk_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    shares: tuple[ProductIssuerPublicShareManagementEntryView, ...] = ()
    applied_filters: dict[str, Any] = field(default_factory=dict)
    pagination: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductIssuerPublicShareListResponse.status must be non-empty")
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareListResponse.issuer_user_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareSummaryResponse:
    status: str
    issuer_user_ref: str
    summary: ProductIssuerPublicShareSummaryView
    inventory_summary: ProductIssuerPublicShareSummaryView
    governance_summary: ProductIssuerPublicShareGovernanceSummaryView
    management_capability_summary: ProductIssuerPublicShareManagementCapabilitySummaryView
    bulk_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    applied_filters: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductIssuerPublicShareSummaryResponse.status must be non-empty")
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareSummaryResponse.issuer_user_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareActionReportListResponse:
    status: str
    issuer_user_ref: str
    summary: dict[str, Any]
    inventory_summary: dict[str, Any]
    governance_summary: ProductIssuerPublicShareGovernanceSummaryView
    management_capability_summary: ProductIssuerPublicShareManagementCapabilitySummaryView
    bulk_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    reports: tuple[dict[str, Any], ...] = ()
    applied_filters: dict[str, Any] = field(default_factory=dict)
    pagination: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductIssuerPublicShareActionReportListResponse.status must be non-empty")
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareActionReportListResponse.issuer_user_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareActionReportSummaryResponse:
    status: str
    issuer_user_ref: str
    summary: dict[str, Any]
    inventory_summary: dict[str, Any]
    governance_summary: ProductIssuerPublicShareGovernanceSummaryView
    management_capability_summary: ProductIssuerPublicShareManagementCapabilitySummaryView
    bulk_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    applied_filters: dict[str, Any] = field(default_factory=dict)
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductIssuerPublicShareActionReportSummaryResponse.status must be non-empty")
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareActionReportSummaryResponse.issuer_user_ref must be non-empty")


@dataclass(frozen=True)
class ProductIssuerPublicShareBulkMutationResponse:
    status: str
    issuer_user_ref: str
    action: str
    summary: ProductIssuerPublicShareSummaryView
    governance_summary: ProductIssuerPublicShareGovernanceSummaryView
    management_capability_summary: ProductIssuerPublicShareManagementCapabilitySummaryView
    bulk_action_availability: ProductPublicShareActionAvailabilityView = field(default_factory=ProductPublicShareActionAvailabilityView)
    shares: tuple[ProductIssuerPublicShareManagementEntryView, ...] = ()
    action_report: Optional[dict[str, Any]] = None
    requested_share_ids: tuple[str, ...] = ()
    affected_share_count: int = 0
    expires_at: Optional[str] = None
    links: ProductPublicShareLinks = field(default_factory=ProductPublicShareLinks)
    identity_policy: Optional[dict[str, Any]] = None
    namespace_policy: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.status:
            raise ValueError("ProductIssuerPublicShareBulkMutationResponse.status must be non-empty")
        if not self.issuer_user_ref:
            raise ValueError("ProductIssuerPublicShareBulkMutationResponse.issuer_user_ref must be non-empty")
        if not self.action:
            raise ValueError("ProductIssuerPublicShareBulkMutationResponse.action must be non-empty")

