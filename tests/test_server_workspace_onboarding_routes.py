from __future__ import annotations

from src.server import (
    OnboardingContinuityService,
    ProductOnboardingWriteRequest,
    ProductWorkspaceCreateRequest,
    RequestAuthResolver,
    WorkspaceAuthorizationContext,
    WorkspaceRegistryService,
)


def _auth(user_id: str = 'user-owner'):
    return RequestAuthResolver.resolve(
        headers={'Authorization': 'Bearer token'},
        session_claims={'sub': user_id, 'sid': 'sess-001', 'exp': 4102444800, 'roles': ['editor']},
    )


def _workspace_row(workspace_id: str = 'ws-001', *, owner_user_id: str = 'user-owner', title: str = 'Primary Workspace') -> dict:
    return {
        'workspace_id': workspace_id,
        'owner_user_id': owner_user_id,
        'title': title,
        'description': 'Workspace description',
        'created_at': '2026-04-11T12:00:00+00:00',
        'updated_at': '2026-04-11T12:05:00+00:00',
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


def _workspace_context() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id='ws-001',
        owner_user_ref='user-owner',
        collaborator_user_refs=('user-collab',),
        viewer_user_refs=('user-viewer',),
    )


def test_workspace_registry_list_and_read_respect_visibility() -> None:
    provider_binding_rows = ({
        'binding_id': 'binding-001',
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'updated_at': '2026-04-11T12:06:00+00:00',
        'created_at': '2026-04-11T12:01:00+00:00',
    },)
    managed_secret_rows = ({
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'secret_ref': 'secret://ws-001/openai',
        'last_rotated_at': '2026-04-11T12:06:30+00:00',
    },)
    provider_probe_rows = ({
        'probe_event_id': 'probe-001',
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'probe_status': 'reachable',
        'connectivity_state': 'ok',
        'secret_resolution_status': 'resolved',
        'requested_model_ref': 'gpt-4.1',
        'effective_model_ref': 'gpt-4.1',
        'occurred_at': '2026-04-11T12:08:00+00:00',
        'requested_by_user_id': 'user-owner',
        'message': 'Probe completed.',
    },)
    list_outcome = WorkspaceRegistryService.list_workspaces(
        request_auth=_auth('user-collab'),
        workspace_rows=(_workspace_row(), _workspace_row('ws-002', owner_user_id='user-other', title='Other Workspace')),
        membership_rows=(_membership(),),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    assert list_outcome.ok is True
    assert list_outcome.response is not None
    assert [w.workspace_id for w in list_outcome.response.workspaces] == ['ws-001']
    assert list_outcome.response.workspaces[0].role == 'collaborator'
    assert list_outcome.response.workspaces[0].provider_continuity is not None
    assert list_outcome.response.workspaces[0].provider_continuity.provider_binding_count == 1
    assert list_outcome.response.workspaces[0].provider_continuity.managed_secret_count == 1
    assert list_outcome.response.workspaces[0].provider_continuity.recent_probe_count == 1
    assert list_outcome.response.workspaces[0].activity_continuity is not None
    assert list_outcome.response.workspaces[0].activity_continuity.recent_run_count == 1
    assert list_outcome.response.workspaces[0].activity_continuity.recent_probe_count == 1

    read_outcome = WorkspaceRegistryService.read_workspace(
        request_auth=_auth('user-collab'),
        workspace_context=_workspace_context(),
        workspace_row=_workspace_row(),
        membership_rows=(_membership(),),
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    assert read_outcome.ok is True
    assert read_outcome.response is not None
    assert read_outcome.response.workspace_id == 'ws-001'
    assert read_outcome.response.role == 'collaborator'
    assert read_outcome.response.provider_continuity is not None
    assert read_outcome.response.provider_continuity.latest_provider_binding_id == 'binding-001'
    assert read_outcome.response.provider_continuity.latest_managed_secret_ref == 'secret://ws-001/openai'
    assert read_outcome.response.provider_continuity.latest_probe_event_id == 'probe-001'
    assert read_outcome.response.activity_continuity is not None
    assert read_outcome.response.activity_continuity.latest_run_id == 'run-001'
    assert read_outcome.response.activity_continuity.latest_probe_event_id == 'probe-001'


def test_workspace_create_returns_persistence_ready_rows() -> None:
    outcome = WorkspaceRegistryService.create_workspace(
        request_auth=_auth('user-owner'),
        request=ProductWorkspaceCreateRequest(title='New Workspace', description='Created from API'),
        workspace_id_factory=lambda: 'ws-new',
        membership_id_factory=lambda: 'membership-new',
        now_iso='2026-04-11T13:00:00+00:00',
    )
    assert outcome.ok is True
    assert outcome.accepted is not None
    assert outcome.accepted.workspace.workspace_id == 'ws-new'
    assert outcome.accepted.owner_membership_id == 'membership-new'
    assert outcome.created_workspace_row is not None
    assert outcome.created_workspace_row['owner_user_id'] == 'user-owner'
    assert outcome.created_membership_row is not None
    assert outcome.created_membership_row['role'] == 'owner'


def test_onboarding_continuity_reads_default_and_updates_workspace_scope() -> None:
    provider_binding_rows = ({
        'binding_id': 'binding-001',
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'updated_at': '2026-04-11T12:06:00+00:00',
        'created_at': '2026-04-11T12:01:00+00:00',
    },)
    managed_secret_rows = ({
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'secret_ref': 'secret://ws-001/openai',
        'last_rotated_at': '2026-04-11T12:06:30+00:00',
    },)
    provider_probe_rows = ({
        'probe_event_id': 'probe-001',
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'probe_status': 'reachable',
        'connectivity_state': 'ok',
        'secret_resolution_status': 'resolved',
        'requested_model_ref': 'gpt-4.1',
        'effective_model_ref': 'gpt-4.1',
        'occurred_at': '2026-04-11T12:08:00+00:00',
        'requested_by_user_id': 'user-owner',
        'message': 'Probe completed.',
    },)
    read_outcome = OnboardingContinuityService.read_onboarding_state(
        request_auth=_auth('user-owner'),
        onboarding_rows=(),
        workspace_context=None,
        workspace_id=None,
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    assert read_outcome.ok is True
    assert read_outcome.response is not None
    assert read_outcome.response.state.first_success_achieved is False
    assert read_outcome.response.provider_continuity is None
    assert read_outcome.response.activity_continuity is None
    assert read_outcome.response.message == 'No canonical onboarding continuity has been recorded yet.'

    write_outcome = OnboardingContinuityService.upsert_onboarding_state(
        request_auth=_auth('user-owner'),
        request=ProductOnboardingWriteRequest(
            workspace_id='ws-001',
            first_success_achieved=True,
            advanced_surfaces_unlocked=True,
            current_step='history-ready',
        ),
        onboarding_rows=(),
        workspace_context=_workspace_context(),
        onboarding_state_id_factory=lambda: 'onboard-001',
        now_iso='2026-04-11T14:00:00+00:00',
        recent_run_rows=({'workspace_id': 'ws-001', 'run_id': 'run-001', 'created_at': '2026-04-11T12:07:00+00:00', 'updated_at': '2026-04-11T12:07:00+00:00', 'status': 'completed', 'status_family': 'terminal_success'},),
        provider_binding_rows=provider_binding_rows,
        managed_secret_rows=managed_secret_rows,
        provider_probe_rows=provider_probe_rows,
    )
    assert write_outcome.ok is True
    assert write_outcome.accepted is not None
    assert write_outcome.accepted.state.workspace_id == 'ws-001'
    assert write_outcome.accepted.state.first_success_achieved is True
    assert write_outcome.accepted.state.advanced_surfaces_unlocked is True
    assert write_outcome.accepted.provider_continuity is not None
    assert write_outcome.accepted.provider_continuity.provider_binding_count == 1
    assert write_outcome.accepted.provider_continuity.managed_secret_count == 1
    assert write_outcome.accepted.provider_continuity.recent_probe_count == 1
    assert write_outcome.accepted.activity_continuity is not None
    assert write_outcome.accepted.activity_continuity.latest_run_id == 'run-001'
    assert write_outcome.accepted.activity_continuity.latest_onboarding_state_id == 'onboard-001'
    assert write_outcome.persisted_onboarding_row is not None
    assert write_outcome.persisted_onboarding_row['onboarding_state_id'] == 'onboard-001'
