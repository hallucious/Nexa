from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Callable, Mapping, Optional

from src.server.auth_adapter import AuthorizationGate, RequestAuthResolver
from src.server.auth_models import AuthorizationInput, RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineResultEnvelope, EngineRunLaunchRequest, EngineRunLaunchResponse, EngineRunStatusSnapshot
from src.server.http_route_models import HttpRouteRequest, HttpRouteResponse
from src.server.run_admission import RunAdmissionService
from src.server.run_admission_models import (
    ExecutionTargetCatalogEntry,
    ProductAdmissionPolicy,
    ProductClientContext,
    ProductExecutionTarget,
    ProductLaunchOptions,
    ProductRunLaunchRequest,
)
from src.server.run_read_api import RunResultReadService, RunStatusReadService
from src.server.run_list_api import RunListReadService
from src.server.artifact_trace_read_api import ArtifactReadService, TraceReadService
from src.server.workspace_onboarding_api import OnboardingContinuityService, WorkspaceRegistryService
from src.server.workspace_onboarding_models import ProductOnboardingWriteRequest, ProductWorkspaceCreateRequest
from src.server.recent_activity_api import RecentActivityService
from src.server.provider_probe_history_api import ProviderProbeHistoryService
from src.server.provider_secret_api import ProviderSecretIntegrationService
from src.server.provider_health_api import ProviderHealthService, SecretMetadataReader
from src.server.provider_probe_api import ProviderProbeRunner, ProviderProbeService
from src.server.provider_probe_models import ProductProviderProbeRequest
from src.server.feedback_runtime import build_workspace_feedback_payload, build_feedback_submission_payload
from src.server.provider_secret_models import ProductProviderBindingWriteRequest
from src.server.run_control_api import RunControlService
from src.server.run_action_log_api import RunActionLogReadService
from src.server.workspace_shell_runtime import build_workspace_shell_runtime_payload, resolve_workspace_artifact_source, _default_working_save
from src.server.circuit_library_runtime import build_circuit_library_payload
from src.server.starter_template_models import (
    ProductStarterTemplateApplyAcceptedResponse,
    ProductStarterTemplateCatalogResponse,
    ProductStarterTemplateDetailResponse,
)
from src.server.public_nex_models import ProductPublicNexFormatResponse
from src.server.public_mcp_models import ProductPublicMcpHostBridgeResponse, ProductPublicMcpManifestResponse
from src.server.public_share_models import (
    ProductPublicShareCheckoutAcceptedResponse,
    ProductPublicShareCreateWorkspaceAcceptedResponse,
    ProductPublicShareImportAcceptedResponse,
    ProductPublicShareLinks,
    ProductPublicShareRunAcceptedResponse,
    ProductSavedPublicShareMutationResponse,
)
from src.server.result_history_runtime import build_workspace_result_history_payload
from src.storage.share_api import (
    build_issuer_public_share_management_action_report,
    describe_public_nex_link_share,
    ensure_public_nex_link_share_operation_allowed,
    export_public_nex_link_share,
    extend_public_nex_link_share_expiration,
    extend_public_nex_link_shares_for_issuer_expiration,
    update_public_nex_link_share_archive,
    archive_public_nex_link_shares_for_issuer,
    delete_public_nex_link_shares_for_issuer,
    list_issuer_public_share_management_action_reports_for_issuer,
    list_public_nex_link_share_audit_history,
    list_public_nex_link_shares_for_issuer,
    normalize_issuer_public_share_management_action_report_pagination,
    normalize_issuer_public_share_management_pagination,
    load_public_nex_link_share,
    get_public_nex_share_boundary,
    revoke_public_nex_link_share,
    revoke_public_nex_link_shares_for_issuer,
    summarize_issuer_public_share_management_action_reports_for_issuer,
    summarize_issuer_public_share_governance_for_issuer,
    summarize_public_nex_link_shares_for_issuer,
)
from src.storage.nex_api import describe_public_nex_artifact, get_public_nex_format_boundary
from src.ui.i18n import normalize_ui_language, ui_text
from src.designer.proposal_flow import get_starter_circuit_template, list_starter_circuit_templates


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def _route_response(status_code: int, body: Mapping[str, Any]) -> HttpRouteResponse:
    return HttpRouteResponse(status_code=status_code, body=_to_jsonable(dict(body)))


def _request_app_language(query_params: Mapping[str, Any] | None) -> str:
    params = query_params or {}
    return normalize_ui_language(str(params.get("app_language") or params.get("lang") or "en"))


def _request_optional_text(query_params: Mapping[str, Any] | None, key: str) -> str | None:
    params = query_params or {}
    value = str(params.get(key) or "").strip()
    return value or None


def _working_save_source_dict_from_model(model) -> dict[str, Any]:
    return {
        "meta": {
            "format_version": getattr(model.meta, "format_version", "1.0.0"),
            "storage_role": "working_save",
            "working_save_id": getattr(model.meta, "working_save_id", ""),
            "name": getattr(model.meta, "name", None),
            "description": getattr(model.meta, "description", None),
            "created_at": getattr(model.meta, "created_at", None),
            "updated_at": getattr(model.meta, "updated_at", None),
        },
        "circuit": {
            "nodes": list(getattr(model.circuit, "nodes", [])),
            "edges": list(getattr(model.circuit, "edges", [])),
            "entry": getattr(model.circuit, "entry", None),
            "outputs": list(getattr(model.circuit, "outputs", [])),
            "subcircuits": dict(getattr(model.circuit, "subcircuits", {})),
        },
        "resources": {
            "prompts": dict(getattr(model.resources, "prompts", {})),
            "providers": dict(getattr(model.resources, "providers", {})),
            "plugins": dict(getattr(model.resources, "plugins", {})),
        },
        "state": {
            "input": dict(getattr(model.state, "input", {})),
            "working": dict(getattr(model.state, "working", {})),
            "memory": dict(getattr(model.state, "memory", {})),
        },
        "runtime": {
            "status": getattr(model.runtime, "status", "draft"),
            "validation_summary": dict(getattr(model.runtime, "validation_summary", {})),
            "last_run": dict(getattr(model.runtime, "last_run", {})),
            "errors": list(getattr(model.runtime, "errors", [])),
        },
        "ui": {
            "layout": dict(getattr(model.ui, "layout", {})),
            "metadata": dict(getattr(model.ui, "metadata", {})),
        },
        "designer": dict(getattr(getattr(model, "designer", None), "data", {}) or {}),
    }


def _workspace_artifact_mapping(workspace_row: Mapping[str, Any] | None, artifact_source: Any | None) -> dict[str, Any]:
    source = resolve_workspace_artifact_source(workspace_row, artifact_source)
    if isinstance(source, Mapping):
        return json.loads(json.dumps(_to_jsonable(source)))
    if source is not None:
        try:
            from src.server.workspace_shell_runtime import _load_workspace_model
            model, _ = _load_workspace_model(source, workspace_row)
            return _working_save_source_dict_from_model(model)
        except Exception:
            pass
    return _working_save_source_dict_from_model(_default_working_save(workspace_row))


def _append_bounded_history(current: Any, entry: Mapping[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    existing = [dict(item) for item in (current or ()) if isinstance(item, Mapping)]
    existing.append(dict(entry))
    return existing[-limit:]


def _apply_workspace_shell_draft_patch(current_source: dict[str, Any], body: Mapping[str, Any], now_iso: str | None = None) -> dict[str, Any]:
    data = json.loads(json.dumps(_to_jsonable(current_source)))
    designer = dict(data.get("designer") or {})
    designer_state = dict(designer.get("server_backed_shell_state") or {})
    ui = dict(data.get("ui") or {})
    metadata = dict(ui.get("metadata") or {})
    shell_state = dict(metadata.get("runtime_shell_server_state") or {})

    template_id = str(body.get("template_id") or "").strip() or None
    template_display_name = str(body.get("template_display_name") or "").strip() or None
    template_category = str(body.get("template_category") or "").strip() or None
    template_ref = str(body.get("template_ref") or "").strip() or None
    template_version = str(body.get("template_version") or "").strip() or None
    template_provenance_family = str(body.get("template_provenance_family") or "").strip() or None
    template_provenance_source = str(body.get("template_provenance_source") or "").strip() or None
    template_curation_status = str(body.get("template_curation_status") or "").strip() or None
    template_compatibility_family = str(body.get("template_compatibility_family") or "").strip() or None
    template_apply_behavior = str(body.get("template_apply_behavior") or "").strip() or None
    raw_template_lookup_aliases = body.get("template_lookup_aliases")
    template_lookup_aliases = tuple(
        str(item).strip()
        for item in (raw_template_lookup_aliases or ())
        if str(item).strip()
    ) or None
    request_text = str(body.get("request_text") or "").strip() or None
    designer_action = str(body.get("designer_action") or "").strip() or None
    validation_action = str(body.get("validation_action") or "").strip() or None
    validation_status = str(body.get("validation_status") or "").strip() or None
    validation_message = str(body.get("validation_message") or "").strip() or None
    clear_designer_state = bool(body.get("clear_designer_state"))
    clear_validation_state = bool(body.get("clear_validation_state"))

    if template_id or template_display_name or request_text or designer_action or clear_designer_state:
        if clear_designer_state:
            for key in (
                "selected_template_id",
                "selected_template_display_name",
                "selected_template_category",
                "selected_template_ref",
                "selected_template_version",
                "selected_template_provenance_family",
                "selected_template_provenance_source",
                "selected_template_curation_status",
                "selected_template_compatibility_family",
                "selected_template_apply_behavior",
                "selected_template_lookup_aliases",
                "request_text",
                "last_action",
                "updated_at",
            ):
                designer_state.pop(key, None)
            designer.pop("draft_request_text", None)
            designer_state["history"] = _append_bounded_history(
                designer_state.get("history"),
                {"entry_type": "designer_state_cleared", "occurred_at": now_iso},
            )
        else:
            if template_id is not None:
                designer_state["selected_template_id"] = template_id
            if template_display_name is not None:
                designer_state["selected_template_display_name"] = template_display_name
            if template_category is not None:
                designer_state["selected_template_category"] = template_category
            if template_ref is not None:
                designer_state["selected_template_ref"] = template_ref
            if template_version is not None:
                designer_state["selected_template_version"] = template_version
            if template_provenance_family is not None:
                designer_state["selected_template_provenance_family"] = template_provenance_family
            if template_provenance_source is not None:
                designer_state["selected_template_provenance_source"] = template_provenance_source
            if template_curation_status is not None:
                designer_state["selected_template_curation_status"] = template_curation_status
            if template_compatibility_family is not None:
                designer_state["selected_template_compatibility_family"] = template_compatibility_family
            if template_apply_behavior is not None:
                designer_state["selected_template_apply_behavior"] = template_apply_behavior
            if template_lookup_aliases is not None:
                designer_state["selected_template_lookup_aliases"] = list(template_lookup_aliases)
            if request_text is not None:
                designer_state["request_text"] = request_text
                designer["draft_request_text"] = request_text
            if designer_action is not None:
                designer_state["last_action"] = designer_action
            if now_iso:
                designer_state["updated_at"] = now_iso
            designer_state["history"] = _append_bounded_history(
                designer_state.get("history"),
                {
                    "entry_type": "template_applied" if template_id or template_display_name else "designer_action",
                    "template_id": template_id,
                    "template_display_name": template_display_name,
                    "template_category": template_category,
                    "template_ref": template_ref,
                    "template_version": template_version,
                    "template_provenance_family": template_provenance_family,
                    "template_provenance_source": template_provenance_source,
                    "template_curation_status": template_curation_status,
                    "template_compatibility_family": template_compatibility_family,
                    "template_apply_behavior": template_apply_behavior,
                    "template_lookup_aliases": list(template_lookup_aliases or ()),
                    "request_text": request_text,
                    "designer_action": designer_action,
                    "occurred_at": now_iso,
                },
            )
        designer["server_backed_shell_state"] = designer_state
        data["designer"] = designer

    if validation_action or validation_status or validation_message or clear_validation_state:
        if clear_validation_state:
            for key in ("validation_action", "validation_status", "validation_message", "updated_at"):
                shell_state.pop(key, None)
            shell_state["validation_action_history"] = _append_bounded_history(
                shell_state.get("validation_action_history"),
                {"entry_type": "validation_state_cleared", "occurred_at": now_iso},
            )
        else:
            if validation_action is not None:
                shell_state["validation_action"] = validation_action
            if validation_status is not None:
                shell_state["validation_status"] = validation_status
            if validation_message is not None:
                shell_state["validation_message"] = validation_message
            if now_iso:
                shell_state["updated_at"] = now_iso
            shell_state["validation_action_history"] = _append_bounded_history(
                shell_state.get("validation_action_history"),
                {
                    "entry_type": "validation_action",
                    "validation_action": validation_action,
                    "validation_status": validation_status,
                    "validation_message": validation_message,
                    "occurred_at": now_iso,
                },
            )
        metadata["runtime_shell_server_state"] = shell_state
        ui["metadata"] = metadata
        data["ui"] = ui

    return data


def _reason_to_status_code(reason_code: str) -> int:
    normalized = str(reason_code or "").strip().lower()
    if "authentication_required" in normalized:
        return 401
    if "forbidden" in normalized or "role_insufficient" in normalized:
        return 403
    if "not_found" in normalized:
        return 404
    if "quota" in normalized:
        return 429
    if "invalid" in normalized or "malformed" in normalized or "mismatch" in normalized:
        return 400
    return 409


def _resolve_public_share_payload(share_id: str, share_payload_provider) -> tuple[dict[str, Any] | None, Any | None, HttpRouteResponse | None]:
    if share_payload_provider is None:
        return None, None, _route_response(404, {
            "status": "rejected",
            "error_family": "public_share_not_found",
            "reason_code": "public_share.share_not_found",
            "message": "Requested public share was not found.",
            "share_id": share_id,
        })
    raw_payload = share_payload_provider(share_id)
    if raw_payload is None:
        return None, None, _route_response(404, {
            "status": "rejected",
            "error_family": "public_share_not_found",
            "reason_code": "public_share.share_not_found",
            "message": "Requested public share was not found.",
            "share_id": share_id,
        })
    try:
        payload = load_public_nex_link_share(raw_payload)
        descriptor = describe_public_nex_link_share(payload)
    except Exception as exc:  # noqa: BLE001
        return None, None, _route_response(409, {
            "status": "rejected",
            "error_family": "public_share_invalid",
            "reason_code": "public_share.malformed_payload",
            "message": str(exc) or "Requested public share payload is malformed.",
            "share_id": share_id,
        })
    if descriptor.share_id != share_id:
        return None, None, _route_response(409, {
            "status": "rejected",
            "error_family": "public_share_invalid",
            "reason_code": "public_share.share_id_mismatch",
            "message": "Requested public share payload does not match the requested share_id.",
            "share_id": share_id,
            "resolved_share_id": descriptor.share_id,
        })
    return payload, descriptor, None


def _share_audit_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    history = list_public_nex_link_share_audit_history(payload)
    return {
        "event_count": len(history),
        "last_event_type": history[-1]["event_type"] if history else None,
        "last_event_at": history[-1]["at"] if history else None,
    }


def _public_share_boundary_body() -> dict[str, Any]:
    boundary = get_public_nex_share_boundary()
    return {
        "share_family": boundary.share_family,
        "transport_modes": list(boundary.transport_modes),
        "access_modes": list(boundary.access_modes),
        "public_access_posture": boundary.public_access_posture,
        "management_access_posture": boundary.management_access_posture,
        "history_access_posture": boundary.history_access_posture,
        "artifact_access_posture": boundary.artifact_access_posture,
        "supported_roles": list(boundary.supported_roles),
        "artifact_format_family": boundary.artifact_format_family,
        "viewer_capabilities": list(boundary.viewer_capabilities),
        "supported_operations": list(boundary.supported_operations),
        "public_operation_boundaries": [
            {
                "operation": entry.operation,
                "posture": entry.posture,
                "canonical_http_method": entry.canonical_http_method,
                "canonical_route": entry.canonical_route,
                "result_surface": entry.result_surface,
                "effect_posture": entry.effect_posture,
                "requires_authentication": entry.requires_authentication,
                "requires_issuer_scope": entry.requires_issuer_scope,
                "lifecycle_gate": entry.lifecycle_gate,
                "allowed_storage_roles": list(entry.allowed_storage_roles),
                "allowed_effective_lifecycle_states": list(entry.allowed_effective_lifecycle_states),
                "denial_reason_code": entry.denial_reason_code,
            }
            for entry in boundary.public_operation_boundaries
        ],
        "management_operation_boundaries": [
            {
                "operation": entry.operation,
                "posture": entry.posture,
                "canonical_http_method": entry.canonical_http_method,
                "canonical_route": entry.canonical_route,
                "result_surface": entry.result_surface,
                "effect_posture": entry.effect_posture,
                "requires_authentication": entry.requires_authentication,
                "requires_issuer_scope": entry.requires_issuer_scope,
                "lifecycle_gate": entry.lifecycle_gate,
                "allowed_storage_roles": list(entry.allowed_storage_roles),
                "allowed_effective_lifecycle_states": list(entry.allowed_effective_lifecycle_states),
                "denial_reason_code": entry.denial_reason_code,
            }
            for entry in boundary.management_operation_boundaries
        ],
        "history_boundary": {
            "access_posture": boundary.history_boundary.access_posture,
            "ordering": boundary.history_boundary.ordering,
            "canonical_http_method": boundary.history_boundary.canonical_http_method,
            "canonical_route": boundary.history_boundary.canonical_route,
            "result_surface": boundary.history_boundary.result_surface,
            "actor_identity_posture": boundary.history_boundary.actor_identity_posture,
            "event_types": list(boundary.history_boundary.event_types),
            "includes_stored_lifecycle_state": boundary.history_boundary.includes_stored_lifecycle_state,
            "includes_effective_lifecycle_state": boundary.history_boundary.includes_effective_lifecycle_state,
            "detail_payload_posture": boundary.history_boundary.detail_payload_posture,
            "entry_boundary": {
                "entry_surface": boundary.history_boundary.entry_boundary.entry_surface,
                "identity_field": boundary.history_boundary.entry_boundary.identity_field,
                "timestamp_field": boundary.history_boundary.entry_boundary.timestamp_field,
                "event_type_field": boundary.history_boundary.entry_boundary.event_type_field,
                "actor_identity_field": boundary.history_boundary.entry_boundary.actor_identity_field,
                "stored_lifecycle_field": boundary.history_boundary.entry_boundary.stored_lifecycle_field,
                "effective_lifecycle_field": boundary.history_boundary.entry_boundary.effective_lifecycle_field,
                "detail_payload_field": boundary.history_boundary.entry_boundary.detail_payload_field,
                "detail_payload_value_posture": boundary.history_boundary.entry_boundary.detail_payload_value_posture,
            },
        },
        "supported_lifecycle_states": list(boundary.supported_lifecycle_states),
        "terminal_lifecycle_states": list(boundary.terminal_lifecycle_states),
        "management_operations": list(boundary.management_operations),
    }





def _public_mcp_manifest_body(query_params: Mapping[str, Any] | None) -> dict[str, Any]:
    from src.sdk.integration import build_public_mcp_manifest

    return build_public_mcp_manifest(
        base_url=_request_optional_text(query_params, "base_url"),
        resource_uri_prefix=_request_optional_text(query_params, "resource_uri_prefix") or "nexa://public",
        server_name=_request_optional_text(query_params, "server_name") or "nexa-public",
        server_title=_request_optional_text(query_params, "server_title") or "Nexa Public Integration Surface",
    ).to_dict()


def _public_mcp_host_bridge_body(query_params: Mapping[str, Any] | None) -> dict[str, Any]:
    from src.sdk.integration import build_public_mcp_host_bridge_scaffold

    export = build_public_mcp_host_bridge_scaffold(
        base_url=_request_optional_text(query_params, "base_url"),
        resource_uri_prefix=_request_optional_text(query_params, "resource_uri_prefix") or "nexa://public",
    ).export()
    return _to_jsonable(export)
def _public_nex_format_body() -> dict[str, Any]:
    format_boundary = get_public_nex_format_boundary()
    return {
        "format_family": format_boundary.format_family,
        "shared_backbone_sections": list(format_boundary.shared_backbone_sections),
        "supported_roles": list(format_boundary.supported_roles),
        "legacy_default_role": format_boundary.legacy_default_role,
        "role_boundaries": {
            "working_save": {
                "storage_role": format_boundary.working_save.storage_role,
                "identity_field": format_boundary.working_save.identity_field,
                "required_sections": list(format_boundary.working_save.required_sections),
                "optional_sections": list(format_boundary.working_save.optional_sections),
                "forbidden_sections": list(format_boundary.working_save.forbidden_sections),
                "editor_continuity_posture": format_boundary.working_save.editor_continuity_posture,
                "commit_boundary_posture": format_boundary.working_save.commit_boundary_posture,
            },
            "commit_snapshot": {
                "storage_role": format_boundary.commit_snapshot.storage_role,
                "identity_field": format_boundary.commit_snapshot.identity_field,
                "required_sections": list(format_boundary.commit_snapshot.required_sections),
                "optional_sections": list(format_boundary.commit_snapshot.optional_sections),
                "forbidden_sections": list(format_boundary.commit_snapshot.forbidden_sections),
                "editor_continuity_posture": format_boundary.commit_snapshot.editor_continuity_posture,
                "commit_boundary_posture": format_boundary.commit_snapshot.commit_boundary_posture,
            },
        },
        "artifact_operation_boundaries": [
            {
                "operation": entry.operation,
                "posture": entry.posture,
                "canonical_api": entry.canonical_api,
                "canonical_http_method": entry.canonical_http_method,
                "canonical_route": entry.canonical_route,
                "result_surface": entry.result_surface,
                "allowed_source_roles": list(entry.allowed_source_roles),
                "result_role_posture": entry.result_role_posture,
                "denial_reason_code": entry.denial_reason_code,
                "execution_anchor_posture": entry.execution_anchor_posture,
            }
            for entry in format_boundary.artifact_operation_boundaries
        ],
        "public_sdk_entrypoints": {
            "load_artifact": "load_nex",
            "validate_working_save": "validate_working_save",
            "validate_commit_snapshot": "validate_commit_snapshot",
            "commit_transition": "create_commit_snapshot_from_working_save",
            "checkout_transition": "create_working_save_from_commit_snapshot",
        },
        "routes": {
            "format": "/api/formats/public-nex",
            "public_share_artifact": "/api/public-shares/{share_id}/artifact",
            "workspace_shell_commit": "/api/workspaces/{workspace_id}/shell/commit",
            "workspace_shell_checkout": "/api/workspaces/{workspace_id}/shell/checkout",
            "workspace_shell_share": "/api/workspaces/{workspace_id}/shell/share",
        },
    }


def _public_share_identity_body(descriptor) -> dict[str, Any]:
    return {
        "canonical_key": "share_id",
        "canonical_value": descriptor.share_id,
        "public_path_key": "share_path",
        "public_path_value": descriptor.share_path,
        "lookup_mode": "share_id_only",
        "share_family": "public_nex_link_share",
    }


def _public_share_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "share_id",
        "public_path_key": "share_path",
        "lookup_mode": "share_id_only",
        "share_family": "public_nex_link_share",
    }


def _public_share_namespace_policy_body() -> dict[str, Any]:
    return {
        "share_family": "public_nex_link_share",
        "canonical_route": "/api/public-shares/{share_id}",
        "public_path_format": "/share/{share_id}",
        "id_kind": "opaque-share-id",
    }


def _public_share_catalog_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "share_id",
        "collection_surface": "public-share-catalog",
        "lookup_mode": "share_id_only",
        "member_identity_policy": _public_share_identity_policy_body(),
    }


def _public_share_catalog_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-share-catalog",
        "canonical_route": "/api/public-shares",
        "summary_route": "/api/public-shares/summary",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }


def _saved_public_share_collection_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "saved_by_user_ref",
        "lookup_mode": "authenticated_self_route",
        "collection_surface": "saved-public-share-collection",
        "member_identity_policy": _public_share_identity_policy_body(),
    }


def _saved_public_share_collection_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "saved-public-share-collection",
        "canonical_route": "/api/users/me/saved-public-shares",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }


