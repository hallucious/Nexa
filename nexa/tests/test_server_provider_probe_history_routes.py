from __future__ import annotations

from src.server import (
    FrameworkInboundRequest,
    FrameworkRouteBindings,
    HttpRouteRequest,
    ProviderProbeHistoryService,
    RequestAuthResolver,
    RunHttpRouteSurface,
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


def _probe_row(probe_event_id: str, occurred_at: str, *, probe_status: str = 'reachable', provider_key: str = 'openai') -> dict:
    return {
        'probe_event_id': probe_event_id,
        'binding_id': 'binding-001',
        'workspace_id': 'ws-001',
        'provider_key': provider_key,
        'provider_family': provider_key,
        'display_name': 'OpenAI GPT',
        'probe_status': probe_status,
        'connectivity_state': 'ok' if probe_status == 'reachable' else 'provider_error',
        'secret_resolution_status': 'resolved',
        'requested_model_ref': 'gpt-4.1',
        'effective_model_ref': 'gpt-4.1',
        'round_trip_latency_ms': 111,
        'requested_by_user_id': 'user-owner',
        'occurred_at': occurred_at,
        'message': 'Probe completed.',
    }


def test_provider_probe_history_service_returns_sorted_paginated_items() -> None:
    outcome = ProviderProbeHistoryService.list_workspace_provider_probe_history(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key='openai',
        probe_history_rows=(
            _probe_row('probe-001', '2026-04-11T12:06:00+00:00', probe_status='failed'),
            _probe_row('probe-002', '2026-04-11T12:07:00+00:00', probe_status='reachable'),
        ),
        limit=1,
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.returned_count == 1
    assert outcome.response.items[0].probe_event_id == 'probe-002'
    assert outcome.response.next_cursor == 'probe-002'


def test_provider_probe_history_route_round_trip() -> None:
    response = RunHttpRouteSurface.handle_list_provider_probe_history(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/workspaces/ws-001/provider-bindings/openai/probe-history',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-owner', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['admin']},
            path_params={'workspace_id': 'ws-001', 'provider_key': 'openai'},
            query_params={'limit': 2},
        ),
        workspace_context=_workspace(),
        provider_key='openai',
        probe_history_rows=(
            _probe_row('probe-001', '2026-04-11T12:06:00+00:00'),
            _probe_row('probe-002', '2026-04-11T12:07:00+00:00', probe_status='warning'),
        ),
    )
    assert response.status_code == 200
    assert response.body['returned_count'] == 2
    assert response.body['items'][0]['probe_event_id'] == 'probe-002'
    assert response.body['provider_continuity'] is None or response.body['provider_continuity']['recent_probe_count'] >= 1


def test_provider_probe_history_framework_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_provider_probe_history(
        request=FrameworkInboundRequest(
            method='GET',
            path='/api/workspaces/ws-001/provider-bindings/openai/probe-history',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-owner', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['admin']},
            path_params={'workspace_id': 'ws-001', 'provider_key': 'openai'},
            query_params={'limit': 1},
        ),
        workspace_context=_workspace(),
        provider_key='openai',
        probe_history_rows=(
            _probe_row('probe-001', '2026-04-11T12:06:00+00:00'),
            _probe_row('probe-002', '2026-04-11T12:07:00+00:00'),
        ),
    )
    assert response.status_code == 200
    assert 'probe-002' in response.body_text


def test_provider_probe_history_service_accepts_canonical_projection_row_aliases() -> None:
    outcome = ProviderProbeHistoryService.list_workspace_provider_probe_history(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key='openai',
        probe_history_rows=({
            'probe_id': 'probe-003',
            'workspace_id': 'ws-001',
            'binding_id': 'binding-001',
            'provider_key': 'openai',
            'provider_family': 'openai',
            'display_name': 'OpenAI GPT',
            'probe_status': 'reachable',
            'connectivity_state': 'ok',
            'created_at': '2026-04-11T12:08:00+00:00',
        },),
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.items[0].probe_event_id == 'probe-003'
    assert outcome.response.items[0].occurred_at == '2026-04-11T12:08:00+00:00'


def test_provider_probe_history_rejection_includes_workspace_continuity_for_invalid_cursor() -> None:
    outcome = ProviderProbeHistoryService.list_workspace_provider_probe_history(
        request_auth=_auth(),
        workspace_context=_workspace(),
        provider_key='openai',
        probe_history_rows=(
            _probe_row('probe-001', '2026-04-11T12:06:00+00:00'),
        ),
        workspace_row={'workspace_id': 'ws-001', 'title': 'Primary Workspace'},
        binding_rows=({'workspace_id': 'ws-001', 'binding_id': 'binding-001', 'updated_at': '2026-04-11T12:03:00+00:00'},),
        managed_secret_rows=({'workspace_id': 'ws-001', 'secret_ref': 'secret://ws-001/openai', 'last_rotated_at': '2026-04-11T12:04:00+00:00'},),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:00:00+00:00', 'updated_at': '2026-04-11T12:00:00+00:00', 'status_family': 'pending'},),
        onboarding_rows=({'workspace_id': 'ws-001', 'user_id': 'user-owner', 'onboarding_state_id': 'onboard-001', 'updated_at': '2026-04-11T12:06:00+00:00'},),
        cursor='missing-cursor',
    )
    assert outcome.ok is False
    assert outcome.rejected is not None
    assert outcome.rejected.reason_code == 'provider_probe_history.cursor_invalid'
    assert outcome.rejected.workspace_title == 'Primary Workspace'
    assert outcome.rejected.provider_continuity is not None
    assert outcome.rejected.activity_continuity is not None
