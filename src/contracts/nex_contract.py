from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ShareLifecycleState = Literal["active", "expired", "revoked"]
ShareAuditEventType = Literal["created", "expiration_extended", "revoked", "archived", "unarchived"]

StorageRole = Literal["working_save", "commit_snapshot"]
FindingCategory = Literal[
    "parse",
    "top_level_shape",
    "storage_role",
    "shared_schema",
    "role_schema",
    "structural",
    "resource_resolution",
    "state_shape",
    "runtime_section",
    "approval_section",
    "lineage_section",
    "semantic",
]
FindingSeverity = Literal["low", "medium", "high"]
ValidationResult = Literal["passed", "passed_with_findings", "failed"]
LoadStatus = Literal["loaded", "loaded_with_findings", "rejected"]
ShareTransport = Literal["link"]
ShareAccessMode = Literal["public_readonly"]
ShareOperation = Literal["inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy", "extend_expiration"]
IssuerShareManagementAction = Literal["revoke", "extend_expiration", "delete", "archive"]
ManagementActionScope = Literal["issuer_bulk", "single_share"]

WORKING_SAVE_ROLE: StorageRole = "working_save"
COMMIT_SNAPSHOT_ROLE: StorageRole = "commit_snapshot"
ALLOWED_STORAGE_ROLES = {WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE}


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    category: FindingCategory
    severity: FindingSeverity
    blocking: bool
    location: Optional[str]
    message: str
    hint: Optional[str] = None


@dataclass(frozen=True)
class ValidationReport:
    role: StorageRole
    findings: list[ValidationFinding]
    blocking_count: int
    warning_count: int
    result: ValidationResult


@dataclass(frozen=True)
class PublicNexRoleBoundary:
    storage_role: StorageRole
    required_sections: tuple[str, ...]
    optional_sections: tuple[str, ...]
    forbidden_sections: tuple[str, ...]
    identity_field: str
    editor_continuity_posture: str
    commit_boundary_posture: str


@dataclass(frozen=True)
class PublicNexArtifactOperationBoundary:
    operation: str
    posture: str
    canonical_api: str
    canonical_http_method: str
    canonical_route: str
    result_surface: str
    allowed_source_roles: tuple[StorageRole, ...]
    result_role_posture: str
    denial_reason_code: str
    execution_anchor_posture: Optional[str] = None


@dataclass(frozen=True)
class PublicNexFormatBoundary:
    format_family: str
    shared_backbone_sections: tuple[str, ...]
    supported_roles: tuple[StorageRole, ...]
    legacy_default_role: StorageRole
    working_save: PublicNexRoleBoundary
    commit_snapshot: PublicNexRoleBoundary
    artifact_operation_boundaries: tuple[PublicNexArtifactOperationBoundary, ...]

    def role_boundary(self, storage_role: StorageRole) -> PublicNexRoleBoundary:
        if storage_role == WORKING_SAVE_ROLE:
            return self.working_save
        if storage_role == COMMIT_SNAPSHOT_ROLE:
            return self.commit_snapshot
        raise ValueError(f"Unsupported public .nex storage_role: {storage_role}")


@dataclass(frozen=True)
class PublicNexExecutionTargetDescriptor:
    storage_role: StorageRole
    target_type: Literal["working_save", "commit_snapshot"]
    target_ref: str
    execution_anchor_posture: str
    source_working_save_id: Optional[str] = None


@dataclass(frozen=True)
class NexExecutionTargetDescriptor:
    storage_role: StorageRole
    target_type: Literal["working_save", "commit_snapshot"]
    target_ref: str
    execution_anchor_posture: str
    source_working_save_id: Optional[str] = None


@dataclass(frozen=True)
class PublicNexArtifactDescriptor:
    storage_role: StorageRole
    canonical_ref: str
    identity_field: str
    top_level_sections: tuple[str, ...]
    required_sections: tuple[str, ...]
    optional_sections: tuple[str, ...]
    forbidden_sections: tuple[str, ...]
    editor_continuity_posture: str
    commit_boundary_posture: str
    export_ready: bool
    source_working_save_id: Optional[str] = None


@dataclass(frozen=True)
class PublicNexShareOperationBoundary:
    operation: str
    posture: str
    canonical_http_method: str
    canonical_route: str
    result_surface: str
    effect_posture: str
    requires_authentication: bool
    requires_issuer_scope: bool
    lifecycle_gate: str
    allowed_storage_roles: tuple[StorageRole, ...]
    allowed_effective_lifecycle_states: tuple[ShareLifecycleState, ...]
    denial_reason_code: str


@dataclass(frozen=True)
class PublicNexShareHistoryEntryBoundary:
    entry_surface: str
    identity_field: str
    timestamp_field: str
    event_type_field: str
    actor_identity_field: str
    stored_lifecycle_field: str
    effective_lifecycle_field: str
    detail_payload_field: str
    detail_payload_value_posture: str