def _saved_public_share_mutation_identity_policy_body(*, action: str, route_template: str) -> dict[str, Any]:
    return {
        "subject_boundary": "saved_public_share_mutation",
        "action": action,
        "canonical_route": route_template,
        "share_id_source": "path_param",
        "saved_by_user_ref_source": "authenticated_session",
        "response_identity_posture": "share_and_saved_collection_identity_exposed",
        "sdk_posture": "saved_public_share_state_mutation",
    }


def _saved_public_share_mutation_namespace_policy_body(*, action: str) -> dict[str, Any]:
    return {
        "namespace_scope": "saved_public_share_mutation",
        "action": action,
        "allowed_namespaces": ["share.public_descriptor", "saved_public_share.collection"],
        "write_behavior": "bounded_saved_collection_mutation",
        "cross_workspace_write": "not_applicable",
        "sdk_posture": "saved_public_share_state_mutation",
    }


def _public_share_related_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "share_id",
        "lookup_mode": "share_id_only",
        "surface_family": "public-share-related",
        "member_identity_policy": _public_share_identity_policy_body(),
    }


def _public_share_related_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-share-related",
        "canonical_route": "/api/public-shares/{share_id}/related",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }


def _public_share_compare_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "share_id",
        "lookup_mode": "share_id_only",
        "surface_family": "public-share-compare-summary",
        "member_identity_policy": _public_share_identity_policy_body(),
    }


def _public_share_compare_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-share-compare-summary",
        "canonical_route": "/api/public-shares/{share_id}/compare-summary",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }


def _public_share_consumer_action_identity_policy_body(*, action: str, route_template: str) -> dict[str, Any]:
    return {
        "subject_boundary": "public_share_consumer_action",
        "action": action,
        "canonical_route": route_template,
        "share_id_source": "path_param",
        "workspace_identity_source": "request_body.workspace_id_when_required",
        "response_identity_posture": "share_and_workspace_identity_exposed",
        "sdk_posture": "public_share_action_write_projection",
    }


def _public_share_consumer_action_namespace_policy_body(*, action: str) -> dict[str, Any]:
    return {
        "namespace_scope": "public_share_consumer_action",
        "action": action,
        "allowed_namespaces": ["share.public_descriptor", "share.public_artifact", "workspace.public_artifact", "workspace.public_registry", "run.public_launch"],
        "write_behavior": "bounded_server_side_mutation",
        "cross_workspace_write": "explicit_workspace_context_required",
        "sdk_posture": "public_share_action_write_projection",
    }


def _public_share_consumer_action_links(*, share_id: str, workspace_id: str | None = None, run_id: str | None = None) -> dict[str, str]:
    links = {
        "share_detail": f"/api/public-shares/{share_id}",
        "share_history": f"/api/public-shares/{share_id}/history",
        "share_artifact": f"/api/public-shares/{share_id}/artifact",
    }
    if workspace_id:
        links["workspace_detail"] = f"/api/workspaces/{workspace_id}"
        links["workspace_shell"] = f"/api/workspaces/{workspace_id}/shell"
    if run_id:
        links["run_status"] = f"/api/runs/{run_id}"
        links["run_result"] = f"/api/runs/{run_id}/result"
        links["run_artifacts"] = f"/api/runs/{run_id}/artifacts"
    return links


def _iter_active_public_share_descriptors(rows: Sequence[Mapping[str, Any]], *, now_iso: str | None = None) -> tuple[Any, ...]:
    descriptors = []
    for row in rows:
        try:
            descriptor = describe_public_nex_link_share(row, now_iso=now_iso)
        except Exception:
            continue
        if descriptor.archived:
            continue
        if descriptor.lifecycle_state != "active":
            continue
        descriptors.append(descriptor)
    descriptors.sort(key=lambda item: (str(item.updated_at or ""), str(item.share_id or "")), reverse=True)
    return tuple(descriptors)


def _filter_public_share_descriptors(
    rows: Sequence[Mapping[str, Any]],
    *,
    search: str = "",
    storage_role: str | None = None,
    operation: str | None = None,
    issuer_user_ref: str | None = None,
    now_iso: str | None = None,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    visible: list[Any] = []
    filtered: list[Any] = []
    normalized_search = str(search or "").strip().lower()
    normalized_storage_role = str(storage_role or "").strip() or None
    normalized_operation = str(operation or "").strip() or None
    normalized_issuer = str(issuer_user_ref or "").strip() or None
    for descriptor in _iter_active_public_share_descriptors(rows, now_iso=now_iso):
        if normalized_issuer and descriptor.issued_by_user_ref != normalized_issuer:
            continue
        visible.append(descriptor)
        haystack = " ".join(filter(None, (descriptor.title, descriptor.summary, descriptor.share_path, descriptor.issued_by_user_ref))).lower()
        if normalized_search and normalized_search not in haystack:
            continue
        if normalized_storage_role and descriptor.storage_role != normalized_storage_role:
            continue
        if normalized_operation and normalized_operation not in descriptor.operation_capabilities:
            continue
        filtered.append(descriptor)
    return tuple(visible), tuple(filtered)


def _normalize_saved_public_share_rows(rows: Sequence[Mapping[str, Any]], *, saved_by_user_ref: str | None = None) -> tuple[dict[str, Any], ...]:
    normalized_user = str(saved_by_user_ref or "").strip() or None
    if normalized_user is None:
        return ()
    normalized: list[dict[str, Any]] = []
    for row in rows:
        share_id = str(row.get("share_id") or "").strip()
        row_user = str(row.get("saved_by_user_ref") or "").strip() or None
        if not share_id or row_user != normalized_user:
            continue
        normalized.append({
            "share_id": share_id,
            "saved_at": str(row.get("saved_at") or ""),
            "saved_by_user_ref": row_user,
        })
    normalized.sort(key=lambda item: (str(item.get("saved_at") or ""), str(item.get("share_id") or "")), reverse=True)
    return tuple(normalized)


def _public_share_capability_summary_body(descriptor: Any) -> dict[str, Any]:
    operation_capabilities = set(getattr(descriptor, "operation_capabilities", ()) or ())
    create_workspace_supported_modes: list[str] = []
    if "checkout_working_copy" in operation_capabilities:
        create_workspace_supported_modes.append("checkout_working_copy")
    if "import_copy" in operation_capabilities:
        create_workspace_supported_modes.append("import_copy")
    preferred_create_workspace_mode = create_workspace_supported_modes[0] if create_workspace_supported_modes else None
    return {
        "can_download_artifact": "download_artifact" in operation_capabilities,
        "can_import_copy": "import_copy" in operation_capabilities,
        "can_run_artifact": "run_artifact" in operation_capabilities,
        "can_checkout_working_copy": "checkout_working_copy" in operation_capabilities,
        "can_create_workspace_from_share": bool(create_workspace_supported_modes),
        "create_workspace_supported_modes": create_workspace_supported_modes,
        "preferred_create_workspace_mode": preferred_create_workspace_mode,
    }


def _public_share_action_availability_body(descriptor: Any) -> dict[str, Any]:
    share_id = str(getattr(descriptor, "share_id", "") or "").strip()
    capability_summary = _public_share_capability_summary_body(descriptor)
    return {
        "download": {
            "allowed": capability_summary["can_download_artifact"],
            "operation": "download_artifact",
            "api_route": f"/api/public-shares/{share_id}/artifact",
            "page_route": f"/app/public-shares/{share_id}/download",
            "requires_workspace_context": False,
            "denial_reason_code": None if capability_summary["can_download_artifact"] else "public_share.download_not_allowed",
        },
        "import": {
            "allowed": capability_summary["can_import_copy"],
            "operation": "import_copy",
            "api_route": f"/api/public-shares/{share_id}/import",
            "page_route": f"/app/public-shares/{share_id}/import",
            "requires_workspace_context": True,
            "denial_reason_code": None if capability_summary["can_import_copy"] else "public_share.import_not_allowed",
        },
        "run": {
            "allowed": capability_summary["can_run_artifact"],
            "operation": "run_artifact",
            "api_route": f"/api/public-shares/{share_id}/run",
            "page_route": f"/app/public-shares/{share_id}/run",
            "requires_workspace_context": True,
            "denial_reason_code": None if capability_summary["can_run_artifact"] else "public_share.run_not_allowed",
        },
        "checkout": {
            "allowed": capability_summary["can_checkout_working_copy"],
            "operation": "checkout_working_copy",
            "api_route": f"/api/public-shares/{share_id}/checkout",
            "page_route": f"/app/public-shares/{share_id}/checkout",
            "requires_workspace_context": True,
            "denial_reason_code": None if capability_summary["can_checkout_working_copy"] else "public_share.checkout_not_allowed",
        },
        "create_workspace_from_share": {
            "allowed": capability_summary["can_create_workspace_from_share"],
            "operation": "create_workspace_from_share",
            "api_route": f"/api/public-shares/{share_id}/create-workspace",
            "page_route": f"/app/public-shares/{share_id}/create-workspace",
            "requires_workspace_context": False,
            "supported_modes": list(capability_summary["create_workspace_supported_modes"]),
            "preferred_mode": capability_summary["preferred_create_workspace_mode"],
            "denial_reason_code": None if capability_summary["can_create_workspace_from_share"] else "public_share.workspace_create_not_allowed",
        },
    }


def _public_share_catalog_entry_body(descriptor: Any, *, is_saved: bool = False, saved_at: str | None = None) -> dict[str, Any]:
    return {
        "share_id": descriptor.share_id,
        "share_path": descriptor.share_path,
        "title": descriptor.title,
        "summary": descriptor.summary,
        "storage_role": descriptor.storage_role,
        "lifecycle_state": descriptor.lifecycle_state,
        "updated_at": descriptor.updated_at,
        "issued_by_user_ref": descriptor.issued_by_user_ref,
        "viewer_capabilities": list(descriptor.viewer_capabilities),
        "operation_capabilities": list(descriptor.operation_capabilities),
        "capability_summary": _public_share_capability_summary_body(descriptor),
        "action_availability": _public_share_action_availability_body(descriptor),
        "identity": _public_share_identity_body(descriptor),
        "is_saved": bool(is_saved),
        "saved_at": saved_at,
    }


def _public_share_catalog_summary_body(descriptors: Sequence[Any], *, inventory_count: int, saved_ids: set[str] | None = None) -> dict[str, Any]:
    saved_ids = saved_ids or set()
    return {
        "inventory_share_count": int(inventory_count),
        "filtered_share_count": len(tuple(descriptors)),
        "working_save_share_count": sum(1 for descriptor in descriptors if descriptor.storage_role == "working_save"),
        "commit_snapshot_share_count": sum(1 for descriptor in descriptors if descriptor.storage_role == "commit_snapshot"),
        "runnable_share_count": sum(1 for descriptor in descriptors if "run_artifact" in descriptor.operation_capabilities),
        "checkoutable_share_count": sum(1 for descriptor in descriptors if "checkout_working_copy" in descriptor.operation_capabilities),
        "saved_share_count": sum(1 for descriptor in descriptors if descriptor.share_id in saved_ids),
    }


def _related_public_share_entries(target_descriptor: Any, rows: Sequence[Mapping[str, Any]], *, limit: int = 12, saved_ids: set[str] | None = None, now_iso: str | None = None) -> tuple[dict[str, Any], ...]:
    saved_ids = saved_ids or set()
    related: list[tuple[int, str, str, Any, bool, bool, list[str]]] = []
    target_ops = set(target_descriptor.operation_capabilities)
    for descriptor in _iter_active_public_share_descriptors(rows, now_iso=now_iso):
        if descriptor.share_id == target_descriptor.share_id:
            continue
        same_issuer = bool(target_descriptor.issued_by_user_ref and descriptor.issued_by_user_ref == target_descriptor.issued_by_user_ref)
        same_storage_role = descriptor.storage_role == target_descriptor.storage_role
        shared_operations = sorted(target_ops.intersection(descriptor.operation_capabilities))
        score = (4 if same_issuer else 0) + (2 if same_storage_role else 0) + len(shared_operations)
        if score <= 0:
            continue
        related.append((score, str(descriptor.updated_at or ""), str(descriptor.share_id or ""), descriptor, same_issuer, same_storage_role, shared_operations))
    related.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    entries: list[dict[str, Any]] = []
    for score, _updated_at, _share_id, descriptor, same_issuer, same_storage_role, shared_operations in related[:limit]:
        entry = _public_share_catalog_entry_body(descriptor, is_saved=descriptor.share_id in saved_ids)
        entry.update({
            "match_score": score,
            "same_issuer": same_issuer,
            "same_storage_role": same_storage_role,
            "shared_operations": shared_operations,
        })
        entries.append(entry)
    return tuple(entries)


def _artifact_compare_summary_body(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    from src.server.public_share_runtime import _artifact_compare_summary
    return _artifact_compare_summary(artifact)


def _public_share_compare_summary_body(share_artifact: Mapping[str, Any] | None, workspace_artifact: Mapping[str, Any] | None, *, workspace_id: str | None = None) -> dict[str, Any]:
    share_summary = _artifact_compare_summary_body(share_artifact)
    workspace_summary = _artifact_compare_summary_body(workspace_artifact)
    workspace_found = bool(workspace_id and workspace_artifact is not None)
    return {
        "workspace_id": workspace_id,
        "workspace_found": workspace_found,
        "share_artifact": share_artifact,
        "workspace_artifact": workspace_artifact,
        "share_storage_role": share_summary.get("storage_role") if share_summary.get("present") else None,
        "workspace_storage_role": workspace_summary.get("storage_role") if workspace_summary.get("present") else None,
        "storage_role_match": bool(share_summary.get("present") and workspace_summary.get("present") and share_summary.get("storage_role") == workspace_summary.get("storage_role")),
        "canonical_ref_match": bool(share_summary.get("present") and workspace_summary.get("present") and share_summary.get("canonical_ref") == workspace_summary.get("canonical_ref")),
        "artifact_digest_match": bool(share_summary.get("present") and workspace_summary.get("present") and share_summary.get("digest") == workspace_summary.get("digest")),
        "share_summary": share_summary,
        "workspace_summary": workspace_summary,
    }


def _issuer_public_share_management_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "issuer_user_ref",
        "lookup_mode": "authenticated_self_route",
        "surface_family": "issuer-public-share-management",
        "member_identity_policy": _public_share_identity_policy_body(),
    }


def _issuer_public_share_management_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "issuer-public-share-management",
        "canonical_route": "/api/users/me/public-shares",
        "summary_route": "/api/users/me/public-shares/summary",
        "actions_base_route": "/api/users/me/public-shares/actions/{action}",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }


def _issuer_public_share_action_report_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "issuer_user_ref",
        "lookup_mode": "authenticated_self_route",
        "surface_family": "issuer-public-share-action-report",
        "report_identity_key": "report_id",
    }


def _issuer_public_share_action_report_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "issuer-public-share-action-report",
        "canonical_route": "/api/users/me/public-shares/action-reports",
        "summary_route": "/api/users/me/public-shares/action-reports/summary",
        "member_namespace_policy": _public_share_namespace_policy_body(),
    }

def _starter_template_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "template_ref",
        "legacy_key": "template_id",
        "lookup_mode": "template_id_or_template_ref",
    }


def _starter_template_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "starter-template",
        "source_scope": "nexa-curated",
        "canonical_ref_format": "{source}:{template_id}@{template_version}",
    }


def _public_nex_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "format_boundary.format_family",
        "lookup_mode": "fixed_public_route",
        "surface_family": "public-nex-format",
    }


def _public_nex_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-nex-format",
        "canonical_route": "/api/formats/public-nex",
        "format_family": ".nex",
    }


def _public_mcp_manifest_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "manifest.server.name",
        "lookup_mode": "fixed_public_route",
        "surface_family": "public-mcp-manifest",
    }


def _public_mcp_manifest_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-mcp-manifest",
        "canonical_route": "/api/integrations/public-mcp/manifest",
        "resource_uri_prefix_field": "manifest.resource_uri_prefix",
    }


def _public_mcp_host_bridge_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "host_bridge.framework_binding_class",
        "lookup_mode": "fixed_public_route",
        "surface_family": "public-mcp-host-bridge",
    }


def _public_mcp_host_bridge_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "public-mcp-host-bridge",
        "canonical_route": "/api/integrations/public-mcp/host-bridge",
        "resource_uri_prefix_field": "host_bridge.resource_uri_prefix",
    }


def _circuit_library_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "library_scope",
        "scope_kind": "authenticated_user",
        "surface_family": "circuit-library",
        "member_identity_key": "workspace_id",
    }


def _circuit_library_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "circuit-library",
        "canonical_route": "/api/workspaces/library",
        "member_namespace_family": "workspace",
        "continuity_surface": "return-use-library",
    }


def _workspace_result_history_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-result-history",
        "member_identity_key": "run_id",
        "selection_query_key": "run_id",
    }


def _workspace_result_history_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-result-history",
        "canonical_route": "/api/workspaces/{workspace_id}/result-history",
        "member_namespace_family": "run",
        "selection_query_key": "run_id",
    }


def _workspace_feedback_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-feedback",
        "member_identity_key": "feedback_id",
        "submission_surface": "workspace-scoped-feedback",
    }


def _workspace_feedback_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-feedback",
        "canonical_route": "/api/workspaces/{workspace_id}/feedback",
        "member_namespace_family": "feedback",
        "submission_posture": "workspace-scoped-write",
    }


def _workspace_registry_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-registry",
        "member_identity_key": "workspace_id",
        "family_group": "workspace-bootstrap",
    }


def _workspace_registry_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-registry",
        "canonical_route": "/api/workspaces",
        "detail_path_format": "/api/workspaces/{workspace_id}",
        "member_namespace_family": "workspace",
        "family_group": "workspace-bootstrap",
    }


def _workspace_onboarding_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "continuity_scope",
        "surface_family": "workspace-onboarding",
        "member_identity_key": "onboarding_state_id",
        "family_group": "workspace-bootstrap",
    }


def _workspace_onboarding_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-onboarding",
        "canonical_route": "/api/users/me/onboarding",
        "workspace_query_key": "workspace_id",
        "member_namespace_family": "onboarding-state",
        "family_group": "workspace-bootstrap",
    }


def _recent_activity_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "activity_scope",
        "surface_family": "recent-activity",
        "member_identity_key": "activity_id",
        "filter_query_key": "workspace_id",
        "family_group": "workspace-bootstrap",
    }


def _recent_activity_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "recent-activity",
        "canonical_route": "/api/users/me/activity",
        "filter_query_key": "workspace_id",
        "member_namespace_family": "activity",
        "family_group": "workspace-bootstrap",
    }


def _history_summary_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "scope",
        "surface_family": "history-summary",
        "family_group": "workspace-bootstrap",
    }


def _history_summary_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "history-summary",
        "canonical_route": "/api/users/me/history-summary",
        "filter_query_key": "workspace_id",
        "family_group": "workspace-bootstrap",
    }

def _workspace_run_list_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-run-list",
        "member_identity_key": "run_id",
        "family_group": "run",
    }


def _workspace_run_list_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-run-list",
        "canonical_route": "/api/workspaces/{workspace_id}/runs",
        "member_namespace_family": "run",
        "family_group": "run",
    }


def _run_status_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-status",
        "family_group": "run",
    }


def _run_status_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-status",
        "canonical_route": "/api/runs/{run_id}",
        "family_group": "run",
    }


def _run_result_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-result",
        "family_group": "run",
    }


def _run_result_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-result",
        "canonical_route": "/api/runs/{run_id}/result",
        "family_group": "run",
    }


def _run_trace_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-trace",
        "member_identity_key": "event_id",
        "family_group": "run",
    }


def _run_trace_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-trace",
        "canonical_route": "/api/runs/{run_id}/trace",
        "family_group": "run",
    }


def _run_artifacts_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-artifacts",
        "member_identity_key": "artifact_id",
        "family_group": "run",
    }


def _run_artifacts_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-artifacts",
        "canonical_route": "/api/runs/{run_id}/artifacts",
        "family_group": "run",
    }


def _artifact_detail_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "artifact_id",
        "surface_family": "artifact-detail",
        "family_group": "artifact",
    }


def _artifact_detail_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "artifact-detail",
        "canonical_route": "/api/artifacts/{artifact_id}",
        "family_group": "artifact",
    }


def _run_action_log_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-action-log",
        "member_identity_key": "event_id",
        "family_group": "run",
    }


def _run_action_log_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-action-log",
        "canonical_route": "/api/runs/{run_id}/actions",
        "family_group": "run",
    }


def _run_control_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-control",
        "action_key": "action",
        "family_group": "run",
    }


def _run_control_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-control",
        "canonical_route": "/api/runs/{run_id}/{action}",
        "family_group": "run",
    }


def _provider_catalog_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "provider_catalog_family",
        "surface_family": "provider-catalog",
        "member_identity_key": "provider_key",
        "family_group": "workspace-provider",
    }


def _provider_catalog_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "provider-catalog",
        "canonical_route": "/api/providers/catalog",
        "member_namespace_family": "provider",
        "family_group": "workspace-provider",
    }


def _workspace_provider_binding_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-provider-binding",
        "member_identity_key": "binding_id",
        "family_group": "workspace-provider",
    }


def _workspace_provider_binding_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-provider-binding",
        "canonical_route": "/api/workspaces/{workspace_id}/provider-bindings",
        "member_namespace_family": "provider-binding",
        "family_group": "workspace-provider",
    }


def _workspace_provider_health_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-provider-health",
        "member_identity_key": "provider_key",
        "family_group": "workspace-provider",
    }


def _workspace_provider_health_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-provider-health",
        "canonical_route": "/api/workspaces/{workspace_id}/provider-bindings/health",
        "detail_path_format": "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health",
        "member_namespace_family": "provider-health",
        "family_group": "workspace-provider",
    }


def _workspace_provider_probe_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-provider-probe",
        "member_identity_key": "provider_key",
        "family_group": "workspace-provider",
    }


def _workspace_provider_probe_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-provider-probe",
        "canonical_route": "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe",
        "member_namespace_family": "provider-probe",
        "family_group": "workspace-provider",
    }


def _workspace_provider_probe_history_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-provider-probe-history",
        "member_identity_key": "probe_event_id",
        "family_group": "workspace-provider",
    }


def _workspace_provider_probe_history_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-provider-probe-history",
        "canonical_route": "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history",
        "member_namespace_family": "provider-probe-event",
        "family_group": "workspace-provider",
    }



def _workspace_shell_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "workspace_id",
        "surface_family": "workspace-shell",
        "member_identity_key": "workspace_id",
        "family_group": "workspace-shell-family",
    }


def _workspace_shell_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "workspace-shell",
        "canonical_route": "/api/workspaces/{workspace_id}/shell",
        "draft_write_route": "/api/workspaces/{workspace_id}/shell/draft",
        "commit_route": "/api/workspaces/{workspace_id}/shell/commit",
        "checkout_route": "/api/workspaces/{workspace_id}/shell/checkout",
        "launch_route": "/api/workspaces/{workspace_id}/shell/launch",
        "member_namespace_family": "workspace-shell",
        "family_group": "workspace-shell-family",
    }


def _run_launch_identity_policy_body() -> dict[str, Any]:
    return {
        "canonical_key": "run_id",
        "surface_family": "run-launch",
        "secondary_identity_key": "workspace_id",
        "member_identity_key": "run_id",
        "family_group": "run-family",
    }


def _run_launch_namespace_policy_body() -> dict[str, Any]:
    return {
        "family": "run-launch",
        "canonical_route": "/api/runs",
        "member_namespace_family": "run",
        "family_group": "run-family",
    }


def _inject_mapping_identity(mapping: Any, *, canonical_key: str, canonical_value: Any | None = None, lookup_mode: str = "direct") -> None:
    if not isinstance(mapping, dict):
        return
    value = canonical_value if canonical_value is not None else mapping.get(canonical_key)
    canonical_value_text = str(value or "").strip()
    if not canonical_value_text:
        return
    mapping["identity"] = {
        "canonical_key": canonical_key,
        "canonical_value": canonical_value_text,
        "lookup_mode": lookup_mode,
    }


def _inject_collection_identity(collection: Any, *, canonical_key: str, lookup_mode: str = "direct") -> None:
    if not isinstance(collection, (list, tuple)):
        return
    for item in collection:
        if not isinstance(item, dict):
            continue
        canonical_value = str(item.get(canonical_key) or "").strip()
        if not canonical_value:
            continue
        item["identity"] = {
            "canonical_key": canonical_key,
            "canonical_value": canonical_value,
            "lookup_mode": lookup_mode,
        }


