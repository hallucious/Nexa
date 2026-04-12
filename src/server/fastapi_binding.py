from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from fastapi import APIRouter, Body, FastAPI, Request
from fastapi.responses import JSONResponse, Response

from src.server.framework_binding import FrameworkRouteBindings
from src.server.aws_secrets_manager_binding import AwsSecretsManagerSecretAuthority
from src.server.aws_secrets_manager_models import AwsSecretsManagerBindingConfig
from src.server.framework_binding_models import FrameworkInboundRequest, FrameworkOutboundResponse
from src.server.fastapi_binding_models import FastApiBindingConfig, FastApiRouteDependencies


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
