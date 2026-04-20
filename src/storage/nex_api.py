from __future__ import annotations

from pathlib import Path
from typing import Any

from src.contracts.commit_snapshot_contract import (
    COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS,
    COMMIT_SNAPSHOT_IDENTITY_FIELD,
    COMMIT_SNAPSHOT_REQUIRED_SECTIONS,
)
from src.contracts.nex_contract import (
    ALLOWED_STORAGE_ROLES,
    COMMIT_SNAPSHOT_ROLE,
    WORKING_SAVE_ROLE,
    PublicNexArtifactDescriptor,
    PublicNexArtifactOperationBoundary,
    PublicNexFormatBoundary,
    PublicNexRoleBoundary,
)
from src.contracts.working_save_contract import (
    WORKING_SAVE_IDENTITY_FIELD,
    WORKING_SAVE_OPTIONAL_SECTIONS,
    WORKING_SAVE_REQUIRED_SECTIONS,
)
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.storage.serialization import (
    serialize_commit_snapshot,
    serialize_working_save,
    validate_serialized_storage_artifact_for_write,
)
from src.storage.validators.shared_validator import (
    load_nex,
    validate_commit_snapshot,
    validate_working_save,
)

_SHARED_PUBLIC_BACKBONE = ("meta", "circuit", "resources", "state")
_PUBLIC_NEX_FORMAT_BOUNDARY = PublicNexFormatBoundary(
    format_family=".nex",
    shared_backbone_sections=_SHARED_PUBLIC_BACKBONE,
    supported_roles=(WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE),
    legacy_default_role=WORKING_SAVE_ROLE,
    working_save=PublicNexRoleBoundary(
        storage_role=WORKING_SAVE_ROLE,
        required_sections=WORKING_SAVE_REQUIRED_SECTIONS,
        optional_sections=WORKING_SAVE_OPTIONAL_SECTIONS,
        forbidden_sections=tuple(),
        identity_field=WORKING_SAVE_IDENTITY_FIELD,
        editor_continuity_posture="ui_continuity_allowed",
        commit_boundary_posture="must_strip_ui_before_commit_snapshot",
    ),
    commit_snapshot=PublicNexRoleBoundary(
        storage_role=COMMIT_SNAPSHOT_ROLE,
        required_sections=COMMIT_SNAPSHOT_REQUIRED_SECTIONS,
        optional_sections=tuple(),
        forbidden_sections=COMMIT_SNAPSHOT_FORBIDDEN_SECTIONS,
        identity_field=COMMIT_SNAPSHOT_IDENTITY_FIELD,
        editor_continuity_posture="ui_forbidden_in_canonical_snapshot",
        commit_boundary_posture="already_crossed_commit_boundary",
    ),
    artifact_operation_boundaries=(
        PublicNexArtifactOperationBoundary(
            operation="load_artifact",
            posture="role_aware_unified_loader",
            canonical_api="load_nex",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE),
            result_role_posture="role_preserving_loaded_model",
            denial_reason_code="public_nex.load_not_allowed",
        ),
        PublicNexArtifactOperationBoundary(
            operation="validate_working_save",
            posture="working_save_only_role_validator",
            canonical_api="validate_working_save",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(WORKING_SAVE_ROLE,),
            result_role_posture="working_save_only",
            denial_reason_code="public_nex.role_validation_not_allowed",
        ),
        PublicNexArtifactOperationBoundary(
            operation="validate_commit_snapshot",
            posture="commit_snapshot_only_role_validator",
            canonical_api="validate_commit_snapshot",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(COMMIT_SNAPSHOT_ROLE,),
            result_role_posture="commit_snapshot_only",
            denial_reason_code="public_nex.role_validation_not_allowed",
        ),
        PublicNexArtifactOperationBoundary(
            operation="import_copy",
            posture="role_preserving_public_import_copy",
            canonical_api="load_nex",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE),
            result_role_posture="role_preserving_import_copy",
            denial_reason_code="public_nex.import_not_allowed",
        ),
        PublicNexArtifactOperationBoundary(
            operation="run_artifact",
            posture="role_aware_runtime_entry",
            canonical_api="load_nex",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(WORKING_SAVE_ROLE, COMMIT_SNAPSHOT_ROLE),
            result_role_posture="runtime_accepts_loaded_model",
            denial_reason_code="public_nex.run_not_allowed",
            execution_anchor_posture="working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor",
        ),
        PublicNexArtifactOperationBoundary(
            operation="checkout_working_copy",
            posture="commit_snapshot_to_working_save_checkout",
            canonical_api="load_nex",
            canonical_http_method="GET",
            canonical_route="/api/public-shares/{share_id}/artifact",
            result_surface="public_share_artifact",
            allowed_source_roles=(COMMIT_SNAPSHOT_ROLE,),
            result_role_posture="commit_snapshot_to_working_save_checkout",
            denial_reason_code="public_nex.checkout_not_allowed",
        ),
    ),
)


