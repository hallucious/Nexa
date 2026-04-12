from __future__ import annotations

from src.server import HttpRouteRequest, RecentActivityService, RequestAuthResolver, RunHttpRouteSurface


def _auth(user_id: str = 'user-owner'):
    return RequestAuthResolver.resolve(
        headers={'Authorization': 'Bearer token'},
        session_claims={'sub': user_id, 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['editor']},
    )


def _workspace_row(workspace_id: str = 'ws-001', *, owner_user_id: str = 'user-owner', title: str = 'Primary Workspace', updated_at: str = '2026-04-11T12:05:00+00:00') -> dict:
    return {
        'workspace_id': workspace_id,
        'owner_user_id': owner_user_id,
        'title': title,
        'description': 'Workspace description',
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': updated_at,
        'last_run_id': 'run-001',
        'last_result_status': 'completed',
        'continuity_source': 'server',
        'archived': False,
    }


def _membership(workspace_id: str = 'ws-001', *, user_id: str = 'user-collab', role: str = 'collaborator') -> dict:
    return {
        'membership_id': f'membership:{workspace_id}:{user_id}',
        'workspace_id': workspace_id,
        'user_id': user_id,
        'role': role,
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:00:00+00:00',
    }


def _run_row(run_id: str, created_at: str, *, status: str = 'running', status_family: str = 'active', workspace_id: str = 'ws-001', requested_by_user_id: str = 'user-owner') -> dict:
    return {
        'run_id': run_id,
        'workspace_id': workspace_id,
        'execution_target_type': 'commit_snapshot',
        'execution_target_ref': f'snap-{run_id}',
        'status': status,
        'status_family': status_family,
        'created_at': created_at,
        'updated_at': created_at,
        'requested_by_user_id': requested_by_user_id,
        'trace_available': status_family != 'pending',
        'artifact_count': 1,
    }




def _probe_row(probe_event_id: str, occurred_at: str, *, probe_status: str = 'reachable', workspace_id: str = 'ws-001', provider_key: str = 'openai') -> dict:
    return {
        'probe_event_id': probe_event_id,
        'workspace_id': workspace_id,
        'provider_key': provider_key,
        'provider_family': provider_key,
        'display_name': 'OpenAI GPT',
        'probe_status': probe_status,
        'connectivity_state': 'ok' if probe_status == 'reachable' else 'provider_error',
        'secret_resolution_status': 'resolved',
        'requested_model_ref': 'gpt-4.1',
        'effective_model_ref': 'gpt-4.1',
        'occurred_at': occurred_at,
        'requested_by_user_id': 'user-collab',
        'message': 'Probe completed.',
    }



def _binding_row(binding_id: str, updated_at: str, *, workspace_id: str = 'ws-001', provider_key: str = 'openai', display_name: str = 'OpenAI GPT', enabled: bool = True, secret_ref: str = 'secret://ws-001/openai') -> dict:
    return {
        'binding_id': binding_id,
        'workspace_id': workspace_id,
        'provider_key': provider_key,
        'provider_family': provider_key,
        'display_name': display_name,
        'credential_source': 'managed',
        'secret_ref': secret_ref,
        'enabled': enabled,
        'updated_at': updated_at,
        'updated_by_user_id': 'user-owner',
    }



def _onboarding_row(onboarding_state_id: str, updated_at: str, *, user_id: str = "user-collab", workspace_id: str = "ws-001", current_step: str = "workspace-ready") -> dict:
    return {
        'onboarding_state_id': onboarding_state_id,
        'user_id': user_id,
        'workspace_id': workspace_id,
        'first_success_achieved': True,
        'advanced_surfaces_unlocked': True,
        'dismissed_guidance_state': {},
        'current_step': current_step,
        'updated_at': updated_at,
    }

def _headers(user_id: str = 'user-owner') -> dict[str, str]:
    return {
        'Authorization': 'Bearer token',
        'X-Nexa-Session-Claims': '{"sub": "%s", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]}' % user_id,
    }


