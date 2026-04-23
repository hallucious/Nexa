from __future__ import annotations

from src.server import (
    ProductProviderBindingWriteRequest,
    ProviderSecretIntegrationService,
    RequestAuthResolver,
    RunHttpRouteSurface,
    HttpRouteRequest,
    WorkspaceAuthorizationContext,
)


def _auth(user_id: str = 'user-owner', roles: list[str] | None = None):
    return RequestAuthResolver.resolve(
        headers={'Authorization': 'Bearer token'},
        session_claims={'sub': user_id, 'sid': 'sess-001', 'exp': 4102444800, 'roles': roles or ['admin']},
    )


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id='ws-001',
        owner_user_ref='user-owner',
        collaborator_user_refs=('user-collab',),
        viewer_user_refs=('user-viewer',),
    )


def _catalog_row() -> dict:
    return {
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'managed_supported': True,
        'recommended_scope': 'workspace',
        'local_env_var_hint': 'OPENAI_API_KEY',
        'default_secret_name_template': 'nexa/{workspace_id}/providers/openai',
    }


def _workspace_row() -> dict:
    return {
        'workspace_id': 'ws-001',
        'owner_user_id': 'user-owner',
        'title': 'Primary Workspace',
        'description': 'Workspace description',
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:05:00+00:00',
        'last_run_id': 'run-001',
        'last_result_status': 'completed',
        'continuity_source': 'server',
        'archived': False,
    }


def _membership() -> dict:
    return {
        'membership_id': 'membership-001',
        'workspace_id': 'ws-001',
        'user_id': 'user-owner',
        'role': 'owner',
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:05:00+00:00',
    }


def _binding_row() -> dict:
    return {
        'binding_id': 'binding-001',
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'credential_source': 'managed',
        'secret_ref': 'secret://ws-001/openai',
        'secret_version_ref': 'v1',
        'enabled': True,
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:05:00+00:00',
        'updated_by_user_id': 'user-owner',
    }


def test_provider_catalog_and_workspace_binding_list_round_trip() -> None:
    catalog_outcome = ProviderSecretIntegrationService.list_provider_catalog(
        request_auth=_auth(),
        provider_catalog_rows=(_catalog_row(),),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=(_binding_row(),),
        managed_secret_rows=({'workspace_id': 'ws-001', 'provider_key': 'openai', 'secret_ref': 'secret://ws-001/openai', 'last_rotated_at': '2026-04-11T12:06:30+00:00'},),
        provider_probe_rows=({'probe_event_id': 'probe-001', 'workspace_id': 'ws-001', 'provider_key': 'openai', 'provider_family': 'openai', 'display_name': 'OpenAI GPT', 'probe_status': 'reachable', 'connectivity_state': 'ok', 'secret_resolution_status': 'resolved', 'requested_model_ref': 'gpt-4.1', 'effective_model_ref': 'gpt-4.1', 'occurred_at': '2026-04-11T12:08:00+00:00', 'requested_by_user_id': 'user-owner', 'message': 'Probe completed.'},),
        onboarding_rows=({'onboarding_state_id': 'onboard-001', 'user_id': 'user-owner', 'workspace_id': 'ws-001', 'updated_at': '2026-04-11T12:09:00+00:00'},),
    )
    assert catalog_outcome.ok is True
    assert catalog_outcome.response is not None
    assert catalog_outcome.response.providers[0].provider_key == 'openai'
    assert catalog_outcome.response.provider_continuity is not None
    assert catalog_outcome.response.provider_continuity.provider_binding_count == 1
    assert catalog_outcome.response.activity_continuity is not None
    assert catalog_outcome.response.activity_continuity.latest_run_id == 'run-001'

    list_outcome = ProviderSecretIntegrationService.list_workspace_provider_bindings(
        request_auth=_auth(),
        workspace_context=_workspace(),
        binding_rows=({
            'binding_id': 'binding-001',
            'workspace_id': 'ws-001',
            'provider_key': 'openai',
            'provider_family': 'openai',
            'display_name': 'OpenAI GPT',
            'credential_source': 'managed',
            'secret_ref': 'secret://ws-001/openai',
            'secret_version_ref': 'v1',
            'enabled': True,
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:05:00+00:00',
            'updated_by_user_id': 'user-owner',
        },),
        provider_catalog_rows=(_catalog_row(),),
    )
    assert list_outcome.ok is True
    assert list_outcome.response is not None
    assert list_outcome.response.bindings[0].status == 'configured'
    assert list_outcome.response.provider_continuity is not None
    assert list_outcome.response.provider_continuity.provider_binding_count == 1


