from __future__ import annotations

import pytest

from src.server import (
    AwsSecretsManagerBindingConfig,
    AwsSecretsManagerSecretAuthority,
    FrameworkRouteBindings,
    HttpRouteRequest,
    ProviderHealthService,
    RequestAuthResolver,
    RunHttpRouteSurface,
    WorkspaceAuthorizationContext,
)

pytest.importorskip("fastapi")


def _auth(user_id: str = "user-owner", roles: list[str] | None = None):
    return RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": roles or ["admin"]},
    )


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _catalog_rows():
    return ({
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "managed_supported": True,
        "recommended_scope": "workspace",
        "local_env_var_hint": "OPENAI_API_KEY",
        "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
    },)


def _binding_rows(secret_ref: str = "aws-secretsmanager://nexa/ws-001/providers/openai"):
    return ({
        "binding_id": "binding-001",
        "workspace_id": "ws-001",
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "credential_source": "managed",
        "secret_ref": secret_ref,
        "secret_version_ref": "v1",
        "enabled": True,
        "default_model_ref": "gpt-4.1",
        "allowed_model_refs": ("gpt-4.1", "gpt-4o"),
        "created_at": "2026-04-11T12:00:00+00:00",
        "updated_at": "2026-04-11T12:05:00+00:00",
        "updated_by_user_id": "user-owner",
    },)


class _FakeSecretsClient:
    def describe_secret(self, SecretId: str):
        if SecretId != "nexa/ws-001/providers/openai":
            raise type("ResourceNotFoundException", (Exception,), {})()
        return {"ARN": "arn:aws:secretsmanager:region:acct:secret:nexa/ws-001/providers/openai", "LastChangedDate": "2026-04-11T12:06:00+00:00"}


def test_provider_health_service_and_route_round_trip() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )
    outcome = ProviderHealthService.list_workspace_provider_health(
        request_auth=_auth(),
        workspace_context=_workspace(),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
    )
    assert outcome.ok is True
    assert outcome.response is not None
    health = outcome.response.providers[0]
    assert health.health_status == "healthy"
    assert health.secret_resolution_status == "resolved"

    route_response = RunHttpRouteSurface.handle_get_workspace_provider_health(
        http_request=HttpRouteRequest(
            method="GET",
            path="/api/workspaces/ws-001/provider-bindings/openai/health",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
        ),
        workspace_context=_workspace(),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
    )
    assert route_response.status_code == 200
    assert route_response.body["provider_key"] == "openai"
    assert route_response.body["health"]["provider_key"] == "openai"
    assert route_response.body["health"]["secret_resolution_status"] == "resolved"


def test_provider_health_list_round_trip_in_framework_binding() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )
    from src.server import FrameworkInboundRequest
    response = FrameworkRouteBindings.handle_list_workspace_provider_health(
        request=FrameworkInboundRequest(
            method="GET",
            path="/api/workspaces/ws-001/provider-bindings/health",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"workspace_id": "ws-001"},
        ),
        workspace_context=_workspace(),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
    )
    assert response.status_code == 200


def test_provider_health_denied_response_includes_continuity_snapshot() -> None:
    outcome = ProviderHealthService.list_workspace_provider_health(
        request_auth=_auth("user-viewer", ["viewer"]),
        workspace_context=_workspace(),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=None,
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=({"workspace_id": "ws-001", "run_id": "run-001", "status_family": "running", "created_at": "2026-04-11T12:00:00+00:00", "updated_at": "2026-04-11T12:00:00+00:00", "started_at": "2026-04-11T12:00:01+00:00"},),
    )
    assert outcome.ok is False
    assert outcome.rejected is not None
    assert outcome.rejected.workspace_title == "Primary Workspace"
    assert outcome.rejected.provider_continuity is not None
    assert outcome.rejected.activity_continuity is not None