def get_public_nex_format_boundary() -> PublicNexFormatBoundary:
    return _PUBLIC_NEX_FORMAT_BOUNDARY


def _first_blocking_finding_message(loaded: LoadedNexArtifact) -> str | None:
    for finding in loaded.findings or []:
        if getattr(finding, "blocking", False):
            return getattr(finding, "message", None)
    return None


def _coerce_public_nex_model(
    model_or_data: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact | dict[str, Any],
) -> WorkingSaveModel | CommitSnapshotModel:
    if isinstance(model_or_data, WorkingSaveModel | CommitSnapshotModel):
        return model_or_data

    if isinstance(model_or_data, LoadedNexArtifact):
        if model_or_data.parsed_model is None:
            blocking = _first_blocking_finding_message(model_or_data)
            suffix = f": {blocking}" if blocking else ""
            raise ValueError(f"Cannot export rejected public .nex artifact{suffix}")
        return model_or_data.parsed_model

    if isinstance(model_or_data, dict):
        meta = model_or_data.get("meta") if isinstance(model_or_data.get("meta"), dict) else {}
        storage_role = meta.get("storage_role")
        if storage_role not in ALLOWED_STORAGE_ROLES:
            raise ValueError("public .nex export requires explicit meta.storage_role")
        loaded = load_nex(model_or_data, allow_legacy_fallback=False)
        if loaded.parsed_model is None:
            blocking = _first_blocking_finding_message(loaded)
            suffix = f": {blocking}" if blocking else ""
            raise ValueError(f"public .nex artifact is not loadable for export{suffix}")
        return loaded.parsed_model

    raise TypeError(
        "public .nex export expects WorkingSaveModel, CommitSnapshotModel, LoadedNexArtifact, or dict"
    )


def export_public_nex_artifact(
    model_or_data: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact | dict[str, Any],
) -> dict[str, Any]:
    model = _coerce_public_nex_model(model_or_data)
    payload = (
        serialize_working_save(model)
        if isinstance(model, WorkingSaveModel)
        else serialize_commit_snapshot(model)
    )
    validate_serialized_storage_artifact_for_write(payload)
    return payload


def describe_public_nex_artifact(
    model_or_data: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact | dict[str, Any],
) -> PublicNexArtifactDescriptor:
    payload = export_public_nex_artifact(model_or_data)
    meta = payload.get("meta", {})
    storage_role = str(meta.get("storage_role") or "")
    if storage_role not in ALLOWED_STORAGE_ROLES:
        raise ValueError("public .nex artifact must declare a supported storage_role")
    boundary = _PUBLIC_NEX_FORMAT_BOUNDARY.role_boundary(storage_role)
    canonical_ref = str(meta.get(boundary.identity_field) or "")
    return PublicNexArtifactDescriptor(
        storage_role=storage_role,  # type: ignore[arg-type]
        canonical_ref=canonical_ref,
        identity_field=boundary.identity_field,
        top_level_sections=tuple(payload.keys()),
        required_sections=boundary.required_sections,
        optional_sections=boundary.optional_sections,
        forbidden_sections=boundary.forbidden_sections,
        editor_continuity_posture=boundary.editor_continuity_posture,
        commit_boundary_posture=boundary.commit_boundary_posture,
        export_ready=True,
        source_working_save_id=(
            str(meta.get("source_working_save_id"))
            if storage_role == COMMIT_SNAPSHOT_ROLE and meta.get("source_working_save_id") is not None
            else None
        ),
    )


__all__ = [
    "load_nex",
    "validate_working_save",
    "validate_commit_snapshot",
    "get_public_nex_format_boundary",
    "describe_public_nex_artifact",
    "export_public_nex_artifact",
]