@dataclass(frozen=True)
class PublicNexShareHistoryBoundary:
    access_posture: str
    ordering: str
    canonical_http_method: str
    canonical_route: str
    result_surface: str
    actor_identity_posture: str
    event_types: tuple[ShareAuditEventType, ...]
    includes_stored_lifecycle_state: bool
    includes_effective_lifecycle_state: bool
    detail_payload_posture: str
    entry_boundary: PublicNexShareHistoryEntryBoundary


@dataclass(frozen=True)
class PublicNexShareBoundary:
    share_family: str
    transport_modes: tuple[ShareTransport, ...]
    access_modes: tuple[ShareAccessMode, ...]
    public_access_posture: str
    management_access_posture: str
    history_access_posture: str
    artifact_access_posture: str
    supported_roles: tuple[StorageRole, ...]
    artifact_format_family: str
    viewer_capabilities: tuple[str, ...]
    supported_operations: tuple[ShareOperation, ...]
    public_operation_boundaries: tuple[PublicNexShareOperationBoundary, ...]
    management_operation_boundaries: tuple[PublicNexShareOperationBoundary, ...]
    history_boundary: PublicNexShareHistoryBoundary
    supported_lifecycle_states: tuple[ShareLifecycleState, ...]
    terminal_lifecycle_states: tuple[ShareLifecycleState, ...]
    management_operations: tuple[str, ...]


@dataclass(frozen=True)
class PublicNexShareAuditEntry:
    sequence: int
    event_type: ShareAuditEventType
    at: str
    actor_user_ref: Optional[str]
    stored_lifecycle_state: ShareLifecycleState
    effective_lifecycle_state: ShareLifecycleState
    details: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class PublicNexShareDescriptor:
    share_id: str
    share_path: str
    transport: ShareTransport
    access_mode: ShareAccessMode
    storage_role: StorageRole
    canonical_ref: str
    title: str
    summary: Optional[str]
    artifact_format_family: str
    viewer_capabilities: tuple[str, ...]
    operation_capabilities: tuple[ShareOperation, ...]
    stored_lifecycle_state: ShareLifecycleState
    lifecycle_state: ShareLifecycleState
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    issued_by_user_ref: Optional[str] = None
    archived: bool = False
    archived_at: Optional[str] = None
    source_working_save_id: Optional[str] = None
    audit_event_count: int = 0
    last_audit_event_type: Optional[ShareAuditEventType] = None
    last_audit_event_at: Optional[str] = None


@dataclass(frozen=True)
class IssuerPublicShareManagementEntry:
    share_id: str
    share_path: str
    title: str
    summary: Optional[str]
    storage_role: StorageRole
    lifecycle_state: ShareLifecycleState
    stored_lifecycle_state: ShareLifecycleState
    operation_capabilities: tuple[ShareOperation, ...]
    canonical_ref: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    archived: bool = False
    archived_at: Optional[str] = None
    audit_event_count: int = 0
    last_audit_event_type: Optional[ShareAuditEventType] = None
    last_audit_event_at: Optional[str] = None


@dataclass(frozen=True)
class IssuerPublicShareManagementSummary:
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


@dataclass(frozen=True)
class IssuerPublicShareManagementActionReportEntry:
    report_id: str
    issuer_user_ref: str
    action: IssuerShareManagementAction
    scope: ManagementActionScope
    created_at: str
    requested_share_ids: tuple[str, ...]
    affected_share_ids: tuple[str, ...]
    affected_share_count: int
    before_total_share_count: int
    after_total_share_count: int
    actor_user_ref: Optional[str] = None
    expires_at: Optional[str] = None
    archived: Optional[bool] = None


@dataclass(frozen=True)
class IssuerPublicShareManagementActionReportSummary:
    issuer_user_ref: str
    total_report_count: int
    revoke_report_count: int
    extend_report_count: int
    archive_report_count: int
    delete_report_count: int
    total_requested_share_count: int
    total_affected_share_count: int
    latest_report_at: Optional[str] = None


@dataclass(frozen=True)
class IssuerPublicShareGovernanceSummary:
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
    total_action_report_count: int
    revoke_action_report_count: int
    extend_action_report_count: int
    archive_action_report_count: int
    delete_action_report_count: int
    latest_created_at: Optional[str] = None
    latest_updated_at: Optional[str] = None
    latest_audit_event_at: Optional[str] = None
    latest_action_report_at: Optional[str] = None
    recent_action_reports: tuple[IssuerPublicShareManagementActionReportEntry, ...] = ()


@dataclass(frozen=True)
class IssuerPublicShareManagementActionResult:
    issuer_user_ref: str
    action: IssuerShareManagementAction
    requested_share_ids: tuple[str, ...]
    affected_share_count: int
    summary: IssuerPublicShareManagementSummary
    shares: tuple[IssuerPublicShareManagementEntry, ...]
