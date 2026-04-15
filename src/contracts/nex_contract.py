from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

ShareLifecycleState = Literal["active", "expired", "revoked"]
ShareAuditEventType = Literal["created", "expiration_extended", "revoked"]

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


@dataclass(frozen=True)
class PublicNexFormatBoundary:
    format_family: str
    shared_backbone_sections: tuple[str, ...]
    supported_roles: tuple[StorageRole, ...]
    legacy_default_role: StorageRole
    working_save: PublicNexRoleBoundary
    commit_snapshot: PublicNexRoleBoundary

    def role_boundary(self, storage_role: StorageRole) -> PublicNexRoleBoundary:
        if storage_role == WORKING_SAVE_ROLE:
            return self.working_save
        if storage_role == COMMIT_SNAPSHOT_ROLE:
            return self.commit_snapshot
        raise ValueError(f"Unsupported public .nex storage_role: {storage_role}")


@dataclass(frozen=True)
class PublicNexArtifactDescriptor:
    storage_role: StorageRole
    canonical_ref: str
    identity_field: str
    top_level_sections: tuple[str, ...]
    required_sections: tuple[str, ...]
    optional_sections: tuple[str, ...]
    forbidden_sections: tuple[str, ...]
    export_ready: bool
    source_working_save_id: Optional[str] = None


@dataclass(frozen=True)
class PublicNexShareBoundary:
    share_family: str
    transport_modes: tuple[ShareTransport, ...]
    access_modes: tuple[ShareAccessMode, ...]
    supported_roles: tuple[StorageRole, ...]
    artifact_format_family: str
    viewer_capabilities: tuple[str, ...]
    supported_operations: tuple[ShareOperation, ...]
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
    source_working_save_id: Optional[str] = None
    audit_event_count: int = 0
    last_audit_event_type: Optional[ShareAuditEventType] = None
    last_audit_event_at: Optional[str] = None
