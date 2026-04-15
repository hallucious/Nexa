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
from src.server.result_history_runtime import build_workspace_result_history_payload
from src.storage.share_api import (
    describe_public_nex_link_share,
    ensure_public_nex_link_share_operation_allowed,
    export_public_nex_link_share,
    extend_public_nex_link_share_expiration,
    list_public_nex_link_share_audit_history,
    list_public_nex_link_shares_for_issuer,
    load_public_nex_link_share,
    revoke_public_nex_link_share,
    summarize_public_nex_link_shares_for_issuer,
)
from src.ui.i18n import normalize_ui_language


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


def _issuer_share_management_entry_body(entry) -> dict[str, Any]:
    return {
        "share_id": entry.share_id,
        "share_path": entry.share_path,
        "title": entry.title,
        "summary": entry.summary,
        "storage_role": entry.storage_role,
        "canonical_ref": entry.canonical_ref,
        "operation_capabilities": list(entry.operation_capabilities),
        "lifecycle": {
            "stored_state": entry.stored_lifecycle_state,
            "state": entry.lifecycle_state,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "expires_at": entry.expires_at,
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
        "working_save_share_count": summary.working_save_share_count,
        "commit_snapshot_share_count": summary.commit_snapshot_share_count,
        "runnable_share_count": summary.runnable_share_count,
        "checkoutable_share_count": summary.checkoutable_share_count,
        "latest_created_at": summary.latest_created_at,
        "latest_updated_at": summary.latest_updated_at,
        "latest_audit_event_at": summary.latest_audit_event_at,
    }


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
        ("list_workspaces", "GET", "/api/workspaces"),
        ("get_circuit_library", "GET", "/api/workspaces/library"),
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
        ("get_public_share", "GET", "/api/public-shares/{share_id}"),
        ("get_public_share_history", "GET", "/api/public-shares/{share_id}/history"),
        ("get_public_share_artifact", "GET", "/api/public-shares/{share_id}/artifact"),
        ("extend_public_share", "POST", "/api/public-shares/{share_id}/extend"),
        ("revoke_public_share", "POST", "/api/public-shares/{share_id}/revoke"),
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
            app_language_override=_request_app_language(http_request.query_params),
        )
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
            app_language_override=_request_app_language(http_request.query_params),
        )
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
        payload = build_workspace_shell_runtime_payload(workspace_row=workspace_row, artifact_source=persisted_source, recent_run_rows=recent_run_rows, result_rows_by_run_id=result_rows_by_run_id, onboarding_rows=onboarding_rows, artifact_rows_lookup=artifact_rows_lookup, trace_rows_lookup=trace_rows_lookup, app_language_override=_request_app_language(http_request.query_params))
        payload["transition"] = {"action": "commit_workspace_shell", "from_role": "working_save", "to_role": "commit_snapshot", "workspace_id": workspace_context.workspace_id, "commit_id": snapshot.meta.commit_id, "source_working_save_id": snapshot.meta.source_working_save_id}
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
        payload = build_workspace_shell_runtime_payload(workspace_row=workspace_row, artifact_source=persisted_source, recent_run_rows=recent_run_rows, result_rows_by_run_id=result_rows_by_run_id, onboarding_rows=onboarding_rows, artifact_rows_lookup=artifact_rows_lookup, trace_rows_lookup=trace_rows_lookup, app_language_override=_request_app_language(http_request.query_params))
        payload["transition"] = {"action": "checkout_workspace_shell", "from_role": "commit_snapshot", "to_role": "working_save", "workspace_id": workspace_context.workspace_id, "commit_id": model.meta.commit_id, "working_save_id": working_save.meta.working_save_id, "source_share_id": source_share_id}
        return _route_response(200, payload)

    @classmethod
    def handle_list_issuer_public_shares(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_rows_provider=None,
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
        summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        entries = list_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_summary_body(summary),
            "shares": [_issuer_share_management_entry_body(entry) for entry in entries],
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
        summary = summarize_public_nex_link_shares_for_issuer(rows, request_auth.requested_by_user_ref, now_iso=now_iso)
        return _route_response(200, {
            "status": "ready",
            "issuer_user_ref": request_auth.requested_by_user_ref,
            "summary": _issuer_share_management_summary_body(summary),
            "links": {
                "self": "/api/users/me/public-shares/summary",
                "shares": "/api/users/me/public-shares",
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
            "lifecycle": {
                "stored_state": descriptor.stored_lifecycle_state,
                "state": descriptor.lifecycle_state,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "expires_at": descriptor.expires_at,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "artifact_format_family": descriptor.artifact_format_family,
                "source_working_save_id": descriptor.source_working_save_id,
            },
            "links": {
                "self": f"/api/public-shares/{descriptor.share_id}",
                "artifact": f"/api/public-shares/{descriptor.share_id}/artifact",
                "public_share_path": descriptor.share_path,
                "workspace_shell_share": f"/api/workspaces/{workspace_context.workspace_id}/shell/share",
            },
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
            "lifecycle": {
                "stored_state": descriptor.stored_lifecycle_state,
                "state": descriptor.lifecycle_state,
                "created_at": descriptor.created_at,
                "updated_at": descriptor.updated_at,
                "expires_at": descriptor.expires_at,
                "issued_by_user_ref": descriptor.issued_by_user_ref,
            },
            "audit_summary": _share_audit_summary(payload),
            "source_artifact": {
                "storage_role": descriptor.storage_role,
                "canonical_ref": descriptor.canonical_ref,
                "artifact_format_family": descriptor.artifact_format_family,
                "source_working_save_id": descriptor.source_working_save_id,
            },
            "links": {
                "self": expected_path,
                "history": f"{expected_path}/history",
                "artifact": f"{expected_path}/artifact",
                "public_share_path": descriptor.share_path,
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
            "artifact": payload["artifact"],
            "links": {
                "share": f"/api/public-shares/{descriptor.share_id}",
                "public_share_path": descriptor.share_path,
            },
        })

    @classmethod
    def handle_extend_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
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
            "lifecycle": {
                "stored_state": extended_descriptor.stored_lifecycle_state,
                "state": extended_descriptor.lifecycle_state,
                "created_at": extended_descriptor.created_at,
                "updated_at": extended_descriptor.updated_at,
                "expires_at": extended_descriptor.expires_at,
                "issued_by_user_ref": extended_descriptor.issued_by_user_ref,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": extended_descriptor.storage_role,
                "canonical_ref": extended_descriptor.canonical_ref,
                "artifact_format_family": extended_descriptor.artifact_format_family,
                "source_working_save_id": extended_descriptor.source_working_save_id,
            },
            "links": {
                "self": f"/api/public-shares/{extended_descriptor.share_id}",
                "history": f"/api/public-shares/{extended_descriptor.share_id}/history",
                "artifact": f"/api/public-shares/{extended_descriptor.share_id}/artifact",
                "public_share_path": extended_descriptor.share_path,
                "extend": expected_path,
            },
        })

    @classmethod
    def handle_revoke_public_share(
        cls,
        *,
        http_request: HttpRouteRequest,
        share_payload_provider=None,
        public_share_payload_writer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
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
            "lifecycle": {
                "stored_state": revoked_descriptor.stored_lifecycle_state,
                "state": revoked_descriptor.lifecycle_state,
                "created_at": revoked_descriptor.created_at,
                "updated_at": revoked_descriptor.updated_at,
                "expires_at": revoked_descriptor.expires_at,
                "issued_by_user_ref": revoked_descriptor.issued_by_user_ref,
            },
            "audit_summary": _share_audit_summary(persisted),
            "source_artifact": {
                "storage_role": revoked_descriptor.storage_role,
                "canonical_ref": revoked_descriptor.canonical_ref,
                "artifact_format_family": revoked_descriptor.artifact_format_family,
                "source_working_save_id": revoked_descriptor.source_working_save_id,
            },
            "links": {
                "self": f"/api/public-shares/{revoked_descriptor.share_id}",
                "history": f"/api/public-shares/{revoked_descriptor.share_id}/history",
                "artifact": f"/api/public-shares/{revoked_descriptor.share_id}/artifact",
                "public_share_path": revoked_descriptor.share_path,
                "revoke": expected_path,
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
            return _route_response(202, asdict(outcome.accepted_response))
        assert outcome.rejected_response is not None
        rejected = asdict(outcome.rejected_response)
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))

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
        return _route_response(200, payload)

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
            confirmation_feedback_id=str((http_request.query_params or {}).get("feedback_id") or "").strip() or None,
            app_language=_request_app_language(http_request.query_params),
        )
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
        if category not in {"confusing_screen", "friction_note", "bug_report"}:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.category_invalid",
                "message": "Feedback category must be one of confusing_screen, friction_note, or bug_report.",
                "workspace_id": workspace_context.workspace_id,
            })
        if surface not in {"circuit_library", "result_history", "workspace_shell", "unknown"}:
            return _route_response(400, {
                "status": "rejected",
                "error_family": "workspace_feedback_write_failure",
                "reason_code": "workspace_feedback.surface_invalid",
                "message": "Feedback surface must be recognized before it can be recorded.",
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
            "status": "received",
            "created_at": str(now_iso or "").strip() or "1970-01-01T00:00:00+00:00",
        }
        persisted = feedback_writer(row) if feedback_writer is not None else row
        payload = build_feedback_submission_payload(
            row=persisted,
            workspace_title=str(workspace_row.get("title") or workspace_context.workspace_id),
            app_language=_request_app_language(http_request.query_params),
        )
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(201, asdict(outcome.accepted))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.accepted))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.accepted))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.accepted))
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
            return _route_response(200, asdict(outcome.response))
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
            return _route_response(200, asdict(outcome.response))
        assert outcome.rejected is not None
        return _route_response(_reason_to_status_code(outcome.rejected.reason_code), asdict(outcome.rejected))