def _public_artifact_boundary_body(model_or_data: Any) -> dict[str, Any]:
    descriptor = describe_public_nex_artifact(model_or_data)
    format_boundary = get_public_nex_format_boundary()
    return {
        "format_family": format_boundary.format_family,
        "shared_backbone_sections": list(format_boundary.shared_backbone_sections),
        "supported_roles": list(format_boundary.supported_roles),
        "legacy_default_role": format_boundary.legacy_default_role,
        "role_boundary": {
            "storage_role": descriptor.storage_role,
            "identity_field": descriptor.identity_field,
            "required_sections": list(descriptor.required_sections),
            "optional_sections": list(descriptor.optional_sections),
            "forbidden_sections": list(descriptor.forbidden_sections),
            "editor_continuity_posture": descriptor.editor_continuity_posture,
            "commit_boundary_posture": descriptor.commit_boundary_posture,
        },
        "artifact_operation_boundaries": [
            {
                "operation": entry.operation,
                "posture": entry.posture,
                "canonical_api": entry.canonical_api,
                "canonical_http_method": entry.canonical_http_method,
                "canonical_route": entry.canonical_route,
                "result_surface": entry.result_surface,
                "allowed_source_roles": list(entry.allowed_source_roles),
                "result_role_posture": entry.result_role_posture,
                "denial_reason_code": entry.denial_reason_code,
                "execution_anchor_posture": entry.execution_anchor_posture,
            }
            for entry in format_boundary.artifact_operation_boundaries
        ],
    }


def _issuer_share_management_entry_capability_summary_body(entry) -> dict[str, Any]:
    lifecycle_state = str(entry.lifecycle_state or "").strip()
    archived = bool(entry.archived)
    can_mutate_lifecycle = lifecycle_state == "active"
    return {
        "can_revoke": can_mutate_lifecycle,
        "can_extend_expiration": can_mutate_lifecycle,
        "can_archive": not archived,
        "can_unarchive": archived,
        "can_delete": True,
    }


def _issuer_share_management_entry_action_availability_body(entry) -> dict[str, Any]:
    capability_summary = _issuer_share_management_entry_capability_summary_body(entry)
    archived = bool(entry.archived)
    return {
        "revoke": {
            "allowed": capability_summary["can_revoke"],
            "denial_reason_code": None if capability_summary["can_revoke"] else "public_share.transition_not_allowed",
        },
        "extend_expiration": {
            "allowed": capability_summary["can_extend_expiration"],
            "denial_reason_code": None if capability_summary["can_extend_expiration"] else "public_share.transition_not_allowed",
        },
        "archive": {
            "allowed": capability_summary["can_archive"],
            "target_archived_state": True,
            "denial_reason_code": None if capability_summary["can_archive"] else "public_share.already_archived",
        },
        "unarchive": {
            "allowed": capability_summary["can_unarchive"],
            "target_archived_state": False,
            "denial_reason_code": None if capability_summary["can_unarchive"] else "public_share.not_archived",
        },
        "delete": {
            "allowed": capability_summary["can_delete"],
            "denial_reason_code": None,
        },
    }


def _issuer_share_management_capability_summary_body(entries) -> dict[str, Any]:
    resolved_entries = tuple(entries or ())
    entry_summaries = tuple(_issuer_share_management_entry_capability_summary_body(entry) for entry in resolved_entries)
    total = len(resolved_entries)
    return {
        "total_share_count": total,
        "revokable_share_count": sum(1 for summary in entry_summaries if summary["can_revoke"]),
        "extendable_share_count": sum(1 for summary in entry_summaries if summary["can_extend_expiration"]),
        "archivable_share_count": sum(1 for summary in entry_summaries if summary["can_archive"]),
        "unarchivable_share_count": sum(1 for summary in entry_summaries if summary["can_unarchive"]),
        "deletable_share_count": sum(1 for summary in entry_summaries if summary["can_delete"]),
    }


def _issuer_share_bulk_action_availability_body(capability_summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "revoke": {
            "allowed": bool(capability_summary.get("revokable_share_count", 0)),
            "denial_reason_code": None if bool(capability_summary.get("revokable_share_count", 0)) else "public_share.no_revokable_shares",
        },
        "extend_expiration": {
            "allowed": bool(capability_summary.get("extendable_share_count", 0)),
            "denial_reason_code": None if bool(capability_summary.get("extendable_share_count", 0)) else "public_share.no_extendable_shares",
        },
        "archive": {
            "allowed": bool(capability_summary.get("archivable_share_count", 0)),
            "target_archived_state": True,
            "denial_reason_code": None if bool(capability_summary.get("archivable_share_count", 0)) else "public_share.no_archivable_shares",
        },
        "unarchive": {
            "allowed": bool(capability_summary.get("unarchivable_share_count", 0)),
            "target_archived_state": False,
            "denial_reason_code": None if bool(capability_summary.get("unarchivable_share_count", 0)) else "public_share.no_unarchivable_shares",
        },
        "delete": {
            "allowed": bool(capability_summary.get("deletable_share_count", 0)),
            "denial_reason_code": None if bool(capability_summary.get("deletable_share_count", 0)) else "public_share.no_deletable_shares",
        },
    }


def _issuer_share_management_entry_body(entry) -> dict[str, Any]:
    capability_summary = _issuer_share_management_entry_capability_summary_body(entry)
    return {
        "share_id": entry.share_id,
        "share_path": entry.share_path,
        "identity": _public_share_identity_body(entry),
        "title": entry.title,
        "summary": entry.summary,
        "storage_role": entry.storage_role,
        "canonical_ref": entry.canonical_ref,
        "operation_capabilities": list(entry.operation_capabilities),
        "management_capability_summary": capability_summary,
        "management_action_availability": _issuer_share_management_entry_action_availability_body(entry),
        "lifecycle": {
            "stored_state": entry.stored_lifecycle_state,
            "state": entry.lifecycle_state,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "expires_at": entry.expires_at,
        },
        "management": {
            "archived": entry.archived,
            "archived_at": entry.archived_at,
        },
        "audit_summary": {
            "event_count": entry.audit_event_count,
            "last_event_type": entry.last_audit_event_type,
            "last_event_at": entry.last_audit_event_at,
        },
    }


def _issuer_share_management_summary_body(summary) -> dict[str, Any]:
    return {
        "issuer_user_ref": summary.issuer_user_ref,
        "total_share_count": summary.total_share_count,
        "active_share_count": summary.active_share_count,
        "expired_share_count": summary.expired_share_count,
        "revoked_share_count": summary.revoked_share_count,
        "archived_share_count": summary.archived_share_count,
        "working_save_share_count": summary.working_save_share_count,
        "commit_snapshot_share_count": summary.commit_snapshot_share_count,
        "runnable_share_count": summary.runnable_share_count,
        "checkoutable_share_count": summary.checkoutable_share_count,
        "latest_created_at": summary.latest_created_at,
        "latest_updated_at": summary.latest_updated_at,
        "latest_audit_event_at": summary.latest_audit_event_at,
    }


def _report_attr_or_key(report: Any, key: str, default: Any = None) -> Any:
    if isinstance(report, Mapping):
        return report.get(key, default)
    return getattr(report, key, default)


def _issuer_share_management_action_report_entry_body(report: Any) -> dict[str, Any]:
    return {
        "report_id": _report_attr_or_key(report, "report_id"),
        "issuer_user_ref": _report_attr_or_key(report, "issuer_user_ref"),
        "action": _report_attr_or_key(report, "action"),
        "scope": _report_attr_or_key(report, "scope"),
        "created_at": _report_attr_or_key(report, "created_at"),
        "requested_share_ids": list(_report_attr_or_key(report, "requested_share_ids", ()) or ()),
        "affected_share_ids": list(_report_attr_or_key(report, "affected_share_ids", ()) or ()),
        "affected_share_count": int(_report_attr_or_key(report, "affected_share_count", 0) or 0),
        "before_total_share_count": int(_report_attr_or_key(report, "before_total_share_count", 0) or 0),
        "after_total_share_count": int(_report_attr_or_key(report, "after_total_share_count", 0) or 0),
        "actor_user_ref": _report_attr_or_key(report, "actor_user_ref"),
        "expires_at": _report_attr_or_key(report, "expires_at"),
        "archived": _report_attr_or_key(report, "archived"),
    }


def _issuer_share_management_action_report_summary_body(summary) -> dict[str, Any]:
    return {
        "issuer_user_ref": summary.issuer_user_ref,
        "total_report_count": summary.total_report_count,
        "revoke_report_count": summary.revoke_report_count,
        "extend_report_count": summary.extend_report_count,
        "archive_report_count": summary.archive_report_count,
        "delete_report_count": summary.delete_report_count,
        "total_requested_share_count": summary.total_requested_share_count,
        "total_affected_share_count": summary.total_affected_share_count,
        "latest_report_at": summary.latest_report_at,
    }


def _issuer_share_governance_summary_body(summary) -> dict[str, Any]:
    return {
        "issuer_user_ref": summary.issuer_user_ref,
        "total_share_count": summary.total_share_count,
        "active_share_count": summary.active_share_count,
        "expired_share_count": summary.expired_share_count,
        "revoked_share_count": summary.revoked_share_count,
        "archived_share_count": summary.archived_share_count,
        "working_save_share_count": summary.working_save_share_count,
        "commit_snapshot_share_count": summary.commit_snapshot_share_count,
        "runnable_share_count": summary.runnable_share_count,
        "checkoutable_share_count": summary.checkoutable_share_count,
        "total_action_report_count": summary.total_action_report_count,
        "revoke_action_report_count": summary.revoke_action_report_count,
        "extend_action_report_count": summary.extend_action_report_count,
        "archive_action_report_count": summary.archive_action_report_count,
        "delete_action_report_count": summary.delete_action_report_count,
        "latest_created_at": summary.latest_created_at,
        "latest_updated_at": summary.latest_updated_at,
        "latest_audit_event_at": summary.latest_audit_event_at,
        "latest_action_report_at": summary.latest_action_report_at,
        "recent_action_reports": [_issuer_share_management_action_report_entry_body(report) for report in summary.recent_action_reports],
    }


def _effective_action_report_rows(
    action_report_rows_provider=None,
    *,
    fallback_rows: tuple[Mapping[str, Any], ...] = (),
) -> tuple[Mapping[str, Any], ...]:
    provider_rows = tuple(action_report_rows_provider() or ()) if action_report_rows_provider is not None else ()
    if not fallback_rows:
        return provider_rows
    merged: list[Mapping[str, Any]] = list(provider_rows)
    seen_report_ids = {str(row.get("report_id") or "").strip() for row in provider_rows if isinstance(row, Mapping)}
    for row in fallback_rows:
        if not isinstance(row, Mapping):
            continue
        report_id = str(row.get("report_id") or "").strip()
        if report_id and report_id in seen_report_ids:
            continue
        merged.append(row)
        if report_id:
            seen_report_ids.add(report_id)
    return tuple(merged)


def _build_public_share_management_action_report(
    *,
    issuer_user_ref: str,
    action: str,
    scope: str,
    created_at: str,
    requested_share_ids: tuple[str, ...],
    affected_share_ids: tuple[str, ...],
    before_summary,
    after_summary,
    actor_user_ref: str | None = None,
    expires_at: str | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    return build_issuer_public_share_management_action_report(
        issuer_user_ref=issuer_user_ref,
        action=action,
        scope=scope,
        created_at=created_at,
        requested_share_ids=requested_share_ids,
        affected_share_ids=affected_share_ids,
        before_summary=before_summary,
        after_summary=after_summary,
        actor_user_ref=actor_user_ref,
        expires_at=expires_at,
        archived=archived,
    )


def _parse_non_negative_int_query_param(query_params: Mapping[str, Any], key: str) -> int | None:
    raw_value = query_params.get(key)
    if raw_value is None or str(raw_value).strip() == "":
        return None
    try:
        resolved = int(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"issuer public share management query parameter '{key}' must be an integer") from exc
    if resolved < 0:
        raise ValueError(f"issuer public share management query parameter '{key}' must be >= 0")
    return resolved


def _parse_optional_string_query_param(query_params: Mapping[str, Any], key: str) -> str | None:
    raw_value = query_params.get(key)
    if raw_value is None:
        return None
    resolved = str(raw_value).strip()
    return resolved or None


def _parse_optional_bool_query_param(query_params: Mapping[str, Any], key: str) -> bool | None:
    raw_value = query_params.get(key)
    if raw_value is None or str(raw_value).strip() == "":
        return None
    resolved = str(raw_value).strip().lower()
    if resolved in {"true", "1", "yes"}:
        return True
    if resolved in {"false", "0", "no"}:
        return False
    raise ValueError(f"issuer public share management query parameter '{key}' must be a boolean")


def _issuer_public_share_management_filters(query_params: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lifecycle_state": _parse_optional_string_query_param(query_params, "lifecycle_state"),
        "stored_lifecycle_state": _parse_optional_string_query_param(query_params, "stored_lifecycle_state"),
        "storage_role": _parse_optional_string_query_param(query_params, "storage_role"),
        "operation": _parse_optional_string_query_param(query_params, "operation"),
        "archived": _parse_optional_bool_query_param(query_params, "archived"),
    }


def _issuer_public_share_management_pagination(query_params: Mapping[str, Any]) -> tuple[int, int]:
    limit = _parse_non_negative_int_query_param(query_params, "limit")
    offset = _parse_non_negative_int_query_param(query_params, "offset")
    return normalize_issuer_public_share_management_pagination(limit=limit, offset=offset or 0)


def _apply_issuer_public_share_management_page(entries: tuple[Any, ...], *, limit: int, offset: int) -> tuple[tuple[Any, ...], dict[str, Any]]:
    page_entries = tuple(entries[offset: offset + limit])
    filtered_count = len(entries)
    return page_entries, {
        "limit": limit,
        "offset": offset,
        "returned_count": len(page_entries),
        "filtered_share_count": filtered_count,
        "has_more": offset + len(page_entries) < filtered_count,
        "next_offset": offset + len(page_entries) if offset + len(page_entries) < filtered_count else None,
    }


def _merge_public_share_rows(rows: Sequence[Mapping[str, Any]], updated_payloads: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    replacements = {describe_public_nex_link_share(payload).share_id: load_public_nex_link_share(payload) for payload in updated_payloads}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        payload = load_public_nex_link_share(row)
        share_id = describe_public_nex_link_share(payload).share_id
        if share_id in replacements:
            merged.append(replacements[share_id])
            seen.add(share_id)
        else:
            merged.append(payload)
    for share_id, payload in replacements.items():
        if share_id not in seen:
            merged.append(payload)
    return tuple(merged)


def _parse_management_share_ids(body: Any) -> tuple[tuple[str, ...] | None, HttpRouteResponse | None]:
    if not isinstance(body, Mapping):
        return None, _route_response(400, {
            "status": "rejected",
            "error_family": "public_share_management_rejected",
            "reason_code": "public_share.invalid_request",
            "message": "Issuer share management action payload is invalid.",
        })
    raw_share_ids = body.get("share_ids")
    if not isinstance(raw_share_ids, (list, tuple)):
        return None, _route_response(400, {
            "status": "rejected",
            "error_family": "public_share_management_rejected",
            "reason_code": "public_share.share_ids_missing",
            "message": "Issuer share management action requires share_ids.",
        })
    resolved: list[str] = []
    for raw in raw_share_ids:
        if not isinstance(raw, str) or not raw.strip():
            return None, _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.invalid_share_ids",
                "message": "Issuer share management action share_ids must contain non-empty strings.",
            })
        share_id = raw.strip()
        if share_id not in resolved:
            resolved.append(share_id)
    if not resolved:
        return None, _route_response(400, {
            "status": "rejected",
            "error_family": "public_share_management_rejected",
            "reason_code": "public_share.share_ids_missing",
            "message": "Issuer share management action requires at least one share id.",
        })
    return tuple(resolved), None


def _request_auth(request: HttpRouteRequest):
    return RequestAuthResolver.resolve(
        headers=request.headers,
        session_claims=request.session_claims,
    )