def test_recent_activity_service_returns_sorted_paginated_feed() -> None:
    outcome = RecentActivityService.list_recent_activity(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        onboarding_rows=(
            _onboarding_row('onboard-001', '2026-04-11T12:12:00+00:00'),
        ),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
        provider_probe_rows=(
            _probe_row('probe-001', '2026-04-11T12:08:00+00:00'),
        ),
        provider_binding_rows=(
            _binding_row('binding-001', '2026-04-11T12:09:00+00:00'),
        ),
        managed_secret_rows=(
            {
                'workspace_id': 'ws-001',
                'provider_key': 'openai',
                'secret_ref': 'secret://ws-001/openai',
                'last_rotated_at': '2026-04-11T12:11:00+00:00',
            },
        ),
        limit=2,
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert [item.activity_type for item in outcome.response.activities] == ['onboarding_updated', 'managed_secret_updated']
    assert outcome.response.next_cursor == outcome.response.activities[-1].activity_id
    assert outcome.response.total_visible_count == 7


def test_recent_activity_summary_filters_to_visible_workspace() -> None:
    outcome = RecentActivityService.read_history_summary(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(), _workspace_row('ws-002', owner_user_id='user-other', title='Other Workspace')),
        membership_rows=(_membership(),),
        onboarding_rows=(
            _onboarding_row('onboard-001', '2026-04-11T12:11:00+00:00'),
        ),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='failed', status_family='terminal_failure', workspace_id='ws-002'),
        ),
        provider_probe_rows=(
            _probe_row('probe-001', '2026-04-11T12:08:00+00:00'),
        ),
        provider_binding_rows=(
            _binding_row('binding-001', '2026-04-11T12:09:00+00:00'),
        ),
        managed_secret_rows=(
            {
                'workspace_id': 'ws-001',
                'provider_key': 'openai',
                'secret_ref': 'secret://ws-001/openai',
                'last_rotated_at': '2026-04-11T12:10:00+00:00',
            },
        ),
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.visible_workspace_count == 1
    assert outcome.response.recent_workspace_count == 1
    assert outcome.response.latest_workspace_id == 'ws-001'
    assert outcome.response.total_visible_runs == 1
    assert outcome.response.terminal_success_runs == 1
    assert outcome.response.terminal_failure_runs == 0
    assert outcome.response.recent_probe_count == 1
    assert outcome.response.failed_probe_count == 0
    assert outcome.response.latest_probe_event_id == 'probe-001'
    assert outcome.response.recent_provider_binding_count == 1
    assert outcome.response.recent_managed_secret_count == 1
    assert outcome.response.latest_provider_binding_id == 'binding-001'
    assert outcome.response.latest_managed_secret_ref == 'secret://ws-001/openai'
    assert outcome.response.recent_onboarding_count == 1
    assert outcome.response.latest_onboarding_state_id == 'onboard-001'
    assert outcome.response.latest_activity_at == '2026-04-11T12:11:00+00:00'


