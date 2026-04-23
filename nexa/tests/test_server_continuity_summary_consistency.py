from __future__ import annotations

from src.server import (
    OnboardingContinuityService,
    RecentActivityService,
    RequestAuthResolver,
    WorkspaceAuthorizationContext,
    WorkspaceRegistryService,
)


def _auth(user_id: str = 'user-owner', roles: list[str] | None = None):
    return RequestAuthResolver.resolve(
        headers={'Authorization': 'Bearer token'},
        session_claims={'sub': user_id, 'sid': 'sess-001', 'exp': 4102444800, 'roles': roles or ['editor']},
    )



def _workspace_context(workspace_id: str = 'ws-001') -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id=workspace_id,
        owner_user_ref='user-owner',
        collaborator_user_refs=('user-collab',),
        viewer_user_refs=('user-viewer',),
    )



def _workspace_row(workspace_id: str = 'ws-001', *, owner_user_id: str = 'user-owner', title: str = 'Primary Workspace') -> dict:
    return {
        'workspace_id': workspace_id,
        'owner_user_id': owner_user_id,
        'title': title,
        'description': 'Workspace description',
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:05:00+00:00',
        'last_run_id': 'run-002',
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



def _run_row(run_id: str, created_at: str, *, status: str, status_family: str, workspace_id: str = 'ws-001') -> dict:
    return {
        'run_id': run_id,
        'workspace_id': workspace_id,
        'execution_target_type': 'commit_snapshot',
        'execution_target_ref': f'snap-{run_id}',
        'status': status,
        'status_family': status_family,
        'created_at': created_at,
        'updated_at': created_at,
        'requested_by_user_id': 'user-owner',
        'trace_available': status_family != 'pending',
        'artifact_count': 1,
    }



def _probe_row(probe_event_id: str, occurred_at: str, *, probe_status: str = 'reachable', workspace_id: str = 'ws-001') -> dict:
    return {
        'probe_event_id': probe_event_id,
        'workspace_id': workspace_id,
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'probe_status': probe_status,
        'connectivity_state': 'ok' if probe_status == 'reachable' else 'provider_error',
        'secret_resolution_status': 'resolved',
        'requested_model_ref': 'gpt-4.1',
        'effective_model_ref': 'gpt-4.1',
        'occurred_at': occurred_at,
        'requested_by_user_id': 'user-owner',
        'message': 'Probe completed.',
    }



def _binding_row(binding_id: str, updated_at: str, *, workspace_id: str = 'ws-001') -> dict:
    return {
        'binding_id': binding_id,
        'workspace_id': workspace_id,
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'credential_source': 'managed',
        'secret_ref': 'secret://ws-001/openai',
        'enabled': True,
        'created_at': '2026-04-11T12:01:00+00:00',
        'updated_at': updated_at,
        'updated_by_user_id': 'user-owner',
    }



def _secret_row(rotated_at: str, *, workspace_id: str = 'ws-001') -> dict:
    return {
        'workspace_id': workspace_id,
        'provider_key': 'openai',
        'secret_ref': 'secret://ws-001/openai',
        'last_rotated_at': rotated_at,
    }



def _onboarding_row(onboarding_state_id: str, updated_at: str, *, user_id: str = 'user-collab', workspace_id: str = 'ws-001', current_step: str = 'workspace-ready') -> dict:
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



def _dataset():
    workspace_rows = (
        _workspace_row(),
        _workspace_row('ws-002', owner_user_id='user-other', title='Other Workspace'),
    )
    membership_rows = (_membership(),)
    run_rows = (
        _run_row('run-001', '2026-04-11T12:06:00+00:00', status='queued', status_family='pending'),
        _run_row('run-002', '2026-04-11T12:07:00+00:00', status='running', status_family='active'),
        _run_row('run-003', '2026-04-11T12:08:00+00:00', status='failed', status_family='terminal_failure'),
        _run_row('run-004', '2026-04-11T12:09:00+00:00', status='completed', status_family='terminal_success', workspace_id='ws-002'),
    )
    probe_rows = (
        _probe_row('probe-001', '2026-04-11T12:10:00+00:00', probe_status='reachable'),
        _probe_row('probe-002', '2026-04-11T12:11:00+00:00', probe_status='failed'),
        _probe_row('probe-003', '2026-04-11T12:12:00+00:00', workspace_id='ws-002'),
    )
    binding_rows = (
        _binding_row('binding-001', '2026-04-11T12:09:30+00:00'),
        _binding_row('binding-002', '2026-04-11T12:13:00+00:00', workspace_id='ws-002'),
    )
    secret_rows = (
        _secret_row('2026-04-11T12:10:30+00:00'),
        _secret_row('2026-04-11T12:14:00+00:00', workspace_id='ws-002'),
    )
    onboarding_rows = (
        _onboarding_row('onboard-001', '2026-04-11T12:12:30+00:00'),
        _onboarding_row('onboard-002', '2026-04-11T12:15:00+00:00', user_id='user-other', workspace_id='ws-002'),
    )
    return workspace_rows, membership_rows, run_rows, probe_rows, binding_rows, secret_rows, onboarding_rows



def test_history_summary_derives_visible_counts_and_latest_ids_from_underlying_rows() -> None:
    workspace_rows, membership_rows, run_rows, probe_rows, binding_rows, secret_rows, onboarding_rows = _dataset()

    outcome = RecentActivityService.read_history_summary(
        request_auth=_auth('user-collab'),
        workspace_rows=workspace_rows,
        membership_rows=membership_rows,
        onboarding_rows=onboarding_rows,
        run_rows=run_rows,
        provider_probe_rows=probe_rows,
        provider_binding_rows=binding_rows,
        managed_secret_rows=secret_rows,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    response = outcome.response

    assert response.visible_workspace_count == 1
    assert response.total_visible_runs == 3
    assert response.terminal_success_runs == 0
    assert response.terminal_failure_runs == 1
    assert response.recent_probe_count == 2
    assert response.failed_probe_count == 1
    assert response.recent_provider_binding_count == 1
    assert response.recent_managed_secret_count == 1
    assert response.recent_onboarding_count == 1
    assert response.latest_workspace_id == 'ws-001'
    assert response.latest_probe_event_id == 'probe-002'
    assert response.latest_provider_binding_id == 'binding-001'
    assert response.latest_managed_secret_ref == 'secret://ws-001/openai'
    assert response.latest_onboarding_state_id == 'onboard-001'
    assert response.latest_activity_at == '2026-04-11T12:12:30+00:00'



def test_workspace_detail_continuity_matches_same_workspace_store_projection() -> None:
    workspace_rows, membership_rows, run_rows, probe_rows, binding_rows, secret_rows, onboarding_rows = _dataset()

    outcome = WorkspaceRegistryService.read_workspace(
        request_auth=_auth('user-collab'),
        workspace_context=_workspace_context(),
        workspace_row=_workspace_row(),
        membership_rows=membership_rows,
        recent_run_rows=run_rows,
        provider_binding_rows=binding_rows,
        managed_secret_rows=secret_rows,
        provider_probe_rows=probe_rows,
        onboarding_rows=onboarding_rows,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    response = outcome.response
    assert response.provider_continuity is not None
    assert response.activity_continuity is not None

    assert response.provider_continuity.provider_binding_count == 1
    assert response.provider_continuity.managed_secret_count == 1
    assert response.provider_continuity.recent_probe_count == 2
    assert response.provider_continuity.latest_provider_binding_id == 'binding-001'
    assert response.provider_continuity.latest_managed_secret_ref == 'secret://ws-001/openai'
    assert response.provider_continuity.latest_probe_event_id == 'probe-002'

    assert response.activity_continuity.recent_run_count == 3
    assert response.activity_continuity.pending_run_count == 1
    assert response.activity_continuity.active_run_count == 1
    assert response.activity_continuity.terminal_failure_run_count == 1
    assert response.activity_continuity.recent_probe_count == 2
    assert response.activity_continuity.failed_probe_count == 1
    assert response.activity_continuity.recent_provider_binding_count == 1
    assert response.activity_continuity.recent_managed_secret_count == 1
    assert response.activity_continuity.recent_onboarding_count == 1
    assert response.activity_continuity.latest_run_id == 'run-003'
    assert response.activity_continuity.latest_probe_event_id == 'probe-002'
    assert response.activity_continuity.latest_provider_binding_id == 'binding-001'
    assert response.activity_continuity.latest_managed_secret_ref == 'secret://ws-001/openai'
    assert response.activity_continuity.latest_onboarding_state_id == 'onboard-001'
    assert response.activity_continuity.latest_activity_at == '2026-04-11T12:12:30+00:00'



def test_onboarding_workspace_scope_reuses_same_continuity_projection() -> None:
    workspace_rows, membership_rows, run_rows, probe_rows, binding_rows, secret_rows, onboarding_rows = _dataset()

    outcome = OnboardingContinuityService.read_onboarding_state(
        request_auth=_auth('user-collab'),
        onboarding_rows=onboarding_rows,
        workspace_context=_workspace_context(),
        workspace_id='ws-001',
        workspace_rows=workspace_rows,
        membership_rows=membership_rows,
        recent_run_rows=run_rows,
        provider_binding_rows=binding_rows,
        managed_secret_rows=secret_rows,
        provider_probe_rows=probe_rows,
    )

    assert outcome.ok is True
    assert outcome.response is not None
    response = outcome.response
    assert response.provider_continuity is not None
    assert response.activity_continuity is not None

    assert response.provider_continuity.provider_binding_count == 1
    assert response.provider_continuity.managed_secret_count == 1
    assert response.provider_continuity.recent_probe_count == 2
    assert response.provider_continuity.latest_probe_event_id == 'probe-002'

    assert response.activity_continuity.recent_run_count == 3
    assert response.activity_continuity.terminal_failure_run_count == 1
    assert response.activity_continuity.failed_probe_count == 1
    assert response.activity_continuity.latest_run_id == 'run-003'
    assert response.activity_continuity.latest_onboarding_state_id == 'onboard-001'
    assert response.activity_continuity.latest_activity_at == '2026-04-11T12:12:30+00:00'
