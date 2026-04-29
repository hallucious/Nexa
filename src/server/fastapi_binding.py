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
from src.server.fastapi_app_bootstrap import install_fastapi_app_observability_bootstrap
from src.server.fastapi_edge_middleware import register_fastapi_edge_middleware
from src.server.workspace_shell_runtime import render_workspace_shell_runtime_html
from src.server.circuit_library_runtime import render_circuit_library_runtime_html
from src.server.result_history_runtime import render_workspace_result_history_html
from src.server.starter_template_runtime import render_starter_template_catalog_html, render_starter_template_detail_html
from src.server.public_community_runtime import render_public_community_hub_html
from src.server.public_plugin_runtime import render_public_plugin_catalog_html
from src.server.public_ecosystem_runtime import render_public_ecosystem_catalog_html
from src.server.public_sdk_runtime import render_public_sdk_catalog_html
from src.server.public_mcp_runtime import render_public_mcp_catalog_html
from src.server.public_provider_runtime import render_public_provider_catalog_html
from src.server.public_nex_runtime import render_public_nex_format_html
from src.server.public_hub_runtime import render_public_hub_html
from src.server.web_skeleton_runtime import render_web_sign_in_html, render_web_workspace_dashboard_html, render_web_upload_entry_html, render_web_run_entry_html
from src.server.public_integration_runtime import render_public_integration_hub_html
from src.server.feedback_runtime import render_workspace_feedback_html
from src.server.run_admission_models import ExecutionTargetCatalogEntry
from src.server.provider_probe_resolution import resolve_managed_secret_metadata_reader, resolve_provider_probe_runner
from src.server.public_share_runtime import (
    _canonical_ref_for_workspace_artifact,
    build_workspace_public_share_history_payload,
    render_workspace_public_share_history_html,
    render_workspace_share_create_html,
    render_public_share_catalog_html,
    render_public_share_catalog_summary_html,
    render_public_share_issuer_catalog_html,
    render_public_share_issuer_summary_html,
    render_public_share_compare_html,
    render_public_share_checkout_html,
    render_public_share_download_html,
    render_public_share_import_html,
    render_public_share_create_workspace_html,
    render_public_share_run_html,
    render_public_share_detail_html,
    render_public_share_history_html,
    render_public_share_related_html,
    render_saved_public_share_collection_html,
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


def _public_share_artifact_download_filename(*, share_id: str, share_title: str, storage_role: str) -> str:
    base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in (share_title or share_id).lower()).strip("-")
    if not base:
        base = share_id or "public-share"
    role = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in (storage_role or "artifact").lower()).strip("-") or "artifact"
    return f"{base}-{role}.nex.json"


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
        from src.server.fastapi_route_registry import build_fastapi_router

        return build_fastapi_router(self)

    def build_app(self) -> FastAPI:
        app = FastAPI(title=self.config.title, version=self.config.version)
        install_fastapi_app_observability_bootstrap(
            app,
            self.config,
            session_claims_resolver=self._resolve_session_claims,
        )
        register_fastapi_edge_middleware(
            app=app,
            config=self.config,
            dependencies=self.dependencies,
            session_claims_resolver=self._resolve_session_claims,
        )
        app.include_router(self.build_router())
        return app

    def _resolve_managed_secret_metadata_reader(self):
        client = self.dependencies.aws_secrets_manager_client_provider() if self.dependencies.aws_secrets_manager_client_provider is not None else None
        return resolve_managed_secret_metadata_reader(
            secret_metadata_reader=self.dependencies.managed_secret_metadata_reader,
            aws_secrets_manager_client=client,
            aws_secrets_manager_config=self.dependencies.aws_secrets_manager_config or AwsSecretsManagerBindingConfig(),
        )

    def _resolve_provider_probe_runner(self):
        client = self.dependencies.aws_secrets_manager_client_provider() if self.dependencies.aws_secrets_manager_client_provider is not None else None
        return resolve_provider_probe_runner(
            probe_runner=self.dependencies.provider_probe_runner,
            aws_secrets_manager_client=client,
            aws_secrets_manager_config=self.dependencies.aws_secrets_manager_config or AwsSecretsManagerBindingConfig(),
        )

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
