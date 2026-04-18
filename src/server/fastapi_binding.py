from __future__ import annotations

import json
from urllib.parse import parse_qsl, quote
from typing import Any, Mapping, Optional

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from src.server.framework_binding import FrameworkRouteBindings
from src.server.aws_secrets_manager_binding import AwsSecretsManagerSecretAuthority
from src.server.aws_secrets_manager_models import AwsSecretsManagerBindingConfig
from src.server.framework_binding_models import FrameworkInboundRequest, FrameworkOutboundResponse
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies
from src.server.workspace_shell_runtime import render_workspace_shell_runtime_html
from src.server.circuit_library_runtime import render_circuit_library_runtime_html
from src.server.result_history_runtime import render_workspace_result_history_html
from src.server.starter_template_runtime import render_starter_template_catalog_html, render_starter_template_detail_html
from src.server.feedback_runtime import render_workspace_feedback_html
from src.server.run_admission_models import ExecutionTargetCatalogEntry
from src.server.public_share_runtime import (
    _canonical_ref_for_workspace_artifact,
    build_workspace_public_share_history_payload,
    build_public_share_catalog_payload,
    render_workspace_public_share_history_html,
    render_workspace_share_create_html,
    render_public_share_catalog_html,
    render_public_share_catalog_summary_html,
    render_public_share_checkout_html,
    render_public_share_import_html,
    render_public_share_run_html,
    render_public_share_detail_html,
    render_public_share_history_html,
    render_issuer_public_share_portfolio_html,
    render_issuer_public_share_summary_html,
    render_issuer_public_share_action_reports_html,
)


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


def _read_simple_form_data(body: bytes) -> dict[str, str]:
    if not body:
        return {}
    return {key: value for key, value in parse_qsl(body.decode("utf-8"), keep_blank_values=True)}


