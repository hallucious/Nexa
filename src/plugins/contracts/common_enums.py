from __future__ import annotations

from typing import Final

BUILDER_MODE_CREATE_NEW: Final[str] = "create_new"
BUILDER_MODE_UPDATE_CANDIDATE: Final[str] = "update_candidate"
BUILDER_MODE_REVIEW_EXISTING: Final[str] = "review_existing"
BUILDER_MODE_BUILD_AND_REGISTER: Final[str] = "build_and_register"

BUILDER_MODES: Final[frozenset[str]] = frozenset(
    {
        BUILDER_MODE_CREATE_NEW,
        BUILDER_MODE_UPDATE_CANDIDATE,
        BUILDER_MODE_REVIEW_EXISTING,
        BUILDER_MODE_BUILD_AND_REGISTER,
    }
)

CALLER_TYPE_DESIGNER_FLOW: Final[str] = "designer_flow"
CALLER_TYPE_MANUAL_BUILDER_UI: Final[str] = "manual_builder_ui"
CALLER_TYPE_AUTOMATION_FLOW: Final[str] = "automation_flow"
CALLER_TYPE_ADMIN_FLOW: Final[str] = "admin_flow"

CALLER_TYPES: Final[frozenset[str]] = frozenset(
    {
        CALLER_TYPE_DESIGNER_FLOW,
        CALLER_TYPE_MANUAL_BUILDER_UI,
        CALLER_TYPE_AUTOMATION_FLOW,
        CALLER_TYPE_ADMIN_FLOW,
    }
)

SOURCE_TYPE_DESIGNER_PROPOSAL: Final[str] = "designer_plugin_build_proposal"
SOURCE_TYPE_MANUAL_SPEC: Final[str] = "manual_builder_spec"
SOURCE_TYPE_EXISTING_CANDIDATE: Final[str] = "existing_candidate"
SOURCE_TYPE_EXISTING_REGISTRY_ENTRY: Final[str] = "existing_registry_entry"

SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {
        SOURCE_TYPE_DESIGNER_PROPOSAL,
        SOURCE_TYPE_MANUAL_SPEC,
        SOURCE_TYPE_EXISTING_CANDIDATE,
        SOURCE_TYPE_EXISTING_REGISTRY_ENTRY,
    }
)

BUILDER_STATUS_INTAKE_REJECTED: Final[str] = "intake_rejected"
BUILDER_STATUS_NORMALIZED_PREVIEW_READY: Final[str] = "normalized_preview_ready"
BUILDER_STATUS_VALIDATION_FAILED: Final[str] = "validation_failed"
BUILDER_STATUS_BUILD_COMPLETE_UNREGISTERED: Final[str] = "build_complete_unregistered"
BUILDER_STATUS_REGISTERED: Final[str] = "registered"

BUILDER_STATUSES: Final[frozenset[str]] = frozenset(
    {
        BUILDER_STATUS_INTAKE_REJECTED,
        BUILDER_STATUS_NORMALIZED_PREVIEW_READY,
        BUILDER_STATUS_VALIDATION_FAILED,
        BUILDER_STATUS_BUILD_COMPLETE_UNREGISTERED,
        BUILDER_STATUS_REGISTERED,
    }
)

FINDING_SEVERITY_INFO: Final[str] = "info"
FINDING_SEVERITY_WARNING: Final[str] = "warning"
FINDING_SEVERITY_BLOCKING: Final[str] = "blocking"

FINDING_SEVERITIES: Final[frozenset[str]] = frozenset(
    {FINDING_SEVERITY_INFO, FINDING_SEVERITY_WARNING, FINDING_SEVERITY_BLOCKING}
)

BUILDER_STAGE_INTAKE: Final[str] = "intake"
BUILDER_STAGE_NORMALIZE: Final[str] = "normalize"
BUILDER_STAGE_VALIDATION: Final[str] = "validation"
BUILDER_STAGE_VERIFICATION: Final[str] = "verification"
BUILDER_STAGE_REGISTRATION: Final[str] = "registration"

BUILDER_STAGES: Final[frozenset[str]] = frozenset(
    {
        BUILDER_STAGE_INTAKE,
        BUILDER_STAGE_NORMALIZE,
        BUILDER_STAGE_VALIDATION,
        BUILDER_STAGE_VERIFICATION,
        BUILDER_STAGE_REGISTRATION,
    }
)

REGISTRATION_SCOPE_WORKSPACE: Final[str] = "workspace"
REGISTRATION_SCOPE_USER: Final[str] = "user"
REGISTRATION_SCOPE_ORG: Final[str] = "org"
REGISTRATION_SCOPE_PUBLIC: Final[str] = "public"
REGISTRATION_SCOPES: Final[frozenset[str]] = frozenset(
    {
        REGISTRATION_SCOPE_WORKSPACE,
        REGISTRATION_SCOPE_USER,
        REGISTRATION_SCOPE_ORG,
        REGISTRATION_SCOPE_PUBLIC,
    }
)


def require_known_value(value: str, *, allowed: frozenset[str], field_name: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed:
        raise ValueError(f"Unsupported {field_name}: {normalized!r}")
    return normalized


__all__ = [
    "BUILDER_MODE_BUILD_AND_REGISTER",
    "BUILDER_MODE_CREATE_NEW",
    "BUILDER_MODE_REVIEW_EXISTING",
    "BUILDER_MODE_UPDATE_CANDIDATE",
    "BUILDER_MODES",
    "BUILDER_STAGE_INTAKE",
    "BUILDER_STAGE_NORMALIZE",
    "BUILDER_STAGE_REGISTRATION",
    "BUILDER_STAGE_VALIDATION",
    "BUILDER_STAGE_VERIFICATION",
    "BUILDER_STAGES",
    "BUILDER_STATUS_BUILD_COMPLETE_UNREGISTERED",
    "BUILDER_STATUS_INTAKE_REJECTED",
    "BUILDER_STATUS_NORMALIZED_PREVIEW_READY",
    "BUILDER_STATUS_REGISTERED",
    "BUILDER_STATUS_VALIDATION_FAILED",
    "BUILDER_STATUSES",
    "CALLER_TYPE_ADMIN_FLOW",
    "CALLER_TYPE_AUTOMATION_FLOW",
    "CALLER_TYPE_DESIGNER_FLOW",
    "CALLER_TYPE_MANUAL_BUILDER_UI",
    "CALLER_TYPES",
    "FINDING_SEVERITIES",
    "FINDING_SEVERITY_BLOCKING",
    "FINDING_SEVERITY_INFO",
    "FINDING_SEVERITY_WARNING",
    "REGISTRATION_SCOPE_ORG",
    "REGISTRATION_SCOPE_PUBLIC",
    "REGISTRATION_SCOPE_USER",
    "REGISTRATION_SCOPE_WORKSPACE",
    "REGISTRATION_SCOPES",
    "SOURCE_TYPE_DESIGNER_PROPOSAL",
    "SOURCE_TYPE_EXISTING_CANDIDATE",
    "SOURCE_TYPE_EXISTING_REGISTRY_ENTRY",
    "SOURCE_TYPE_MANUAL_SPEC",
    "SOURCE_TYPES",
    "require_known_value",
]
