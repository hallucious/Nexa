from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence

from src.server.provider_health_api import SecretMetadataReader
from src.server.provider_probe_api import ProviderProbeRunner

from src.server.auth_models import RunAuthorizationContext, WorkspaceAuthorizationContext
from src.server.boundary_models import EngineResultEnvelope, EngineRunLaunchRequest, EngineRunLaunchResponse, EngineRunStatusSnapshot
from src.server.framework_binding_models import FrameworkInboundRequest, FrameworkOutboundResponse, FrameworkRouteDefinition
from src.server.http_route_models import HttpRouteRequest, HttpRouteResponse
from src.server.http_route_surface import RunHttpRouteSurface
from src.server.run_admission_models import ExecutionTargetCatalogEntry, ProductAdmissionPolicy


class FrameworkRouteBindings:
    _ROUTE_DEFINITIONS: tuple[FrameworkRouteDefinition, ...] = (
        FrameworkRouteDefinition(
            route_name="get_recent_activity",
            method="GET",
            path_template="/api/users/me/activity",
            summary="List recent continuity activity for the current user.",
        ),
        FrameworkRouteDefinition(
            route_name="get_history_summary",
            method="GET",
            path_template="/api/users/me/history-summary",
            summary="Read aggregate history summary for the current user.",
        ),
        FrameworkRouteDefinition(
            route_name="list_issuer_public_shares",
            method="GET",
            path_template="/api/users/me/public-shares",
            summary="List bounded public shares issued by the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="get_issuer_public_share_summary",
            method="GET",
            path_template="/api/users/me/public-shares/summary",
            summary="Read bounded public share management summary for the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="list_issuer_public_share_action_reports",
            method="GET",
            path_template="/api/users/me/public-shares/action-reports",
            summary="List bounded public share management action reports for the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="get_issuer_public_share_action_report_summary",
            method="GET",
            path_template="/api/users/me/public-shares/action-reports/summary",
            summary="Read bounded public share management action report summary for the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="revoke_issuer_public_shares",
            method="POST",
            path_template="/api/users/me/public-shares/actions/revoke",
            summary="Revoke bounded public shares issued by the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="extend_issuer_public_shares",
            method="POST",
            path_template="/api/users/me/public-shares/actions/extend",
            summary="Extend bounded public share expirations issued by the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="delete_issuer_public_shares",
            method="POST",
            path_template="/api/users/me/public-shares/actions/delete",
            summary="Delete bounded public shares issued by the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="archive_issuer_public_shares",
            method="POST",
            path_template="/api/users/me/public-shares/actions/archive",
            summary="Archive or unarchive bounded public shares issued by the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="list_workspaces",
            method="GET",
            path_template="/api/workspaces",
            summary="List accessible workspaces.",
        ),
        FrameworkRouteDefinition(
            route_name="get_circuit_library",
            method="GET",
            path_template="/api/workspaces/library",
            summary="Read beginner-facing circuit library surface.",
        ),
        FrameworkRouteDefinition(
            route_name="list_starter_circuit_templates",
            method="GET",
            path_template="/api/templates/starter-circuits",
            summary="Read the public starter-template catalog surface.",
        ),
        FrameworkRouteDefinition(
            route_name="get_starter_circuit_template",
            method="GET",
            path_template="/api/templates/starter-circuits/{template_id}",
            summary="Read one starter template from the public catalog.",
        ),
        FrameworkRouteDefinition(
            route_name="apply_starter_circuit_template",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/starter-templates/{template_id}/apply",
            summary="Apply a starter template to a workspace shell draft.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_nex_format",
            method="GET",
            path_template="/api/formats/public-nex",
            summary="Read the public .nex format boundary and role-aware operation catalog.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_mcp_manifest",
            method="GET",
            path_template="/api/integrations/public-mcp/manifest",
            summary="Read the public MCP manifest export surface.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_mcp_host_bridge",
            method="GET",
            path_template="/api/integrations/public-mcp/host-bridge",
            summary="Read the public MCP host bridge export surface.",
        ),
        FrameworkRouteDefinition(
            route_name="get_workspace_result_history",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/result-history",
            summary="Read beginner-facing workspace result history surface.",
        ),
        FrameworkRouteDefinition(
            route_name="get_workspace_feedback",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/feedback",
            summary="Read beginner-facing workspace feedback channel.",
        ),
        FrameworkRouteDefinition(
            route_name="submit_workspace_feedback",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/feedback",
            summary="Record structured product feedback for a workspace.",
        ),
        FrameworkRouteDefinition(
            route_name="get_workspace",
            method="GET",
            path_template="/api/workspaces/{workspace_id}",
            summary="Read workspace detail.",
        ),
        FrameworkRouteDefinition(
            route_name="create_workspace",
            method="POST",
            path_template="/api/workspaces",
            summary="Create a new workspace continuity record.",
        ),
        FrameworkRouteDefinition(
            route_name="get_provider_catalog",
            method="GET",
            path_template="/api/providers/catalog",
            summary="List managed provider options.",
        ),
        FrameworkRouteDefinition(
            route_name="list_workspace_provider_bindings",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/provider-bindings",
            summary="List workspace managed provider bindings.",
        ),
        FrameworkRouteDefinition(
            route_name="put_workspace_provider_binding",
            method="PUT",
            path_template="/api/workspaces/{workspace_id}/provider-bindings/{provider_key}",
            summary="Create or update a workspace managed provider binding.",
        ),
        FrameworkRouteDefinition(
            route_name="list_workspace_provider_health",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/provider-bindings/health",
            summary="List provider health for a workspace.",
        ),
        FrameworkRouteDefinition(
            route_name="get_workspace_provider_health",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health",
            summary="Read provider health detail for a workspace binding.",
        ),
        FrameworkRouteDefinition(
            route_name="probe_workspace_provider",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe",
            summary="Run a provider connectivity probe for a workspace binding.",
        ),
        FrameworkRouteDefinition(
            route_name="list_provider_probe_history",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history",
            summary="List provider probe history for a workspace binding.",
        ),
        FrameworkRouteDefinition(
            route_name="get_onboarding",
            method="GET",
            path_template="/api/users/me/onboarding",
            summary="Read canonical onboarding continuity.",
        ),
        FrameworkRouteDefinition(
            route_name="put_onboarding",
            method="PUT",
            path_template="/api/users/me/onboarding",
            summary="Update canonical onboarding continuity.",
        ),
        FrameworkRouteDefinition(
            route_name="list_workspace_runs",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/runs",
            summary="List workspace runs with pagination.",
        ),
        FrameworkRouteDefinition(
            route_name="get_workspace_shell",
            method="GET",
            path_template="/api/workspaces/{workspace_id}/shell",
            summary="Read browser-runnable workspace shell projection.",
        ),
        FrameworkRouteDefinition(
            route_name="put_workspace_shell_draft",
            method="PUT",
            path_template="/api/workspaces/{workspace_id}/shell/draft",
            summary="Persist server-backed workspace shell draft state.",
        ),
        FrameworkRouteDefinition(
            route_name="commit_workspace_shell",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/shell/commit",
            summary="Commit the current workspace shell draft into a public commit snapshot.",
        ),
        FrameworkRouteDefinition(
            route_name="checkout_workspace_shell",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/shell/checkout",
            summary="Checkout the current workspace shell commit snapshot into a public working save.",
        ),
        FrameworkRouteDefinition(
            route_name="create_workspace_shell_share",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/shell/share",
            summary="Create a bounded public share from the current workspace shell public artifact.",
        ),
        FrameworkRouteDefinition(
            route_name="launch_workspace_shell",
            method="POST",
            path_template="/api/workspaces/{workspace_id}/shell/launch",
            summary="Launch a run directly from the current workspace shell public artifact.",
        ),
        FrameworkRouteDefinition(
            route_name="list_public_shares",
            method="GET",
            path_template="/api/public-shares",
            summary="List active public shares through the public discovery catalog.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share_catalog_summary",
            method="GET",
            path_template="/api/public-shares/summary",
            summary="Read compact public share discovery catalog summary counts.",
        ),
        FrameworkRouteDefinition(
            route_name="list_public_shares_by_issuer",
            method="GET",
            path_template="/api/public-shares/issuers/{issuer_user_ref}",
            summary="List active public shares published by a specific issuer through the public discovery surface.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share_issuer_catalog_summary",
            method="GET",
            path_template="/api/public-shares/issuers/{issuer_user_ref}/summary",
            summary="Read compact public share catalog summary counts for a specific issuer.",
        ),
        FrameworkRouteDefinition(
            route_name="list_saved_public_shares",
            method="GET",
            path_template="/api/users/me/saved-public-shares",
            summary="List saved public shares for the current authenticated user.",
        ),
        FrameworkRouteDefinition(
            route_name="save_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/save",
            summary="Save a public share into the current authenticated user's saved-share collection.",
        ),
        FrameworkRouteDefinition(
            route_name="unsave_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/unsave",
            summary="Remove a public share from the current authenticated user's saved-share collection.",
        ),
        FrameworkRouteDefinition(
            route_name="get_related_public_shares",
            method="GET",
            path_template="/api/public-shares/{share_id}/related",
            summary="List related public shares for a target public share.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share_compare_summary",
            method="GET",
            path_template="/api/public-shares/{share_id}/compare-summary",
            summary="Read a bounded compare summary between a public share artifact and a workspace artifact.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share",
            method="GET",
            path_template="/api/public-shares/{share_id}",
            summary="Read bounded public share metadata.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share_history",
            method="GET",
            path_template="/api/public-shares/{share_id}/history",
            summary="Read bounded public share lifecycle audit history.",
        ),
        FrameworkRouteDefinition(
            route_name="get_public_share_artifact",
            method="GET",
            path_template="/api/public-shares/{share_id}/artifact",
            summary="Read the canonical public artifact for a bounded public share.",
        ),
        FrameworkRouteDefinition(
            route_name="checkout_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/checkout",
            summary="Restore a public share commit snapshot into an existing workspace as a working copy.",
        ),
        FrameworkRouteDefinition(
            route_name="import_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/import",
            summary="Import a public share artifact into an existing workspace.",
        ),
        FrameworkRouteDefinition(
            route_name="create_workspace_from_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/create-workspace",
            summary="Create a new workspace directly from a public share artifact.",
        ),
        FrameworkRouteDefinition(
            route_name="run_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/run",
            summary="Launch a run directly from a public share artifact in an existing workspace.",
        ),
        FrameworkRouteDefinition(
            route_name="extend_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/extend",
            summary="Extend a bounded public share expiration when requested by the issuing user.",
        ),
        FrameworkRouteDefinition(
            route_name="revoke_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/revoke",
            summary="Revoke a bounded public share when requested by the issuing user.",
        ),
        FrameworkRouteDefinition(
            route_name="archive_public_share",
            method="POST",
            path_template="/api/public-shares/{share_id}/archive",
            summary="Archive or unarchive a bounded public share when requested by the issuing user.",
        ),
        FrameworkRouteDefinition(
            route_name="delete_public_share",
            method="DELETE",
            path_template="/api/public-shares/{share_id}",
            summary="Delete a bounded public share when requested by the issuing user.",
        ),
        FrameworkRouteDefinition(
            route_name="launch_run",
            method="POST",
            path_template="/api/runs",
            summary="Launch a new admitted run.",
        ),
        FrameworkRouteDefinition(
            route_name="get_run_status",
            method="GET",
            path_template="/api/runs/{run_id}",
            summary="Read normalized run status.",
        ),
        FrameworkRouteDefinition(
            route_name="get_run_result",
            method="GET",
            path_template="/api/runs/{run_id}/result",
            summary="Read normalized run result.",
        ),
        FrameworkRouteDefinition(
            route_name="get_run_actions",
            method="GET",
            path_template="/api/runs/{run_id}/actions",
            summary="Read append-only action log for a run.",
        ),
        FrameworkRouteDefinition(
            route_name="retry_run",
            method="POST",
            path_template="/api/runs/{run_id}/retry",
            summary="Retry a failed or retry-pending run.",
        ),
        FrameworkRouteDefinition(
            route_name="force_reset_run",
            method="POST",
            path_template="/api/runs/{run_id}/force-reset",
            summary="Force reset a leased run and require orphan review.",
        ),
        FrameworkRouteDefinition(
            route_name="mark_run_reviewed",
            method="POST",
            path_template="/api/runs/{run_id}/mark-reviewed",
            summary="Clear orphan review requirement for a run.",
        ),
        FrameworkRouteDefinition(
            route_name="list_run_artifacts",
            method="GET",
            path_template="/api/runs/{run_id}/artifacts",
            summary="List artifacts produced by a run.",
        ),
        FrameworkRouteDefinition(
            route_name="get_artifact_detail",
            method="GET",
            path_template="/api/artifacts/{artifact_id}",
            summary="Read artifact detail.",
        ),
        FrameworkRouteDefinition(
            route_name="get_run_trace",
            method="GET",
            path_template="/api/runs/{run_id}/trace",
            summary="Read ordered trace events for a run.",
        ),
    )

    @classmethod
    def route_definitions(cls) -> tuple[FrameworkRouteDefinition, ...]:
        return cls._ROUTE_DEFINITIONS

    @staticmethod
    def to_http_route_request(request: FrameworkInboundRequest) -> HttpRouteRequest:
        headers = {str(key): str(value) for key, value in dict(request.headers or {}).items()}
        path_params = {str(key): value for key, value in dict(request.path_params or {}).items()}
        query_params = {str(key): value for key, value in dict(request.query_params or {}).items()}
        session_claims = dict(request.session_claims) if request.session_claims is not None else None
        return HttpRouteRequest(
            method=request.method,
            path=request.path,
            headers=headers,
            json_body=request.json_body,
            path_params=path_params,
            query_params=query_params,
            session_claims=session_claims,
        )

    @staticmethod
    def to_framework_response(response: HttpRouteResponse) -> FrameworkOutboundResponse:
        headers = {str(key): str(value) for key, value in dict(response.headers).items()}
        if "content-type" not in {key.lower() for key in headers}:
            headers["content-type"] = "application/json"
        return FrameworkOutboundResponse(
            status_code=response.status_code,
            headers=headers,
            body_text=json.dumps(dict(response.body), ensure_ascii=False, sort_keys=True),
            media_type=headers.get("content-type", "application/json"),
        )

    @classmethod
    def handle_recent_activity(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_recent_activity(
            http_request=cls.to_http_route_request(request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_history_summary(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_history_summary(
            http_request=cls.to_http_route_request(request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            onboarding_rows=onboarding_rows,
            run_rows=run_rows,
            provider_probe_rows=provider_probe_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_workspaces(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_workspaces(
            http_request=cls.to_http_route_request(request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_starter_circuit_templates(
        cls,
        *,
        request: FrameworkInboundRequest,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_starter_circuit_templates(
            http_request=cls.to_http_route_request(request),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_starter_circuit_template(
        cls,
        *,
        request: FrameworkInboundRequest,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_starter_circuit_template(
            http_request=cls.to_http_route_request(request),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_apply_starter_circuit_template(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        artifact_source: Any | None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_apply_starter_circuit_template(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            artifact_source=artifact_source,
            recent_run_rows=recent_run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=onboarding_rows,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
        )
        return cls.to_framework_response(response)


    @classmethod
    def handle_circuit_library(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_circuit_library(
            http_request=cls.to_http_route_request(request),
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)


    @classmethod
    def handle_public_mcp_manifest(
        cls,
        *,
        request: FrameworkInboundRequest,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_public_mcp_manifest(
            http_request=cls.to_http_route_request(request),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_public_mcp_host_bridge(
        cls,
        *,
        request: FrameworkInboundRequest,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_public_mcp_host_bridge(
            http_request=cls.to_http_route_request(request),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_public_nex_format(
        cls,
        *,
        request: FrameworkInboundRequest,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_public_nex_format(
            http_request=cls.to_http_route_request(request),
        )
        return cls.to_framework_response(response)


    @classmethod
    def handle_workspace_result_history(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        artifact_rows_lookup=None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_workspace_result_history(
            http_request=cls.to_http_route_request(request),
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
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_workspace_feedback(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_workspace_feedback(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            feedback_rows=feedback_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_submit_workspace_feedback(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        feedback_writer=None,
        feedback_id_factory=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_submit_workspace_feedback(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            feedback_writer=feedback_writer,
            feedback_id_factory=feedback_id_factory,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_workspace(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_workspace(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_create_workspace(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_id_factory,
        membership_id_factory,
        now_iso: str,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_registry_writer=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_create_workspace(
            http_request=cls.to_http_route_request(request),
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
            workspace_registry_writer=workspace_registry_writer,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_provider_catalog(
        cls,
        *,
        request: FrameworkInboundRequest,
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_provider_catalog(
            http_request=cls.to_http_route_request(request),
            provider_catalog_rows=provider_catalog_rows,
            workspace_rows=workspace_rows,
            membership_rows=membership_rows,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_workspace_provider_bindings(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_workspace_provider_bindings(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            binding_rows=binding_rows,
            provider_catalog_rows=provider_catalog_rows,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_put_workspace_provider_binding(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        existing_binding_row: Optional[Mapping[str, Any]],
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        binding_id_factory=None,
        secret_writer=None,
        binding_writer=None,
        now_iso: str,
        workspace_row: Optional[Mapping[str, Any]] = None,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_put_workspace_provider_binding(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            existing_binding_row=existing_binding_row,
            provider_catalog_rows=provider_catalog_rows,
            binding_id_factory=binding_id_factory,
            secret_writer=secret_writer,
            binding_writer=binding_writer,
            now_iso=now_iso,
            workspace_row=workspace_row,
            binding_rows=binding_rows,
            recent_run_rows=recent_run_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)


    @classmethod
    def handle_probe_workspace_provider(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        probe_runner: Optional[ProviderProbeRunner] = None,
        probe_event_id_factory=None,
        probe_history_writer=None,
        now_iso: Optional[str] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_probe_workspace_provider(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            provider_key=provider_key,
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_workspace_provider_health(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_workspace_provider_health(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            binding_rows=tuple(binding_rows),
            provider_catalog_rows=tuple(provider_catalog_rows),
            secret_metadata_reader=secret_metadata_reader,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_workspace_provider_health(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        binding_rows: Sequence[Mapping[str, Any]] = (),
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
        secret_metadata_reader: Optional[SecretMetadataReader] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_workspace_provider_health(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            binding_rows=tuple(binding_rows),
            provider_catalog_rows=tuple(provider_catalog_rows),
            secret_metadata_reader=secret_metadata_reader,
            workspace_row=workspace_row,
            recent_run_rows=tuple(recent_run_rows),
            managed_secret_rows=tuple(managed_secret_rows),
            provider_probe_rows=tuple(provider_probe_rows),
            onboarding_rows=tuple(onboarding_rows),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_provider_probe_history(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        provider_key: str,
        probe_history_rows: Sequence[Mapping[str, Any]] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_provider_probe_history(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            provider_key=provider_key,
            probe_history_rows=tuple(probe_history_rows),
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_onboarding(
        cls,
        *,
        request: FrameworkInboundRequest,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_onboarding(
            http_request=cls.to_http_route_request(request),
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            workspace_rows=tuple(workspace_rows),
            membership_rows=tuple(membership_rows),
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_put_onboarding(
        cls,
        *,
        request: FrameworkInboundRequest,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        workspace_context: Optional[WorkspaceAuthorizationContext] = None,
        onboarding_state_id_factory=None,
        now_iso: str,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_state_writer=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_put_onboarding(
            http_request=cls.to_http_route_request(request),
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
            onboarding_state_id_factory=onboarding_state_id_factory,
            now_iso=now_iso,
            workspace_rows=tuple(workspace_rows),
            membership_rows=tuple(membership_rows),
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_state_writer=onboarding_state_writer,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_workspace_runs(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_workspace_runs(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            run_rows=run_rows,
            result_rows_by_run_id=result_rows_by_run_id,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_workspace_shell(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        share_payload_rows_provider=None,
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_workspace_shell(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=list(recent_run_rows),
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=list(onboarding_rows),
            artifact_source=artifact_source,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_put_workspace_shell_draft(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer=None,
        share_payload_rows_provider=None,
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_put_workspace_shell_draft(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=list(recent_run_rows),
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=list(onboarding_rows),
            artifact_source=artifact_source,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_launch_workspace_shell(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[callable] = None,
        run_id_factory: Optional[callable] = None,
        run_request_id_factory: Optional[callable] = None,
        now_iso: Optional[str] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_source: Any | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_launch_workspace_shell(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
            recent_run_rows=list(recent_run_rows),
            provider_binding_rows=list(provider_binding_rows),
            managed_secret_rows=list(managed_secret_rows),
            provider_probe_rows=list(provider_probe_rows),
            onboarding_rows=list(onboarding_rows),
            artifact_source=artifact_source,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_commit_workspace_shell(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer=None,
        share_payload_rows_provider=None,
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_commit_workspace_shell(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=list(recent_run_rows),
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=list(onboarding_rows),
            artifact_source=artifact_source,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_checkout_workspace_shell(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        result_rows_by_run_id: Mapping[str, Mapping[str, Any]] | None = None,
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_source: Any | None = None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer=None,
        public_share_payload_provider=None,
        share_payload_rows_provider=None,
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        feedback_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_checkout_workspace_shell(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            recent_run_rows=list(recent_run_rows),
            result_rows_by_run_id=result_rows_by_run_id,
            onboarding_rows=list(onboarding_rows),
            artifact_source=artifact_source,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            public_share_payload_provider=public_share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            feedback_rows=feedback_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_issuer_public_shares(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_issuer_public_shares(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=action_report_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_issuer_public_share_summary(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_issuer_public_share_summary(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=action_report_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_issuer_public_share_action_reports(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_issuer_public_share_action_reports(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=action_report_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_issuer_public_share_action_report_summary(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        action_report_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_issuer_public_share_action_report_summary(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=action_report_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_revoke_issuer_public_shares(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_rows_provider=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_revoke_issuer_public_shares(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_extend_issuer_public_shares(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_rows_provider=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_extend_issuer_public_shares(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_archive_issuer_public_shares(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_rows_provider=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_archive_issuer_public_shares(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_delete_issuer_public_shares(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_rows_provider=None,
        public_share_payload_deleter=None,
        public_share_action_report_rows_provider=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_delete_issuer_public_shares(
            http_request=cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            public_share_payload_deleter=public_share_payload_deleter,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_create_workspace_shell_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]],
        artifact_source: Any | None = None,
        public_share_payload_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_create_workspace_shell_share(
            http_request=cls.to_http_route_request(request),
            workspace_context=workspace_context,
            workspace_row=workspace_row,
            artifact_source=artifact_source,
            public_share_payload_writer=public_share_payload_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_public_shares(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_rows_provider=None,
        saved_public_share_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_public_shares(
            cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share_catalog_summary(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_rows_provider=None,
        saved_public_share_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share_catalog_summary(
            cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_public_shares_by_issuer(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_rows_provider=None,
        saved_public_share_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_public_shares_by_issuer(
            cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share_issuer_catalog_summary(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_rows_provider=None,
        saved_public_share_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share_issuer_catalog_summary(
            cls.to_http_route_request(request),
            share_payload_rows_provider=share_payload_rows_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_saved_public_shares(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_provider=None,
        saved_public_share_rows_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_saved_public_shares(
            cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
        )
        return cls.to_framework_response(response)



    @classmethod
    def handle_save_public_share(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_provider=None,
        saved_public_share_rows_provider=None,
        saved_public_share_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_save_public_share(
            cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            saved_public_share_writer=saved_public_share_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_unsave_public_share(
        cls,
        request: FrameworkInboundRequest,
        *,
        saved_public_share_rows_provider=None,
        saved_public_share_deleter=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_unsave_public_share(
            cls.to_http_route_request(request),
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            saved_public_share_deleter=saved_public_share_deleter,
        )
        return cls.to_framework_response(response)
    @classmethod
    def handle_get_related_public_shares(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        saved_public_share_rows_provider=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_related_public_shares(
            cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            saved_public_share_rows_provider=saved_public_share_rows_provider,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share_compare_summary(
        cls,
        request: FrameworkInboundRequest,
        *,
        share_payload_provider=None,
        workspace_row_provider=None,
        workspace_artifact_source_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share_compare_summary(
            cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            workspace_row_provider=workspace_row_provider,
            workspace_artifact_source_provider=workspace_artifact_source_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share_history(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share_history(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_get_public_share_artifact(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_public_share_artifact(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_checkout_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        workspace_run_rows_provider=None,
        workspace_result_rows_provider=None,
        onboarding_rows_provider=None,
        workspace_artifact_source_provider=None,
        artifact_rows_lookup=None,
        trace_rows_lookup=None,
        workspace_artifact_source_writer=None,
        public_share_payload_provider=None,
        share_payload_rows_provider=None,
        provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        provider_probe_rows_provider=None,
        feedback_rows_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_checkout_public_share(
            http_request=cls.to_http_route_request(request),
            workspace_context_provider=workspace_context_provider,
            workspace_row_provider=workspace_row_provider,
            workspace_run_rows_provider=workspace_run_rows_provider,
            workspace_result_rows_provider=workspace_result_rows_provider,
            onboarding_rows_provider=onboarding_rows_provider,
            workspace_artifact_source_provider=workspace_artifact_source_provider,
            artifact_rows_lookup=artifact_rows_lookup,
            trace_rows_lookup=trace_rows_lookup,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            public_share_payload_provider=public_share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            provider_binding_rows_provider=provider_binding_rows_provider,
            managed_secret_rows_provider=managed_secret_rows_provider,
            provider_probe_rows_provider=provider_probe_rows_provider,
            feedback_rows_provider=feedback_rows_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_import_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        workspace_artifact_source_writer=None,
        public_share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_import_public_share(
            http_request=cls.to_http_route_request(request),
            workspace_context_provider=workspace_context_provider,
            workspace_row_provider=workspace_row_provider,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            public_share_payload_provider=public_share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_create_workspace_from_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_id_factory,
        membership_id_factory,
        now_iso: str,
        workspace_rows_provider=None,
        membership_rows_provider=None,
        recent_run_rows_provider=None,
        recent_provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        recent_provider_probe_rows_provider=None,
        onboarding_rows_provider=None,
        workspace_registry_writer=None,
        workspace_artifact_source_writer=None,
        public_share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_create_workspace_from_public_share(
            http_request=cls.to_http_route_request(request),
            workspace_id_factory=workspace_id_factory,
            membership_id_factory=membership_id_factory,
            now_iso=now_iso,
            workspace_rows_provider=workspace_rows_provider,
            membership_rows_provider=membership_rows_provider,
            recent_run_rows_provider=recent_run_rows_provider,
            recent_provider_binding_rows_provider=recent_provider_binding_rows_provider,
            managed_secret_rows_provider=managed_secret_rows_provider,
            recent_provider_probe_rows_provider=recent_provider_probe_rows_provider,
            onboarding_rows_provider=onboarding_rows_provider,
            workspace_registry_writer=workspace_registry_writer,
            workspace_artifact_source_writer=workspace_artifact_source_writer,
            public_share_payload_provider=public_share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_run_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context_provider=None,
        workspace_row_provider=None,
        target_catalog_provider=None,
        policy: ProductAdmissionPolicy,
        engine_launch_decider,
        run_id_factory,
        run_request_id_factory=None,
        now_iso: str | None = None,
        workspace_run_rows_provider=None,
        provider_binding_rows_provider=None,
        managed_secret_rows_provider=None,
        provider_probe_rows_provider=None,
        onboarding_rows_provider=None,
        public_share_payload_provider=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_public_share(
            http_request=cls.to_http_route_request(request),
            workspace_context_provider=workspace_context_provider,
            workspace_row_provider=workspace_row_provider,
            target_catalog_provider=target_catalog_provider,
            policy=policy,
            engine_launch_decider=engine_launch_decider,
            run_id_factory=run_id_factory,
            run_request_id_factory=run_request_id_factory,
            now_iso=now_iso,
            workspace_run_rows_provider=workspace_run_rows_provider,
            provider_binding_rows_provider=provider_binding_rows_provider,
            managed_secret_rows_provider=managed_secret_rows_provider,
            provider_probe_rows_provider=provider_probe_rows_provider,
            onboarding_rows_provider=onboarding_rows_provider,
            public_share_payload_provider=public_share_payload_provider,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_extend_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        public_share_action_report_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_extend_public_share(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_revoke_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        public_share_action_report_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_revoke_public_share(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_archive_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        public_share_action_report_rows_provider=None,
        public_share_payload_writer=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_archive_public_share(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_payload_writer=public_share_payload_writer,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_delete_public_share(
        cls,
        *,
        request: FrameworkInboundRequest,
        share_payload_provider=None,
        share_payload_rows_provider=None,
        public_share_action_report_rows_provider=None,
        public_share_payload_deleter=None,
        public_share_action_report_writer=None,
        now_iso: str | None = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_delete_public_share(
            http_request=cls.to_http_route_request(request),
            share_payload_provider=share_payload_provider,
            share_payload_rows_provider=share_payload_rows_provider,
            action_report_rows_provider=public_share_action_report_rows_provider,
            public_share_payload_deleter=public_share_payload_deleter,
            public_share_action_report_writer=public_share_action_report_writer,
            now_iso=now_iso,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_launch(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: WorkspaceAuthorizationContext,
        target_catalog: Mapping[str, ExecutionTargetCatalogEntry],
        policy: ProductAdmissionPolicy = ProductAdmissionPolicy(),
        engine_launch_decider: Optional[callable] = None,
        run_id_factory: Optional[callable] = None,
        run_request_id_factory: Optional[callable] = None,
        now_iso: Optional[str] = None,
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_launch(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_run_status(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        engine_status: Optional[EngineRunStatusSnapshot] = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_status(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)


    @classmethod
    def handle_run_actions(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_actions(
            http_request=cls.to_http_route_request(request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_retry_run(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_record_writer=None,
        now_iso_factory=None,
        queue_job_id_factory=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_retry_run(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_force_reset_run(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_record_writer=None,
        now_iso_factory=None,
        queue_job_id_factory=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_force_reset_run(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_mark_run_reviewed(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        run_record_writer=None,
        now_iso_factory=None,
        queue_job_id_factory=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_mark_run_reviewed(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)


    @classmethod
    def handle_run_result(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        result_row: Optional[Mapping[str, Any]] = None,
        artifact_rows: Sequence[Mapping[str, Any]] = (),
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        engine_result: Optional[EngineResultEnvelope] = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_result(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_run_artifacts(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_rows: Sequence[Mapping[str, Any]] = (),
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_artifacts(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_artifact_detail(
        cls,
        *,
        request: FrameworkInboundRequest,
        workspace_context: Optional[WorkspaceAuthorizationContext],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        artifact_row: Optional[Mapping[str, Any]] = None,
        run_record_row: Optional[Mapping[str, Any]] = None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_artifact_detail(
            http_request=cls.to_http_route_request(request),
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
        return cls.to_framework_response(response)

    @classmethod
    def handle_run_trace(
        cls,
        *,
        request: FrameworkInboundRequest,
        run_context: Optional[RunAuthorizationContext],
        run_record_row: Optional[Mapping[str, Any]],
        workspace_row: Optional[Mapping[str, Any]] = None,
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
        onboarding_rows: Sequence[Mapping[str, Any]] = (),
        trace_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_run_trace(
            http_request=cls.to_http_route_request(request),
            run_context=run_context,
            run_record_row=run_record_row,
            workspace_row=workspace_row,
            recent_run_rows=recent_run_rows,
            provider_binding_rows=provider_binding_rows,
            managed_secret_rows=managed_secret_rows,
            provider_probe_rows=provider_probe_rows,
            onboarding_rows=onboarding_rows,
            trace_rows=trace_rows,
        )
        return cls.to_framework_response(response)