def test_recent_activity_route_family_round_trip() -> None:
    activity_response = RunHttpRouteSurface.handle_recent_activity(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/users/me/activity',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-collab', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['editor']},
            query_params={'limit': 2},
        ),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        onboarding_rows=(
            _onboarding_row('onboard-001', '2026-04-11T12:12:00+00:00'),
        ),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
        provider_probe_rows=(
            _probe_row('probe-001', '2026-04-11T12:08:00+00:00'),
        ),
        provider_binding_rows=(
            _binding_row('binding-001', '2026-04-11T12:09:00+00:00'),
        ),
        managed_secret_rows=(
            {
                'workspace_id': 'ws-001',
                'provider_key': 'openai',
                'secret_ref': 'secret://ws-001/openai',
                'last_rotated_at': '2026-04-11T12:10:00+00:00',
            },
        ),
    )
    assert activity_response.status_code == 200
    assert activity_response.body['returned_count'] == 2
    assert activity_response.body['activities'][0]['activity_type'] == 'onboarding_updated'
    assert activity_response.body['activities'][0]['links']['onboarding'] == '/api/users/me/onboarding?workspace_id=ws-001'

    summary_response = RunHttpRouteSurface.handle_history_summary(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/users/me/history-summary',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-collab', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['editor']},
        ),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        onboarding_rows=(
            _onboarding_row('onboard-001', '2026-04-11T12:12:00+00:00'),
        ),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
        provider_probe_rows=(
            _probe_row('probe-001', '2026-04-11T12:08:00+00:00'),
        ),
        provider_binding_rows=(
            _binding_row('binding-001', '2026-04-11T12:09:00+00:00'),
        ),
        managed_secret_rows=(
            {
                'workspace_id': 'ws-001',
                'provider_key': 'openai',
                'secret_ref': 'secret://ws-001/openai',
                'last_rotated_at': '2026-04-11T12:10:00+00:00',
            },
        ),
    )
    assert summary_response.status_code == 200
    assert summary_response.body['recent_workspace_count'] == 1
    assert summary_response.body['latest_workspace_id'] == 'ws-001'
    assert summary_response.body['total_visible_runs'] == 2
    assert summary_response.body['pending_runs'] == 1
    assert summary_response.body['recent_probe_count'] == 1
    assert summary_response.body['recent_provider_binding_count'] == 1
    assert summary_response.body['recent_managed_secret_count'] == 1
    assert summary_response.body['latest_probe_event_id'] == 'probe-001'
    assert summary_response.body['latest_provider_binding_id'] == 'binding-001'
    assert summary_response.body['latest_managed_secret_ref'] == 'secret://ws-001/openai'
    assert summary_response.body['recent_onboarding_count'] == 1
    assert summary_response.body['latest_onboarding_state_id'] == 'onboard-001'


def test_recent_activity_accepts_provider_probe_projection_aliases() -> None:
    outcome = RecentActivityService.list_recent_activity(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        run_rows=(),
        provider_probe_rows=({
            'probe_id': 'probe-002',
            'workspace_id': 'ws-001',
            'binding_id': 'binding-001',
            'provider_key': 'openai',
            'provider_family': 'openai',
            'display_name': 'OpenAI GPT',
            'probe_status': 'warning',
            'connectivity_state': 'provider_error',
            'created_at': '2026-04-11T12:09:00+00:00',
        },),
        limit=5,
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.activities[0].activity_type == 'provider_probe_warning'
    assert outcome.response.activities[0].links.provider_probe_history is not None


def test_recent_activity_rejected_response_includes_workspace_continuity_projection() -> None:
    outcome = RecentActivityService.list_recent_activity(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        onboarding_rows=(_onboarding_row('onboard-001', '2026-04-11T12:12:00+00:00'),),
        run_rows=(_run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),),
        provider_probe_rows=(_probe_row('probe-001', '2026-04-11T12:08:00+00:00'),),
        provider_binding_rows=(_binding_row('binding-001', '2026-04-11T12:09:00+00:00'),),
        managed_secret_rows=({
            'workspace_id': 'ws-001',
            'provider_key': 'openai',
            'secret_ref': 'secret://ws-001/openai',
            'last_rotated_at': '2026-04-11T12:10:00+00:00',
        },),
        workspace_id='ws-001',
        limit=0,
    )
    assert outcome.ok is False
    assert outcome.rejected is not None
    assert outcome.rejected.workspace_title == 'Primary Workspace'
    assert outcome.rejected.provider_continuity is not None
    assert outcome.rejected.provider_continuity.provider_binding_count == 1
    assert outcome.rejected.activity_continuity is not None
    assert outcome.rejected.activity_continuity.recent_run_count == 1