def test_provider_binding_upsert_requires_manage_scope_and_never_echoes_secret() -> None:
    denied = ProviderSecretIntegrationService.upsert_workspace_provider_binding(
        request_auth=_auth('user-viewer', ['viewer']),
        workspace_context=_workspace(),
        provider_key='openai',
        request=ProductProviderBindingWriteRequest(secret_value='secret-1', enabled=True),
        existing_binding_row=None,
        provider_catalog_rows=(_catalog_row(),),
        workspace_row={'workspace_id': 'ws-001', 'title': 'Primary Workspace'},
        binding_rows=({'workspace_id': 'ws-001', 'binding_id': 'binding-000', 'provider_key': 'openai', 'updated_at': '2026-04-11T12:00:00+00:00'},),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'status_family': 'running', 'created_at': '2026-04-11T12:01:00+00:00', 'updated_at': '2026-04-11T12:02:00+00:00', 'started_at': '2026-04-11T12:01:10+00:00'},),
        binding_id_factory=lambda: 'binding-001',
        secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v2',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },
        now_iso='2026-04-11T12:06:00+00:00',
    )
    assert denied.ok is False
    assert denied.rejected is not None
    assert denied.rejected.reason_code.endswith('role_insufficient')
    assert denied.rejected.workspace_title == 'Primary Workspace'
    assert denied.rejected.provider_continuity is not None
    assert denied.rejected.activity_continuity is not None

    accepted = ProviderSecretIntegrationService.upsert_workspace_provider_binding(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key='openai',
        request=ProductProviderBindingWriteRequest(secret_value='super-secret', enabled=True),
        existing_binding_row=None,
        provider_catalog_rows=(_catalog_row(),),
        binding_id_factory=lambda: 'binding-001',
        secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v2',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },
        now_iso='2026-04-11T12:06:00+00:00',
    )
    assert accepted.ok is True
    assert accepted.accepted is not None
    assert accepted.accepted.binding.secret_ref == 'secret://ws-001/openai'
    assert accepted.accepted.secret_rotated is True
    assert 'super-secret' not in str(accepted.accepted)


def test_provider_secret_http_routes_round_trip() -> None:
    catalog_response = RunHttpRouteSurface.handle_list_provider_catalog(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/providers/catalog',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-owner', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['admin']},
        ),
        provider_catalog_rows=(_catalog_row(),),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=(_binding_row(),),
        managed_secret_rows=({'workspace_id': 'ws-001', 'provider_key': 'openai', 'secret_ref': 'secret://ws-001/openai', 'last_rotated_at': '2026-04-11T12:06:30+00:00'},),
        provider_probe_rows=({'probe_event_id': 'probe-001', 'workspace_id': 'ws-001', 'provider_key': 'openai', 'provider_family': 'openai', 'display_name': 'OpenAI GPT', 'probe_status': 'reachable', 'connectivity_state': 'ok', 'secret_resolution_status': 'resolved', 'requested_model_ref': 'gpt-4.1', 'effective_model_ref': 'gpt-4.1', 'occurred_at': '2026-04-11T12:08:00+00:00', 'requested_by_user_id': 'user-owner', 'message': 'Probe completed.'},),
        onboarding_rows=({'onboarding_state_id': 'onboard-001', 'user_id': 'user-owner', 'workspace_id': 'ws-001', 'updated_at': '2026-04-11T12:09:00+00:00'},),
    )
    assert catalog_response.status_code == 200
    assert catalog_response.body['providers'][0]['provider_key'] == 'openai'
    assert catalog_response.body['provider_continuity']['provider_binding_count'] == 1
    assert catalog_response.body['activity_continuity']['latest_run_id'] == 'run-001'

    list_response = RunHttpRouteSurface.handle_list_workspace_provider_bindings(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/workspaces/ws-001/provider-bindings',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-owner', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['admin']},
            path_params={'workspace_id': 'ws-001'},
        ),
        workspace_context=_workspace(),
        binding_rows=(),
        provider_catalog_rows=(_catalog_row(),),
    )
    assert list_response.status_code == 200
    assert list_response.body['workspace_id'] == 'ws-001'
    assert list_response.body['provider_continuity'] is None

    put_response = RunHttpRouteSurface.handle_put_workspace_provider_binding(
        http_request=HttpRouteRequest(
            method='PUT',
            path='/api/workspaces/ws-001/provider-bindings/openai',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-owner', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['admin']},
            path_params={'workspace_id': 'ws-001', 'provider_key': 'openai'},
            json_body={'display_name': 'OpenAI GPT', 'secret_value': 'very-secret', 'enabled': True},
        ),
        workspace_context=_workspace(),
        existing_binding_row=None,
        provider_catalog_rows=(_catalog_row(),),
        binding_id_factory=lambda: 'binding-001',
        secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v2',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },
        now_iso='2026-04-11T12:06:00+00:00',
    )
    assert put_response.status_code == 200
    assert put_response.body['binding']['provider_key'] == 'openai'
    assert put_response.body['provider_continuity'] is not None
    assert put_response.body['binding']['secret_ref'] == 'secret://ws-001/openai'
    assert 'very-secret' not in str(put_response.body)
