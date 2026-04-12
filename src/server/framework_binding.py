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
            route_name="list_workspaces",
            method="GET",
            path_template="/api/workspaces",
            summary="List accessible workspaces.",
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
        workspace_registry_writer=None,
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_create_workspace(
            http_request=cls.to_http_route_request(request),
            workspace_id_factory=workspace_id_factory,
            membership_id_factory=membership_id_factory,
            now_iso=now_iso,
            workspace_registry_writer=workspace_registry_writer,
        )
        return cls.to_framework_response(response)

    @classmethod
    def handle_list_provider_catalog(
        cls,
        *,
        request: FrameworkInboundRequest,
        provider_catalog_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_list_provider_catalog(
            http_request=cls.to_http_route_request(request),
            provider_catalog_rows=provider_catalog_rows,
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
        recent_run_rows: Sequence[Mapping[str, Any]] = (),
        provider_binding_rows: Sequence[Mapping[str, Any]] = (),
        managed_secret_rows: Sequence[Mapping[str, Any]] = (),
        provider_probe_rows: Sequence[Mapping[str, Any]] = (),
    ) -> FrameworkOutboundResponse:
        response = RunHttpRouteSurface.handle_get_onboarding(
            http_request=cls.to_http_route_request(request),
            onboarding_rows=onboarding_rows,
            workspace_context=workspace_context,
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