def _collect_share_ids_from_form(form: Mapping[str, str]) -> list[str]:
    share_ids: list[str] = []
    share_ids_csv = str(form.get("share_ids_csv") or "").strip()
    if share_ids_csv:
        for raw_value in share_ids_csv.split(","):
            share_id = raw_value.strip()
            if share_id and share_id not in share_ids:
                share_ids.append(share_id)
    share_id = str(form.get("share_id") or "").strip()
    if share_id and share_id not in share_ids:
        share_ids.append(share_id)
    return share_ids


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

        def _public_share_app_target(*, share_id: str, app_language: str, workspace_id: str | None, origin: str | None = None) -> str:
            workspace_query = f"&workspace_id={workspace_id}" if workspace_id else ""
            if origin == "history":
                return f"/app/public-shares/{share_id}/history?app_language={app_language}{workspace_query}"
            return f"/app/public-shares/{share_id}?app_language={app_language}{workspace_query}"

        def _public_share_delete_target(*, app_language: str, workspace_id: str | None, share_id: str, status: str | None = None, reason: str | None = None) -> str:
            if workspace_id:
                target = f"/app/workspaces/{workspace_id}/shares?app_language={app_language}&action=delete&share_id={share_id}"
                if status:
                    target += f"&status={status}"
                if reason:
                    from urllib.parse import quote
                    target += f"&reason={quote(reason)}"
                return target
            target = f"/app/library?app_language={app_language}"
            if status:
                target += f"&share_action=delete&status={status}"
            return target

        def _issuer_public_share_app_target(*, app_language: str, action: str | None = None, status: str | None = None, reason: str | None = None) -> str:
            target = f"/app/users/me/public-shares?app_language={app_language}"
            if action:
                target += f"&action={action}"
            if status:
                target += f"&status={status}"
            if reason:
                from urllib.parse import quote
                target += f"&reason={quote(reason)}"
            return target

        def _public_share_notice_payload(request: Request) -> dict[str, str]:
            query = dict(request.query_params)
            payload: dict[str, str] = {}
            for key in ("action", "status", "reason"):
                value = str(query.get(key) or "").strip()
                if value:
                    payload[key] = value
            return payload

        @router.get("/app/users/me/public-shares")
        async def get_issuer_public_share_portfolio_page(request: Request) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            api_query = {key: value for key, value in query.items() if key not in {"app_language", "action", "status", "reason"}}
            inbound = FrameworkInboundRequest(
                method="GET",
                path="/api/users/me/public-shares",
                headers=dict(request.headers),
                path_params={},
                query_params=api_query,
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_list_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            payload["app_language"] = app_language
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_issuer_public_share_portfolio_html(payload, app_language=app_language), status_code=200)

        @router.get("/app/users/me/public-shares/summary")
        async def get_issuer_public_share_summary_page(request: Request) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            api_query = {key: value for key, value in query.items() if key != "app_language"}
            inbound = FrameworkInboundRequest(
                method="GET",
                path="/api/users/me/public-shares/summary",
                headers=dict(request.headers),
                path_params={},
                query_params=api_query,
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_issuer_public_share_summary(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            payload["app_language"] = app_language
            return HTMLResponse(content=render_issuer_public_share_summary_html(payload, app_language=app_language), status_code=200)

        @router.get("/app/users/me/public-shares/action-reports")
        async def get_issuer_public_share_action_reports_page(request: Request) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            api_query = {key: value for key, value in query.items() if key not in {"app_language", "status", "reason"}}
            inbound = FrameworkInboundRequest(
                method="GET",
                path="/api/users/me/public-shares/action-reports",
                headers=dict(request.headers),
                path_params={},
                query_params=api_query,
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_list_issuer_public_share_action_reports(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            payload["app_language"] = app_language
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_issuer_public_share_action_reports_html(payload, app_language=app_language), status_code=200)

        @router.post("/app/users/me/public-shares/actions/revoke")
        async def revoke_issuer_public_shares_page(request: Request) -> Response:
            app_language = str(dict(request.query_params).get("app_language") or "en")
            form = _read_simple_form_data(await request.body())
            share_ids = _collect_share_ids_from_form(form)
            inbound = FrameworkInboundRequest(
                method="POST",
                path="/api/users/me/public-shares/actions/revoke",
                headers=dict(request.headers),
                path_params={},
                query_params={},
                json_body={"share_ids": share_ids},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_revoke_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            return RedirectResponse(
                url=_issuer_public_share_app_target(
                    app_language=app_language,
                    action="revoke",
                    status="done" if outbound.status_code == 200 else "error",
                    reason=str(payload.get("reason_code") or "").strip() or None,
                ),
                status_code=303,
            )

        @router.post("/app/users/me/public-shares/actions/archive")
        async def archive_issuer_public_shares_page(request: Request) -> Response:
            app_language = str(dict(request.query_params).get("app_language") or "en")
            form = _read_simple_form_data(await request.body())
            share_ids = _collect_share_ids_from_form(form)
            archived = str(form.get("archived") or "true").strip().lower() in {"1", "true", "yes", "on"}
            inbound = FrameworkInboundRequest(
                method="POST",
                path="/api/users/me/public-shares/actions/archive",
                headers=dict(request.headers),
                path_params={},
                query_params={},
                json_body={"share_ids": share_ids, "archived": archived},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_archive_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            return RedirectResponse(
                url=_issuer_public_share_app_target(
                    app_language=app_language,
                    action="archive" if archived else "unarchive",
                    status="done" if outbound.status_code == 200 else "error",
                    reason=str(payload.get("reason_code") or "").strip() or None,
                ),
                status_code=303,
            )

        @router.post("/app/users/me/public-shares/actions/extend")
        async def extend_issuer_public_shares_page(request: Request) -> Response:
            app_language = str(dict(request.query_params).get("app_language") or "en")
            form = _read_simple_form_data(await request.body())
            share_ids = _collect_share_ids_from_form(form)
            expires_at = str(form.get("expires_at") or "").strip()
            inbound = FrameworkInboundRequest(
                method="POST",
                path="/api/users/me/public-shares/actions/extend",
                headers=dict(request.headers),
                path_params={},
                query_params={},
                json_body={"share_ids": share_ids, "expires_at": expires_at},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_extend_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            return RedirectResponse(
                url=_issuer_public_share_app_target(
                    app_language=app_language,
                    action="extend",
                    status="done" if outbound.status_code == 200 else "error",
                    reason=str(payload.get("reason_code") or "").strip() or None,
                ),
                status_code=303,
            )

        @router.post("/app/users/me/public-shares/actions/delete")
        async def delete_issuer_public_shares_page(request: Request) -> Response:
            app_language = str(dict(request.query_params).get("app_language") or "en")
            form = _read_simple_form_data(await request.body())
            share_ids = _collect_share_ids_from_form(form)
            inbound = FrameworkInboundRequest(
                method="POST",
                path="/api/users/me/public-shares/actions/delete",
                headers=dict(request.headers),
                path_params={},
                query_params={},
                json_body={"share_ids": share_ids},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_delete_issuer_public_shares(
                request=inbound,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_payload_deleter=self.dependencies.public_share_payload_deleter,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            return RedirectResponse(
                url=_issuer_public_share_app_target(
                    app_language=app_language,
                    action="delete",
                    status="done" if outbound.status_code == 200 else "error",
                    reason=str(payload.get("reason_code") or "").strip() or None,
                ),
                status_code=303,
            )

        @router.get("/app/workspaces/{workspace_id}/shares")
        async def get_workspace_share_history_page(request: Request, workspace_id: str) -> Response:
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            workspace_row = self.dependencies.workspace_row_provider(workspace_id)
            if workspace_context is None or workspace_row is None:
                return JSONResponse(status_code=404, content={"error_family": "workspace_read_failure", "reason_code": "workspace.not_found", "message": "Requested workspace was not found."})
            app_language = str(dict(request.query_params).get("app_language") or "en")
            payload = build_workspace_public_share_history_payload(
                workspace_id=workspace_id,
                workspace_title=str(workspace_row.get("title") or workspace_id),
                workspace_row=workspace_row,
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                share_payload_rows=self.dependencies.public_share_payload_rows_provider() if self.dependencies.public_share_payload_rows_provider is not None else (),
                app_language=app_language,
            )
            return HTMLResponse(content=render_workspace_public_share_history_html(payload), status_code=200)

        @router.get("/app/workspaces/{workspace_id}/shares/create")
        async def get_workspace_share_create_page(request: Request, workspace_id: str) -> Response:
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            workspace_row = self.dependencies.workspace_row_provider(workspace_id)
            if workspace_context is None or workspace_row is None:
                return JSONResponse(status_code=404, content={"error_family": "workspace_read_failure", "reason_code": "workspace.not_found", "message": "Requested workspace was not found."})
            app_language = str(dict(request.query_params).get("app_language") or "en")
            artifact_source = self.dependencies.workspace_artifact_source_provider(workspace_id)
            canonical_ref, storage_role = _canonical_ref_for_workspace_artifact(workspace_row, artifact_source)
            share_rows = self.dependencies.public_share_payload_rows_provider() if self.dependencies.public_share_payload_rows_provider is not None else ()
            share_count = 0
            for row in share_rows:
                try:
                    source_artifact = dict(row.get("source_artifact") or {}) if isinstance(row, Mapping) else {}
                    row_ref = str(source_artifact.get("canonical_ref") or "").strip()
                except Exception:
                    row_ref = ""
                if canonical_ref and row_ref == canonical_ref:
                    share_count += 1
            workspace_title = str(workspace_row.get("title") or workspace_id)
            payload = {
                "workspace_id": workspace_id,
                "workspace_title": workspace_title,
                "app_language": app_language,
                "canonical_ref": canonical_ref,
                "storage_role": storage_role,
                "share_count": share_count,
                "prefill_title": f"{workspace_title} snapshot",
                "prefill_summary": f"Public share for {workspace_title}.",
                "prefill_expires_at": "",
                "routes": {
                    "workspace_page": f"/app/workspaces/{workspace_id}?app_language={app_language}",
                    "workspace_feedback_page": f"/app/workspaces/{workspace_id}/feedback?surface=workspace_shell&app_language={app_language}",
                    "workspace_share_create_page": f"/app/workspaces/{workspace_id}/shares/create?app_language={app_language}",
                    "workspace_share_history_page": f"/app/workspaces/{workspace_id}/shares?app_language={app_language}",
                    "starter_template_catalog_page": f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}",
                    "library_page": f"/app/workspaces/{workspace_id}/library?app_language={app_language}",
                },
            }
            return HTMLResponse(content=render_workspace_share_create_html(payload), status_code=200)

        @router.post("/app/workspaces/{workspace_id}/shares/create")
        async def create_workspace_share_page(request: Request, workspace_id: str) -> Response:
            form = _read_simple_form_data(await request.body())
            json_body = {
                "title": str(form.get("title") or "").strip() or None,
                "summary": str(form.get("summary") or "").strip() or None,
                "expires_at": str(form.get("expires_at") or "").strip() or None,
            }
            if all(value is None for value in json_body.values()):
                json_body = None
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/workspaces/{workspace_id}/shell/share",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id},
                query_params=dict(request.query_params),
                json_body=json_body,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_create_workspace_shell_share(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 201:
                return framework_response
            payload = json.loads(outbound.body_text)
            share_id = str(payload.get("share_id") or "").strip()
            app_language = str(dict(request.query_params).get("app_language") or "en")
            return RedirectResponse(url=f"/app/public-shares/{share_id}?app_language={app_language}&workspace_id={workspace_id}", status_code=303)

        @router.get("/app/public-shares")
        async def get_public_share_catalog_page(request: Request) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            payload = build_public_share_catalog_payload(
                share_payload_rows=self.dependencies.public_share_payload_rows_provider(),
                app_language=app_language,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
                workspace_id=workspace_id,
                query=str(query.get("q") or "").strip() or None,
                storage_role=str(query.get("storage_role") or "").strip() or None,
                operation=str(query.get("operation") or "").strip() or None,
            )
            return HTMLResponse(content=render_public_share_catalog_html(payload, app_language=app_language), status_code=200)

        @router.get("/app/public-shares/summary")
        async def get_public_share_catalog_summary_page(request: Request) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            payload = build_public_share_catalog_payload(
                share_payload_rows=self.dependencies.public_share_payload_rows_provider(),
                app_language=app_language,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
                workspace_id=workspace_id,
                query=str(query.get("q") or "").strip() or None,
                storage_role=str(query.get("storage_role") or "").strip() or None,
                operation=str(query.get("operation") or "").strip() or None,
            )
            return HTMLResponse(content=render_public_share_catalog_summary_html(payload, app_language=app_language), status_code=200)

        @router.get("/app/public-shares/{share_id}")
        async def get_public_share_page(request: Request, share_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            app_language = str(dict(request.query_params).get("app_language") or "en")
            workspace_id = str(dict(request.query_params).get("workspace_id") or "").strip() or None
            session_claims = self._resolve_session_claims(request)
            requested_by_user_ref = str((session_claims or {}).get("sub") or "").strip() or None
            issued_by_user_ref = str(dict(payload.get("lifecycle") or {}).get("issued_by_user_ref") or "").strip() or None
            payload["viewer_context"] = {
                "requested_by_user_ref": requested_by_user_ref,
                "can_manage": bool(requested_by_user_ref and issued_by_user_ref and requested_by_user_ref == issued_by_user_ref),
            }
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_public_share_detail_html(payload, app_language=app_language, workspace_id=workspace_id), status_code=200)

        @router.get("/app/public-shares/{share_id}/history")
        async def get_public_share_history_page(request: Request, share_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/public-shares/{share_id}/history",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_public_share_history(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            app_language = str(dict(request.query_params).get("app_language") or "en")
            workspace_id = str(dict(request.query_params).get("workspace_id") or "").strip() or None
            session_claims = self._resolve_session_claims(request)
            requested_by_user_ref = str((session_claims or {}).get("sub") or "").strip() or None
            detail_inbound = FrameworkInboundRequest(
                method="GET",
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=session_claims,
            )
            detail_outbound = FrameworkRouteBindings.handle_get_public_share(
                request=detail_inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            if detail_outbound.status_code == 200 and detail_outbound.body_text:
                detail_payload = json.loads(detail_outbound.body_text)
                payload["lifecycle"] = dict(detail_payload.get("lifecycle") or {})
                payload["management"] = dict(detail_payload.get("management") or {})
                payload["operation_capabilities"] = list(detail_payload.get("operation_capabilities") or ())
            issued_by_user_ref = str(dict(payload.get("lifecycle") or {}).get("issued_by_user_ref") or "").strip() or None
            payload["viewer_context"] = {
                "requested_by_user_ref": requested_by_user_ref,
                "can_manage": bool(requested_by_user_ref and issued_by_user_ref and requested_by_user_ref == issued_by_user_ref),
            }
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_public_share_history_html(payload, app_language=app_language, workspace_id=workspace_id), status_code=200)

        @router.get("/app/public-shares/{share_id}/checkout")
        async def get_public_share_checkout_page(request: Request, share_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method="GET",
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            payload["app_language"] = app_language
            payload["prefill_workspace_id"] = workspace_id or ""
            payload["prefill_working_save_id"] = str(query.get("working_save_id") or "").strip()
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_public_share_checkout_html(payload, app_language=app_language, workspace_id=workspace_id), status_code=200)

        @router.post("/app/public-shares/{share_id}/checkout")
        async def checkout_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            form = _read_simple_form_data(await request.body())
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(form.get("workspace_id") or query.get("workspace_id") or "").strip()
            working_save_id = str(form.get("working_save_id") or "").strip()
            if not workspace_id:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/checkout?app_language={app_language}&action=checkout&status=error&reason=workspace_id_required", status_code=303)
            json_body: dict[str, Any] = {"share_id": share_id}
            if working_save_id:
                json_body["working_save_id"] = working_save_id
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/workspaces/{workspace_id}/shell/checkout",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id},
                query_params={"app_language": app_language},
                json_body=json_body,
                session_claims=self._resolve_session_claims(request),
            )
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
                feedback_rows=self.dependencies.feedback_rows_provider(),
            )
            if outbound.status_code != 200:
                payload = json.loads(outbound.body_text) if outbound.body_text else {}
                reason = str(payload.get("reason_code") or "checkout_failed").strip() or "checkout_failed"
                ws_q = f"&workspace_id={workspace_id}" if workspace_id else ""
                back = f"/app/public-shares/{share_id}/checkout?app_language={app_language}{ws_q}&action=checkout&status=error&reason={quote(reason)}"
                if working_save_id:
                    back += f"&working_save_id={quote(working_save_id)}"
                return RedirectResponse(url=back, status_code=303)
            target = f"/app/workspaces/{workspace_id}?app_language={app_language}&action=checkout&status=done&source_share_id={share_id}"
            if working_save_id:
                target += f"&working_save_id={quote(working_save_id)}"
            return RedirectResponse(url=target, status_code=303)

        @router.get("/app/public-shares/{share_id}/import")
        async def get_public_share_import_page(request: Request, share_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method="GET",
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            payload["app_language"] = app_language
            payload["prefill_workspace_id"] = workspace_id or ""
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_public_share_import_html(payload, app_language=app_language, workspace_id=workspace_id), status_code=200)

        @router.post("/app/public-shares/{share_id}/import")
        async def import_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            form = _read_simple_form_data(await request.body())
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(form.get("workspace_id") or query.get("workspace_id") or "").strip()
            if not workspace_id:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/import?app_language={app_language}&action=import_copy&status=error&reason=workspace_id_required", status_code=303)
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            workspace_row = self.dependencies.workspace_row_provider(workspace_id)
            if workspace_context is None or workspace_row is None:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/import?app_language={app_language}&workspace_id={quote(workspace_id)}&action=import_copy&status=error&reason=workspace_not_found", status_code=303)
            share_payload = self.dependencies.public_share_payload_provider(share_id) if self.dependencies.public_share_payload_provider is not None else None
            if not isinstance(share_payload, Mapping):
                return RedirectResponse(url=f"/app/public-shares/{share_id}/import?app_language={app_language}&workspace_id={quote(workspace_id)}&action=import_copy&status=error&reason=share_not_found", status_code=303)
            from src.storage.share_api import ensure_public_nex_link_share_operation_allowed
            from src.storage.validators.shared_validator import load_nex
            from src.storage.serialization import serialize_nex_artifact
            try:
                ensure_public_nex_link_share_operation_allowed(share_payload, "import_copy")
            except ValueError as exc:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/import?app_language={app_language}&workspace_id={quote(workspace_id)}&action=import_copy&status=error&reason={quote(str(exc))}", status_code=303)
            loaded_share = load_nex(share_payload["artifact"])
            model = loaded_share.parsed_model
            serialized = serialize_nex_artifact(model)
            if self.dependencies.workspace_artifact_source_writer is not None:
                self.dependencies.workspace_artifact_source_writer(workspace_id, serialized)
            storage_role = str(serialized.get("meta", {}).get("storage_role") or "unknown")
            target = f"/app/workspaces/{workspace_id}?app_language={app_language}&action=import_copy&status=done&source_share_id={share_id}&storage_role={quote(storage_role)}"
            return RedirectResponse(url=target, status_code=303)

        @router.get("/app/public-shares/{share_id}/run")
        async def get_public_share_run_page(request: Request, share_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method="GET",
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            payload["app_language"] = app_language
            payload["prefill_workspace_id"] = workspace_id or ""
            payload["prefill_input_payload_json"] = str(query.get("input_payload_json") or "")
            payload["notice"] = _public_share_notice_payload(request)
            return HTMLResponse(content=render_public_share_run_html(payload, app_language=app_language, workspace_id=workspace_id), status_code=200)

        @router.post("/app/public-shares/{share_id}/run")
        async def run_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            form = _read_simple_form_data(await request.body())
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(form.get("workspace_id") or query.get("workspace_id") or "").strip()
            input_payload_json = str(form.get("input_payload_json") or "").strip()
            if not workspace_id:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&action=run_artifact&status=error&reason=workspace_id_required", status_code=303)
            workspace_context = self.dependencies.workspace_context_provider(workspace_id)
            workspace_row = self.dependencies.workspace_row_provider(workspace_id)
            if workspace_context is None or workspace_row is None:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason=workspace_not_found", status_code=303)
            share_payload = self.dependencies.public_share_payload_provider(share_id) if self.dependencies.public_share_payload_provider is not None else None
            if not isinstance(share_payload, Mapping):
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason=share_not_found", status_code=303)
            from src.storage.share_api import ensure_public_nex_link_share_operation_allowed
            from src.storage.validators.shared_validator import load_nex
            try:
                ensure_public_nex_link_share_operation_allowed(share_payload, "run_artifact")
            except ValueError as exc:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason={quote(str(exc))}", status_code=303)
            input_payload = None
            if input_payload_json:
                try:
                    input_payload = json.loads(input_payload_json)
                except json.JSONDecodeError:
                    return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason=input_payload_invalid_json&input_payload_json={quote(input_payload_json)}", status_code=303)
            loaded_share = load_nex(share_payload["artifact"])
            if loaded_share.parsed_model is None:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason=share_artifact_invalid", status_code=303)
            model = loaded_share.parsed_model
            storage_role = str(getattr(model.meta, "storage_role", "") or "").strip()
            target_ref = str(getattr(model.meta, "commit_id", "") or getattr(model.meta, "working_save_id", "") or "").strip()
            if not target_ref or storage_role not in {"commit_snapshot", "working_save"}:
                return RedirectResponse(url=f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason=share_target_unsupported", status_code=303)
            target_type = "commit_snapshot" if storage_role == "commit_snapshot" else "working_save"
            target_catalog = dict(self.dependencies.target_catalog_provider(workspace_id) or {})
            target_catalog[target_ref] = ExecutionTargetCatalogEntry(
                workspace_id=workspace_id,
                target_ref=target_ref,
                target_type=target_type,
                source=share_payload["artifact"],
            )
            launch_payload: dict[str, Any] = {
                "workspace_id": workspace_id,
                "execution_target": {"target_type": target_type, "target_ref": target_ref},
                "client_context": {"source": "public_share_run", "correlation_token": share_id},
            }
            if input_payload is not None:
                launch_payload["input_payload"] = input_payload
            if target_type == "working_save":
                launch_payload["launch_options"] = {"allow_working_save_execution": True}
            inbound = FrameworkInboundRequest(
                method="POST",
                path="/api/runs",
                headers=dict(request.headers),
                path_params={},
                query_params={"app_language": app_language},
                json_body=launch_payload,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_launch(
                request=inbound,
                workspace_context=workspace_context,
                target_catalog=target_catalog,
                policy=self.dependencies.admission_policy,
                engine_launch_decider=self.dependencies.engine_launch_decider,
                run_id_factory=self.dependencies.run_id_factory,
                run_request_id_factory=self.dependencies.run_request_id_factory,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
                workspace_row=workspace_row,
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                provider_binding_rows=self.dependencies.workspace_provider_binding_rows_provider(workspace_id),
                managed_secret_rows=self.dependencies.recent_managed_secret_rows_provider(),
                provider_probe_rows=self.dependencies.workspace_provider_probe_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
            )
            if outbound.status_code != 202:
                payload = json.loads(outbound.body_text) if outbound.body_text else {}
                reason = str(payload.get("reason_code") or "run_artifact_failed").strip() or "run_artifact_failed"
                back = f"/app/public-shares/{share_id}/run?app_language={app_language}&workspace_id={quote(workspace_id)}&action=run_artifact&status=error&reason={quote(reason)}"
                if input_payload_json:
                    back += f"&input_payload_json={quote(input_payload_json)}"
                return RedirectResponse(url=back, status_code=303)
            launch_result = json.loads(outbound.body_text) if outbound.body_text else {}
            run_id = str(launch_result.get("run_id") or "").strip()
            target = f"/app/workspaces/{workspace_id}?app_language={app_language}&action=run_artifact&status=accepted&source_share_id={share_id}"
            if run_id:
                target += f"&run_id={quote(run_id)}"
            return RedirectResponse(url=target, status_code=303)


        @router.post("/app/public-shares/{share_id}/revoke")
        async def revoke_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            form = _read_simple_form_data(await request.body())
            origin = str(form.get("origin") or query.get("origin") or "detail").strip() or "detail"
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/public-shares/{share_id}/revoke",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=query,
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_revoke_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            status = "done" if outbound.status_code == 200 else "error"
            reason = str(payload.get("reason_code") or "").strip() or None
            target = _public_share_app_target(share_id=share_id, app_language=app_language, workspace_id=workspace_id, origin=origin)
            sep = '&' if '?' in target else '?'
            target = f"{target}{sep}action=revoke&status={status}"
            if reason:
                from urllib.parse import quote
                target += f"&reason={quote(reason)}"
            return RedirectResponse(url=target, status_code=303)

        @router.post("/app/public-shares/{share_id}/archive")
        async def archive_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            form = _read_simple_form_data(await request.body())
            origin = str(form.get("origin") or query.get("origin") or "detail").strip() or "detail"
            archived = str(form.get("archived") or "true").strip().lower() in {"1", "true", "yes", "on"}
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/public-shares/{share_id}/archive",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=query,
                json_body={"archived": archived},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_archive_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            status = "done" if outbound.status_code == 200 else "error"
            reason = str(payload.get("reason_code") or "").strip() or None
            target = _public_share_app_target(share_id=share_id, app_language=app_language, workspace_id=workspace_id, origin=origin)
            sep = '&' if '?' in target else '?'
            action_name = 'archive' if archived else 'unarchive'
            target = f"{target}{sep}action={action_name}&status={status}"
            if reason:
                from urllib.parse import quote
                target += f"&reason={quote(reason)}"
            return RedirectResponse(url=target, status_code=303)

        @router.post("/app/public-shares/{share_id}/extend")
        async def extend_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            form = _read_simple_form_data(await request.body())
            origin = str(form.get("origin") or query.get("origin") or "detail").strip() or "detail"
            expires_at = str(form.get("expires_at") or "").strip()
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/public-shares/{share_id}/extend",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=query,
                json_body={"expires_at": expires_at},
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_extend_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_writer=self.dependencies.public_share_payload_writer,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            status = "done" if outbound.status_code == 200 else "error"
            reason = str(payload.get("reason_code") or "").strip() or None
            target = _public_share_app_target(share_id=share_id, app_language=app_language, workspace_id=workspace_id, origin=origin)
            sep = '&' if '?' in target else '?'
            target = f"{target}{sep}action=extend&status={status}"
            if reason:
                from urllib.parse import quote
                target += f"&reason={quote(reason)}"
            return RedirectResponse(url=target, status_code=303)

        @router.post("/app/public-shares/{share_id}/delete")
        async def delete_public_share_page(request: Request, share_id: str) -> Response:
            query = dict(request.query_params)
            app_language = str(query.get("app_language") or "en")
            workspace_id = str(query.get("workspace_id") or "").strip() or None
            inbound = FrameworkInboundRequest(
                method="DELETE",
                path=f"/api/public-shares/{share_id}",
                headers=dict(request.headers),
                path_params={"share_id": share_id},
                query_params=query,
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_delete_public_share(
                request=inbound,
                share_payload_provider=self.dependencies.public_share_payload_provider,
                share_payload_rows_provider=self.dependencies.public_share_payload_rows_provider,
                public_share_action_report_rows_provider=self.dependencies.public_share_action_report_rows_provider,
                public_share_payload_deleter=self.dependencies.public_share_payload_deleter,
                public_share_action_report_writer=self.dependencies.public_share_action_report_writer,
                now_iso=self.dependencies.now_iso_provider() if self.dependencies.now_iso_provider is not None else None,
            )
            payload = json.loads(outbound.body_text) if outbound.body_text else {}
            status = "done" if outbound.status_code == 200 else "error"
            reason = str(payload.get("reason_code") or "").strip() or None
            target = _public_share_delete_target(app_language=app_language, workspace_id=workspace_id, share_id=share_id, status=status, reason=reason)
            return RedirectResponse(url=target, status_code=303)

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

        @router.get("/app/workspaces/{workspace_id}/starter-templates")
        async def get_workspace_starter_template_catalog_page(request: Request, workspace_id: str) -> Response:
            if self.dependencies.workspace_context_provider(workspace_id) is None or self.dependencies.workspace_row_provider(workspace_id) is None:
                return JSONResponse(status_code=404, content={"error_family": "workspace_read_failure", "reason_code": "workspace.not_found", "message": "Requested workspace was not found."})
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
            app_language = str(dict(request.query_params).get("app_language") or payload.get("app_language") or "en")
            payload.setdefault("routes", {})["app_catalog"] = f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}"
            payload["routes"]["workspace_page"] = f"/app/workspaces/{workspace_id}?app_language={app_language}"
            payload["routes"]["workspace_app_library"] = f"/app/workspaces/{workspace_id}/library?app_language={app_language}"
            payload["routes"]["workspace_feedback_page"] = f"/app/workspaces/{workspace_id}/feedback?surface=starter_templates&app_language={app_language}"
            for template in list(payload.get("templates") or []):
                template_routes = dict(template.get("routes") or {})
                template_id = str(template.get("template_id") or "").strip()
                if not template_id:
                    continue
                template_routes["app_workspace_detail"] = f"/app/workspaces/{workspace_id}/starter-templates/{template_id}?app_language={app_language}"
                template["routes"] = template_routes
            return HTMLResponse(content=render_starter_template_catalog_html(payload), status_code=200)

        @router.get("/app/workspaces/{workspace_id}/starter-templates/{template_id}")
        async def get_workspace_starter_template_detail_page(request: Request, workspace_id: str, template_id: str) -> Response:
            if self.dependencies.workspace_context_provider(workspace_id) is None or self.dependencies.workspace_row_provider(workspace_id) is None:
                return JSONResponse(status_code=404, content={"error_family": "workspace_read_failure", "reason_code": "workspace.not_found", "message": "Requested workspace was not found."})
            inbound = FrameworkInboundRequest(
                method=request.method,
                path=f"/api/templates/starter-circuits/{template_id}",
                headers=dict(request.headers),
                path_params={"template_id": template_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_get_starter_circuit_template(request=inbound)
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            payload = json.loads(outbound.body_text)
            app_language = str(dict(request.query_params).get("app_language") or payload.get("app_language") or "en")
            payload.setdefault("routes", {})["workspace_page"] = f"/app/workspaces/{workspace_id}?app_language={app_language}"
            payload["routes"]["workspace_app_library"] = f"/app/workspaces/{workspace_id}/library?app_language={app_language}"
            payload["routes"]["workspace_feedback_page"] = f"/app/workspaces/{workspace_id}/feedback?surface=starter_templates&template_id={template_id}&app_language={app_language}"
            payload["routes"]["workspace_templates_page"] = f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}"
            payload["routes"]["workspace_apply_html"] = f"/app/workspaces/{workspace_id}/starter-templates/{template_id}/apply?app_language={app_language}"
            payload["routes"]["api_detail"] = f"/api/templates/starter-circuits/{template_id}"
            return HTMLResponse(content=render_starter_template_detail_html(payload), status_code=200)

        @router.post("/app/workspaces/{workspace_id}/starter-templates/{template_id}/apply")
        async def apply_workspace_starter_template_page(request: Request, workspace_id: str, template_id: str) -> Response:
            inbound = FrameworkInboundRequest(
                method="POST",
                path=f"/api/workspaces/{workspace_id}/starter-templates/{template_id}/apply",
                headers=dict(request.headers),
                path_params={"workspace_id": workspace_id, "template_id": template_id},
                query_params=dict(request.query_params),
                json_body=None,
                session_claims=self._resolve_session_claims(request),
            )
            outbound = FrameworkRouteBindings.handle_apply_starter_circuit_template(
                request=inbound,
                workspace_context=self.dependencies.workspace_context_provider(workspace_id),
                workspace_row=self.dependencies.workspace_row_provider(workspace_id),
                artifact_source=self.dependencies.workspace_artifact_source_provider(workspace_id),
                recent_run_rows=self.dependencies.recent_run_rows_provider(),
                result_rows_by_run_id=self.dependencies.workspace_result_rows_provider(workspace_id),
                onboarding_rows=self.dependencies.onboarding_rows_provider(),
                artifact_rows_lookup=self.dependencies.artifact_rows_provider,
                trace_rows_lookup=self.dependencies.trace_rows_provider,
                workspace_artifact_source_writer=self.dependencies.workspace_artifact_source_writer,
            )
            framework_response = self._framework_response(outbound)
            if framework_response.status_code != 200:
                return framework_response
            app_language = str(dict(request.query_params).get("app_language") or "en")
            return RedirectResponse(url=f"/app/workspaces/{workspace_id}?app_language={app_language}", status_code=303)

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

        @router.get("/app/workspaces/{workspace_id}/library")
        async def get_workspace_circuit_library_page(request: Request, workspace_id: str) -> Response:
            if self.dependencies.workspace_context_provider(workspace_id) is None or self.dependencies.workspace_row_provider(workspace_id) is None:
                return JSONResponse(status_code=404, content={"error_family": "workspace_read_failure", "reason_code": "workspace.not_found", "message": "Requested workspace was not found."})
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
            app_language = str(dict(request.query_params).get("app_language") or payload.get("app_language") or "en")
            payload.setdefault("routes", {})["app_library"] = f"/app/workspaces/{workspace_id}/library?app_language={app_language}"
            payload["routes"]["workspace_page"] = f"/app/workspaces/{workspace_id}?app_language={app_language}"
            payload["routes"]["starter_template_catalog_page"] = f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}"
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
            app_language = str(dict(request.query_params).get("app_language") or payload.get("app_language") or "en")
            payload.setdefault("routes", {})["workspace_feedback_page"] = f"/app/workspaces/{workspace_id}/feedback?surface=result_history&app_language={app_language}"
            payload["routes"]["workspace_page"] = f"/app/workspaces/{workspace_id}?app_language={app_language}"
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
            app_language = str(dict(request.query_params).get("app_language") or payload.get("app_language") or "en")
            payload.setdefault("routes", {})["workspace_library"] = f"/app/workspaces/{workspace_id}/library?app_language={app_language}"
            payload["routes"]["starter_template_catalog_page"] = f"/app/workspaces/{workspace_id}/starter-templates?app_language={app_language}"
            payload["routes"]["workspace_page"] = f"/app/workspaces/{workspace_id}?app_language={app_language}"
            payload["routes"]["result_history"] = f"/app/workspaces/{workspace_id}/results?app_language={app_language}"
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
