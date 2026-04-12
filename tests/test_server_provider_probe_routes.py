from __future__ import annotations

import pytest

from src.server import (
    AwsSecretsManagerBindingConfig,
    AwsSecretsManagerSecretAuthority,
    FrameworkInboundRequest,
    FrameworkRouteBindings,
    HttpRouteRequest,
    ProductProviderProbeRequest,
    ProviderProbeExecutionInput,
    ProviderProbeService,
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


def _probe_runner(probe_input: ProviderProbeExecutionInput):
    assert probe_input.provider_key == "openai"
    return {
        "probe_status": "reachable",
        "connectivity_state": "ok",
        "message": "Provider connectivity probe succeeded.",
        "effective_model_ref": probe_input.requested_model_ref or probe_input.default_model_ref,
        "round_trip_latency_ms": 187,
    }


def test_provider_probe_service_and_route_round_trip() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )
    outcome = ProviderProbeService.probe_workspace_provider(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key="openai",
        request=ProductProviderProbeRequest(model_ref="gpt-4.1"),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
        probe_runner=_probe_runner,
        now_iso="2026-04-11T12:07:00+00:00",
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.probe_status == "reachable"
    assert outcome.response.connectivity_state == "ok"
    assert outcome.response.secret_resolution_status == "resolved"
    assert outcome.response.provider_continuity is not None

    route_response = RunHttpRouteSurface.handle_probe_workspace_provider(
        http_request=HttpRouteRequest(
            method="POST",
            path="/api/workspaces/ws-001/provider-bindings/openai/probe",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
            json_body={"model_ref": "gpt-4.1"},
        ),
        workspace_context=_workspace(),
        provider_key="openai",
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
        probe_runner=_probe_runner,
        now_iso="2026-04-11T12:07:00+00:00",
    )
    assert route_response.status_code == 200
    assert route_response.body["probe_status"] == "reachable"
    assert route_response.body['effective_model_ref'] == 'gpt-4.1'
    assert route_response.body['provider_continuity'] is not None


def test_provider_probe_framework_round_trip() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )
    response = FrameworkRouteBindings.handle_probe_workspace_provider(
        request=FrameworkInboundRequest(
            method="POST",
            path="/api/workspaces/ws-001/provider-bindings/openai/probe",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
            json_body={"model_ref": "gpt-4.1"},
        ),
        workspace_context=_workspace(),
        provider_key="openai",
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
        probe_runner=_probe_runner,
        now_iso="2026-04-11T12:07:00+00:00",
    )
    assert response.status_code == 200


def test_provider_probe_service_builds_persistable_probe_history_row() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )
    written_rows: list[dict] = []

    outcome = ProviderProbeService.probe_workspace_provider(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key="openai",
        request=ProductProviderProbeRequest(model_ref="gpt-4.1"),
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
        probe_runner=_probe_runner,
        probe_event_id_factory=lambda: "probe-123",
        probe_history_writer=lambda row: written_rows.append(dict(row)),
        now_iso="2026-04-11T12:07:00+00:00",
    )

    assert outcome.ok is True
    assert outcome.persisted_probe_row is not None
    assert outcome.persisted_probe_row["probe_event_id"] == "probe-123"
    assert outcome.persisted_probe_row["workspace_id"] == "ws-001"
    assert outcome.persisted_probe_row["provider_key"] == "openai"
    assert outcome.persisted_probe_row["probe_status"] == "reachable"
    assert written_rows == [outcome.persisted_probe_row]


def test_provider_probe_route_returns_conflict_when_probe_history_persistence_fails() -> None:
    reader = AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(
        client=_FakeSecretsClient(),
        config=AwsSecretsManagerBindingConfig(),
    )

    route_response = RunHttpRouteSurface.handle_probe_workspace_provider(
        http_request=HttpRouteRequest(
            method="POST",
            path="/api/workspaces/ws-001/provider-bindings/openai/probe",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
            json_body={"model_ref": "gpt-4.1"},
        ),
        workspace_context=_workspace(),
        provider_key="openai",
        binding_rows=_binding_rows(),
        provider_catalog_rows=_catalog_rows(),
        secret_metadata_reader=reader,
        probe_runner=_probe_runner,
        probe_event_id_factory=lambda: "probe-err",
        probe_history_writer=lambda row: (_ for _ in ()).throw(RuntimeError("write failed")),
        now_iso="2026-04-11T12:07:00+00:00",
    )
    assert route_response.status_code == 409
    assert route_response.body["reason_code"] == "provider_probe.persistence_write_failed"
