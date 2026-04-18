from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from src.server.framework_binding import FrameworkRouteBindings
from src.server.aws_secrets_manager_binding import AwsSecretsManagerSecretAuthority
from src.server.aws_secrets_manager_models import AwsSecretsManagerBindingConfig
from src.server.framework_binding_models import FrameworkInboundRequest, FrameworkOutboundResponse
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.workspace_shell_runtime import render_workspace_shell_runtime_html
from src.server.circuit_library_runtime import render_circuit_library_runtime_html
from src.server.result_history_runtime import render_workspace_result_history_html
from src.server.starter_template_runtime import render_starter_template_catalog_html
from src.server.feedback_runtime import render_workspace_feedback_html


def default_fastapi_session_claims_resolver(
    request: Request,
    *,
    header_name: str = "x-nexa-session-claims",
) -> Optional[Mapping[str, Any]]:
    state_claims = getattr(request.state, "session_claims", None)
    if isinstance(state_claims, Mapping):
        return dict(state_claims)
    header_value = request.headers.get(header_name)
    if not header_value:
        return None
    try:
        parsed = json.loads(header_value)
    except json.JSONDecodeError:
        return None
    return dict(parsed) if isinstance(parsed, Mapping) else None


class FastApiRouteBindings:
    def __init__(self, *, dependencies: FastApiRouteDependencies, config: FastApiBindingConfig | None = None) -> None:
        self.dependencies = dependencies
        self.config = config or FastApiBindingConfig()

    def _resolve_managed_secret_writer(self, now_iso: str):
        if self.dependencies.aws_secrets_manager_client_provider is not None:
            client = self.dependencies.aws_secrets_manager_client_provider()
            config = self.dependencies.aws_secrets_manager_config or AwsSecretsManagerBindingConfig()
            writer = AwsSecretsManagerSecretAuthority.build_secret_writer(client=client, config=config)
            return lambda w, p, s, metadata: writer(w, p, s, {**dict(metadata), "now_iso": now_iso})
        return lambda w, p, s, metadata: self.dependencies.managed_secret_writer(w, p, s, {**dict(metadata), "now_iso": now_iso})

    def build_router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/api/users/me/activity")
        async def get_recent_activity(request: Request, workspace_id: str | None = None, limit: int = 20, cursor: str | None = None) -> Response:
            inbound = self._inbound_request(
                request=request,
                query_params={"workspace_id": workspace_id, "limit": limit, "cursor": cursor} if workspace_id is not None or cursor is not None else {"limit": limit},
            )
            outbound = FrameworkRouteBindings.handle_recent_activity(
                request=inbound,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                run_rows=self.dependencies.recent_run_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/users/me/history-summary")
        async def get_history_summary(request: Request, workspace_id: str | None = None) -> Response:
            inbound = self._inbound_request(
                request=request,
                query_params={"workspace_id": workspace_id} if workspace_id is not None else {},
            )
            outbound = FrameworkRouteBindings.handle_history_summary(
                request=inbound,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                run_rows=self.dependencies.recent_run_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces")
        async def list_workspaces(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_list_workspaces(
                request=inbound,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/library")
        async def get_circuit_library(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_circuit_library(
                request=inbound,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/templates/starter-circuits")
        async def list_starter_circuit_templates(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_list_starter_circuit_templates(request=inbound)
            return self._framework_response(outbound)

        @router.get("/api/templates/starter-circuits/{template_id}")
        async def get_starter_circuit_template(template_id: str, request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={"template_id": template_id})
            outbound = FrameworkRouteBindings.handle_get_starter_circuit_template(request=inbound)
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/starter-templates/{template_id}/apply")
        async def apply_starter_circuit_template(workspace_id: str, template_id: str, request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id, "template_id": template_id})
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            workspace_row = self.dependencies.workspace_row_provider(workspace_id)
            artifact_source = self.dependencies.workspace_artifact_source_provider(workspace_id)
            outbound = FrameworkRouteBindings.handle_apply_starter_circuit_template(
                request=inbound,
                workspace_context=workspace_context,
                workspace_row=workspace_row,
                artifact_source=artifact_source,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
            )
            return self._framework_response(outbound)

        @router.get("/api/formats/public-nex")
        async def get_public_nex_format(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_public_nex_format(request=inbound)
            return self._framework_response(outbound)

        @router.get("/api/integrations/public-mcp/manifest")
        async def get_public_mcp_manifest(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_public_mcp_manifest(request=inbound)
            return self._framework_response(outbound)

        @router.get("/api/integrations/public-mcp/host-bridge")
        async def get_public_mcp_host_bridge(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_public_mcp_host_bridge(request=inbound)
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/result-history")
        async def get_workspace_result_history(request: Request, workspace_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_workspace_result_history(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/feedback")
        async def get_workspace_feedback(request: Request, workspace_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_workspace_feedback(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/feedback")
        async def submit_workspace_feedback(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_submit_workspace_feedback(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                feedback_writer=self.dependencies.feedback_writer,
                feedback_id_factory=self.dependencies.feedback_id_factory or (lambda: 'feedback-missing-id-factory'),
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else '',
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}")
        async def get_workspace(request: Request, workspace_id: str) -> Response:
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_get_workspace(
                request=inbound,
                workspace_context=workspace_context,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces")
        async def create_workspace(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, json_body=payload)
            outbound = FrameworkRouteBindings.handle_create_workspace(
                request=inbound,
                workspace_id_factory=self.dependencies.workspace_id_factory or (lambda: 'workspace-missing-id-factory'),
                membership_id_factory=self.dependencies.membership_id_factory or (lambda: 'membership-missing-id-factory'),
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else '',
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                workspace_registry_writer=self.dependencies.workspace_registry_writer,
            )
            return self._framework_response(outbound)

        @router.get("/api/providers/catalog")
        async def get_provider_catalog(request: Request) -> Response:
            inbound = self._inbound_request(request=request)
            outbound = FrameworkRouteBindings.handle_list_provider_catalog(
                request=inbound,
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/provider-bindings")
        async def list_workspace_provider_bindings(request: Request, workspace_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_list_workspace_provider_bindings(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.put("/api/workspaces/{workspace_id}/provider-bindings/{provider_key}")
        async def put_workspace_provider_binding(
            request: Request,
            workspace_id: str,
            provider_key: str,
            payload: dict[str, Any] | None = Body(default=None),
        ) -> Response:
            inbound = self._inbound_request(
                request=request,
                json_body=payload,
                path_params={"workspace_id": workspace_id, "provider_key": provider_key},
            )
            now_iso = self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else ''
            outbound = FrameworkRouteBindings.handle_put_workspace_provider_binding(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                existing_binding_row=self.dependencies.workspace_provider_binding_row_provider(workspace_id, provider_key),
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                binding_id_factory=self.dependencies.binding_id_factory or (lambda: 'binding-missing-id-factory'),
                secret_writer=self._resolve_managed_secret_writer(now_iso),
                binding_writer=self.dependencies.provider_binding_writer,
                now_iso=now_iso,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/provider-bindings/health")
        async def list_workspace_provider_health(request: Request, workspace_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_list_workspace_provider_health(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                secret_metadata_reader=self._resolve_managed_secret_metadata_reader(),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/health")
        async def get_workspace_provider_health(request: Request, workspace_id: str, provider_key: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id, "provider_key": provider_key})
            outbound = FrameworkRouteBindings.handle_get_workspace_provider_health(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                secret_metadata_reader=self._resolve_managed_secret_metadata_reader(),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe")
        async def probe_workspace_provider(
            request: Request,
            workspace_id: str,
            provider_key: str,
            payload: dict[str, Any] | None = Body(default=None),
        ) -> Response:
            inbound = self._inbound_request(
                request=request,
                json_body=payload,
                path_params={"workspace_id": workspace_id, "provider_key": provider_key},
            )
            now_iso = self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else ''
            outbound = FrameworkRouteBindings.handle_probe_workspace_provider(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                provider_key=provider_key,
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                provider_catalog_rows=self.dependencies.provider_catalog_rows_provider(),
                secret_metadata_reader=self._resolve_managed_secret_metadata_reader(),
                probe_runner=self.dependencies.provider_probe_runner,
                probe_event_id_factory=self.dependencies.probe_event_id_factory,
                probe_history_writer=self.dependencies.provider_probe_history_writer,
                now_iso=now_iso,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/provider-bindings/{provider_key}/probe-history")
        async def list_provider_probe_history(
            request: Request,
            workspace_id: str,
            provider_key: str,
            limit: int = 20,
            cursor: str | None = None,
        ) -> Response:
            inbound = self._inbound_request(
                request=request,
                path_params={"workspace_id": workspace_id, "provider_key": provider_key},
                query_params={"limit": limit, "cursor": cursor},
            )
            outbound = FrameworkRouteBindings.handle_list_provider_probe_history(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                provider_key=provider_key,
                probe_history_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/users/me/onboarding")
        async def get_onboarding(request: Request, workspace_id: str | None = None) -> Response:
            workspace_context = self.dependencies.workspace_context_provider(workspace_id) if workspace_id else None
            inbound = self._inbound_request(request=request, query_params={"workspace_id": workspace_id} if workspace_id is not None else {})
            outbound = FrameworkRouteBindings.handle_get_onboarding(
                request=inbound,
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                workspace_context=workspace_context,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.put("/api/users/me/onboarding")
        async def put_onboarding(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            workspace_id = str((payload or {}).get('workspace_id') or '').strip() or None
            workspace_context = self.dependencies.workspace_context_provider(workspace_id) if workspace_id else None
            inbound = self._inbound_request(request=request, json_body=payload)
            outbound = FrameworkRouteBindings.handle_put_onboarding(
                request=inbound,
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                workspace_context=workspace_context,
                onboarding_state_id_factory=self.dependencies.onboarding_state_id_factory or (lambda: 'onboarding-missing-id-factory'),
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else '',
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_state_writer=self.dependencies.onboarding_state_writer,
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/runs")
        async def list_workspace_runs(
            workspace_id: str,
            request: Request,
            limit: int = 20,
            cursor: str | None = None,
            status_family: str | None = None,
            requested_by_user_id: str | None = None,
        ) -> Response:
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            inbound = self._inbound_request(
                request=request,
                path_params={"workspace_id": workspace_id},
                query_params={
                    "limit": limit,
                    "cursor": cursor,
                    "status_family": status_family,
                    "requested_by_user_id": requested_by_user_id,
                },
            )
            outbound = FrameworkRouteBindings.handle_list_workspace_runs(
                request=inbound,
                workspace_context=workspace_context,
                run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/workspaces/{workspace_id}/shell")
        async def get_workspace_shell(request: Request, workspace_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id})
            outbound = FrameworkRouteBindings.handle_workspace_shell(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.put("/api/workspaces/{workspace_id}/shell/draft")
        async def put_workspace_shell_draft(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_put_workspace_shell_draft(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                workspace_artifact_source_writer=self.dependencies.workspace_artifact_source_writer,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/shell/commit")
        async def commit_workspace_shell(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_commit_workspace_shell(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                workspace_artifact_source_writer=self.dependencies.workspace_artifact_source_writer,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/shell/checkout")
        async def checkout_workspace_shell(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_checkout_workspace_shell(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                workspace_artifact_source_writer=self.dependencies.workspace_artifact_source_writer,
                public_share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/shell/share")
        async def create_workspace_shell_share(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_create_workspace_shell_share(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/workspaces/{workspace_id}/shell/launch")
        async def launch_workspace_shell(request: Request, workspace_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"workspace_id": workspace_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_launch_workspace_shell(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                policy=self.dependencies.admission_policy,
                engine_launch_decider=self.dependencies.engine_launch_decider,
                run_id_factory=self.dependencies.run_id_factory,
                run_request_id_factory=self.dependencies.run_request_id_factory,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
            )
            return self._framework_response(outbound)

        @router.get("/api/users/me/public-shares")
        async def list_issuer_public_shares(request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={})
            outbound = FrameworkRouteBindings.handle_list_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.get("/api/users/me/public-shares/summary")
        async def get_issuer_public_share_summary(request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={})
            outbound = FrameworkRouteBindings.handle_get_issuer_public_share_summary(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)



        @router.get("/api/users/me/public-shares/action-reports")
        async def list_issuer_public_share_action_reports(request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={})
            outbound = FrameworkRouteBindings.handle_list_issuer_public_share_action_reports(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.get("/api/users/me/public-shares/action-reports/summary")
        async def get_issuer_public_share_action_report_summary(request: Request) -> Response:
            inbound = self._inbound_request(request=request, path_params={})
            outbound = FrameworkRouteBindings.handle_get_issuer_public_share_action_report_summary(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/users/me/public-shares/actions/revoke")
        async def revoke_issuer_public_shares(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_revoke_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/users/me/public-shares/actions/extend")
        async def extend_issuer_public_shares(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_extend_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/users/me/public-shares/actions/archive")
        async def archive_issuer_public_shares(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_archive_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/users/me/public-shares/actions/delete")
        async def delete_issuer_public_shares(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_delete_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_deleter=self.dependencies.public_share_payload_deleter,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.get("/api/public-shares/{share_id}")
        async def get_public_share(request: Request, share_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id})
            outbound = FrameworkRouteBindings.handle_get_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            return self._framework_response(outbound)

        @router.get("/api/public-shares/{share_id}/history")
        async def get_public_share_history(request: Request, share_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id})
            outbound = FrameworkRouteBindings.handle_get_public_share_history(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            return self._framework_response(outbound)

        @router.get("/api/public-shares/{share_id}/artifact")
        async def get_public_share_artifact(request: Request, share_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id})
            outbound = FrameworkRouteBindings.handle_get_public_share_artifact(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            return self._framework_response(outbound)

        @router.post("/api/public-shares/{share_id}/extend")
        async def extend_public_share(request: Request, share_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_extend_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/public-shares/{share_id}/revoke")
        async def revoke_public_share(request: Request, share_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id})
            outbound = FrameworkRouteBindings.handle_revoke_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.post("/api/public-shares/{share_id}/archive")
        async def archive_public_share(request: Request, share_id: str, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id}, json_body=payload)
            outbound = FrameworkRouteBindings.handle_archive_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.delete("/api/public-shares/{share_id}")
        async def delete_public_share(request: Request, share_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"share_id": share_id})
            outbound = FrameworkRouteBindings.handle_delete_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_deleter=self.dependencies.public_share_payload_deleter,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            return self._framework_response(outbound)

        @router.get("/app/templates/starter-circuits")
        async def get_starter_template_catalog_page(request: Request) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path="/api/templates/starter-circuits",
                headers=dict(request.headers),
                path_params={},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_list_starter_circuit_templates(request=inbound)
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            return HTMLResponse(content=render_starter_template_catalog_html(payload), status_code=200)


        @router.get("/app/library")
        async def get_circuit_library_page(request: Request) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path="/api/workspaces/library",
                headers=dict(request.headers),
                path_params={},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_circuit_library(
                request=inbound,
                workspace_rows=self.dependencies.workspace_rows_provider(),
                membership_rows=self.dependencies.workspace_membership_rows_provider(),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            return HTMLResponse(content=render_circuit_library_runtime_html(payload), status_code=200)


        @router.get("/app/workspaces/{workspace_id}/results")
        async def get_workspace_result_history_page(request: Request, workspace_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/workspaces/{workspace_id}/result-history",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_workspace_result_history(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            return HTMLResponse(content=render_workspace_result_history_html(payload), status_code=200)

        @router.get("/app/workspaces/{workspace_id}/feedback")
        async def get_workspace_feedback_page(request: Request, workspace_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/workspaces/{workspace_id}/feedback",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_workspace_feedback(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            return HTMLResponse(content=render_workspace_feedback_html(payload), status_code=200)

        @router.get("/app/workspaces/{workspace_id}")
        async def get_workspace_shell_page(request: Request, workspace_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/workspaces/{workspace_id}/shell",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_workspace_shell(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.workspace_run_rows_provider(workspace_id),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            return HTMLResponse(content=render_workspace_shell_runtime_html(payload), status_code=200)

        @router.post("/api/runs")
        async def launch_run(request: Request, payload: dict[str, Any] | None = Body(default=None)) -> Response:
            workspace_id = str((payload or {}).get("workspace_id") or "").strip()
            workspace_context = self.dependencies.workspace_context_provider(workspace_id) if workspace_id else None
            inbound = self._inbound_request(request=request, json_body=payload)
            outbound = FrameworkRouteBindings.handle_launch(
                request=inbound,
                workspace_context=workspace_context,
                target_catalog=self.dependencies.target_catalog_provider(workspace_id),
                policy=self.dependencies.admission_policy,
                engine_launch_decider=self.dependencies.engine_launch_decider,
                run_id_factory=self.dependencies.run_id_factory,
                run_request_id_factory=self.dependencies.run_request_id_factory,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.get("/api/runs/{run_id}")
        async def get_run_status(request: Request, run_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_run_status(
                request=inbound,
                run_context=self.dependencies.run_context_provider(run_id),
                run_record_row=self.dependencies.run_record_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                engine_status=self.dependencies.engine_status_provider(run_id),
            )
            return self._framework_response(outbound)


        @router.get("/api/runs/{run_id}/actions")
        async def get_run_actions(request: Request, run_id: str) -> Response:
            run_context = self.dependencies.run_context_provider(run_id)
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_run_actions(
                request=inbound,
                run_context=run_context,
                run_record_row=self.dependencies.run_record_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(run_context.workspace_context.workspace_id) if run_context is not None else None,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            return self._framework_response(outbound)

        @router.post("/api/runs/{run_id}/retry")
        async def retry_run(request: Request, run_id: str) -> Response:
            run_context = self.dependencies.run_context_provider(run_id)
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_retry_run(
                request=inbound,
                run_context=run_context,
                run_record_row=self.dependencies.run_record_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(run_context.workspace_context.workspace_id) if run_context is not None else None,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                run_record_writer=self.dependencies.run_record_writer,
                now_iso_factory=self.dependencies.now_iso_provider,
            )
            return self._framework_response(outbound)

        @router.post("/api/runs/{run_id}/force-reset")
        async def force_reset_run(request: Request, run_id: str) -> Response:
            run_context = self.dependencies.run_context_provider(run_id)
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_force_reset_run(
                request=inbound,
                run_context=run_context,
                run_record_row=self.dependencies.run_record_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(run_context.workspace_context.workspace_id) if run_context is not None else None,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                run_record_writer=self.dependencies.run_record_writer,
                now_iso_factory=self.dependencies.now_iso_provider,
            )
            return self._framework_response(outbound)

        @router.post("/api/runs/{run_id}/mark-reviewed")
        async def mark_run_reviewed(request: Request, run_id: str) -> Response:
            run_context = self.dependencies.run_context_provider(run_id)
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_mark_run_reviewed(
                request=inbound,
                run_context=run_context,
                run_record_row=self.dependencies.run_record_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(run_context.workspace_context.workspace_id) if run_context is not None else None,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.recent_provider_binding_rows_provider(),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.recent_provider_probe_rows_provider(),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                run_record_writer=self.dependencies.run_record_writer,
                now_iso_factory=self.dependencies.now_iso_provider,
            )
            return self._framework_response(outbound)


        @router.get("/api/runs/{run_id}/result")
        async def get_run_result(request: Request, run_id: str) -> Response:
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_run_result(
                request=inbound,
                run_context=self.dependencies.run_context_provider(run_id),
                run_record_row=self.dependencies.run_record_provider(run_id),
                result_row=self.dependencies.result_row_provider(run_id),
                artifact_rows=self.dependencies.artifact_rows_provider(run_id),
                workspace_row=self.dependencies.workspace_row_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(str((self.dependencies.run_record_provider(run_id) or {}).get('workspace_id') or '')),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                engine_result=self.dependencies.engine_result_provider(run_id),
            )
            return self._framework_response(outbound)

        @router.get("/api/runs/{run_id}/artifacts")
        async def list_run_artifacts(request: Request, run_id: str) -> Response:
            run_record_row = self.dependencies.run_record_provider(run_id)
            workspace_id = str((run_record_row or {}).get('workspace_id') or '')
            inbound = self._inbound_request(request=request, path_params={"run_id": run_id})
            outbound = FrameworkRouteBindings.handle_run_artifacts(
                request=inbound,
                run_context=self.dependencies.run_context_provider(run_id),
                run_record_row=run_record_row,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_rows=self.dependencies.artifact_rows_provider(run_id),
            )
            return self._framework_response(outbound)

        @router.get("/api/artifacts/{artifact_id}")
        async def get_artifact_detail(request: Request, artifact_id: str) -> Response:
            artifact_row = self.dependencies.artifact_row_provider(artifact_id)
            run_id = str(artifact_row.get("run_id") or "").strip() if artifact_row is not None else ""
            run_record_row = self.dependencies.run_record_provider(run_id) if run_id else None
            workspace_id = str(artifact_row.get("workspace_id") or "").strip() if artifact_row is not None else ""
            workspace_context = self.dependencies.workspace_context_provider(workspace_id) if workspace_id else None
            inbound = self._inbound_request(request=request, path_params={"artifact_id": artifact_id})
            outbound = FrameworkRouteBindings.handle_artifact_detail(
                request=inbound,
                workspace_context=workspace_context,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_row=artifact_row,
                run_record_row=run_record_row,
            )
            return self._framework_response(outbound)

        @router.get("/api/runs/{run_id}/trace")
        async def get_run_trace(request: Request, run_id: str, limit: int = 100, cursor: str | None = None) -> Response:
            run_record_row = self.dependencies.run_record_provider(run_id)
            workspace_id = str((run_record_row or {}).get('workspace_id') or '')
            inbound = self._inbound_request(
                request=request,
                path_params={"run_id": run_id},
                query_params={"limit": limit, "cursor": cursor} if cursor is not None else {"limit": limit},
            )
            outbound = FrameworkRouteBindings.handle_run_trace(
                request=inbound,
                run_context=self.dependencies.run_context_provider(run_id),
                run_record_row=run_record_row,
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                trace_rows=self.dependencies.trace_rows_provider(run_id),
            )
            return self._framework_response(outbound)

        return router

    def build_app(self) -> FastAPI:
        app = FastAPI(title=self.config.title, version=self.config.version)
        app.include_router(self.build_router())
        return app

    def _resolve_managed_secret_metadata_reader(self):
        if self.dependencies.managed_secret_metadata_reader is not None:
            return self.dependencies.managed_secret_metadata_reader
        if self.dependencies.aws_secrets_manager_client_provider is not None:
            client = self.dependencies.aws_secrets_manager_client_provider()
            config = self.dependencies.aws_secrets_manager_config or AwsSecretsManagerBindingConfig()
            return AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(client=client, config=config)
        return None

    def _resolve_session_claims(self, request: Request) -> Optional[Mapping[str, Any]]:
        if self.dependencies.session_claims_resolver is not None:
            resolved = self.dependencies.session_claims_resolver(request)
            return dict(resolved) if resolved is not None else None
        return default_fastapi_session_claims_resolver(request, header_name=self.config.session_claims_header)

    def _inbound_request(
        self,
        *,
        request: Request,
        json_body: Any = None,
        path_params: Optional[Mapping[str, Any]] = None,
        query_params: Optional[Mapping[str, Any]] = None,
    ) -> FrameworkInboundRequest:
        return FrameworkInboundRequest(
            method=request.method,
            path=request.url.path,
            headers=dict(request.headers),
            path_params=dict(path_params or request.path_params),
            query_params=dict(query_params or request.query_params),
            json_body=json_body,
            session_claims=self._resolve_session_claims(request),
        )

    @staticmethod
    def _framework_response(response: FrameworkOutboundResponse) -> Response:
        headers = {str(key): str(value) for key, value in dict(response.headers).items() if str(key).lower() != "content-type"}
        try:
            payload = json.loads(response.body_text)
        except json.JSONDecodeError:
            payload = response.body_text
        if response.media_type == "application/json" or isinstance(payload, (dict, list)):
            return JSONResponse(status_code=response.status_code, content=payload, headers=headers)
        return Response(status_code=response.status_code, content=response.body_text, headers=headers, media_type=response.media_type)


def create_fastapi_app(
    *,
    dependencies: FastApiRouteDependencies,
    config: FastApiBindingConfig | None = None,
) -> FastAPI:
    return FastApiRouteBindings(dependencies=dependencies, config=config).build_app()
