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
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
        limit=2,
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert [item.activity_type for item in outcome.response.activities] == ['run_queued', 'run_completed']
    assert outcome.response.next_cursor == outcome.response.activities[-1].activity_id
    assert outcome.response.total_visible_count == 3


def test_recent_activity_summary_filters_to_visible_workspace() -> None:
    outcome = RecentActivityService.read_history_summary(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(), _workspace_row('ws-002', owner_user_id='user-other', title='Other Workspace')),
        membership_rows=(_membership(),),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='failed', status_family='terminal_failure', workspace_id='ws-002'),
        ),
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.visible_workspace_count == 1
    assert outcome.response.total_visible_runs == 1
    assert outcome.response.terminal_success_runs == 1
    assert outcome.response.terminal_failure_runs == 0


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
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
    )
    assert activity_response.status_code == 200
    assert activity_response.body['returned_count'] == 2
    assert activity_response.body['activities'][0]['activity_type'] == 'run_queued'

    summary_response = RunHttpRouteSurface.handle_history_summary(
        http_request=HttpRouteRequest(
            method='GET',
            path='/api/users/me/history-summary',
            headers={'Authorization': 'Bearer token'},
            session_claims={'sub': 'user-collab', 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['editor']},
        ),
        workspace_rows=(_workspace_row(),),
        membership_rows=(_membership(),),
        run_rows=(
            _run_row('run-001', '2026-04-11T12:06:00+00:00', status='completed', status_family='terminal_success'),
            _run_row('run-002', '2026-04-11T12:07:00+00:00', status='queued', status_family='pending'),
        ),
    )
    assert summary_response.status_code == 200
    assert summary_response.body['total_visible_runs'] == 2
    assert summary_response.body['pending_runs'] == 1