class RunHttpRouteSurface:
    _ROUTE_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
        ("get_recent_activity", "GET", "/api/users/me/activity"),
        ("get_history_summary", "GET", "/api/users/me/history-summary"),
        ("list_issuer_public_shares", "GET", "/api/users/me/public-shares"),
        ("get_issuer_public_share_summary", "GET", "/api/users/me/public-shares/summary"),
        ("list_issuer_public_share_action_reports", "GET", "/api/users/me/public-shares/action-reports"),
        ("get_issuer_public_share_action_report_summary", "GET", "/api/users/me/public-shares/action-reports/summary"),
        ("revoke_issuer_public_shares", "POST", "/api/users/me/public-shares/actions/revoke"),
        ("extend_issuer_public_shares", "POST", "/api/users/me/public-shares/actions/extend"),
        ("delete_issuer_public_shares", "POST", "/api/users/me/public-shares/actions/delete"),
        ("archive_issuer_public_shares", "POST", "/api/users/me/public-shares/actions/archive"),
        ("list_workspaces", "GET", "/api/workspaces"),
        ("get_circuit_library", "GET", "/api/workspaces/library"),
        ("list_starter_circuit_templates", "GET", "/api/templates/starter-circuits"),
        ("get_starter_circuit_template", "GET", "/api/templates/starter-circuits/{template_id}"),
        ("apply_starter_circuit_template", "POST", "/api/workspaces/{workspace_id}/starter-templates/{template_id}/apply"),
        ("get_public_nex_format", "GET", "/api/formats/public-nex"),
        ("get_public_mcp_manifest", "GET", "/api/integrations/public-mcp/manifest"),
        ("get_public_mcp_host_bridge", "GET", "/api/integrations/public-mcp/host-bridge"),
        ("get_workspace_result_history", "GET", "/api/workspaces/{workspace_id}/result-history"),
        ("get_workspace_feedback", "GET", "/api/workspaces/{workspace_id}/feedback"),
        ("submit_workspace_feedback", "POST", "/api/workspaces/{workspace_id}/feedback"),
        ("get_workspace", "GET", "/api/workspaces/{workspace_id}"),
        ("create_workspace", "POST", "/api/workspaces"),
        ("get_provider_catalog", "GET", "/api/providers/catalog"),
        ("list_workspace_provider_bindings", "GET", "/api/workspaces/{workspace_id}/provider-bindings"),
        ("put_workspace_provider_binding", "PUT", "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"),
        ("list_workspace_provider_health", "GET", "/api/workspaces/{workspace_id}/provider-bindings/health"),
        ("get_workspace_provider_health", "GET", "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health"),
        ("probe_workspace_provider", "POST", "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe"),
        ("list_provider_probe_history", "GET", "/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history"),
        ("get_onboarding", "GET", "/api/users/me/onboarding"),
        ("put_onboarding", "PUT", "/api/users/me/onboarding"),
        ("list_workspace_runs", "GET", "/api/workspaces/{workspace_id}/runs"),
        ("get_workspace_shell", "GET", "/api/workspaces/{workspace_id}/shell"),
        ("put_workspace_shell_draft", "PUT", "/api/workspaces/{workspace_id}/shell/draft"),
        ("commit_workspace_shell", "POST", "/api/workspaces/{workspace_id}/shell/commit"),
        ("checkout_workspace_shell", "POST", "/api/workspaces/{workspace_id}/shell/checkout"),
        ("create_workspace_shell_share", "POST", "/api/workspaces/{workspace_id}/shell/share"),
        ("launch_workspace_shell", "POST", "/api/workspaces/{workspace_id}/shell/launch"),
        ("list_public_shares", "GET", "/api/public-shares"),
        ("get_public_share_catalog_summary", "GET", "/api/public-shares/summary"),
        ("list_public_shares_by_issuer", "GET", "/api/public-shares/issuers/{issuer_user_ref}"),
        ("get_public_share_issuer_catalog_summary", "GET", "/api/public-shares/issuers/{issuer_user_ref}/summary"),
        ("list_saved_public_shares", "GET", "/api/users/me/saved-public-shares"),
        ("save_public_share", "POST", "/api/public-shares/{share_id}/save"),
        ("unsave_public_share", "POST", "/api/public-shares/{share_id}/unsave"),
        ("get_related_public_shares", "GET", "/api/public-shares/{share_id}/related"),
        ("get_public_share_compare_summary", "GET", "/api/public-shares/{share_id}/compare-summary"),
        ("get_public_share", "GET", "/api/public-shares/{share_id}"),
        ("get_public_share_history", "GET", "/api/public-shares/{share_id}/history"),
        ("get_public_share_artifact", "GET", "/api/public-shares/{share_id}/artifact"),
        ("checkout_public_share", "POST", "/api/public-shares/{share_id}/checkout"),
        ("import_public_share", "POST", "/api/public-shares/{share_id}/import"),
        ("create_workspace_from_public_share", "POST", "/api/public-shares/{share_id}/create-workspace"),
        ("run_public_share", "POST", "/api/public-shares/{share_id}/run"),
        ("extend_public_share", "POST", "/api/public-shares/{share_id}/extend"),
        ("revoke_public_share", "POST", "/api/public-shares/{share_id}/revoke"),
        ("archive_public_share", "POST", "/api/public-shares/{share_id}/archive"),
        ("delete_public_share", "DELETE", "/api/public-shares/{share_id}"),
        ("launch_run", "POST", "/api/runs"),
        ("get_run_status", "GET", "/api/runs/{run_id}"),
        ("get_run_result", "GET", "/api/runs/{run_id}/result"),
        ("get_run_actions", "GET", "/api/runs/{run_id}/actions"),
        ("retry_run", "POST", "/api/runs/{run_id}/retry"),
        ("force_reset_run", "POST", "/api/runs/{run_id}/force-reset"),
        ("mark_run_reviewed", "POST", "/api/runs/{run_id}/mark-reviewed"),
        ("list_run_artifacts", "GET", "/api/runs/{run_id}/artifacts"),
        ("get_artifact_detail", "GET", "/api/artifacts/{artifact_id}"),
        ("get_run_trace", "GET", "/api/runs/{run_id}/trace"),
    )

    @classmethod
    def route_definitions(cls) -> tuple[tuple[str, str, str], ...]:
        return cls._ROUTE_DEFINITIONS

    @staticmethod
    def _parse_launch_request(http_request: HttpRouteRequest) -> ProductRunLaunchRequest:
        from src.storage.models.commit_snapshot_model import CommitSnapshotModel
        from src.storage.models.working_save_model import WorkingSaveModel
        from src.storage.validators.shared_validator import load_nex
        body = http_request.json_body
        if not isinstance(body, Mapping):
            raise ValueError("launch.request_body_invalid")
        execution_target = body.get("execution_target")
        if not isinstance(execution_target, Mapping):
            raise ValueError("launch.execution_target_missing")
        return ProductRunLaunchRequest(
            workspace_id=str(body.get("workspace_id") or "").strip(),
            execution_target=ProductExecutionTarget(
                target_type=str(execution_target.get("target_type") or ""),
                target_ref=str(execution_target.get("target_ref") or ""),
            ),
            input_payload=body.get("input_payload"),
            launch_options=ProductLaunchOptions(**dict(body.get("launch_options") or {})),
            client_context=ProductClientContext(**dict(body.get("client_context") or {})),
        )

    @staticmethod
    def _parse_provider_binding_write_request(http_request: HttpRouteRequest) -> ProductProviderBindingWriteRequest:
        body = http_request.json_body
        if not isinstance(body, Mapping):
            raise ValueError("provider_binding_write.request_body_invalid")
        allowed_model_refs_raw = body.get("allowed_model_refs") or ()
        if isinstance(allowed_model_refs_raw, str):
            allowed_model_refs = (allowed_model_refs_raw.strip(),) if allowed_model_refs_raw.strip() else ()
        else:
            allowed_model_refs = tuple(str(item).strip() for item in allowed_model_refs_raw if str(item).strip())
        return ProductProviderBindingWriteRequest(
            display_name=str(body.get("display_name") or "").strip() or None,
            enabled=bool(body.get("enabled", True)),
            credential_source=str(body.get("credential_source") or "managed").strip() or "managed",
            secret_value=str(body.get("secret_value") or "").strip() or None,
            secret_ref_hint=str(body.get("secret_ref_hint") or "").strip() or None,
            default_model_ref=str(body.get("default_model_ref") or "").strip() or None,
            allowed_model_refs=allowed_model_refs,
            notes=str(body.get("notes") or "").strip() or None,
        )

    @classmethod
    def handle_workspace_shell(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        share_payload_rows_provider=None,
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        feedback_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace shell route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/shell"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "workspace_shell_read_failure",
                "reason_code": "workspace_shell.authentication_required",
                "message": "Workspace shell requires an authenticated session.",
            })
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_shell_not_found",
                "reason_code": "workspace_shell.workspace_not_found",
                "message": "Requested workspace shell was not found.",
            })

        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="read",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return _route_response(
                _reason_to_status_code(f"workspace_shell.{decision.reason_code}"),
                {
                    "status": "rejected",
                    "error_family": "workspace_shell_read_failure",
                    "reason_code": f"workspace_shell.{decision.reason_code}",
                    "message": "Current user is not allowed to read the requested workspace shell.",
                    "workspace_id": workspace_context.workspace_id,
                },
            )

        payload = build_workspace_shell_runtime_payload(
            workspace_row=workspace_row,
            artifact_source=artifact_source,
            recent_run_rows=recent_run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=onboarding_rows,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            share_payload_rows=tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (),
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
            app_language_override=_request_app_language(http_request.query_params),
        )
        payload["identity_policy"] = _workspace_shell_identity_policy_body()
        payload["namespace_policy"] = _workspace_shell_namespace_policy_body()
        return _route_response(200, payload)

    @classmethod
    def handle_put_workspace_shell_draft(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        share_payload_rows_provider=None,
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        feedback_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "PUT":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace shell draft write route only supports PUT."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/shell/draft"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.authentication_required",
                "message": "Workspace shell draft write requires an authenticated session.",
            })
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_shell_not_found",
                "reason_code": "workspace_shell.workspace_not_found",
                "message": "Requested workspace shell was not found.",
            })
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="write",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return _route_response(_reason_to_status_code(f"workspace_shell.{decision.reason_code}"), {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": f"workspace_shell.{decision.reason_code}",
                "message": "Current user is not allowed to update the requested workspace shell draft.",
                "workspace_id": workspace_context.workspace_id,
            })
        from src.storage.models.commit_snapshot_model import CommitSnapshotModel
        from src.storage.models.working_save_model import WorkingSaveModel
        from src.storage.validators.shared_validator import load_nex
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.invalid_request",
                "message": "Workspace shell draft update payload is invalid.",
                "workspace_id": workspace_context.workspace_id,
            })
        current_source, model, _loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        if isinstance(model, CommitSnapshotModel):
            return _route_response(409, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.draft_requires_working_save",
                "message": "Workspace shell draft write requires a working_save source; current workspace shell resolves to a commit_snapshot.",
                "workspace_id": workspace_context.workspace_id,
            })
        if not isinstance(model, WorkingSaveModel):
            return _route_response(409, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.unsupported_source_role",
                "message": "Workspace shell draft write requires a working_save source.",
                "workspace_id": workspace_context.workspace_id,
            })
        updated_source = _apply_workspace_shell_draft_patch(
            _workspace_artifact_mapping(workspace_row, current_source),
            body,
            str(body.get("updated_at") or "").strip() or None,
        )
        normalized_loaded = load_nex(updated_source)
        normalized_model = getattr(normalized_loaded, "parsed_model", None)
        if not isinstance(normalized_model, WorkingSaveModel):
            return _route_response(409, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.draft_write_invalid",
                "message": "Workspace shell draft write produced an invalid working_save artifact.",
                "workspace_id": workspace_context.workspace_id,
            })
        persisted_source = updated_source
        persisted_source = workspace_artifact_source_writer(workspace_context.workspace_id, persisted_source) if workspace_artifact_source_writer is not None else persisted_source
        payload = build_workspace_shell_runtime_payload(
            workspace_row=workspace_row,
            artifact_source=persisted_source,
            recent_run_rows=recent_run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=onboarding_rows,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            share_payload_rows=tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (),
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
            app_language_override=_request_app_language(http_request.query_params),
        )
        payload["identity_policy"] = _workspace_shell_identity_policy_body()
        payload["namespace_policy"] = _workspace_shell_namespace_policy_body()
        return _route_response(200, payload)


    @staticmethod
    def _workspace_shell_write_guard(
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        *,
        expected_path: str,
        method_label: str,
    ) -> HttpRouteResponse | tuple[str, Mapping[str, Any], Any]:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": f"{method_label} route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if http_request.path.rstrip("/") != expected_path.format(workspace_id=workspace_id):
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.authentication_required",
                "message": f"{method_label} requires an authenticated session.",
            })
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_shell_not_found",
                "reason_code": "workspace_shell.workspace_not_found",
                "message": "Requested workspace shell was not found.",
            })
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="write",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return _route_response(_reason_to_status_code(f"workspace_shell.{decision.reason_code}"), {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": f"workspace_shell.{decision.reason_code}",
                "message": "Current user is not allowed to update the requested workspace shell draft.",
                "workspace_id": workspace_context.workspace_id,
            })
        return workspace_id, workspace_row, workspace_context

    @staticmethod
    def _load_workspace_shell_artifact_model(workspace_row: Mapping[str, Any] | None, artifact_source: Any | None):
        from src.server.workspace_shell_runtime import _load_workspace_model
        source = resolve_workspace_artifact_source(workspace_row, artifact_source)
        model, loaded = _load_workspace_model(source, workspace_row)
        return source, model, loaded

    @staticmethod
    def _workspace_shell_launch_guard(
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        *,
        expected_path: str,
    ) -> HttpRouteResponse | tuple[str, Mapping[str, Any], Any]:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace shell launch route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if http_request.path.rstrip("/") != expected_path.format(workspace_id=workspace_id):
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_shell_not_found",
                "reason_code": "workspace_shell.workspace_not_found",
                "message": "Requested workspace shell was not found.",
            })
        body = http_request.json_body
        if body is not None and not isinstance(body, Mapping):
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_shell_launch_failure",
                "reason_code": "workspace_shell.invalid_request",
                "message": "Workspace shell launch payload is invalid.",
                "workspace_id": workspace_context.workspace_id,
            })
        return workspace_id, workspace_row, workspace_context


    @classmethod
    def handle_launch_workspace_shell(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[Callable[[EngineRunLaunchRequest], EngineRunLaunchResponse]] = None,
        run_id_factory: Optional[Callable[[], str]] = None,
        run_request_id_factory: Optional[Callable[[], str]] = None,
        now_iso: Optional[str] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_source: Any | None = None,
    ) -> HttpRouteResponse:
        guard = cls._workspace_shell_launch_guard(
            http_request,
            workspace_context,
            workspace_row,
            expected_path="/api/workspaces/{workspace_id}/shell/launch",
        )
        if isinstance(guard, HttpRouteResponse):
            return guard
        workspace_id, workspace_row, workspace_context = guard
        body = http_request.json_body if isinstance(http_request.json_body, Mapping) else {}
        source, model, loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        from src.server.workspace_shell_runtime import _execution_target_for
        target = _execution_target_for(model)
        if target is None:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "workspace_shell_launch_failure",
                "reason_code": "workspace_shell.launch_source_unsupported",
                "message": "Workspace shell launch requires a working_save or commit_snapshot source.",
                "workspace_id": workspace_context.workspace_id,
            })
        launch_options = body.get("launch_options") if isinstance(body.get("launch_options"), Mapping) else {}
        client_context = body.get("client_context") if isinstance(body.get("client_context"), Mapping) else {}
        request_body = {
            "workspace_id": workspace_id,
            "execution_target": target,
            "input_payload": body.get("input_payload") if isinstance(body.get("input_payload"), Mapping) else {},
            "launch_options": {
                "allow_working_save_execution": bool(launch_options.get("allow_working_save_execution", target.get("target_type") == "working_save")),
            },
            "client_context": {
                "source": str(client_context.get("source") or client_context.get("surface") or "workspace_shell"),
                **{k: v for k, v in client_context.items() if k not in {"surface", "source"}},
            },
        }
        source_payload = source if source is not None else (loaded if loaded is not None else model)
        target_catalog = {
            str(target["target_ref"]): ExecutionTargetCatalogEntry(
                workspace_id=workspace_id,
                target_ref=str(target["target_ref"]),
                target_type=str(target["target_type"]),
                source=source_payload,
            )
        }
        delegated = HttpRouteRequest(
            method="POST",
            path="/api/runs",
            headers=dict(http_request.headers),
            path_params={},
            query_params=dict(http_request.query_params),
            json_body=request_body,
            session_claims=http_request.session_claims,
        )
        response = cls.handle_launch(
            http_request=delegated,
            workspace_context=workspace_context,
            target_catalog=target_catalog,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if isinstance(response.body, Mapping):
            body_payload = dict(response.body)
            body_payload["launch_context"] = {
                "action": "launch_workspace_shell",
                "workspace_id": workspace_context.workspace_id,
                "storage_role": target["target_type"],
                "target_ref": target["target_ref"],
            }
            body_payload["identity_policy"] = _run_launch_identity_policy_body()
            body_payload["namespace_policy"] = _run_launch_namespace_policy_body()
            return _route_response(response.status_code, body_payload)
        return response


    @classmethod
    def handle_commit_workspace_shell(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        share_payload_rows_provider=None,
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        feedback_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        guard = cls._workspace_shell_write_guard(http_request, workspace_context, workspace_row, expected_path="/api/workspaces/{workspace_id}/shell/commit", method_label="Workspace shell commit")
        if isinstance(guard, HttpRouteResponse):
            return guard
        workspace_id, workspace_row, workspace_context = guard
        from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
        from src.storage.serialization import serialize_commit_snapshot
        from src.storage.models.commit_snapshot_model import CommitSnapshotModel
        from src.storage.models.working_save_model import WorkingSaveModel
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.invalid_request", "message": "Workspace shell commit payload is invalid.", "workspace_id": workspace_context.workspace_id})
        commit_id = str(body.get("commit_id") or "").strip()
        if not commit_id:
            return _route_response(400, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.commit_id_required", "message": "Workspace shell commit requires a non-empty commit_id.", "workspace_id": workspace_context.workspace_id})
        parent_commit_id = str(body.get("parent_commit_id") or "").strip() or None
        _source, model, _loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        if isinstance(model, CommitSnapshotModel):
            return _route_response(409, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.already_commit_snapshot", "message": "Workspace shell commit requires a working_save source; current workspace shell already resolves to a commit_snapshot.", "workspace_id": workspace_context.workspace_id})
        if not isinstance(model, WorkingSaveModel):
            return _route_response(409, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.unsupported_source_role", "message": "Workspace shell commit requires a working_save source.", "workspace_id": workspace_context.workspace_id})
        try:
            snapshot = create_commit_snapshot_from_working_save(model, commit_id=commit_id, parent_commit_id=parent_commit_id)
        except Exception as exc:
            return _route_response(409, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.commit_blocked", "message": str(exc), "workspace_id": workspace_context.workspace_id})
        serialized = serialize_commit_snapshot(snapshot)
        persisted_source = workspace_artifact_source_writer(workspace_id, serialized) if workspace_artifact_source_writer is not None else serialized
        payload = build_workspace_shell_runtime_payload(workspace_row=workspace_row, artifact_source=persisted_source, recent_run_rows=recent_run_rows, result_rows_by_run_id=result_rows_by_run_id, onboarding_rows=onboarding_rows, artifact_rows_lookup=artifact_rows_lookup, trace_rows_lookup=trace_rows_lookup, share_payload_rows=tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (), provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, feedback_rows=feedback_rows, app_language_override=_request_app_language(http_request.query_params))
        payload["transition"] = {"action": "commit_workspace_shell", "from_role": "working_save", "to_role": "commit_snapshot", "workspace_id": workspace_context.workspace_id, "commit_id": snapshot.meta.commit_id, "source_working_save_id": snapshot.meta.source_working_save_id}
        payload["identity_policy"] = _workspace_shell_identity_policy_body()
        payload["namespace_policy"] = _workspace_shell_namespace_policy_body()
        return _route_response(200, payload)

    @classmethod
    def handle_checkout_workspace_shell(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        public_share_payload_provider=None,
        share_payload_rows_provider=None,
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        feedback_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        guard = cls._workspace_shell_write_guard(http_request, workspace_context, workspace_row, expected_path="/api/workspaces/{workspace_id}/shell/checkout", method_label="Workspace shell checkout")
        if isinstance(guard, HttpRouteResponse):
            return guard
        workspace_id, workspace_row, workspace_context = guard
        from src.storage.lifecycle_api import create_working_save_from_commit_snapshot
        from src.storage.serialization import serialize_working_save
        from src.storage.models.commit_snapshot_model import CommitSnapshotModel
        body = http_request.json_body
        if body is not None and not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.invalid_request", "message": "Workspace shell checkout payload is invalid.", "workspace_id": workspace_context.workspace_id})
        working_save_id = str((body or {}).get("working_save_id") or "").strip() or None
        source_share_id = str((body or {}).get("share_id") or "").strip() or None
        if source_share_id:
            share_payload, _descriptor, error = _resolve_public_share_payload(source_share_id, public_share_payload_provider)
            if error is not None:
                status_code = 404 if error.status_code == 404 else 409
                error_body = dict(error.body)
                error_body.setdefault("workspace_id", workspace_context.workspace_id)
                error_body["error_family"] = "workspace_shell_write_failure"
                error_body["reason_code"] = "workspace_shell.share_not_found" if status_code == 404 else "workspace_shell.invalid_share_payload"
                error_body["message"] = "Workspace shell checkout could not resolve the requested public share." if status_code == 404 else "Workspace shell checkout rejected the requested public share payload."
                return _route_response(status_code, error_body)
            assert share_payload is not None
            try:
                ensure_public_nex_link_share_operation_allowed(share_payload, "checkout_working_copy")
            except ValueError as exc:
                return _route_response(409, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.share_operation_not_allowed", "message": str(exc), "workspace_id": workspace_context.workspace_id, "share_id": source_share_id})
            from src.storage.validators.shared_validator import load_nex
            loaded_share = load_nex(share_payload["artifact"])
            model = loaded_share.parsed_model
        else:
            _source, model, _loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        if not isinstance(model, CommitSnapshotModel):
            return _route_response(409, {"status": "rejected", "error_family": "workspace_shell_write_failure", "reason_code": "workspace_shell.checkout_requires_commit_snapshot", "message": "Workspace shell checkout requires a commit_snapshot source.", "workspace_id": workspace_context.workspace_id})
        working_save = create_working_save_from_commit_snapshot(model, working_save_id=working_save_id)
        serialized = serialize_working_save(working_save)
        persisted_source = workspace_artifact_source_writer(workspace_id, serialized) if workspace_artifact_source_writer is not None else serialized
        payload = build_workspace_shell_runtime_payload(workspace_row=workspace_row, artifact_source=persisted_source, recent_run_rows=recent_run_rows, result_rows_by_run_id=result_rows_by_run_id, onboarding_rows=onboarding_rows, artifact_rows_lookup=artifact_rows_lookup, trace_rows_lookup=trace_rows_lookup, share_payload_rows=tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (), provider_binding_rows=provider_binding_rows, managed_secret_rows=managed_secret_rows, provider_probe_rows=provider_probe_rows, feedback_rows=feedback_rows, app_language_override=_request_app_language(http_request.query_params))
        payload["transition"] = {"action": "checkout_workspace_shell", "from_role": "commit_snapshot", "to_role": "working_save", "workspace_id": workspace_context.workspace_id, "commit_id": model.meta.commit_id, "working_save_id": working_save.meta.working_save_id, "source_share_id": source_share_id}
        payload["identity_policy"] = _workspace_shell_identity_policy_body()
        payload["namespace_policy"] = _workspace_shell_namespace_policy_body()
        return _route_response(200, payload)

    @classmethod
    def handle_list_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public shares route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        action_report_rows = tuple(action_report_rows_provider() or ()) if action_report_rows_provider is not None else ()
        query_params = http_request.query_params or {}
        try:
            filters = _issuer_public_share_management_filters(query_params)
            limit, offset = _issuer_public_share_management_pagination(query_params)
            total_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
            governance_summary = summarize_issuer_public_share_governance_for_issuer(
                rows,
                action_report_rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
            )
            summary = summarize_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
                lifecycle_state=filters["lifecycle_state"],
                stored_lifecycle_state=filters["stored_lifecycle_state"],
                storage_role=filters["storage_role"],
                requires_operation=filters["operation"],
                archived=filters["archived"],
            )
            entries = list_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
                lifecycle_state=filters["lifecycle_state"],
                stored_lifecycle_state=filters["stored_lifecycle_state"],
                storage_role=filters["storage_role"],
                requires_operation=filters["operation"],
                archived=filters["archived"],
            )
        except ValueError as exc:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.invalid_management_filter",
                "message": str(exc),
            })
        page_entries, pagination = _apply_issuer_public_share_management_page(entries, limit=limit, offset=offset)
        management_capability_summary = _issuer_share_management_capability_summary_body(entries)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_summary_body(summary),
            "inventory_summary": _issuer_share_management_summary_body(total_summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "shares": [_issuer_share_management_entry_body(entry) for entry in page_entries],
            "applied_filters": filters,
            "pagination": pagination,
            "links": {
                "self": "/api/users/me/public-shares",
                "summary": "/api/users/me/public-shares/summary",
            },
        })

    @classmethod
    def handle_get_issuer_public_share_summary(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share summary route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/summary":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        action_report_rows = tuple(action_report_rows_provider() or ()) if action_report_rows_provider is not None else ()
        query_params = http_request.query_params or {}
        try:
            filters = _issuer_public_share_management_filters(query_params)
            total_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
            governance_summary = summarize_issuer_public_share_governance_for_issuer(
                rows,
                action_report_rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
            )
            summary = summarize_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
                lifecycle_state=filters["lifecycle_state"],
                stored_lifecycle_state=filters["stored_lifecycle_state"],
                storage_role=filters["storage_role"],
                requires_operation=filters["operation"],
                archived=filters["archived"],
            )
            filtered_entries = list_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
                lifecycle_state=filters["lifecycle_state"],
                stored_lifecycle_state=filters["stored_lifecycle_state"],
                storage_role=filters["storage_role"],
                requires_operation=filters["operation"],
                archived=filters["archived"],
            )
        except ValueError as exc:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.invalid_management_filter",
                "message": str(exc),
            })
        management_capability_summary = _issuer_share_management_capability_summary_body(filtered_entries)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_summary_body(summary),
            "inventory_summary": _issuer_share_management_summary_body(total_summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "applied_filters": filters,
            "links": {
                "self": "/api/users/me/public-shares/summary",
                "shares": "/api/users/me/public-shares",
            },
        })

    @classmethod
    def handle_list_issuer_public_share_action_reports(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share action reports route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/action-reports":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        query_params = http_request.query_params or {}
        action = str(query_params.get("action") or "").strip() or None
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        rows = tuple(action_report_rows_provider() or ()) if action_report_rows_provider is not None else ()
        try:
            limit = _parse_non_negative_int_query_param(query_params, "limit")
            offset = _parse_non_negative_int_query_param(query_params, "offset") or 0
            reports = list_issuer_public_share_management_action_reports_for_issuer(rows, request_auth.requested_by_user_ref, action=action, limit=limit, offset=offset)
            summary = summarize_issuer_public_share_management_action_reports_for_issuer(rows, request_auth.requested_by_user_ref, action=action)
            inventory_summary = summarize_issuer_public_share_management_action_reports_for_issuer(rows, request_auth.requested_by_user_ref)
            governance_summary = summarize_issuer_public_share_governance_for_issuer(
                share_rows,
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
            )
            share_entries = list_public_nex_link_shares_for_issuer(share_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
            resolved_limit, resolved_offset = normalize_issuer_public_share_management_action_report_pagination(limit=limit, offset=offset)
        except ValueError as exc:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.invalid_query",
                "message": str(exc),
            })
        filtered_count = summary.total_report_count
        returned_count = len(reports)
        has_more = resolved_offset + returned_count < filtered_count
        management_capability_summary = _issuer_share_management_capability_summary_body(share_entries)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_action_report_summary_body(summary),
            "inventory_summary": _issuer_share_management_action_report_summary_body(inventory_summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_action_report_identity_policy_body(),
            "namespace_policy": _issuer_public_share_action_report_namespace_policy_body(),
            "applied_filters": {"action": action},
            "pagination": {
                "limit": resolved_limit,
                "offset": resolved_offset,
                "returned_count": returned_count,
                "filtered_report_count": filtered_count,
                "has_more": has_more,
                "next_offset": resolved_offset + returned_count if has_more else None,
            },
            "reports": [_issuer_share_management_action_report_entry_body(report) for report in reports],
            "links": {
                "self": "/api/users/me/public-shares/action-reports",
                "summary": "/api/users/me/public-shares/action-reports/summary",
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
            },
        })

    @classmethod
    def handle_get_issuer_public_share_action_report_summary(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share action report summary route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/action-reports/summary":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        query_params = http_request.query_params or {}
        action = str(query_params.get("action") or "").strip() or None
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        rows = tuple(action_report_rows_provider() or ()) if action_report_rows_provider is not None else ()
        try:
            summary = summarize_issuer_public_share_management_action_reports_for_issuer(rows, request_auth.requested_by_user_ref, action=action)
            inventory_summary = summarize_issuer_public_share_management_action_reports_for_issuer(rows, request_auth.requested_by_user_ref)
            governance_summary = summarize_issuer_public_share_governance_for_issuer(
                share_rows,
                rows,
                request_auth.requested_by_user_ref,
                now_iso=now_iso,
            )
            share_entries = list_public_nex_link_shares_for_issuer(share_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        except ValueError as exc:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.invalid_query",
                "message": str(exc),
            })
        management_capability_summary = _issuer_share_management_capability_summary_body(share_entries)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_action_report_summary_body(summary),
            "inventory_summary": _issuer_share_management_action_report_summary_body(inventory_summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_action_report_identity_policy_body(),
            "namespace_policy": _issuer_public_share_action_report_namespace_policy_body(),
            "applied_filters": {"action": action},
            "links": {
                "self": "/api/users/me/public-shares/action-reports/summary",
                "reports": "/api/users/me/public-shares/action-reports",
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
            },
        })

    @classmethod
    def handle_revoke_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share revoke action route only supports POST."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/actions/revoke":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        share_ids, error = _parse_management_share_ids(http_request.json_body)
        if error is not None:
            return error
        assert share_ids is not None
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        before_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        try:
            updated_payloads = revoke_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                share_ids,
                now_iso=now_iso,
                actor_user_ref=request_auth.requested_by_user_ref,
            )
        except ValueError as exc:
            message = str(exc)
            reason_code = "public_share.share_not_found" if "not found or not owned" in message else "public_share.management_action_rejected"
            status_code = 404 if reason_code.endswith("share_not_found") else 409
            return _route_response(status_code, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": reason_code,
                "message": message,
                "issuer_user_ref": request_auth.requested_by_user_ref,
                "requested_share_ids": list(share_ids),
            })
        persisted = tuple(public_share_payload_writer(payload) if public_share_payload_writer is not None else payload for payload in updated_payloads)
        merged_rows = _merge_public_share_rows(rows, persisted)
        summary = summarize_public_nex_link_shares_for_issuer(merged_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        entries = list_public_nex_link_shares_for_issuer(persisted, request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="revoke",
            scope="issuer_bulk",
            created_at=now_iso or summary.latest_updated_at or before_summary.latest_updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=share_ids,
            affected_share_ids=tuple(entry.share_id for entry in entries),
            before_summary=before_summary,
            after_summary=summary,
            actor_user_ref=request_auth.requested_by_user_ref,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows if 'merged_rows' in locals() else refreshed_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        management_capability_summary = _issuer_share_management_capability_summary_body(entries)
        return _route_response(200, {
            "status": "updated",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "action": "revoke",
            "requested_share_ids": list(share_ids),
            "affected_share_count": len(entries),
            "summary": _issuer_share_management_summary_body(summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "shares": [_issuer_share_management_entry_body(entry) for entry in entries],
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "links": {
                "shares": "/api/users/me/public-shares",
                "summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
                "self": "/api/users/me/public-shares/actions/revoke",
            },
        })

    @classmethod
    def handle_extend_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share extend action route only supports POST."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/actions/extend":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        body = http_request.json_body
        share_ids, error = _parse_management_share_ids(body)
        if error is not None:
            return error
        assert share_ids is not None and isinstance(body, Mapping)
        expires_at = str(body.get("expires_at") or "").strip()
        if not expires_at:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.expires_at_missing",
                "message": "Issuer share management extend action requires expires_at.",
                "issuer_user_ref": request_auth.requested_by_user_ref,
                "requested_share_ids": list(share_ids),
            })
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        before_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        try:
            updated_payloads = extend_public_nex_link_shares_for_issuer_expiration(
                rows,
                request_auth.requested_by_user_ref,
                share_ids,
                expires_at=expires_at,
                now_iso=now_iso,
                actor_user_ref=request_auth.requested_by_user_ref,
            )
        except ValueError as exc:
            message = str(exc)
            reason_code = "public_share.share_not_found" if "not found or not owned" in message else "public_share.management_action_rejected"
            status_code = 404 if reason_code.endswith("share_not_found") else 409
            return _route_response(status_code, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": reason_code,
                "message": message,
                "issuer_user_ref": request_auth.requested_by_user_ref,
                "requested_share_ids": list(share_ids),
            })
        persisted = tuple(public_share_payload_writer(payload) if public_share_payload_writer is not None else payload for payload in updated_payloads)
        merged_rows = _merge_public_share_rows(rows, persisted)
        summary = summarize_public_nex_link_shares_for_issuer(merged_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        entries = list_public_nex_link_shares_for_issuer(persisted, request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="extend_expiration",
            scope="issuer_bulk",
            created_at=now_iso or summary.latest_updated_at or before_summary.latest_updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=share_ids,
            affected_share_ids=tuple(entry.share_id for entry in entries),
            before_summary=before_summary,
            after_summary=summary,
            actor_user_ref=request_auth.requested_by_user_ref,
            expires_at=expires_at,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows if 'merged_rows' in locals() else refreshed_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        management_capability_summary = _issuer_share_management_capability_summary_body(entries)
        return _route_response(200, {
            "status": "updated",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "action": "extend_expiration",
            "expires_at": expires_at,
            "requested_share_ids": list(share_ids),
            "affected_share_count": len(entries),
            "summary": _issuer_share_management_summary_body(summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "shares": [_issuer_share_management_entry_body(entry) for entry in entries],
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "links": {
                "shares": "/api/users/me/public-shares",
                "summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
                "self": "/api/users/me/public-shares/actions/extend",
            },
        })

    @classmethod
    def handle_archive_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share archive action route only supports POST."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/actions/archive":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        share_ids, error = _parse_management_share_ids(http_request.json_body)
        if error is not None:
            return error
        assert share_ids is not None
        body = http_request.json_body if isinstance(http_request.json_body, Mapping) else {}
        archived = bool(body.get("archived", True))
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        before_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        try:
            updated_payloads = archive_public_nex_link_shares_for_issuer(
                rows,
                request_auth.requested_by_user_ref,
                share_ids,
                archived=archived,
                now_iso=now_iso,
                actor_user_ref=request_auth.requested_by_user_ref,
            )
        except ValueError as exc:
            message = str(exc)
            reason_code = "public_share.share_not_found" if "not found or not owned" in message else "public_share.management_action_rejected"
            status_code = 404 if reason_code.endswith("share_not_found") else 409
            return _route_response(status_code, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": reason_code,
                "message": message,
                "issuer_user_ref": request_auth.requested_by_user_ref,
                "requested_share_ids": list(share_ids),
            })
        persisted = tuple(public_share_payload_writer(payload) if public_share_payload_writer is not None else payload for payload in updated_payloads)
        merged_rows = _merge_public_share_rows(rows, persisted)
        summary = summarize_public_nex_link_shares_for_issuer(merged_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        entries = list_public_nex_link_shares_for_issuer(persisted, request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="archive",
            scope="issuer_bulk",
            created_at=now_iso or summary.latest_updated_at or before_summary.latest_updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=share_ids,
            affected_share_ids=tuple(entry.share_id for entry in entries),
            before_summary=before_summary,
            after_summary=summary,
            actor_user_ref=request_auth.requested_by_user_ref,
            archived=archived,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows if 'merged_rows' in locals() else refreshed_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        management_capability_summary = _issuer_share_management_capability_summary_body(entries)
        return _route_response(200, {
            "status": "updated",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "action": "archive",
            "archived": archived,
            "requested_share_ids": list(share_ids),
            "affected_share_count": len(entries),
            "summary": _issuer_share_management_summary_body(summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": management_capability_summary,
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(management_capability_summary),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "shares": [_issuer_share_management_entry_body(entry) for entry in entries],
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "links": {
                "shares": "/api/users/me/public-shares",
                "summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
                "self": "/api/users/me/public-shares/actions/archive",
            },
        })


    @classmethod
    def handle_delete_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_deleter: Callable[[str], bool] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Issuer public share delete route only supports POST."})
        if http_request.path.rstrip("/") != "/api/users/me/public-shares/actions/delete":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Issuer share management routes require an authenticated session.",
            })
        if public_share_payload_deleter is None:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.delete_not_supported",
                "message": "Issuer public share delete requires a persistence deleter.",
            })
        share_ids, error = _parse_management_share_ids(http_request.json_body)
        if error is not None:
            return error
        assert share_ids is not None
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        before_summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        try:
            deleted_entries = delete_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, share_ids, now_iso=now_iso)
        except ValueError as exc:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_management_rejected",
                "reason_code": "public_share.delete_not_allowed",
                "message": str(exc),
            })
        for entry in deleted_entries:
            if public_share_payload_deleter(entry.share_id) is False:
                return _route_response(409, {
                    "status": "rejected",
                    "error_family": "public_share_management_rejected",
                    "reason_code": "public_share.delete_not_persisted",
                    "message": "Issuer public share delete did not persist.",
                    "share_id": entry.share_id,
                })
        refreshed_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        summary = summarize_public_nex_link_shares_for_issuer(refreshed_rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="delete",
            scope="issuer_bulk",
            created_at=now_iso or summary.latest_updated_at or before_summary.latest_updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=share_ids,
            affected_share_ids=tuple(entry.share_id for entry in deleted_entries),
            before_summary=before_summary,
            after_summary=summary,
            actor_user_ref=request_auth.requested_by_user_ref,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows if 'merged_rows' in locals() else refreshed_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        return _route_response(200, {
            "status": "updated",
            "action": "delete",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "requested_share_ids": list(share_ids),
            "affected_share_count": len(deleted_entries),
            "summary": _issuer_share_management_summary_body(summary),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "management_capability_summary": _issuer_share_management_capability_summary_body(deleted_entries),
            "bulk_action_availability": _issuer_share_bulk_action_availability_body(_issuer_share_management_capability_summary_body(deleted_entries)),
            "identity_policy": _issuer_public_share_management_identity_policy_body(),
            "namespace_policy": _issuer_public_share_management_namespace_policy_body(),
            "shares": [_issuer_share_management_entry_body(entry) for entry in deleted_entries],
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "links": {
                "self": "/api/users/me/public-shares/actions/delete",
                "shares": "/api/users/me/public-shares",
                "summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
            },
        })


    @classmethod
    def handle_create_workspace_shell_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        artifact_source: Any | None = None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        guard = cls._workspace_shell_write_guard(
            http_request,
            workspace_context,
            workspace_row,
            expected_path="/api/workspaces/{workspace_id}/shell/share",
            method_label="Workspace shell share creation",
        )
        if isinstance(guard, HttpRouteResponse):
            return guard
        workspace_id, workspace_row, workspace_context = guard
        body = http_request.json_body
        if body is not None and not isinstance(body, Mapping):
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_shell_write_failure",
                "reason_code": "workspace_shell.invalid_request",
                "message": "Workspace shell share payload is invalid.",
                "workspace_id": workspace_context.workspace_id,
            })
        request_auth = _request_auth(http_request)
        _source, model, _loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        lifecycle_created_at = now_iso
        payload = export_public_nex_link_share(
            model,
            share_id=str((body or {}).get("share_id") or "").strip() or None,
            title=str((body or {}).get("title") or "").strip() or None,
            summary=str((body or {}).get("summary") or "").strip() or None,
            expires_at=str((body or {}).get("expires_at") or "").strip() or None,
            created_at=lifecycle_created_at,
            updated_at=lifecycle_created_at,
            issued_by_user_ref=request_auth.requested_by_user_ref,
        )
        persisted = public_share_payload_writer(payload) if public_share_payload_writer is not None else payload
        descriptor = describe_public_nex_link_share(persisted)
        return _route_response(201, {
            "status": "created",
            "workspace_id": workspace_context.workspace_id,
            "share_id": descriptor.share_id,
            "share_path": descriptor.share_path,
            "title": descriptor.title,
            "summary": descriptor.summary,
            "transport": descriptor.transport,
            "access_mode": descriptor.access_mode,
            "viewer_capabilities": list(descriptor.viewer_capabilities),
            "operation_capabilities": list(descriptor.operation_capabilities),
            "capability_summary": _public_share_capability_summary_body(descriptor),
            "action_availability": _public_share_action_availability_body(descriptor),
            "identity": _public_share_identity_body(descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "lifecycle": {
                "stored_state": descriptor.stored_lifecycle_state,
                "state": descriptor.lifecycle_state,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "expires_at": descriptor.expires_at,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": descriptor.archived,
                "archived_at": descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "artifact_format_family": descriptor.artifact_format_family,
                "source_working_save_id": descriptor.source_working_save_id,
            },
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(persisted["artifact"]),
            "links": {
                "self": f"/api/public-shares/{descriptor.share_id}",
                "artifact": f"/api/public-shares/{descriptor.share_id}/artifact",
                "public_share_path": descriptor.share_path,
                "workspace_shell_share": f"/api/workspaces/{workspace_context.workspace_id}/shell/share",
            },
        })

    @classmethod
    def handle_list_public_shares(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method.upper() != "GET" or http_request.path != "/api/public-shares":
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        query_params = dict(http_request.query_params or {})
        search = str(query_params.get("q") or "").strip().lower()
        storage_role = _parse_optional_string_query_param(query_params, "storage_role")
        operation = _parse_optional_string_query_param(query_params, "operation")
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        visible, filtered = _filter_public_share_descriptors(share_rows, search=search, storage_role=storage_role, operation=operation, now_iso=now_iso)
        auth = _request_auth(http_request)
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        saved_lookup = {row["share_id"]: row for row in saved_rows}
        saved_ids = set(saved_lookup)
        entries = [
            _public_share_catalog_entry_body(descriptor, is_saved=descriptor.share_id in saved_ids, saved_at=saved_lookup.get(descriptor.share_id, {}).get("saved_at"))
            for descriptor in filtered
        ]
        return _route_response(200, {
            "status": "ready",
            "returned_count": len(entries),
            "shares": entries,
            "summary": _public_share_catalog_summary_body(filtered, inventory_count=len(visible), saved_ids=saved_ids),
            "inventory_summary": {"inventory_share_count": len(visible)},
            "applied_filters": {"q": search or None, "storage_role": storage_role, "operation": operation},
            "links": {"self": "/api/public-shares", "summary": "/api/public-shares/summary"},
            "identity_policy": _public_share_catalog_identity_policy_body(),
            "namespace_policy": _public_share_catalog_namespace_policy_body(),
        })

    @classmethod
    def handle_get_public_share_catalog_summary(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method.upper() != "GET" or http_request.path != "/api/public-shares/summary":
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        query_params = dict(http_request.query_params or {})
        search = str(query_params.get("q") or "").strip().lower()
        storage_role = _parse_optional_string_query_param(query_params, "storage_role")
        operation = _parse_optional_string_query_param(query_params, "operation")
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        visible, filtered = _filter_public_share_descriptors(share_rows, search=search, storage_role=storage_role, operation=operation, now_iso=now_iso)
        auth = _request_auth(http_request)
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        saved_ids = {row["share_id"] for row in saved_rows}
        return _route_response(200, {
            "status": "ready",
            "summary": _public_share_catalog_summary_body(filtered, inventory_count=len(visible), saved_ids=saved_ids),
            "inventory_summary": {"inventory_share_count": len(visible)},
            "applied_filters": {"q": search or None, "storage_role": storage_role, "operation": operation},
            "links": {"catalog": "/api/public-shares"},
            "identity_policy": _public_share_catalog_identity_policy_body(),
            "namespace_policy": _public_share_catalog_namespace_policy_body(),
        })

    @classmethod
    def handle_list_public_shares_by_issuer(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method.upper() != "GET":
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        issuer_user_ref = str(http_request.path_params.get("issuer_user_ref") or "").strip() if http_request.path_params else ""
        if not issuer_user_ref:
            return _route_response(400, {"status": "error", "reason_code": "public_share.issuer_user_ref_missing"})
        expected_path = f"/api/public-shares/issuers/{issuer_user_ref}"
        if http_request.path != expected_path:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        query_params = dict(http_request.query_params or {})
        search = str(query_params.get("q") or "").strip().lower()
        storage_role = _parse_optional_string_query_param(query_params, "storage_role")
        operation = _parse_optional_string_query_param(query_params, "operation")
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        visible, filtered = _filter_public_share_descriptors(
            share_rows,
            search=search,
            storage_role=storage_role,
            operation=operation,
            issuer_user_ref=issuer_user_ref,
            now_iso=now_iso,
        )
        auth = _request_auth(http_request)
        saved_rows = _normalize_saved_public_share_rows(
            tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (),
            saved_by_user_ref=auth.requested_by_user_ref,
        )
        saved_lookup = {row["share_id"]: row for row in saved_rows}
        saved_ids = set(saved_lookup)
        entries = [
            _public_share_catalog_entry_body(descriptor, is_saved=descriptor.share_id in saved_ids, saved_at=saved_lookup.get(descriptor.share_id, {}).get("saved_at"))
            for descriptor in filtered
        ]
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": issuer_user_ref,
            "returned_count": len(entries),
            "shares": entries,
            "summary": _public_share_catalog_summary_body(filtered, inventory_count=len(visible), saved_ids=saved_ids),
            "inventory_summary": {"inventory_share_count": len(visible)},
            "applied_filters": {"q": search or None, "storage_role": storage_role, "operation": operation},
            "links": {
                "self": f"/api/public-shares/issuers/{issuer_user_ref}",
                "summary": f"/api/public-shares/issuers/{issuer_user_ref}/summary",
                "catalog": "/api/public-shares",
            },
            "identity_policy": _public_share_catalog_identity_policy_body(),
            "namespace_policy": _public_share_catalog_namespace_policy_body(),
        })

    @classmethod
    def handle_get_public_share_issuer_catalog_summary(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method.upper() != "GET":
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        issuer_user_ref = str(http_request.path_params.get("issuer_user_ref") or "").strip() if http_request.path_params else ""
        if not issuer_user_ref:
            return _route_response(400, {"status": "error", "reason_code": "public_share.issuer_user_ref_missing"})
        expected_path = f"/api/public-shares/issuers/{issuer_user_ref}/summary"
        if http_request.path != expected_path:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        query_params = dict(http_request.query_params or {})
        search = str(query_params.get("q") or "").strip().lower()
        storage_role = _parse_optional_string_query_param(query_params, "storage_role")
        operation = _parse_optional_string_query_param(query_params, "operation")
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        visible, filtered = _filter_public_share_descriptors(
            share_rows,
            search=search,
            storage_role=storage_role,
            operation=operation,
            issuer_user_ref=issuer_user_ref,
            now_iso=now_iso,
        )
        auth = _request_auth(http_request)
        saved_rows = _normalize_saved_public_share_rows(
            tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (),
            saved_by_user_ref=auth.requested_by_user_ref,
        )
        saved_ids = {row["share_id"] for row in saved_rows}
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": issuer_user_ref,
            "summary": _public_share_catalog_summary_body(filtered, inventory_count=len(visible), saved_ids=saved_ids),
            "inventory_summary": {"inventory_share_count": len(visible)},
            "applied_filters": {"q": search or None, "storage_role": storage_role, "operation": operation},
            "links": {
                "catalog": f"/api/public-shares/issuers/{issuer_user_ref}",
                "global_catalog": "/api/public-shares",
            },
            "identity_policy": _public_share_catalog_identity_policy_body(),
            "namespace_policy": _public_share_catalog_namespace_policy_body(),
        })

    @classmethod
    def handle_list_saved_public_shares(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_provider: Callable[[str], Mapping[str, Any] | None] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
    ) -> HttpRouteResponse:
        if http_request.method.upper() != "GET" or http_request.path != "/api/users/me/saved-public-shares":
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        auth = _request_auth(http_request)
        if auth.requested_by_user_ref is None:
            return _route_response(401, {
                "status": "rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Authentication is required to list saved public shares.",
            })
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        entries = []
        for row in saved_rows:
            payload = share_payload_provider(row["share_id"]) if share_payload_provider is not None else None
            if payload is None:
                continue
            try:
                descriptor = describe_public_nex_link_share(payload)
            except Exception:
                continue
            if descriptor.archived:
                continue
            entry = _public_share_catalog_entry_body(descriptor, is_saved=True, saved_at=row.get("saved_at"))
            entries.append(entry)
        return _route_response(200, {
            "status": "ready",
            "saved_by_user_ref": auth.requested_by_user_ref,
            "returned_count": len(entries),
            "summary": {"saved_share_count": len(entries)},
            "shares": entries,
            "links": {"catalog": "/api/public-shares"},
            "identity_policy": _saved_public_share_collection_identity_policy_body(),
            "namespace_policy": _saved_public_share_collection_namespace_policy_body(),
        })


    @classmethod
    def handle_save_public_share(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_provider: Callable[[str], Mapping[str, Any] | None] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        share_id = str((http_request.path_params or {}).get("share_id") or "").strip()
        expected_path = f"/api/public-shares/{share_id}/save"
        if http_request.method.upper() != "POST" or http_request.path != expected_path or not share_id:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        auth = _request_auth(http_request)
        if auth.requested_by_user_ref is None:
            return _route_response(401, {
                "status": "rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Authentication is required to save a public share.",
                "share_id": share_id,
            })
        payload = share_payload_provider(share_id) if share_payload_provider is not None else None
        if payload is None:
            return _route_response(404, {"status": "missing", "reason_code": "public_share.not_found", "share_id": share_id})
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        saved_lookup = {row["share_id"]: row for row in saved_rows}
        existing = saved_lookup.get(share_id)
        saved_at = str((existing or {}).get("saved_at") or "").strip() or (now_iso or datetime.now(UTC).isoformat())
        status = "unchanged" if existing is not None else "updated"
        if existing is None and saved_public_share_writer is not None:
            saved_public_share_writer({
                "share_id": share_id,
                "saved_at": saved_at,
                "saved_by_user_ref": auth.requested_by_user_ref,
            })
        response = ProductSavedPublicShareMutationResponse(
            status=status,
            action="save",
            share_id=share_id,
            saved_by_user_ref=auth.requested_by_user_ref,
            saved=True,
            saved_at=saved_at,
            links=ProductPublicShareLinks({
                "detail": f"/api/public-shares/{share_id}",
                "saved_collection": "/api/users/me/saved-public-shares",
                "unsave": f"/api/public-shares/{share_id}/unsave",
            }),
            identity_policy=_saved_public_share_mutation_identity_policy_body(action="save", route_template=expected_path),
            namespace_policy=_saved_public_share_mutation_namespace_policy_body(action="save"),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_unsave_public_share(
        cls,
        http_request: HttpRouteRequest,
        *,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_deleter: Callable[[str], bool] | None = None,
    ) -> HttpRouteResponse:
        share_id = str((http_request.path_params or {}).get("share_id") or "").strip()
        expected_path = f"/api/public-shares/{share_id}/unsave"
        if http_request.method.upper() != "POST" or http_request.path != expected_path or not share_id:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        auth = _request_auth(http_request)
        if auth.requested_by_user_ref is None:
            return _route_response(401, {
                "status": "rejected",
                "reason_code": "public_share.authentication_required",
                "message": "Authentication is required to unsave a public share.",
                "share_id": share_id,
            })
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        saved_lookup = {row["share_id"]: row for row in saved_rows}
        existing = saved_lookup.get(share_id)
        status = "updated" if existing is not None else "unchanged"
        if existing is not None and saved_public_share_deleter is not None:
            saved_public_share_deleter(share_id)
        response = ProductSavedPublicShareMutationResponse(
            status=status,
            action="unsave",
            share_id=share_id,
            saved_by_user_ref=auth.requested_by_user_ref,
            saved=False,
            saved_at=None,
            links=ProductPublicShareLinks({
                "detail": f"/api/public-shares/{share_id}",
                "saved_collection": "/api/users/me/saved-public-shares",
                "save": f"/api/public-shares/{share_id}/save",
            }),
            identity_policy=_saved_public_share_mutation_identity_policy_body(action="unsave", route_template=expected_path),
            namespace_policy=_saved_public_share_mutation_namespace_policy_body(action="unsave"),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_get_related_public_shares(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_provider: Callable[[str], Mapping[str, Any] | None] | None = None,
        share_payload_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        saved_public_share_rows_provider: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        share_id = str((http_request.path_params or {}).get("share_id") or "").strip()
        if http_request.method.upper() != "GET" or http_request.path != f"/api/public-shares/{share_id}/related" or not share_id:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        payload = share_payload_provider(share_id) if share_payload_provider is not None else None
        if payload is None:
            return _route_response(404, {"status": "missing", "reason_code": "public_share.not_found", "share_id": share_id})
        descriptor = describe_public_nex_link_share(payload, now_iso=now_iso)
        limit = _parse_non_negative_int_query_param(http_request.query_params or {}, "limit") or 12
        auth = _request_auth(http_request)
        saved_rows = _normalize_saved_public_share_rows(tuple(saved_public_share_rows_provider() or ()) if saved_public_share_rows_provider is not None else (), saved_by_user_ref=auth.requested_by_user_ref)
        saved_ids = {row["share_id"] for row in saved_rows}
        rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else ()
        shares = list(_related_public_share_entries(descriptor, rows, limit=limit, saved_ids=saved_ids, now_iso=now_iso))
        return _route_response(200, {
            "status": "ready",
            "share_id": share_id,
            "identity": _public_share_identity_body(descriptor),
            "capability_summary": _public_share_capability_summary_body(descriptor),
            "action_availability": _public_share_action_availability_body(descriptor),
            "shares": shares,
            "related_summary": {"limit": limit, "total_related_count": len(shares)},
            "links": {"detail": f"/api/public-shares/{share_id}"},
            "identity_policy": _public_share_related_identity_policy_body(),
            "namespace_policy": _public_share_related_namespace_policy_body(),
        })

    @classmethod
    def handle_get_public_share_compare_summary(
        cls,
        http_request: HttpRouteRequest,
        *,
        share_payload_provider: Callable[[str], Mapping[str, Any] | None] | None = None,
        workspace_row_provider: Callable[[str], Mapping[str, Any] | None] | None = None,
        workspace_artifact_source_provider: Callable[[str], Any | None] | None = None,
    ) -> HttpRouteResponse:
        share_id = str((http_request.path_params or {}).get("share_id") or "").strip()
        if http_request.method.upper() != "GET" or http_request.path != f"/api/public-shares/{share_id}/compare-summary" or not share_id:
            return _route_response(405, {"status": "error", "reason_code": "public_share.unsupported_route"})
        payload = share_payload_provider(share_id) if share_payload_provider is not None else None
        if payload is None:
            return _route_response(404, {"status": "missing", "reason_code": "public_share.not_found", "share_id": share_id})
        descriptor = describe_public_nex_link_share(payload)
        workspace_id = str((http_request.query_params or {}).get("workspace_id") or "").strip() or None
        workspace_artifact = None
        if workspace_id and workspace_row_provider is not None and workspace_artifact_source_provider is not None:
            workspace_row = workspace_row_provider(workspace_id)
            artifact_source = workspace_artifact_source_provider(workspace_id)
            workspace_artifact = _workspace_artifact_mapping(workspace_row, artifact_source) if workspace_row is not None else None
        compare = _public_share_compare_summary_body(payload.get("artifact") if isinstance(payload, Mapping) else None, workspace_artifact, workspace_id=workspace_id)
        return _route_response(200, {
            "status": "ready",
            "share_id": share_id,
            "identity": _public_share_identity_body(descriptor),
            "capability_summary": _public_share_capability_summary_body(descriptor),
            "action_availability": _public_share_action_availability_body(descriptor),
            "compare": compare,
            "links": {"detail": f"/api/public-shares/{share_id}", "artifact": f"/api/public-shares/{share_id}/artifact"},
            "identity_policy": _public_share_compare_identity_policy_body(),
            "namespace_policy": _public_share_compare_namespace_policy_body(),
        })

    @classmethod
    def handle_get_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share route only supports GET."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        return _route_response(200, {
            "status": "ready",
            "share_id": descriptor.share_id,
            "share_path": descriptor.share_path,
            "title": descriptor.title,
            "summary": descriptor.summary,
            "transport": descriptor.transport,
            "access_mode": descriptor.access_mode,
            "viewer_capabilities": list(descriptor.viewer_capabilities),
            "operation_capabilities": list(descriptor.operation_capabilities),
            "capability_summary": _public_share_capability_summary_body(descriptor),
            "action_availability": _public_share_action_availability_body(descriptor),
            "identity": _public_share_identity_body(descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "lifecycle": {
                "stored_state": descriptor.stored_lifecycle_state,
                "state": descriptor.lifecycle_state,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "expires_at": descriptor.expires_at,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": descriptor.archived,
                "archived_at": descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(payload),
            "source_artifact": {
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "artifact_format_family": descriptor.artifact_format_family,
                "source_working_save_id": descriptor.source_working_save_id,
            },
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(payload["artifact"]),
            "links": {
                "self": expected_path,
                "history": f"{expected_path}/history",
                "artifact": f"{expected_path}/artifact",
                "public_share_path": descriptor.share_path,
                "archive": f"/api/public-shares/{descriptor.share_id}/archive",
            },
        })

    @classmethod
    def handle_get_public_share_history(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share history route only supports GET."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/history"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        history = list_public_nex_link_share_audit_history(payload)
        return _route_response(200, {
            "status": "ready",
            "share_id": descriptor.share_id,
            "share_path": descriptor.share_path,
            "audit_summary": _share_audit_summary(payload),
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(payload["artifact"]),
            "identity": _public_share_identity_body(descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "history": list(history),
            "links": {
                "share": f"/api/public-shares/{descriptor.share_id}",
                "artifact": f"/api/public-shares/{descriptor.share_id}/artifact",
                "public_share_path": descriptor.share_path,
            },
        })

    @classmethod
    def handle_get_public_share_artifact(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share artifact route only supports GET."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/artifact"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        try:
            ensure_public_nex_link_share_operation_allowed(payload, "download_artifact")
        except ValueError as exc:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_invalid",
                "reason_code": "public_share.download_not_allowed",
                "message": str(exc),
                "share_id": share_id,
            })
        return _route_response(200, {
            "status": "ready",
            "share_id": descriptor.share_id,
            "share_title": descriptor.title,
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(payload["artifact"]),
            "identity": _public_share_identity_body(descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "artifact": payload["artifact"],
            "links": {
                "share": f"/api/public-shares/{descriptor.share_id}",
                "public_share_path": descriptor.share_path,
            },
        })

    @classmethod
    def handle_checkout_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        workspace_run_rows_provider=None,
        workspace_result_rows_provider=None,
        onboarding_rows_provider=None,
        workspace_artifact_source_provider=None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        public_share_payload_provider=None,
        share_payload_rows_provider=None,
        provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        provider_probe_rows_provider=None,
        feedback_rows_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share checkout route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/checkout"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.invalid_request", "message": "Public share checkout payload is invalid.", "share_id": share_id})
        workspace_id = str(body.get("workspace_id") or "").strip()
        if not workspace_id:
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_id_required", "message": "Public share checkout requires a workspace_id.", "share_id": share_id})
        working_save_id = str(body.get("working_save_id") or "").strip()
        workspace_context = workspace_context_provider(workspace_id) if workspace_context_provider is not None else None
        workspace_row = workspace_row_provider(workspace_id) if workspace_row_provider is not None else None
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_not_found", "message": "Requested workspace was not found.", "share_id": share_id, "workspace_id": workspace_id})
        delegate_body: dict[str, Any] = {"share_id": share_id}
        if working_save_id:
            delegate_body["working_save_id"] = working_save_id
        delegate_request = HttpRouteRequest(
            method="POST",
            path=f"/api/workspaces/{workspace_id}/shell/checkout",
            headers=http_request.headers,
            json_body=delegate_body,
            path_params={"workspace_id": workspace_id},
            query_params=http_request.query_params,
            session_claims=http_request.session_claims,
        )
        delegate = cls.handle_checkout_workspace_shell(
            http_request=delegate_request,
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=workspace_run_rows_provider(workspace_id) if workspace_run_rows_provider is not None else (),
            result_rows_by_run_id=workspace_result_rows_provider(workspace_id) if workspace_result_rows_provider is not None else None,
            onboarding_rows=onboarding_rows_provider() if onboarding_rows_provider is not None else (),
            artifact_source=workspace_artifact_source_provider(workspace_id) if workspace_artifact_source_provider is not None else None,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            public_share_payload_provider=public_share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows=provider_binding_rows_provider(workspace_id) if provider_binding_rows_provider is not None else (),
            managed_secret_rows=managed_secret_rows_provider() if managed_secret_rows_provider is not None else (),
            provider_probe_rows=provider_probe_rows_provider(workspace_id) if provider_probe_rows_provider is not None else (),
            feedback_rows=feedback_rows_provider() if feedback_rows_provider is not None else (),
        )
        if delegate.status_code != 200:
            return delegate
        payload = dict(delegate.body)
        transition = dict(payload.get("transition") or {})
        target_ref = str(transition.get("working_save_id") or payload.get("working_save_id") or "").strip() or None
        response = ProductPublicShareCheckoutAcceptedResponse(
            status="accepted",
            action="checkout_working_copy",
            share_id=share_id,
            workspace_id=workspace_id,
            storage_role=str(payload.get("storage_role") or "working_save"),
            target_ref=target_ref,
            source_share_id=share_id,
            working_save_id=target_ref,
            transition=transition or None,
            links=ProductPublicShareLinks(_public_share_consumer_action_links(share_id=share_id, workspace_id=workspace_id)),
            identity_policy=_public_share_consumer_action_identity_policy_body(action="checkout_working_copy", route_template=expected_path),
            namespace_policy=_public_share_consumer_action_namespace_policy_body(action="checkout_working_copy"),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_import_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        public_share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share import route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/import"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.invalid_request", "message": "Public share import payload is invalid.", "share_id": share_id})
        workspace_id = str(body.get("workspace_id") or "").strip()
        if not workspace_id:
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_id_required", "message": "Public share import requires a workspace_id.", "share_id": share_id})
        workspace_context = workspace_context_provider(workspace_id) if workspace_context_provider is not None else None
        workspace_row = workspace_row_provider(workspace_id) if workspace_row_provider is not None else None
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_not_found", "message": "Requested workspace was not found.", "share_id": share_id, "workspace_id": workspace_id})
        share_payload, _descriptor, error = _resolve_public_share_payload(share_id, public_share_payload_provider)
        if error is not None:
            return error
        assert share_payload is not None
        from src.storage.serialization import serialize_nex_artifact
        from src.storage.validators.shared_validator import load_nex
        try:
            ensure_public_nex_link_share_operation_allowed(share_payload, "import_copy")
        except ValueError as exc:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.import_not_allowed", "message": str(exc), "share_id": share_id, "workspace_id": workspace_id})
        loaded_share = load_nex(share_payload["artifact"])
        model = loaded_share.parsed_model
        if model is None:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.share_artifact_invalid", "message": "Public share artifact is invalid.", "share_id": share_id, "workspace_id": workspace_id})
        serialized = serialize_nex_artifact(model)
        if workspace_artifact_source_writer is not None:
            workspace_artifact_source_writer(workspace_id, serialized)
        meta = dict(serialized.get("meta") or {})
        target_ref = str(meta.get("working_save_id") or meta.get("commit_id") or "").strip() or None
        response = ProductPublicShareImportAcceptedResponse(
            status="accepted",
            action="import_copy",
            share_id=share_id,
            workspace_id=workspace_id,
            storage_role=str(meta.get("storage_role") or "unknown"),
            target_ref=target_ref,
            source_share_id=share_id,
            links=ProductPublicShareLinks(_public_share_consumer_action_links(share_id=share_id, workspace_id=workspace_id)),
            identity_policy=_public_share_consumer_action_identity_policy_body(action="import_copy", route_template=expected_path),
            namespace_policy=_public_share_consumer_action_namespace_policy_body(action="import_copy"),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_create_workspace_from_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_id_factory: Callable[[], str],
        membership_id_factory: Callable[[], str],
        now_iso: str,
        workspace_rows_provider=None,
        membership_rows_provider=None,
        recent_run_rows_provider=None,
        recent_provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        recent_provider_probe_rows_provider=None,
        onboarding_rows_provider=None,
        workspace_registry_writer: Callable[[Mapping[str, Any], Mapping[str, Any]], Any] | None = None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
        public_share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share create-workspace route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/create-workspace"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.invalid_request", "message": "Public share create-workspace payload is invalid.", "share_id": share_id})
        share_payload, descriptor, error = _resolve_public_share_payload(share_id, public_share_payload_provider)
        if error is not None:
            return error
        assert share_payload is not None and descriptor is not None
        title = str(body.get("title") or "").strip()
        description = str(body.get("description") or "").strip() or None
        create_mode = str(body.get("create_mode") or "").strip()
        working_save_id = str(body.get("working_save_id") or "").strip() or None
        operation_capabilities = set(getattr(descriptor, "operation_capabilities", ()) or ())
        if not create_mode:
            create_mode = "checkout_working_copy" if "checkout_working_copy" in operation_capabilities else "import_copy"
        try:
            ensure_public_nex_link_share_operation_allowed(share_payload, create_mode)
        except ValueError as exc:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_create_not_allowed", "message": str(exc), "share_id": share_id})
        create_request = HttpRouteRequest(
            method="POST",
            path="/api/workspaces",
            headers=http_request.headers,
            json_body={"title": title or str(getattr(descriptor, "title", None) or descriptor.share_path or "Imported public share"), "description": description or (str(getattr(descriptor, "summary", None) or "").strip() or None)},
            path_params={},
            query_params=http_request.query_params,
            session_claims=http_request.session_claims,
        )
        create_response = cls.handle_create_workspace(
            http_request=create_request,
            workspace_id_factory=workspace_id_factory,
            membership_id_factory=membership_id_factory,
            now_iso=now_iso,
            workspace_rows=workspace_rows_provider() if workspace_rows_provider is not None else (),
            membership_rows=membership_rows_provider() if membership_rows_provider is not None else (),
            recent_run_rows=recent_run_rows_provider() if recent_run_rows_provider is not None else (),
            provider_binding_rows=recent_provider_binding_rows_provider() if recent_provider_binding_rows_provider is not None else (),
            managed_secret_rows=managed_secret_rows_provider() if managed_secret_rows_provider is not None else (),
            provider_probe_rows=recent_provider_probe_rows_provider() if recent_provider_probe_rows_provider is not None else (),
            onboarding_rows=onboarding_rows_provider() if onboarding_rows_provider is not None else (),
            workspace_registry_writer=workspace_registry_writer,
        )
        if create_response.status_code != 201:
            return create_response
        created_payload = dict(create_response.body)
        workspace = dict(created_payload.get("workspace") or {})
        created_workspace_id = str(created_payload.get("workspace_id") or workspace.get("workspace_id") or "").strip()
        if not created_workspace_id:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_id_missing", "message": "Created workspace response did not include a workspace id.", "share_id": share_id})
        from src.storage.serialization import serialize_nex_artifact
        from src.storage.validators.shared_validator import load_nex
        loaded_share = load_nex(share_payload["artifact"])
        model = loaded_share.parsed_model
        if model is None:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.share_artifact_invalid", "message": "Public share artifact is invalid.", "share_id": share_id, "workspace_id": created_workspace_id})
        if create_mode == "checkout_working_copy":
            from src.storage.lifecycle_api import create_working_save_from_commit_snapshot
            working_save = create_working_save_from_commit_snapshot(model, working_save_id=working_save_id)
            serialized = serialize_nex_artifact(working_save)
            result_role = "working_save"
            target_ref = str(working_save.meta.working_save_id or "").strip() or None
        else:
            serialized = serialize_nex_artifact(model)
            meta = dict(serialized.get("meta") or {})
            result_role = str(meta.get("storage_role") or "unknown")
            target_ref = str(meta.get("working_save_id") or meta.get("commit_id") or "").strip() or None
        if workspace_artifact_source_writer is not None:
            workspace_artifact_source_writer(created_workspace_id, serialized)
        response = ProductPublicShareCreateWorkspaceAcceptedResponse(
            status="accepted",
            action="create_workspace_from_share",
            share_id=share_id,
            workspace_id=created_workspace_id,
            create_mode=create_mode,
            storage_role=result_role,
            target_ref=target_ref,
            source_share_id=share_id,
            links=ProductPublicShareLinks(_public_share_consumer_action_links(share_id=share_id, workspace_id=created_workspace_id)),
            identity_policy=_public_share_consumer_action_identity_policy_body(action="create_workspace_from_share", route_template=expected_path),
            namespace_policy=_public_share_consumer_action_namespace_policy_body(action="create_workspace_from_share"),
        )
        return _route_response(201, asdict(response))

    @classmethod
    def handle_run_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        target_catalog_provider=None,
        policy: ProductAdmissionPolicy,
        engine_launch_decider: Callable[[EngineRunLaunchRequest], EngineRunLaunchResponse],
        run_id_factory: Callable[[], str],
        run_request_id_factory: Callable[[], str] | None = None,
        now_iso: str | None = None,
        workspace_run_rows_provider=None,
        provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        provider_probe_rows_provider=None,
        onboarding_rows_provider=None,
        public_share_payload_provider=None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share run route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/run"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.invalid_request", "message": "Public share run payload is invalid.", "share_id": share_id})
        workspace_id = str(body.get("workspace_id") or "").strip()
        if not workspace_id:
            return _route_response(400, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_id_required", "message": "Public share run requires a workspace_id.", "share_id": share_id})
        workspace_context = workspace_context_provider(workspace_id) if workspace_context_provider is not None else None
        workspace_row = workspace_row_provider(workspace_id) if workspace_row_provider is not None else None
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.workspace_not_found", "message": "Requested workspace was not found.", "share_id": share_id, "workspace_id": workspace_id})
        share_payload, _descriptor, error = _resolve_public_share_payload(share_id, public_share_payload_provider)
        if error is not None:
            return error
        assert share_payload is not None
        from src.storage.validators.shared_validator import load_nex
        try:
            ensure_public_nex_link_share_operation_allowed(share_payload, "run_artifact")
        except ValueError as exc:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.run_not_allowed", "message": str(exc), "share_id": share_id, "workspace_id": workspace_id})
        input_payload = body.get("input_payload")
        loaded_share = load_nex(share_payload["artifact"])
        model = loaded_share.parsed_model
        if model is None:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.share_artifact_invalid", "message": "Public share artifact is invalid.", "share_id": share_id, "workspace_id": workspace_id})
        storage_role = str(getattr(model.meta, "storage_role", "") or "").strip()
        target_ref = str(getattr(model.meta, "commit_id", "") or getattr(model.meta, "working_save_id", "") or "").strip()
        if not target_ref or storage_role not in {"commit_snapshot", "working_save"}:
            return _route_response(409, {"status": "rejected", "error_family": "public_share_action_rejected", "reason_code": "public_share.share_target_unsupported", "message": "Public share artifact cannot be launched directly.", "share_id": share_id, "workspace_id": workspace_id})
        target_type = "commit_snapshot" if storage_role == "commit_snapshot" else "working_save"
        target_catalog = dict(target_catalog_provider(workspace_id) or {}) if target_catalog_provider is not None else {}
        target_catalog[target_ref] = ExecutionTargetCatalogEntry(
            workspace_id=workspace_id,
            target_ref=target_ref,
            target_type=target_type,
            source=share_payload["artifact"],
        )
        launch_body: dict[str, Any] = {
            "workspace_id": workspace_id,
            "execution_target": {"target_type": target_type, "target_ref": target_ref},
            "client_context": {"source": "public_share_run", "correlation_token": share_id},
        }
        if input_payload is not None:
            launch_body["input_payload"] = input_payload
        if target_type == "working_save":
            launch_body["launch_options"] = {"allow_working_save_execution": True}
        launch_request = HttpRouteRequest(
            method="POST",
            path="/api/runs",
            headers=http_request.headers,
            json_body=launch_body,
            path_params={},
            query_params=http_request.query_params,
            session_claims=http_request.session_claims,
        )
        launch_response = cls.handle_launch(
            http_request=launch_request,
            workspace_context=workspace_context,
            target_catalog=target_catalog,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
            workspace_row=workspace_row,
            recent_run_rows=workspace_run_rows_provider(workspace_id) if workspace_run_rows_provider is not None else (),
            provider_binding_rows=provider_binding_rows_provider(workspace_id) if provider_binding_rows_provider is not None else (),
            managed_secret_rows=managed_secret_rows_provider() if managed_secret_rows_provider is not None else (),
            provider_probe_rows=provider_probe_rows_provider(workspace_id) if provider_probe_rows_provider is not None else (),
            onboarding_rows=onboarding_rows_provider() if onboarding_rows_provider is not None else (),
        )
        if launch_response.status_code != 202:
            return launch_response
        launch_payload = dict(launch_response.body)
        run_id = str(launch_payload.get("run_id") or "").strip()
        response = ProductPublicShareRunAcceptedResponse(
            status="accepted",
            action="run_artifact",
            share_id=share_id,
            workspace_id=workspace_id,
            run_id=run_id,
            target_type=target_type,
            target_ref=target_ref,
            source_share_id=share_id,
            launch_context=dict(launch_payload.get("launch_context") or {}) or None,
            links=ProductPublicShareLinks(_public_share_consumer_action_links(share_id=share_id, workspace_id=workspace_id, run_id=run_id or None)),
            identity_policy=_public_share_consumer_action_identity_policy_body(action="run_artifact", route_template=expected_path),
            namespace_policy=_public_share_consumer_action_namespace_policy_body(action="run_artifact"),
        )
        return _route_response(202, asdict(response))

    @classmethod
    def handle_extend_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share extend route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/extend"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.authentication_required",
                "message": "Public share lifecycle updates require an authenticated session.",
                "share_id": share_id,
            })
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        if not descriptor.issued_by_user_ref:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.management_not_supported",
                "message": "Public share lifecycle management requires issuer metadata.",
                "share_id": share_id,
            })
        if descriptor.issued_by_user_ref != request_auth.requested_by_user_ref:
            return _route_response(403, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.forbidden",
                "message": "Current user is not allowed to update this public share.",
                "share_id": share_id,
            })
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.invalid_request",
                "message": "Public share extend payload is invalid.",
                "share_id": share_id,
            })
        expires_at = str(body.get("expires_at") or "").strip()
        if not expires_at:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.expires_at_missing",
                "message": "Public share extension requires expires_at.",
                "share_id": share_id,
            })
        try:
            extended_payload = extend_public_nex_link_share_expiration(payload, expires_at=expires_at, now_iso=now_iso, actor_user_ref=request_auth.requested_by_user_ref)
        except ValueError as exc:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.transition_not_allowed",
                "message": str(exc),
                "share_id": share_id,
            })
        persisted = public_share_payload_writer(extended_payload) if public_share_payload_writer is not None else extended_payload
        extended_descriptor = describe_public_nex_link_share(persisted, now_iso=now_iso)
        before_summary = summarize_public_nex_link_shares_for_issuer((payload,), request_auth.requested_by_user_ref, now_iso=now_iso)
        after_summary = summarize_public_nex_link_shares_for_issuer((persisted,), request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="extend_expiration",
            scope="single_share",
            created_at=now_iso or extended_descriptor.updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=(share_id,),
            affected_share_ids=(share_id,),
            before_summary=before_summary,
            after_summary=after_summary,
            actor_user_ref=request_auth.requested_by_user_ref,
            expires_at=expires_at,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (payload,)
        merged_rows = _merge_public_share_rows(share_rows, (persisted,))
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        return _route_response(200, {
            "status": "updated",
            "share_id": extended_descriptor.share_id,
            "share_path": extended_descriptor.share_path,
            "title": extended_descriptor.title,
            "summary": extended_descriptor.summary,
            "transport": extended_descriptor.transport,
            "access_mode": extended_descriptor.access_mode,
            "viewer_capabilities": list(extended_descriptor.viewer_capabilities),
            "operation_capabilities": list(extended_descriptor.operation_capabilities),
            "identity": _public_share_identity_body(extended_descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "lifecycle": {
                "stored_state": extended_descriptor.stored_lifecycle_state,
                "state": extended_descriptor.lifecycle_state,
                "created_at": extended_descriptor.created_at,
                "updated_at": extended_descriptor.updated_at,
                "expires_at": extended_descriptor.expires_at,
                "issued_by_user_ref": extended_descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": extended_descriptor.archived,
                "archived_at": extended_descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": extended_descriptor.storage_role,
                "canonical_ref": extended_descriptor.canonical_ref,
                "artifact_format_family": extended_descriptor.artifact_format_family,
                "source_working_save_id": extended_descriptor.source_working_save_id,
            },
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(persisted["artifact"]),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "links": {
                "self": f"/api/public-shares/{extended_descriptor.share_id}",
                "history": f"/api/public-shares/{extended_descriptor.share_id}/history",
                "artifact": f"/api/public-shares/{extended_descriptor.share_id}/artifact",
                "public_share_path": extended_descriptor.share_path,
                "extend": expected_path,
                "archive": f"/api/public-shares/{extended_descriptor.share_id}/archive",
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
            },
        })

    @classmethod
    def handle_revoke_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share revoke route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/revoke"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.authentication_required",
                "message": "Public share lifecycle updates require an authenticated session.",
                "share_id": share_id,
            })
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        if not descriptor.issued_by_user_ref:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.management_not_supported",
                "message": "Public share lifecycle management requires issuer metadata.",
                "share_id": share_id,
            })
        if descriptor.issued_by_user_ref != request_auth.requested_by_user_ref:
            return _route_response(403, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.forbidden",
                "message": "Current user is not allowed to update this public share.",
                "share_id": share_id,
            })
        revoked_payload = revoke_public_nex_link_share(payload, now_iso=now_iso, actor_user_ref=request_auth.requested_by_user_ref)
        persisted = public_share_payload_writer(revoked_payload) if public_share_payload_writer is not None else revoked_payload
        revoked_descriptor = describe_public_nex_link_share(persisted, now_iso=now_iso)
        before_summary = summarize_public_nex_link_shares_for_issuer((payload,), request_auth.requested_by_user_ref, now_iso=now_iso)
        after_summary = summarize_public_nex_link_shares_for_issuer((persisted,), request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="revoke",
            scope="single_share",
            created_at=now_iso or revoked_descriptor.updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=(share_id,),
            affected_share_ids=(share_id,),
            before_summary=before_summary,
            after_summary=after_summary,
            actor_user_ref=request_auth.requested_by_user_ref,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (payload,)
        merged_rows = _merge_public_share_rows(share_rows, (persisted,))
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        return _route_response(200, {
            "status": "updated",
            "share_id": revoked_descriptor.share_id,
            "share_path": revoked_descriptor.share_path,
            "title": revoked_descriptor.title,
            "summary": revoked_descriptor.summary,
            "transport": revoked_descriptor.transport,
            "access_mode": revoked_descriptor.access_mode,
            "viewer_capabilities": list(revoked_descriptor.viewer_capabilities),
            "operation_capabilities": list(revoked_descriptor.operation_capabilities),
            "identity": _public_share_identity_body(revoked_descriptor),
            "lifecycle": {
                "stored_state": revoked_descriptor.stored_lifecycle_state,
                "state": revoked_descriptor.lifecycle_state,
                "created_at": revoked_descriptor.created_at,
                "updated_at": revoked_descriptor.updated_at,
                "expires_at": revoked_descriptor.expires_at,
                "issued_by_user_ref": revoked_descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": revoked_descriptor.archived,
                "archived_at": revoked_descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": revoked_descriptor.storage_role,
                "canonical_ref": revoked_descriptor.canonical_ref,
                "artifact_format_family": revoked_descriptor.artifact_format_family,
                "source_working_save_id": revoked_descriptor.source_working_save_id,
            },
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(persisted["artifact"]),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "links": {
                "self": f"/api/public-shares/{revoked_descriptor.share_id}",
                "history": f"/api/public-shares/{revoked_descriptor.share_id}/history",
                "artifact": f"/api/public-shares/{revoked_descriptor.share_id}/artifact",
                "public_share_path": revoked_descriptor.share_path,
                "revoke": expected_path,
                "archive": f"/api/public-shares/{revoked_descriptor.share_id}/archive",
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
            },
        })

    @classmethod
    def handle_archive_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share archive route only supports POST."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}/archive"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.authentication_required",
                "message": "Public share archive requires an authenticated session.",
                "share_id": share_id,
            })
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        if not descriptor.issued_by_user_ref:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.management_not_supported",
                "message": "Public share archive requires issuer metadata.",
                "share_id": share_id,
            })
        if descriptor.issued_by_user_ref != request_auth.requested_by_user_ref:
            return _route_response(403, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.forbidden",
                "message": "Current user is not allowed to archive this public share.",
                "share_id": share_id,
            })
        body = http_request.json_body if isinstance(http_request.json_body, Mapping) else {}
        archived = bool(body.get("archived", True))
        updated_payload = update_public_nex_link_share_archive(
            payload,
            archived=archived,
            updated_at=now_iso or None,
            now_iso=now_iso,
            actor_user_ref=request_auth.requested_by_user_ref,
        )
        persisted = public_share_payload_writer(updated_payload) if public_share_payload_writer is not None else updated_payload
        updated_descriptor = describe_public_nex_link_share(persisted, now_iso=now_iso)
        before_summary = summarize_public_nex_link_shares_for_issuer((payload,), request_auth.requested_by_user_ref, now_iso=now_iso)
        after_summary = summarize_public_nex_link_shares_for_issuer((persisted,), request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="archive",
            scope="single_share",
            created_at=now_iso or updated_descriptor.updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=(share_id,),
            affected_share_ids=(share_id,),
            before_summary=before_summary,
            after_summary=after_summary,
            actor_user_ref=request_auth.requested_by_user_ref,
            archived=archived,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (payload,)
        merged_rows = _merge_public_share_rows(share_rows, (persisted,))
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            merged_rows,
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        return _route_response(200, {
            "status": "updated",
            "share_id": updated_descriptor.share_id,
            "share_path": updated_descriptor.share_path,
            "title": updated_descriptor.title,
            "summary": updated_descriptor.summary,
            "transport": updated_descriptor.transport,
            "access_mode": updated_descriptor.access_mode,
            "viewer_capabilities": list(updated_descriptor.viewer_capabilities),
            "operation_capabilities": list(updated_descriptor.operation_capabilities),
            "identity": _public_share_identity_body(updated_descriptor),
            "lifecycle": {
                "stored_state": updated_descriptor.stored_lifecycle_state,
                "state": updated_descriptor.lifecycle_state,
                "created_at": updated_descriptor.created_at,
                "updated_at": updated_descriptor.updated_at,
                "expires_at": updated_descriptor.expires_at,
                "issued_by_user_ref": updated_descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": updated_descriptor.archived,
                "archived_at": updated_descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": updated_descriptor.storage_role,
                "canonical_ref": updated_descriptor.canonical_ref,
                "artifact_format_family": updated_descriptor.artifact_format_family,
                "source_working_save_id": updated_descriptor.source_working_save_id,
            },
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(persisted["artifact"]),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "links": {
                "self": f"/api/public-shares/{updated_descriptor.share_id}",
                "history": f"/api/public-shares/{updated_descriptor.share_id}/history",
                "artifact": f"/api/public-shares/{updated_descriptor.share_id}/artifact",
                "public_share_path": updated_descriptor.share_path,
                "archive": expected_path,
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
            },
        })


    @classmethod
    def handle_delete_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        public_share_payload_deleter: Callable[[str], bool] | None = None,
        public_share_action_report_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "DELETE":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public share delete route only supports DELETE."})
        share_id = str(http_request.path_params.get("share_id") or "").strip() if http_request.path_params else ""
        if not share_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.share_id_missing", "message": "Share id path parameter is required."})
        expected_path = f"/api/public-shares/{share_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated or not request_auth.requested_by_user_ref:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.authentication_required",
                "message": "Public share delete requires an authenticated session.",
                "share_id": share_id,
            })
        if public_share_payload_deleter is None:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.delete_not_supported",
                "message": "Public share delete requires a persistence deleter.",
                "share_id": share_id,
            })
        payload, descriptor, error = _resolve_public_share_payload(share_id, share_payload_provider)
        if error is not None:
            return error
        assert payload is not None and descriptor is not None
        if not descriptor.issued_by_user_ref:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.management_not_supported",
                "message": "Public share lifecycle management requires issuer metadata.",
                "share_id": share_id,
            })
        if descriptor.issued_by_user_ref != request_auth.requested_by_user_ref:
            return _route_response(403, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.forbidden",
                "message": "Current user is not allowed to delete this public share.",
                "share_id": share_id,
            })
        if public_share_payload_deleter(share_id) is False:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "public_share_write_failure",
                "reason_code": "public_share.delete_not_persisted",
                "message": "Public share delete did not persist.",
                "share_id": share_id,
            })
        before_summary = summarize_public_nex_link_shares_for_issuer((payload,), request_auth.requested_by_user_ref, now_iso=now_iso)
        after_summary = summarize_public_nex_link_shares_for_issuer((), request_auth.requested_by_user_ref, now_iso=now_iso)
        action_report = _build_public_share_management_action_report(
            issuer_user_ref=request_auth.requested_by_user_ref,
            action="delete",
            scope="single_share",
            created_at=now_iso or descriptor.updated_at or datetime.now(UTC).isoformat(),
            requested_share_ids=(share_id,),
            affected_share_ids=(share_id,),
            before_summary=before_summary,
            after_summary=after_summary,
            actor_user_ref=request_auth.requested_by_user_ref,
        )
        persisted_action_report = public_share_action_report_writer(action_report) if public_share_action_report_writer is not None else action_report
        share_rows = tuple(share_payload_rows_provider() or ()) if share_payload_rows_provider is not None else (payload,)
        remaining_rows = []
        for row in share_rows:
            resolved_payload = load_public_nex_link_share(row)
            resolved_share_id = describe_public_nex_link_share(resolved_payload).share_id
            if resolved_share_id == share_id:
                continue
            remaining_rows.append(resolved_payload)
        governance_rows = _effective_action_report_rows(
            action_report_rows_provider,
            fallback_rows=(persisted_action_report,),
        )
        governance_summary = summarize_issuer_public_share_governance_for_issuer(
            tuple(remaining_rows),
            governance_rows,
            request_auth.requested_by_user_ref,
            now_iso=now_iso,
        )
        return _route_response(200, {
            "status": "deleted",
            "share_id": descriptor.share_id,
            "share_path": descriptor.share_path,
            "title": descriptor.title,
            "summary": descriptor.summary,
            "transport": descriptor.transport,
            "access_mode": descriptor.access_mode,
            "viewer_capabilities": list(descriptor.viewer_capabilities),
            "operation_capabilities": list(descriptor.operation_capabilities),
            "capability_summary": _public_share_capability_summary_body(descriptor),
            "action_availability": _public_share_action_availability_body(descriptor),
            "identity": _public_share_identity_body(descriptor),
            "identity_policy": _public_share_identity_policy_body(),
            "namespace_policy": _public_share_namespace_policy_body(),
            "lifecycle": {
                "stored_state": descriptor.stored_lifecycle_state,
                "state": descriptor.lifecycle_state,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "expires_at": descriptor.expires_at,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
            },
            "management": {
                "archived": descriptor.archived,
                "archived_at": descriptor.archived_at,
            },
            "audit_summary": _share_audit_summary(payload),
            "source_artifact": {
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "artifact_format_family": descriptor.artifact_format_family,
                "source_working_save_id": descriptor.source_working_save_id,
            },
            "share_boundary": _public_share_boundary_body(),
            "artifact_boundary": _public_artifact_boundary_body(payload["artifact"]),
            "action_report": _issuer_share_management_action_report_entry_body(persisted_action_report),
            "governance_summary": _issuer_share_governance_summary_body(governance_summary),
            "links": {
                "shares": "/api/users/me/public-shares",
                "share_summary": "/api/users/me/public-shares/summary",
                "action_reports": "/api/users/me/public-shares/action-reports",
                "action_report_summary": "/api/users/me/public-shares/action-reports/summary",
            },
        })


    @classmethod
    def handle_launch(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: WorkspaceAuthorizationContext,
        target_catalog: Mapping[str, ExecutionTargetCatalogEntry],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[Callable[[EngineRunLaunchRequest], EngineRunLaunchResponse]] = None,
        run_id_factory: Optional[Callable[[], str]] = None,
        run_request_id_factory: Optional[Callable[[], str]] = None,
        now_iso: Optional[str] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Launch route only supports POST."})
        if http_request.path.rstrip("/") != "/api/runs":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            launch_request = cls._parse_launch_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(
                400,
                {
                    "status": "rejected",
                    "error_family": "product_rejection",
                    "reason_code": getattr(exc, "args", ["launch.invalid_request"])[0] or "launch.invalid_request",
                    "message": "Launch request payload is invalid.",
                },
            )

        outcome = RunAdmissionService.admit(
            request=launch_request,
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            target_catalog=target_catalog,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.accepted:
            assert outcome.accepted_response is not None
            accepted_payload = asdict(outcome.accepted_response)
            accepted_payload["identity_policy"] = _run_launch_identity_policy_body()
            accepted_payload["namespace_policy"] = _run_launch_namespace_policy_body()
            return _route_response(202, accepted_payload)
        assert outcome.rejected_response is not None
        rejected = asdict(outcome.rejected_response)
        rejected["identity_policy"] = _run_launch_identity_policy_body()
        rejected["namespace_policy"] = _run_launch_namespace_policy_body()
        if outcome.rejected_response.failure_family == "engine_rejection":
            rejected["status"] = "rejected_by_engine"
            rejected["error_family"] = "engine_launch_rejection"
            return _route_response(409, rejected)
        rejected["error_family"] = outcome.rejected_response.failure_family
        return _route_response(_reason_to_status_code(outcome.rejected_response.reason_code), rejected)

    @classmethod
    def handle_run_status(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        engine_status: Optional[EngineRunStatusSnapshot] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run status route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = RunStatusReadService.read_status(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            engine_status=engine_status,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            payload["identity_policy"] = _run_status_identity_policy_body()
            payload["namespace_policy"] = _run_status_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_run_artifacts(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run artifacts route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/artifacts"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = ArtifactReadService.list_run_artifacts(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            artifact_rows=artifact_rows,
            run_record_row=run_record_row,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("artifacts"), canonical_key="artifact_id", lookup_mode="artifact_id_only")
            payload["identity_policy"] = _run_artifacts_identity_policy_body()
            payload["namespace_policy"] = _run_artifacts_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_artifact_detail(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_row: Optional[Mapping[str, Any]] = None,
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Artifact detail route only supports GET."})
        artifact_id = str(http_request.path_params.get("artifact_id") or "").strip() if http_request.path_params else ""
        if not artifact_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.artifact_id_missing", "message": "Artifact id path parameter is required."})
        expected_path = f"/api/artifacts/{artifact_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = ArtifactReadService.read_artifact(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            artifact_row=artifact_row,
            run_record_row=run_record_row,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_mapping_identity(payload, canonical_key="artifact_id", lookup_mode="artifact_id_only")
            payload["identity_policy"] = _artifact_detail_identity_policy_body()
            payload["namespace_policy"] = _artifact_detail_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_run_trace(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        trace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run trace route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/trace"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        limit = http_request.query_params.get("limit", 100) if http_request.query_params else 100
        cursor = http_request.query_params.get("cursor") if http_request.query_params else None
        outcome = TraceReadService.read_run_trace(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            trace_rows=trace_rows,
            cursor=str(cursor) if cursor is not None else None,
            limit=int(limit),
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("events"), canonical_key="event_id", lookup_mode="event_id_only")
            payload["identity_policy"] = _run_trace_identity_policy_body()
            payload["namespace_policy"] = _run_trace_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))


    @classmethod
    def handle_list_workspaces(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace list route only supports GET."})
        if http_request.path.rstrip("/") != "/api/workspaces":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = WorkspaceRegistryService.list_workspaces(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("workspaces"), canonical_key="workspace_id", lookup_mode="workspace_id_only")
            payload["identity_policy"] = _workspace_registry_identity_policy_body()
            payload["namespace_policy"] = _workspace_registry_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @staticmethod
    def _starter_template_view(spec, *, app_language: str) -> dict[str, Any]:
        category_label = ui_text(
            f"template_gallery.category.{spec.category}",
            app_language=app_language,
            fallback_text=spec.category.replace("_", " "),
        )
        display_name = ui_text(
            f"template_gallery.template.{spec.template_id}.name",
            app_language=app_language,
            fallback_text=spec.display_name,
        )
        summary = ui_text(
            f"template_gallery.template.{spec.template_id}.summary",
            app_language=app_language,
            fallback_text=spec.summary,
        )
        return {
            "template_id": spec.template_id,
            "template_ref": spec.template_ref,
            "lookup_aliases": list(spec.lookup_aliases),
            "identity": {
                "canonical_key": "template_ref",
                "canonical_value": spec.template_ref,
                "legacy_key": "template_id",
                "legacy_value": spec.template_id,
                "lookup_mode": "template_id_or_template_ref",
            },
            "display_name": display_name,
            "category": category_label,
            "category_id": spec.category,
            "summary": summary,
            "designer_request_text": spec.designer_request_text,
            "template_version": spec.template_version,
            "curation_status": spec.curation_status,
            "apply_behavior": spec.apply_behavior,
            "supported_entry_surfaces": list(spec.supported_entry_surfaces),
            "supported_storage_roles": list(spec.supported_storage_roles),
            "provenance": {
                "family": spec.provenance_family,
                "source": spec.provenance_source,
            },
            "compatibility": {
                "family": spec.compatibility_family,
                "supported_storage_roles": list(spec.supported_storage_roles),
                "supported_entry_surfaces": list(spec.supported_entry_surfaces),
                "apply_behavior": spec.apply_behavior,
            },
            "routes": {
                "self": f"/api/templates/starter-circuits/{spec.template_id}",
                "apply": f"/api/workspaces/{{workspace_id}}/starter-templates/{spec.template_id}/apply",
            },
        }

    @classmethod
    def handle_list_starter_circuit_templates(
        cls,
        *,
        http_request: HttpRouteRequest,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Starter template catalog route only supports GET."})
        if http_request.path.rstrip("/") != "/api/templates/starter-circuits":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        app_language = _request_app_language(http_request.query_params)
        templates = [cls._starter_template_view(spec, app_language=app_language) for spec in list_starter_circuit_templates()]
        categories: dict[str, dict[str, Any]] = {}
        for item in templates:
            category_id = str(item.get("category_id") or "").strip()
            if category_id not in categories:
                categories[category_id] = {
                    "category_id": category_id,
                    "display_name": item["category"],
                    "template_count": 0,
                }
            categories[category_id]["template_count"] += 1
        response = ProductStarterTemplateCatalogResponse(
            status="ready",
            catalog={
                "family": "starter-circuit-template-catalog",
                "title": ui_text("template_gallery.title", app_language=app_language, fallback_text="Starter workflows"),
                "subtitle": ui_text("template_gallery.subtitle", app_language=app_language, fallback_text="Choose a starter workflow to begin faster."),
                "template_count": len(templates),
                "category_count": len(categories),
                "identity_policy": _starter_template_identity_policy_body(),
                "namespace_policy": _starter_template_namespace_policy_body(),
            },
            categories=tuple(categories.values()),
            templates=tuple(templates),
            app_language=app_language,
            routes={
                "self": "/api/templates/starter-circuits",
                "workspace_library": "/api/workspaces/library",
                "app_catalog": f"/app/templates/starter-circuits?app_language={app_language}",
                "app_library": f"/app/library?app_language={app_language}",
            },
            identity_policy=_starter_template_identity_policy_body(),
            namespace_policy=_starter_template_namespace_policy_body(),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_get_starter_circuit_template(
        cls,
        *,
        http_request: HttpRouteRequest,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Starter template detail route only supports GET."})
        template_id = str(http_request.path_params.get("template_id") or "").strip() if http_request.path_params else ""
        if not template_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.template_id_missing", "message": "Template id path parameter is required."})
        expected_path = f"/api/templates/starter-circuits/{template_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            spec = get_starter_circuit_template(template_id)
        except KeyError:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "starter_template_read_failure",
                "reason_code": "starter_template.not_found",
                "message": "Requested starter template was not found.",
                "template_id": template_id,
            })
        app_language = _request_app_language(http_request.query_params)
        template = cls._starter_template_view(spec, app_language=app_language)
        response = ProductStarterTemplateDetailResponse(
            status="ready",
            template=template,
            app_language=app_language,
            routes={
                "self": expected_path,
                "catalog": "/api/templates/starter-circuits",
                "workspace_library": "/api/workspaces/library",
            },
            identity_policy=_starter_template_identity_policy_body(),
            namespace_policy=_starter_template_namespace_policy_body(),
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_apply_starter_circuit_template(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        artifact_source: Any | None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer: Callable[[str, Any], Any] | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Starter template apply route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        template_id = str(http_request.path_params.get("template_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not template_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.template_id_missing", "message": "Template id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/starter-templates/{template_id}/apply"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            spec = get_starter_circuit_template(template_id)
        except KeyError:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "starter_template_write_failure",
                "reason_code": "starter_template.not_found",
                "message": "Requested starter template was not found.",
                "workspace_id": workspace_id,
                "template_id": template_id,
            })
        guard = cls._workspace_shell_write_guard(http_request, workspace_context, workspace_row, expected_path=expected_path, method_label="Starter template apply")
        if isinstance(guard, HttpRouteResponse):
            return guard
        workspace_id, workspace_row, workspace_context = guard
        current_source, model, _loaded = cls._load_workspace_shell_artifact_model(workspace_row, artifact_source)
        current_storage_role = str(getattr(model.meta, "storage_role", None) or "").strip()
        if current_storage_role != "working_save":
            return _route_response(409, {
                "status": "rejected",
                "error_family": "starter_template_write_failure",
                "reason_code": "starter_template.draft_requires_working_save",
                "message": "Applying a starter template requires a working_save workspace shell source.",
                "workspace_id": workspace_id,
                "template_id": template_id,
            })
        if not spec.supports_storage_role(current_storage_role):
            return _route_response(409, {
                "status": "rejected",
                "error_family": "starter_template_write_failure",
                "reason_code": "starter_template.storage_role_not_supported",
                "message": "Requested starter template does not support the current workspace storage role.",
                "workspace_id": workspace_id,
                "template_id": template_id,
                "storage_role": current_storage_role,
            })
        updated_source = _apply_workspace_shell_draft_patch(
            current_source,
            {
                "request_text": spec.designer_request_text,
                "template_id": spec.template_id,
                "template_ref": spec.template_ref,
                "template_version": spec.template_version,
                "template_display_name": spec.display_name,
                "template_category": spec.category,
                "template_provenance_family": spec.provenance_family,
                "template_provenance_source": spec.provenance_source,
                "template_curation_status": spec.curation_status,
                "template_compatibility_family": spec.compatibility_family,
                "template_apply_behavior": spec.apply_behavior,
                "template_lookup_aliases": list(spec.lookup_aliases),
                "designer_action": "apply_template",
            },
        )
        try:
            persisted_source = workspace_artifact_source_writer(workspace_id, updated_source) if workspace_artifact_source_writer is not None else updated_source
        except ValueError as exc:
            return _route_response(409, {
                "status": "rejected",
                "error_family": "starter_template_write_failure",
                "reason_code": "starter_template.apply_invalid",
                "message": str(exc),
                "workspace_id": workspace_id,
                "template_id": template_id,
            })
        payload = build_workspace_shell_runtime_payload(
            workspace_row=workspace_row,
            artifact_source=persisted_source,
            recent_run_rows=recent_run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=onboarding_rows,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            app_language_override=_request_app_language(http_request.query_params),
        )
        app_language = _request_app_language(http_request.query_params)
        response = ProductStarterTemplateApplyAcceptedResponse(
            status="accepted",
            workspace_id=workspace_id,
            template=cls._starter_template_view(spec, app_language=app_language),
            shell=payload,
            routes={
                "self": expected_path,
                "workspace_shell": f"/api/workspaces/{workspace_id}/shell",
                "catalog": "/api/templates/starter-circuits",
            },
            identity_policy=_starter_template_identity_policy_body(),
            namespace_policy=_starter_template_namespace_policy_body(),
        )
        return _route_response(200, asdict(response))


    @classmethod
    def handle_circuit_library(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Circuit library route only supports GET."})
        if http_request.path.rstrip("/") != "/api/workspaces/library":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "circuit_library_read_failure",
                "reason_code": "circuit_library.authentication_required",
                "message": "Circuit library requires an authenticated session.",
            })

        payload = build_circuit_library_payload(
            request_auth=request_auth,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            app_language=_request_app_language(http_request.query_params),
        )
        if payload is None:
            return _route_response(403, {
                "status": "rejected",
                "error_family": "circuit_library_read_failure",
                "reason_code": "circuit_library.forbidden",
                "message": "Current user is not allowed to read the circuit library.",
            })
        library = payload.get("library")
        if isinstance(library, dict):
            _inject_collection_identity(library.get("items"), canonical_key="workspace_id", lookup_mode="workspace_id_only")
        _inject_collection_identity(payload.get("item_sections"), canonical_key="workspace_id", lookup_mode="workspace_id_only")
        payload["identity_policy"] = _circuit_library_identity_policy_body()
        payload["namespace_policy"] = _circuit_library_namespace_policy_body()
        return _route_response(200, payload)


    @classmethod
    def handle_public_mcp_manifest(
        cls,
        *,
        http_request: HttpRouteRequest,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public MCP manifest route only supports GET."})
        if http_request.path.rstrip("/") != "/api/integrations/public-mcp/manifest":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        payload = _public_mcp_manifest_body(http_request.query_params)
        response = ProductPublicMcpManifestResponse(
            status="ready",
            manifest=payload,
            identity_policy=_public_mcp_manifest_identity_policy_body(),
            namespace_policy=_public_mcp_manifest_namespace_policy_body(),
            routes={
                "self": "/api/integrations/public-mcp/manifest",
                "host_bridge": "/api/integrations/public-mcp/host-bridge",
                "public_nex_format": "/api/formats/public-nex",
            },
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_public_mcp_host_bridge(
        cls,
        *,
        http_request: HttpRouteRequest,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public MCP host bridge route only supports GET."})
        if http_request.path.rstrip("/") != "/api/integrations/public-mcp/host-bridge":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        payload = _public_mcp_host_bridge_body(http_request.query_params)
        response = ProductPublicMcpHostBridgeResponse(
            status="ready",
            host_bridge=payload,
            identity_policy=_public_mcp_host_bridge_identity_policy_body(),
            namespace_policy=_public_mcp_host_bridge_namespace_policy_body(),
            routes={
                "self": "/api/integrations/public-mcp/host-bridge",
                "manifest": "/api/integrations/public-mcp/manifest",
            },
        )
        return _route_response(200, asdict(response))

    @classmethod
    def handle_public_nex_format(
        cls,
        *,
        http_request: HttpRouteRequest,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Public .nex format route only supports GET."})
        if http_request.path.rstrip("/") != "/api/formats/public-nex":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        payload = _public_nex_format_body()
        response = ProductPublicNexFormatResponse(
            status="ready",
            format_boundary={
                "format_family": payload["format_family"],
                "shared_backbone_sections": tuple(payload["shared_backbone_sections"]),
                "supported_roles": tuple(payload["supported_roles"]),
                "legacy_default_role": payload["legacy_default_role"],
                "artifact_operation_boundaries": tuple(payload["artifact_operation_boundaries"]),
            },
            role_boundaries={
                "working_save": payload["role_boundaries"]["working_save"],
                "commit_snapshot": payload["role_boundaries"]["commit_snapshot"],
            },
            public_sdk_entrypoints=payload["public_sdk_entrypoints"],
            identity_policy=_public_nex_identity_policy_body(),
            namespace_policy=_public_nex_namespace_policy_body(),
            routes=payload["routes"],
        )
        body = asdict(response)
        body["format_boundary"]["artifact_operation_boundaries"] = payload["artifact_operation_boundaries"]
        return _route_response(200, body)


    @classmethod
    def handle_workspace_result_history(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        artifact_rows_lookup=None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace result history route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/result-history"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        request_auth = _request_auth(http_request)
        payload = build_workspace_result_history_payload(
            request_auth=request_auth,
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            run_rows=run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            artifact_rows_lookup=artifact_rows_lookup,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            app_language=_request_app_language(http_request.query_params),
            selected_run_id=str((http_request.query_params or {}).get("run_id") or "").strip() or None,
        )
        if payload is None:
            return _route_response(403 if request_auth.is_authenticated else 401, {
                "status": "rejected",
                "error_family": "result_history_read_failure",
                "reason_code": "result_history.forbidden" if request_auth.is_authenticated else "result_history.authentication_required",
                "message": "Current user is not allowed to read workspace result history." if request_auth.is_authenticated else "Workspace result history requires an authenticated session.",
                "workspace_id": workspace_id,
            })
        result_history = payload.get("result_history")
        if isinstance(result_history, dict):
            _inject_collection_identity(result_history.get("items"), canonical_key="run_id", lookup_mode="run_id_only")
        _inject_collection_identity(payload.get("item_sections"), canonical_key="run_id", lookup_mode="run_id_only")
        selected_result = payload.get("selected_result")
        if isinstance(selected_result, dict):
            _inject_collection_identity([selected_result], canonical_key="run_id", lookup_mode="run_id_only")
        payload["identity_policy"] = _workspace_result_history_identity_policy_body()
        payload["namespace_policy"] = _workspace_result_history_namespace_policy_body()
        return _route_response(200, payload)

    @classmethod
    def handle_workspace_feedback(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace feedback route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/feedback"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "workspace_feedback_read_failure",
                "reason_code": "workspace_feedback.authentication_required",
                "message": "Workspace feedback requires an authenticated session.",
            })
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_feedback_not_found",
                "reason_code": "workspace_feedback.workspace_not_found",
                "message": "Requested workspace feedback context was not found.",
            })
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="read",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return _route_response(_reason_to_status_code(f"workspace_feedback.{decision.reason_code}"), {
                "status": "rejected",
                "error_family": "workspace_feedback_read_failure",
                "reason_code": f"workspace_feedback.{decision.reason_code}",
                "message": "Current user is not allowed to read the requested workspace feedback channel.",
                "workspace_id": workspace_context.workspace_id,
            })
        payload = build_workspace_feedback_payload(
            workspace_id=workspace_context.workspace_id,
            workspace_title=str(workspace_row.get("title") or workspace_context.workspace_id),
            feedback_rows=feedback_rows,
            current_user_id=request_auth.requested_by_user_ref or None,
            prefill_category=str((http_request.query_params or {}).get("category") or "").strip() or None,
            prefill_surface=str((http_request.query_params or {}).get("surface") or "").strip() or None,
            prefill_run_id=str((http_request.query_params or {}).get("run_id") or "").strip() or None,
            prefill_template_id=str((http_request.query_params or {}).get("template_id") or "").strip() or None,
            confirmation_feedback_id=str((http_request.query_params or {}).get("feedback_id") or "").strip() or None,
            app_language=_request_app_language(http_request.query_params),
        )
        channel = payload.get("feedback_channel")
        if isinstance(channel, dict):
            _inject_collection_identity(channel.get("items"), canonical_key="feedback_id", lookup_mode="feedback_id_only")
        payload["identity_policy"] = _workspace_feedback_identity_policy_body()
        payload["namespace_policy"] = _workspace_feedback_namespace_policy_body()
        return _route_response(200, payload)

    @classmethod
    def handle_submit_workspace_feedback(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        feedback_writer: Callable[[Mapping[str, Any]], Any] | None = None,
        feedback_id_factory: Callable[[], str] | None = None,
        now_iso: str | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace feedback submission route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/feedback"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        request_auth = _request_auth(http_request)
        if not request_auth.is_authenticated:
            return _route_response(401, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.authentication_required",
                "message": "Workspace feedback submission requires an authenticated session.",
            })
        if workspace_context is None or workspace_row is None:
            return _route_response(404, {
                "status": "rejected",
                "error_family": "workspace_feedback_not_found",
                "reason_code": "workspace_feedback.workspace_not_found",
                "message": "Requested workspace feedback context was not found.",
            })
        auth_input = AuthorizationInput(
            user_id=request_auth.requested_by_user_ref or "",
            workspace_id=workspace_context.workspace_id,
            requested_action="write",
            role_context=request_auth.authenticated_identity.role_refs if request_auth.authenticated_identity else (),
        )
        decision = AuthorizationGate.authorize_workspace_scope(auth_input, workspace_context)
        if not decision.allowed:
            return _route_response(_reason_to_status_code(f"workspace_feedback.{decision.reason_code}"), {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": f"workspace_feedback.{decision.reason_code}",
                "message": "Current user is not allowed to submit feedback for the requested workspace.",
                "workspace_id": workspace_context.workspace_id,
            })
        body = http_request.json_body
        if not isinstance(body, Mapping):
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.invalid_request",
                "message": "Feedback payload is invalid.",
                "workspace_id": workspace_context.workspace_id,
            })
        category = str(body.get("category") or "").strip().lower()
        surface = str(body.get("surface") or "").strip().lower() or "unknown"
        message = str(body.get("message") or "").strip()
        run_id = str(body.get("run_id") or "").strip() or None
        template_id = str(body.get("template_id") or "").strip() or None
        if surface != "starter_templates":
            template_id = None
        if category not in {"confusing_screen", "friction_note", "bug_report"}:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.category_invalid",
                "message": "Feedback category must be one of confusing_screen, friction_note, or bug_report.",
                "workspace_id": workspace_context.workspace_id,
            })
        if surface not in {"circuit_library", "result_history", "starter_templates", "workspace_shell", "unknown"}:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.surface_invalid",
                "message": "Feedback surface must be recognized before it can be recorded. Allowed values are circuit_library, result_history, starter_templates, workspace_shell, and unknown.",
                "workspace_id": workspace_context.workspace_id,
            })
        if not message:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.message_missing",
                "message": "Feedback message must not be empty.",
                "workspace_id": workspace_context.workspace_id,
            })
        if len(message) > 1000:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.message_too_long",
                "message": "Feedback message must be 1000 characters or fewer.",
                "workspace_id": workspace_context.workspace_id,
            })
        row = {
            "feedback_id": feedback_id_factory() if feedback_id_factory is not None else "feedback-missing-id",
            "user_id": request_auth.requested_by_user_ref or "",
            "workspace_id": workspace_context.workspace_id,
            "workspace_title": str(workspace_row.get("title") or workspace_context.workspace_id),
            "category": category,
            "surface": surface,
            "message": message,
            "run_id": run_id,
            "template_id": template_id,
            "status": "received",
            "created_at": str(now_iso or "").strip() or "1970-01-01T00:00:00+00:00",
        }
        persisted = feedback_writer(row) if feedback_writer is not None else row
        payload = build_feedback_submission_payload(
            row=persisted,
            workspace_title=str(workspace_row.get("title") or workspace_context.workspace_id),
            app_language=_request_app_language(http_request.query_params),
        )
        feedback = payload.get("feedback")
        if isinstance(feedback, dict):
            _inject_collection_identity([feedback], canonical_key="feedback_id", lookup_mode="feedback_id_only")
        payload["identity_policy"] = _workspace_feedback_identity_policy_body()
        payload["namespace_policy"] = _workspace_feedback_namespace_policy_body()
        return _route_response(202, payload)

    @classmethod
    def handle_get_workspace(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace detail route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = WorkspaceRegistryService.read_workspace(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_mapping_identity(payload, canonical_key="workspace_id", lookup_mode="workspace_id_only")
            payload["identity_policy"] = _workspace_registry_identity_policy_body()
            payload["namespace_policy"] = _workspace_registry_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_create_workspace(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_id_factory: Callable[[], str],
        membership_id_factory: Callable[[], str],
        now_iso: str,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_registry_writer: Callable[[Mapping[str, Any], Mapping[str, Any]], Any] | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace create route only supports POST."})
        if http_request.path.rstrip("/") != "/api/workspaces":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            body = http_request.json_body
            if not isinstance(body, Mapping):
                raise ValueError('workspace_write.request_body_invalid')
            create_request = ProductWorkspaceCreateRequest(
                title=str(body.get('title') or ''),
                description=str(body.get('description') or '').strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                'status': 'rejected',
                'error_family': 'product_write_failure',
                'reason_code': getattr(exc, 'args', ['workspace_write.invalid_request'])[0] or 'workspace_write.invalid_request',
                'message': 'Workspace create request payload is invalid.',
            })
        outcome = WorkspaceRegistryService.create_workspace(
            request_auth=_request_auth(http_request),
            request=create_request,
            workspace_id_factory=workspace_id_factory,
            membership_id_factory=membership_id_factory,
            now_iso=now_iso,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            if workspace_registry_writer is not None and outcome.created_workspace_row is not None and outcome.created_membership_row is not None:
                workspace_registry_writer(dict(outcome.created_workspace_row), dict(outcome.created_membership_row))
            payload = asdict(outcome.accepted)
            workspace = payload.get("workspace")
            if isinstance(workspace, dict):
                _inject_mapping_identity(workspace, canonical_key="workspace_id", lookup_mode="workspace_id_only")
                workspace_id = str(workspace.get("workspace_id") or "").strip()
                if workspace_id:
                    payload["workspace_id"] = workspace_id
            payload["identity_policy"] = _workspace_registry_identity_policy_body()
            payload["namespace_policy"] = _workspace_registry_namespace_policy_body()
            return _route_response(201, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_get_onboarding(
        cls,
        *,
        http_request: HttpRouteRequest,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Onboarding route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/onboarding":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        outcome = OnboardingContinuityService.read_onboarding_state(
            request_auth=_request_auth(http_request),
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            workspace_id=workspace_id,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            state = payload.get("state")
            if isinstance(state, dict):
                _inject_mapping_identity(state, canonical_key="onboarding_state_id", lookup_mode="onboarding_state_id_only")
                if "identity" not in state:
                    _inject_mapping_identity(
                        state,
                        canonical_key="continuity_scope",
                        canonical_value=payload.get("continuity_scope"),
                        lookup_mode="continuity_scope_only",
                    )
            payload["identity_policy"] = _workspace_onboarding_identity_policy_body()
            payload["namespace_policy"] = _workspace_onboarding_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_put_onboarding(
        cls,
        *,
        http_request: HttpRouteRequest,
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        onboarding_state_id_factory: Callable[[], str],
        now_iso: str,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_state_writer: Callable[[Mapping[str, Any]], Any] | None = None,
    ) -> HttpRouteResponse:
        if http_request.method != "PUT":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Onboarding write route only supports PUT."})
        if http_request.path.rstrip("/") != "/api/users/me/onboarding":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            body = http_request.json_body
            if not isinstance(body, Mapping):
                raise ValueError('onboarding_write.request_body_invalid')
            write_request = ProductOnboardingWriteRequest(
                workspace_id=str(body.get('workspace_id') or '').strip() or None,
                first_success_achieved=body.get('first_success_achieved'),
                advanced_surfaces_unlocked=body.get('advanced_surfaces_unlocked'),
                dismissed_guidance_state=dict(body.get('dismissed_guidance_state')) if body.get('dismissed_guidance_state') is not None else None,
                current_step=str(body.get('current_step') or '').strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                'status': 'rejected',
                'error_family': 'product_write_failure',
                'reason_code': getattr(exc, 'args', ['onboarding_write.invalid_request'])[0] or 'onboarding_write.invalid_request',
                'message': 'Onboarding continuity request payload is invalid.',
            })
        outcome = OnboardingContinuityService.upsert_onboarding_state(
            request_auth=_request_auth(http_request),
            request=write_request,
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            onboarding_state_id_factory=onboarding_state_id_factory,
            now_iso=now_iso,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            if onboarding_state_writer is not None and outcome.persisted_onboarding_row is not None:
                onboarding_state_writer(dict(outcome.persisted_onboarding_row))
            payload = asdict(outcome.accepted)
            state = payload.get("state")
            if isinstance(state, dict):
                _inject_mapping_identity(state, canonical_key="onboarding_state_id", lookup_mode="onboarding_state_id_only")
                if "identity" not in state:
                    _inject_mapping_identity(
                        state,
                        canonical_key="continuity_scope",
                        canonical_value=payload.get("continuity_scope"),
                        lookup_mode="continuity_scope_only",
                    )
            payload["identity_policy"] = _workspace_onboarding_identity_policy_body()
            payload["namespace_policy"] = _workspace_onboarding_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_recent_activity(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Recent activity route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/activity":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        limit = int(query_params.get('limit', 20))
        cursor = str(query_params.get('cursor') or '').strip() or None
        outcome = RecentActivityService.list_recent_activity(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            workspace_id=workspace_id,
            limit=limit,
            cursor=cursor,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("activities"), canonical_key="activity_id", lookup_mode="activity_id_only")
            payload["identity_policy"] = _recent_activity_identity_policy_body()
            payload["namespace_policy"] = _recent_activity_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_history_summary(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        membership_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "History summary route only supports GET."})
        if http_request.path.rstrip("/") != "/api/users/me/history-summary":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        workspace_id = str(query_params.get('workspace_id') or '').strip() or None
        outcome = RecentActivityService.read_history_summary(
            request_auth=_request_auth(http_request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            workspace_id=workspace_id,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            payload["identity_policy"] = _history_summary_identity_policy_body()
            payload["namespace_policy"] = _history_summary_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @staticmethod
    def _parse_provider_probe_request(http_request: HttpRouteRequest) -> ProductProviderProbeRequest:
        body = http_request.json_body
        if body is None:
            body = {}
        if not isinstance(body, Mapping):
            raise ValueError("provider_probe.request_body_invalid")
        timeout_ms = body.get("timeout_ms")
        return ProductProviderProbeRequest(
            model_ref=str(body.get("model_ref") or "").strip() or None,
            probe_message=str(body.get("probe_message") or "").strip() or None,
            timeout_ms=int(timeout_ms) if timeout_ms is not None else None,
        )

    @classmethod
    def handle_probe_workspace_provider(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        probe_runner: Optional[ProviderProbeRunner] = None,
        probe_event_id_factory: Optional[Callable[[], str]] = None,
        probe_history_writer = None,
        now_iso: Optional[str] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider probe route only supports POST."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            probe_request = cls._parse_provider_probe_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                "error_family": "product_probe_failure",
                "reason_code": getattr(exc, "args", ["provider_probe.invalid_request"])[0] or "provider_probe.invalid_request",
                "message": "Provider probe request payload is invalid.",
                "workspace_id": workspace_id,
                "provider_key": provider_key,
            })
        outcome = ProviderProbeService.probe_workspace_provider(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            request=probe_request,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
            probe_runner=probe_runner,
            probe_event_id_factory=probe_event_id_factory,
            probe_history_writer=probe_history_writer,
            now_iso=now_iso,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            payload["identity_policy"] = _workspace_provider_probe_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_probe_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_provider_health(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider health route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/health"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderHealthService.list_workspace_provider_health(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("providers"), canonical_key="provider_key", lookup_mode="provider_key_only")
            payload["identity_policy"] = _workspace_provider_health_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_health_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_get_workspace_provider_health(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider health detail route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        provider_key = str(http_request.path_params.get("provider_key") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderHealthService.read_workspace_provider_health(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            secret_metadata_reader=secret_metadata_reader,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_mapping_identity(payload.get("health"), canonical_key="provider_key", lookup_mode="workspace_id_and_provider_key")
            payload["identity_policy"] = _workspace_provider_health_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_health_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_provider_probe_history(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        probe_history_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider probe history route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        query_params = dict(http_request.query_params or {})
        limit = int(query_params.get('limit', 20))
        cursor = str(query_params.get('cursor') or '').strip() or None
        outcome = ProviderProbeHistoryService.list_workspace_provider_probe_history(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            probe_history_rows=probe_history_rows,
            limit=limit,
            cursor=cursor,
            workspace_row=workspace_row,
            binding_rows=binding_rows,
            managed_secret_rows=managed_secret_rows,
            recent_run_rows=recent_run_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("items"), canonical_key="probe_event_id", lookup_mode="probe_event_id_only")
            payload["identity_policy"] = _workspace_provider_probe_history_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_probe_history_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_provider_catalog(
        cls,
        *,
        http_request: HttpRouteRequest,
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Provider catalog route only supports GET."})
        if http_request.path.rstrip("/") != "/api/providers/catalog":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderSecretIntegrationService.list_provider_catalog(
            request_auth=_request_auth(http_request),
            provider_catalog_rows=provider_catalog_rows,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_mapping_identity(payload, canonical_key="provider_catalog_family", canonical_value="provider-catalog", lookup_mode="provider_catalog")
            _inject_collection_identity(payload.get("providers"), canonical_key="provider_key", lookup_mode="provider_key_only")
            payload["identity_policy"] = _provider_catalog_identity_policy_body()
            payload["namespace_policy"] = _provider_catalog_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_provider_bindings(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider bindings route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = ProviderSecretIntegrationService.list_workspace_provider_bindings(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("bindings"), canonical_key="binding_id", lookup_mode="binding_id_only")
            payload["identity_policy"] = _workspace_provider_binding_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_binding_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_put_workspace_provider_binding(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        existing_binding_row: Optional[Mapping[str, Any]],
        provider_catalog_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        binding_id_factory: Callable[[], str],
        secret_writer,
        binding_writer=None,
        now_iso: str,
        workspace_row: Optional[Mapping[str, Any]] = None,
        binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "PUT":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace provider binding route only supports PUT."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        provider_key = str(http_request.path_params.get("provider_key") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        if not provider_key:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.provider_key_missing", "message": "Provider key path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/provider-bindings/{provider_key}"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        try:
            write_request = cls._parse_provider_binding_write_request(http_request)
        except Exception as exc:  # noqa: BLE001
            return _route_response(400, {
                "status": "rejected",
                "error_family": "product_write_failure",
                "reason_code": getattr(exc, "args", ["provider_binding_write.invalid_request"])[0] or "provider_binding_write.invalid_request",
                "message": "Provider binding request payload is invalid.",
            })
        outcome = ProviderSecretIntegrationService.upsert_workspace_provider_binding(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            request=write_request,
            existing_binding_row=existing_binding_row,
            provider_catalog_rows=provider_catalog_rows,
            binding_id_factory=binding_id_factory,
            secret_writer=secret_writer,
            now_iso=now_iso,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            if binding_writer is not None and outcome.created_or_updated_binding_row is not None:
                binding_writer(dict(outcome.created_or_updated_binding_row))
            payload = asdict(outcome.accepted)
            _inject_mapping_identity(payload.get("binding"), canonical_key="binding_id", lookup_mode="binding_id_only")
            payload["identity_policy"] = _workspace_provider_binding_identity_policy_body()
            payload["namespace_policy"] = _workspace_provider_binding_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_list_workspace_runs(
        cls,
        *,
        http_request: HttpRouteRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        result_rows_by_run_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Workspace run list route only supports GET."})
        workspace_id = str(http_request.path_params.get("workspace_id") or "").strip() if http_request.path_params else ""
        if not workspace_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.workspace_id_missing", "message": "Workspace id path parameter is required."})
        expected_path = f"/api/workspaces/{workspace_id}/runs"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        query_params = dict(http_request.query_params or {})
        limit = int(query_params.get("limit", 20))
        cursor = query_params.get("cursor")
        status_family = query_params.get("status_family")
        requested_by_user_id = query_params.get("requested_by_user_id")
        outcome = RunListReadService.list_workspace_runs(
            request_auth=_request_auth(http_request),
            workspace_context=workspace_context,
            run_rows=run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            cursor=str(cursor) if cursor is not None else None,
            limit=limit,
            status_family=str(status_family) if status_family is not None else None,
            requested_by_user_id=str(requested_by_user_id) if requested_by_user_id is not None else None,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("runs"), canonical_key="run_id", lookup_mode="run_id_only")
            payload["identity_policy"] = _workspace_run_list_identity_policy_body()
            payload["namespace_policy"] = _workspace_run_list_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def _handle_run_control(
        cls,
        *,
        action: str,
        expected_suffix: str,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        run_record_writer=None,
        now_iso_factory=None,
        queue_job_id_factory=None,
    ) -> HttpRouteResponse:
        if http_request.method != "POST":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": f"Run control route only supports POST for {action}."})
        run_id = str((http_request.path_params or {}).get("run_id") or "").strip()
        if not run_id or http_request.path.rstrip("/") != f"/api/runs/{run_id}/{expected_suffix}":
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = RunControlService.apply_action(
            action=action,
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            run_record_writer=run_record_writer,
            now_iso_factory=now_iso_factory,
            queue_job_id_factory=queue_job_id_factory,
        )
        if outcome.ok:
            assert outcome.accepted is not None
            payload = asdict(outcome.accepted)
            payload["identity_policy"] = _run_control_identity_policy_body()
            payload["namespace_policy"] = _run_control_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))


    @classmethod
    def handle_run_actions(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run actions route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/actions"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})
        outcome = RunActionLogReadService.read_actions(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            _inject_collection_identity(payload.get("actions"), canonical_key="event_id", lookup_mode="event_id_only")
            payload["identity_policy"] = _run_action_log_identity_policy_body()
            payload["namespace_policy"] = _run_action_log_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

    @classmethod
    def handle_retry_run(
        cls,
        **kwargs,
    ) -> HttpRouteResponse:
        return cls._handle_run_control(action="retry", expected_suffix="retry", **kwargs)

    @classmethod
    def handle_force_reset_run(
        cls,
        **kwargs,
    ) -> HttpRouteResponse:
        return cls._handle_run_control(action="force_reset", expected_suffix="force-reset", **kwargs)

    @classmethod
    def handle_mark_run_reviewed(
        cls,
        **kwargs,
    ) -> HttpRouteResponse:
        return cls._handle_run_control(action="mark_reviewed", expected_suffix="mark-reviewed", **kwargs)


    @classmethod
    def handle_run_result(
        cls,
        *,
        http_request: HttpRouteRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        result_row: Optional[Mapping[str, Any]] = None,
        artifact_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_binding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        managed_secret_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        provider_probe_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        onboarding_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
        engine_result: Optional[EngineResultEnvelope] = None,
    ) -> HttpRouteResponse:
        if http_request.method != "GET":
            return _route_response(405, {"error_family": "route_error", "reason_code": "route.method_not_allowed", "message": "Run result route only supports GET."})
        run_id = str(http_request.path_params.get("run_id") or "").strip() if http_request.path_params else ""
        if not run_id:
            return _route_response(400, {"error_family": "route_error", "reason_code": "route.run_id_missing", "message": "Run id path parameter is required."})
        expected_path = f"/api/runs/{run_id}/result"
        if http_request.path.rstrip("/") != expected_path:
            return _route_response(404, {"error_family": "route_error", "reason_code": "route.not_found", "message": "Requested route was not found."})

        outcome = RunResultReadService.read_result(
            request_auth=_request_auth(http_request),
            run_context=run_context,
            run_record_row=run_record_row,
            result_row=result_row,
            artifact_rows=artifact_rows,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            engine_result=engine_result,
        )
        if outcome.ok:
            assert outcome.response is not None
            payload = asdict(outcome.response)
            payload["identity_policy"] = _run_result_identity_policy_body()
            payload["namespace_policy"] = _run_result_namespace_policy_body()
            return _route_response(200, payload)
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))
