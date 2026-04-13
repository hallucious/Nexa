from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from src.server.managed_secret_metadata_store import InMemoryManagedSecretMetadataStore, bind_managed_secret_metadata_store
from src.server.onboarding_state_store import InMemoryOnboardingStateStore, bind_onboarding_state_store
from src.server.provider_binding_store import InMemoryProviderBindingStore, bind_provider_binding_store
from src.server.provider_probe_history_store import InMemoryProviderProbeHistoryStore, bind_probe_history_store
from src.server.workspace_registry_store import InMemoryWorkspaceRegistryStore, bind_workspace_registry_store
from fastapi.testclient import TestClient

from src.server import (
    AwsSecretsManagerBindingConfig,
    EngineArtifactReference,
    EngineFinalOutput,
    EngineResultEnvelope,
    EngineRunStatusSnapshot,
    EngineSignal,
    ExecutionTargetCatalogEntry,
    FastApiRouteDependencies,
    FrameworkRouteBindings,
    RunAuthorizationContext,
    RunHttpRouteSurface,
    WorkspaceAuthorizationContext,
    create_fastapi_app,
)


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _run_context() -> RunAuthorizationContext:
    return RunAuthorizationContext(
        run_id="run-001",
        workspace_context=_workspace(),
        run_owner_user_ref="user-owner",
    )


def _commit_snapshot(ref: str = "snap-001") -> dict:
    return {
        "meta": {"format_version": "0.1.0", "storage_role": "commit_snapshot", "commit_id": ref},
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"parent_commit_id": None, "metadata": {}},
    }


def _run_row(*, status: str = "running", trace_available: bool = False) -> dict:
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": status,
        "status_family": "active" if status == "running" else "terminal_success",
        "created_at": "2026-04-11T12:00:00+00:00",
        "started_at": "2026-04-11T12:00:05+00:00",
        "updated_at": "2026-04-11T12:00:10+00:00",
        "finished_at": None,
        "requested_by_user_id": "user-owner",
        "trace_available": trace_available,
    }


def _working_save_artifact() -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
        "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {"app_language": "en-US", "viewport_tier": "mobile", "provider_session_keys": {"gpt": "sk-test-session"}}},
    }


def _session_headers(user_id: str = "user-owner") -> dict[str, str]:
    return {
        "Authorization": "Bearer token",
        "X-Nexa-Session-Claims": '{"sub": "%s", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]}' % user_id,
    }


class _FakeSecretsClient:
    def describe_secret(self, SecretId: str):
        return {"ARN": "arn:aws:secretsmanager:region:acct:secret:" + SecretId, "LastChangedDate": "2026-04-11T12:06:00+00:00"}

    def put_secret_value(self, SecretId: str, SecretString: str):
        return {"ARN": "arn:aws:secretsmanager:region:acct:secret:" + SecretId, "VersionId": "v2"}

    def create_secret(self, Name: str, SecretString: str, Description: str, Tags, **kwargs):
        return {"ARN": "arn:aws:secretsmanager:region:acct:secret:" + Name, "VersionId": "v1"}


def test_fastapi_binding_matches_framework_and_http_route_definitions() -> None:
    app = _make_client().app
    fastapi_route_identities = [
        (route.name, method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api")
        for method in sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"})
    ]
    framework_route_identities = [
        (definition.route_name, definition.method, definition.path_template)
        for definition in FrameworkRouteBindings.route_definitions()
    ]
    http_surface_route_identities = list(RunHttpRouteSurface.route_definitions())

    assert len(fastapi_route_identities) == len(set(fastapi_route_identities))
    assert len(framework_route_identities) == len(set(framework_route_identities))
    assert len(http_surface_route_identities) == len(set(http_surface_route_identities))

    fastapi_routes = set(fastapi_route_identities)
    framework_routes = set(framework_route_identities)
    http_surface_routes = set(http_surface_route_identities)

    assert len(fastapi_route_identities) == len(framework_route_identities) == len(http_surface_route_identities)
    assert fastapi_routes == framework_routes == http_surface_routes


def _make_client() -> TestClient:
    artifact_rows = {
        "run-001": [
            {
                "artifact_id": "artifact-1",
                "run_id": "run-001",
                "workspace_id": "ws-001",
                "artifact_type": "report",
                "label": "Primary report",
                "payload_preview": "Hello",
                "metadata_json": {"value_type": "string", "inline_value": "Hello"},
                "created_at": "2026-04-11T12:00:15+00:00",
            }
        ],
        "run-002": [
            {
                "artifact_id": "artifact-2",
                "run_id": "run-002",
                "workspace_id": "ws-001",
                "artifact_type": "summary",
                "label": "Latest report",
                "payload_preview": "Latest Hello",
                "metadata_json": {"value_type": "string", "inline_value": "Latest Hello"},
                "created_at": "2026-04-11T12:01:15+00:00",
            }
        ]
    }
    trace_rows = {
        "run-001": [
            {
                "trace_event_ref": "evt-2",
                "run_id": "run-001",
                "sequence_number": 2,
                "event_type": "node.completed",
                "occurred_at": "2026-04-11T12:00:20+00:00",
                "node_id": "node-b",
                "message_preview": "Node B completed",
            },
            {
                "trace_event_ref": "evt-1",
                "run_id": "run-001",
                "sequence_number": 1,
                "event_type": "node.started",
                "occurred_at": "2026-04-11T12:00:10+00:00",
                "node_id": "node-a",
                "message_preview": "Node A started",
            },
        ],
        "run-002": [
            {
                "trace_event_ref": "evt-4",
                "run_id": "run-002",
                "sequence_number": 2,
                "event_type": "node.completed",
                "occurred_at": "2026-04-11T12:01:20+00:00",
                "node_id": "node-d",
                "message_preview": "Node D completed",
            },
            {
                "trace_event_ref": "evt-3",
                "run_id": "run-002",
                "sequence_number": 1,
                "event_type": "node.started",
                "occurred_at": "2026-04-11T12:01:10+00:00",
                "node_id": "node-c",
                "message_preview": "Node C started",
            },
        ]
    }
    provider_catalog_rows = ({
        'provider_key': 'openai',
        'provider_family': 'openai',
        'display_name': 'OpenAI GPT',
        'managed_supported': True,
        'recommended_scope': 'workspace',
        'local_env_var_hint': 'OPENAI_API_KEY',
        'default_secret_name_template': 'nexa/{workspace_id}/providers/openai',
    },)
    provider_binding_rows = {
        'ws-001': ({
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
    }
    provider_probe_rows = {
        'ws-001': ({
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
        },),
    }
    probe_store = InMemoryProviderProbeHistoryStore.from_rows(provider_probe_rows['ws-001'])

    def _probe_runner(probe_input):
        return {
            'probe_status': 'reachable',
            'connectivity_state': 'ok',
            'message': 'Provider connectivity probe succeeded.',
            'effective_model_ref': probe_input.requested_model_ref or probe_input.default_model_ref,
            'round_trip_latency_ms': 187,
        }
    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:05:00+00:00',
            'continuity_source': 'server',
            'archived': False,
        },),
        workspace_membership_rows_provider=lambda: (),
        recent_run_rows_provider=lambda: (_run_row(trace_available=True),),
        onboarding_rows_provider=lambda: (),
        provider_catalog_rows_provider=lambda: provider_catalog_rows,
        workspace_provider_binding_rows_provider=lambda workspace_id: provider_binding_rows.get(workspace_id, ()),
        workspace_provider_binding_row_provider=lambda workspace_id, provider_key: next((row for row in provider_binding_rows.get(workspace_id, ()) if row['provider_key'] == provider_key), None),
        workspace_provider_probe_rows_provider=lambda workspace_id: provider_probe_rows.get(workspace_id, ()),
        recent_provider_binding_rows_provider=lambda: provider_binding_rows.get('ws-001', ()),
        recent_provider_probe_rows_provider=lambda: provider_probe_rows.get('ws-001', ()),
        recent_managed_secret_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'provider_key': 'openai',
            'secret_ref': 'secret://ws-001/openai',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },),
        workspace_row_provider=lambda workspace_id: {
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:05:00+00:00',
            'continuity_source': 'server',
            'archived': False,
        } if workspace_id == 'ws-001' else None,
        workspace_artifact_source_provider=lambda workspace_id: _working_save_artifact() if workspace_id == 'ws-001' else None,
        run_context_provider=lambda run_id: _run_context() if run_id == "run-001" else None,
        target_catalog_provider=lambda workspace_id: {
            "snap-001": ExecutionTargetCatalogEntry(
                workspace_id="ws-001",
                target_ref="snap-001",
                target_type="approved_snapshot",
                source=_commit_snapshot("snap-001"),
            )
        } if workspace_id == "ws-001" else {},
        run_record_provider=lambda run_id: _run_row(trace_available=True) if run_id == "run-001" else None,
        artifact_rows_provider=lambda run_id: artifact_rows.get(run_id, ()),
        workspace_run_rows_provider=lambda workspace_id: (
            _run_row(trace_available=True),
            {**_run_row(status="completed", trace_available=True), "run_id": "run-002", "created_at": "2026-04-11T12:01:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        ) if workspace_id == "ws-001" else (),
        workspace_result_rows_provider=lambda workspace_id: {
            "run-002": {
                "run_id": "run-002",
                "workspace_id": "ws-001",
                "result_state": "ready_success",
                "final_status": "completed",
                "result_summary": "Success.",
                "updated_at": "2026-04-11T12:01:05+00:00",
            }
        } if workspace_id == "ws-001" else {},
        artifact_row_provider=lambda artifact_id: artifact_rows["run-001"][0] if artifact_id == "artifact-1" else None,
        trace_rows_provider=lambda run_id: trace_rows.get(run_id, ()),
        engine_status_provider=lambda run_id: EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-a",
            active_node_label="Node A",
            progress_percent=25,
            progress_summary="Executing Node A",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node A is executing."),
            trace_ref="trace://run-001",
            artifact_count=1,
        ) if run_id == "run-001" else None,
        engine_result_provider=lambda run_id: EngineResultEnvelope(
            run_id="run-001",
            final_status="completed",
            result_state="ready_success",
            result_summary="Success.",
            trace_ref="trace://run-001",
            metrics={"duration_ms": 123},
            final_output=EngineFinalOutput(output_key="answer", value_preview="ok", value_type="string"),
            artifact_refs=(EngineArtifactReference(artifact_id="artifact-1", artifact_type="report", metadata={"label": "Primary report"}),),
            failure_info=None,
        ) if run_id == "run-001" else None,
        run_id_factory=lambda: "run-001",
        run_request_id_factory=lambda: "req-001",
        workspace_id_factory=lambda: 'ws-new',
        membership_id_factory=lambda: 'membership-new',
        binding_id_factory=lambda: 'binding-new',
        onboarding_state_id_factory=lambda: 'onboard-001',
        managed_secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v2',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },
        aws_secrets_manager_client_provider=lambda: _FakeSecretsClient(),
        aws_secrets_manager_config=AwsSecretsManagerBindingConfig(),
        provider_probe_runner=_probe_runner,
        probe_event_id_factory=lambda: 'probe-new',
        now_iso_provider=lambda: "2026-04-11T12:09:00+00:00",
    )
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    return TestClient(create_fastapi_app(dependencies=deps))


def test_fastapi_binding_launch_endpoint_round_trip() -> None:
    client = _make_client()
    response = client.post(
        "/api/runs",
        headers=_session_headers(),
        json={
            "workspace_id": "ws-001",
            "execution_target": {"target_type": "approved_snapshot", "target_ref": "snap-001"},
            "input_payload": {"question": "hello"},
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["run_id"] == "run-001"
    assert payload["workspace_title"] == "Primary Workspace"
    assert payload["provider_continuity"]["provider_binding_count"] == 1
    assert payload["activity_continuity"]["recent_run_count"] == 2
    assert payload["activity_continuity"]["latest_run_id"] == "run-001"


def test_fastapi_binding_status_endpoint_round_trip() -> None:
    client = _make_client()
    response = client.get("/api/runs/run-001", headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["workspace_title"] == "Primary Workspace"
    assert payload["provider_continuity"]["provider_binding_count"] == 1
    assert payload["activity_continuity"]["recent_run_count"] == 1
    assert payload["progress"]["percent"] == 25


def test_fastapi_binding_result_endpoint_round_trip() -> None:
    client = _make_client()
    response = client.get("/api/runs/run-001/result", headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_state"] == "ready_success"
    assert payload["workspace_title"] == "Primary Workspace"
    assert payload["provider_continuity"]["provider_binding_count"] == 1
    assert payload["activity_continuity"]["recent_run_count"] == 1
    assert payload["final_output"]["output_key"] == "answer"


def test_fastapi_binding_artifact_and_trace_routes_round_trip() -> None:
    client = _make_client()

    artifact_list_response = client.get("/api/runs/run-001/artifacts", headers=_session_headers())
    assert artifact_list_response.status_code == 200
    artifact_list_payload = artifact_list_response.json()
    assert artifact_list_payload["artifact_count"] == 1
    assert artifact_list_payload["workspace_title"] == "Primary Workspace"
    assert artifact_list_payload["provider_continuity"]["provider_binding_count"] == 1
    assert artifact_list_payload["activity_continuity"]["recent_run_count"] == 1

    artifact_detail_response = client.get("/api/artifacts/artifact-1", headers=_session_headers())
    assert artifact_detail_response.status_code == 200
    artifact_detail_payload = artifact_detail_response.json()
    assert artifact_detail_payload["payload_access"]["mode"] == "inline"
    assert artifact_detail_payload["workspace_title"] == "Primary Workspace"
    assert artifact_detail_payload["provider_continuity"]["provider_binding_count"] == 1
    assert artifact_detail_payload["activity_continuity"]["recent_run_count"] == 1

    trace_response = client.get("/api/runs/run-001/trace?limit=10", headers=_session_headers())
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["workspace_id"] == "ws-001"
    assert trace_payload["workspace_title"] == "Primary Workspace"
    assert trace_payload["provider_continuity"]["provider_binding_count"] == 1
    assert trace_payload["activity_continuity"]["recent_run_count"] == 1
    assert [event["sequence"] for event in trace_payload["events"]] == [1, 2]


def test_fastapi_binding_workspace_shell_route_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['workspace_id'] == 'ws-001'
    assert payload['click_test_ready'] is True
    assert payload['launch_request_template']['execution_target']['target_type'] == 'working_save'
    assert payload['shell']['mobile_first_run']['visible'] is True
    assert payload['shell']['privacy_transparency']['visible'] is True
    assert payload['routes']['launch_run'] == '/api/runs'
    assert payload['latest_run_status_preview']['run_id'] == 'run-002'
    assert payload['latest_run_result_preview']['run_id'] == 'run-002'
    assert payload['latest_run_result_preview']['result_state'] == 'ready_success'
    assert payload['routes']['latest_run_trace'] == '/api/runs/run-002/trace?limit=20'
    assert payload['routes']['latest_run_artifacts'] == '/api/runs/run-002/artifacts'
    assert payload['latest_run_trace_preview']['event_count'] == 2
    assert payload['latest_run_trace_preview']['latest_event_type'] == 'node.completed'
    assert payload['latest_run_artifacts_preview']['artifact_count'] == 1
    assert payload['latest_run_artifacts_preview']['first_artifact_id'] == 'artifact-2'
    assert payload['latest_run_status_summary']['headline'] == 'Status: terminal_success'
    assert 'Run id: run-002' in payload['latest_run_status_summary']['lines']
    assert payload['latest_run_status_detail']['title'] == 'Status detail'
    assert 'Status: completed' in payload['latest_run_status_detail']['items']
    assert payload['latest_run_result_summary']['headline'] == 'Success.'
    assert payload['latest_run_result_detail']['title'] == 'Result detail'
    assert 'Result state: ready_success' in payload['latest_run_result_detail']['items']
    assert payload['latest_run_trace_summary']['headline'] == 'Trace events: 2'
    assert 'Latest event: node.completed' in payload['latest_run_trace_summary']['lines']
    assert payload['latest_run_trace_detail']['title'] == 'Trace detail'
    assert 'Event count: 2' in payload['latest_run_trace_detail']['items']
    assert payload['latest_run_artifacts_summary']['headline'] == 'Artifacts: 1'
    assert 'First artifact id: artifact-2' in payload['latest_run_artifacts_summary']['lines']
    assert payload['latest_run_artifacts_detail']['title'] == 'Artifacts detail'
    assert 'Artifact count: 1' in payload['latest_run_artifacts_detail']['items']
    assert payload['navigation']['default_section'] == 'status'
    assert [section['section_id'] for section in payload['navigation']['sections']] == ['status', 'result', 'trace', 'artifacts']


def test_fastapi_binding_workspace_shell_html_page_round_trip() -> None:
    client = _make_client()
    response = client.get('/app/workspaces/ws-001', headers=_session_headers())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    body = response.text
    assert 'Nexa Runtime Shell' in body
    assert 'Run draft' in body
    assert '/api/runs' in body
    assert '/api/workspaces/ws-001/shell' in body
    assert 'Latest run status' in body
    assert 'Latest run result' in body
    assert 'Status detail layer' in body
    assert 'Result detail layer' in body
    assert 'Latest trace' in body
    assert 'Latest artifacts' in body
    assert 'Open latest trace' in body
    assert 'Open latest artifacts' in body
    assert '/api/runs/run-002/trace?limit=20' in body
    assert '/api/runs/run-002/artifacts' in body
    assert 'refreshLatestRunTrace' in body
    assert 'refreshLatestRunArtifacts' in body
    assert 'pollLatestRunUntilSettled' in body
    assert 'Trace events: 2' in body
    assert 'Artifacts: 1' in body
    assert 'Trace detail layer' in body
    assert 'Artifacts detail layer' in body
    assert 'formatSummary' in body
    assert 'formatDetail' in body
    assert 'detailFromStatusBody' in body
    assert 'detailFromResultBody' in body
    assert 'detailFromTraceBody' in body
    assert 'detailFromArtifactsBody' in body
    assert 'summarizeTraceBody' in body
    assert 'summarizeArtifactsBody' in body
    assert 'Runtime focus' in body
    assert 'focus-state' in body
    assert 'renderRuntimeNav' in body
    assert 'setFocusedSection' in body
    assert 'latest-run-status-card' in body
    assert 'latest-run-trace-detail-card' in body


def test_fastapi_binding_returns_auth_failure_without_session_claims() -> None:
    client = _make_client()
    response = client.get("/api/runs/run-001")
    assert response.status_code == 401
    payload = response.json()
    assert payload["reason_code"] == "status.authentication_required"


def test_fastapi_binding_workspace_run_list_route_round_trip() -> None:
    client = _make_client()
    response = client.get("/api/workspaces/ws-001/runs?limit=2", headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "ws-001"
    assert payload["workspace_title"] == "Primary Workspace"
    assert payload["provider_continuity"]["provider_binding_count"] == 1
    assert payload["activity_continuity"]["recent_run_count"] == 1
    assert payload["returned_count"] == 2
    assert payload["runs"][0]["run_id"] == "run-002"


def test_fastapi_binding_workspace_and_onboarding_routes_round_trip() -> None:
    client = _make_client()

    workspace_list = client.get('/api/workspaces', headers=_session_headers())
    assert workspace_list.status_code == 200
    workspace_payload = workspace_list.json()
    assert workspace_payload['returned_count'] == 1
    assert workspace_payload['workspaces'][0]['workspace_id'] == 'ws-001'
    assert workspace_payload['workspaces'][0]['provider_continuity']['recent_probe_count'] == 1

    workspace_detail = client.get('/api/workspaces/ws-001', headers=_session_headers())
    assert workspace_detail.status_code == 200
    assert workspace_detail.json()['workspace_id'] == 'ws-001'
    assert workspace_detail.json()['provider_continuity']['latest_probe_event_id'] == 'probe-001'

    workspace_create = client.post('/api/workspaces', headers=_session_headers(), json={'title': 'Created Workspace'})
    assert workspace_create.status_code == 201
    assert workspace_create.json()['workspace']['workspace_id'] == 'ws-new'

    onboarding_get = client.get('/api/users/me/onboarding', headers=_session_headers())
    assert onboarding_get.status_code == 200
    onboarding_get_payload = onboarding_get.json()
    assert onboarding_get_payload['state']['first_success_achieved'] is False
    assert onboarding_get_payload['provider_continuity']['provider_binding_count'] == 1
    assert onboarding_get_payload['activity_continuity']['latest_run_id'] == 'run-001'

    onboarding_put = client.put(
        '/api/users/me/onboarding',
        headers=_session_headers(),
        json={'first_success_achieved': True, 'advanced_surfaces_unlocked': True},
    )
    assert onboarding_put.status_code == 200
    onboarding_put_payload = onboarding_put.json()
    assert onboarding_put_payload['state']['advanced_surfaces_unlocked'] is True
    assert onboarding_put_payload['provider_continuity']['provider_binding_count'] == 1
    assert onboarding_put_payload['activity_continuity']['latest_run_id'] == 'run-001'


def test_fastapi_binding_provider_catalog_and_workspace_bindings_round_trip() -> None:
    client = _make_client()

    catalog_response = client.get("/api/providers/catalog", headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload["returned_count"] == 1
    assert catalog_payload["providers"][0]["provider_key"] == "openai"
    assert catalog_payload["provider_continuity"]["provider_binding_count"] >= 1
    assert catalog_payload["activity_continuity"]["recent_run_count"] >= 1

    bindings_response = client.get("/api/workspaces/ws-001/provider-bindings", headers=_session_headers())
    assert bindings_response.status_code == 200
    bindings_payload = bindings_response.json()
    assert bindings_payload["returned_count"] == 1
    assert bindings_payload["bindings"][0]["status"] == "configured"

    put_response = client.put(
        "/api/workspaces/ws-001/provider-bindings/openai",
        headers=_session_headers(),
        json={"display_name": "OpenAI GPT", "secret_value": "super-secret", "enabled": True},
    )
    assert put_response.status_code == 200
    put_payload = put_response.json()
    assert put_payload["binding"]["provider_key"] == "openai"
    assert put_payload["binding"]["secret_ref"] == "aws-secretsmanager://nexa/ws-001/providers/openai"
    assert put_payload["secret_rotated"] is True
    assert "super-secret" not in put_response.text


def test_fastapi_binding_provider_probe_round_trip() -> None:
    client = _make_client()
    response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'model_ref': 'gpt-4.1'},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['probe_status'] == 'reachable'
    assert payload['effective_model_ref'] == 'gpt-4.1'


def test_fastapi_binding_recent_activity_includes_provider_probe_event() -> None:
    client = _make_client()
    response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['activities'][0]['activity_type'] == 'provider_probe_reachable'
    assert payload['activities'][0]['links']['provider_probe_history'].endswith('/probe-history')
    assert payload['provider_continuity']['provider_binding_count'] == 1
    assert payload['activity_continuity']['recent_run_count'] == 1




def test_fastapi_binding_provider_binding_round_trip_enables_probe_and_health() -> None:
    probe_store = InMemoryProviderProbeHistoryStore()
    binding_store = InMemoryProviderBindingStore()

    def _probe_runner(probe_input):
        return {
            "probe_status": "reachable",
            "connectivity_state": "ok",
            "message": "Provider connectivity probe succeeded.",
            "effective_model_ref": probe_input.requested_model_ref or probe_input.default_model_ref,
            "round_trip_latency_ms": 144,
        }

    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:00:30+00:00',
            'continuity_source': 'server',
            'archived': False,
        },),
        provider_catalog_rows_provider=lambda: ({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
        managed_secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v1',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },
        provider_probe_runner=_probe_runner,
        binding_id_factory=lambda: 'binding-created',
        probe_event_id_factory=lambda: 'probe-created',
        now_iso_provider=lambda: '2026-04-11T12:10:00+00:00',
    )
    deps = bind_provider_binding_store(dependencies=deps, store=binding_store)
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    put_response = client.put(
        '/api/workspaces/ws-001/provider-bindings/openai',
        headers=_session_headers(),
        json={'display_name': 'OpenAI GPT', 'secret_value': 'very-secret', 'enabled': True, 'default_model_ref': 'gpt-4.1'},
    )
    assert put_response.status_code == 200
    assert put_response.json()['binding']['binding_id'] == 'binding-created'

    recent_response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert recent_response.status_code == 200
    recent_payload = recent_response.json()
    assert recent_payload['activities'][0]['activity_type'] == 'provider_binding_updated'
    assert recent_payload['activities'][0]['activity_id'].startswith('binding:binding-created:')

    list_response = client.get('/api/workspaces/ws-001/provider-bindings', headers=_session_headers())
    assert list_response.status_code == 200
    assert list_response.json()['returned_count'] == 1
    list_payload = list_response.json()
    assert list_payload['bindings'][0]['provider_key'] == 'openai'
    assert list_payload['provider_continuity']['provider_binding_count'] >= 1

    health_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/health', headers=_session_headers())
    assert health_response.status_code == 200
    assert health_response.json()['provider_key'] == 'openai'
    assert health_response.json()['health']['provider_key'] == 'openai'
    assert health_response.json()['health']['health_status'] in {'healthy', 'warning', 'blocked', 'disabled', 'missing'}
    assert health_response.json()['provider_continuity']['provider_binding_count'] >= 1

    probe_response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'requested_model_ref': 'gpt-4.1'},
    )
    assert probe_response.status_code == 200
    probe_payload = probe_response.json()
    assert probe_payload['probe_status'] == 'reachable'
    assert probe_payload['provider_continuity']['provider_binding_count'] >= 1

    history_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history', headers=_session_headers())
    assert history_response.status_code == 200
    assert history_response.json()['returned_count'] == 1
    assert history_response.json()['items'][0]['probe_event_id'] == 'probe-created'
    history_payload = history_response.json()
    assert history_payload['items'][0]['provider_key'] == 'openai'
    assert history_payload['provider_continuity']['recent_probe_count'] >= 1



def test_fastapi_binding_provider_probe_history_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['returned_count'] == 1
    assert payload['items'][0]['probe_event_id'] == 'probe-001'


def test_fastapi_binding_provider_probe_write_is_visible_in_history_and_recent_activity() -> None:
    client = _make_client()

    probe_response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'model_ref': 'gpt-4o'},
    )
    assert probe_response.status_code == 200
    probe_payload = probe_response.json()
    assert probe_payload['effective_model_ref'] == 'gpt-4o'

    history_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1', headers=_session_headers())
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload['items'][0]['probe_event_id'] == 'probe-new'
    assert history_payload['items'][0]['requested_model_ref'] == 'gpt-4o'

    recent_response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert recent_response.status_code == 200
    recent_payload = recent_response.json()
    assert recent_payload['activities'][0]['activity_id'].startswith('probe:probe-new:')
    assert recent_payload['activities'][0]['activity_type'] == 'provider_probe_reachable'


def test_fastapi_binding_workspace_and_onboarding_provider_continuity_round_trip() -> None:
    probe_store = InMemoryProviderProbeHistoryStore()
    binding_store = InMemoryProviderBindingStore()
    secret_store = InMemoryManagedSecretMetadataStore()

    def _probe_runner(probe_input):
        return {
            "probe_status": "reachable",
            "connectivity_state": "ok",
            "message": "Provider connectivity probe succeeded.",
            "effective_model_ref": probe_input.requested_model_ref or probe_input.default_model_ref,
            "round_trip_latency_ms": 155,
        }

    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:00:30+00:00',
            'continuity_source': 'server',
            'archived': False,
        },),
        workspace_row_provider=lambda workspace_id: {
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:00:30+00:00',
            'continuity_source': 'server',
            'archived': False,
        } if workspace_id == 'ws-001' else None,
        recent_run_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'run_id': 'run-workspace-continuity',
            'created_at': '2026-04-11T12:09:00+00:00',
            'updated_at': '2026-04-11T12:09:00+00:00',
            'status': 'completed',
            'status_family': 'terminal_success',
        },),
        provider_catalog_rows_provider=lambda: ({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
        managed_secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v9',
            'last_rotated_at': str(metadata.get('now_iso') or '2026-04-11T12:11:00+00:00'),
        },
        provider_probe_runner=_probe_runner,
        binding_id_factory=lambda: 'binding-workspace-continuity',
        probe_event_id_factory=lambda: 'probe-workspace-continuity',
        onboarding_state_id_factory=lambda: 'onboard-workspace-continuity',
        now_iso_provider=lambda: '2026-04-11T12:11:00+00:00',
    )
    deps = bind_managed_secret_metadata_store(dependencies=deps, store=secret_store)
    deps = bind_provider_binding_store(dependencies=deps, store=binding_store)
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    put_response = client.put(
        '/api/workspaces/ws-001/provider-bindings/openai',
        headers=_session_headers(),
        json={'display_name': 'OpenAI GPT', 'secret_value': 'workspace-secret', 'enabled': True, 'default_model_ref': 'gpt-4.1'},
    )
    assert put_response.status_code == 200

    probe_response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'requested_model_ref': 'gpt-4.1'},
    )
    assert probe_response.status_code == 200

    workspace_list = client.get('/api/workspaces', headers=_session_headers())
    assert workspace_list.status_code == 200
    list_payload = workspace_list.json()
    assert list_payload['workspaces'][0]['provider_continuity']['provider_binding_count'] == 1
    assert list_payload['workspaces'][0]['provider_continuity']['managed_secret_count'] == 1
    assert list_payload['workspaces'][0]['provider_continuity']['recent_probe_count'] == 1
    assert list_payload['workspaces'][0]['activity_continuity']['recent_run_count'] == 1
    assert list_payload['workspaces'][0]['activity_continuity']['latest_run_id'] == 'run-workspace-continuity'

    workspace_detail = client.get('/api/workspaces/ws-001', headers=_session_headers())
    assert workspace_detail.status_code == 200
    detail_payload = workspace_detail.json()
    assert detail_payload['provider_continuity']['latest_provider_binding_id'] == 'binding-workspace-continuity'
    assert detail_payload['provider_continuity']['latest_managed_secret_ref'] == 'secret://ws-001/openai'
    assert detail_payload['provider_continuity']['latest_probe_event_id'] == 'probe-workspace-continuity'
    assert detail_payload['activity_continuity']['latest_run_id'] == 'run-workspace-continuity'
    assert detail_payload['activity_continuity']['latest_probe_event_id'] == 'probe-workspace-continuity'

    onboarding_get = client.get('/api/users/me/onboarding?workspace_id=ws-001', headers=_session_headers())
    assert onboarding_get.status_code == 200
    onboarding_payload = onboarding_get.json()
    assert onboarding_payload['provider_continuity']['provider_binding_count'] == 1
    assert onboarding_payload['provider_continuity']['managed_secret_count'] == 1
    assert onboarding_payload['provider_continuity']['recent_probe_count'] == 1
    assert onboarding_payload['activity_continuity']['recent_run_count'] == 1
    assert onboarding_payload['activity_continuity']['latest_run_id'] == 'run-workspace-continuity'

    onboarding_put = client.put(
        '/api/users/me/onboarding',
        headers=_session_headers(),
        json={'workspace_id': 'ws-001', 'first_success_achieved': True, 'advanced_surfaces_unlocked': True},
    )
    assert onboarding_put.status_code == 200
    onboarding_put_payload = onboarding_put.json()
    assert onboarding_put_payload['provider_continuity']['latest_provider_binding_id'] == 'binding-workspace-continuity'
    assert onboarding_put_payload['provider_continuity']['latest_managed_secret_ref'] == 'secret://ws-001/openai'
    assert onboarding_put_payload['provider_continuity']['latest_probe_event_id'] == 'probe-workspace-continuity'
    assert onboarding_put_payload['activity_continuity']['latest_run_id'] == 'run-workspace-continuity'
    assert onboarding_put_payload['activity_continuity']['latest_onboarding_state_id'] == 'onboard-workspace-continuity'


def test_fastapi_binding_managed_secret_round_trip_enables_health_and_probe_resolution() -> None:
    probe_store = InMemoryProviderProbeHistoryStore()
    binding_store = InMemoryProviderBindingStore()
    secret_store = InMemoryManagedSecretMetadataStore()

    def _probe_runner(probe_input):
        return {
            "probe_status": "reachable",
            "connectivity_state": "ok",
            "message": "Provider connectivity probe succeeded.",
            "effective_model_ref": probe_input.requested_model_ref or probe_input.default_model_ref,
            "round_trip_latency_ms": 155,
        }

    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_rows_provider=lambda: ({
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:00:30+00:00',
            'continuity_source': 'server',
            'archived': False,
        },),
        provider_catalog_rows_provider=lambda: ({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
        managed_secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            'secret_ref': f'secret://{workspace_id}/{provider_key}',
            'secret_version_ref': 'v9',
            'last_rotated_at': str(metadata.get('now_iso') or '2026-04-11T12:11:00+00:00'),
        },
        provider_probe_runner=_probe_runner,
        binding_id_factory=lambda: 'binding-secret-roundtrip',
        probe_event_id_factory=lambda: 'probe-secret-roundtrip',
        now_iso_provider=lambda: '2026-04-11T12:11:00+00:00',
    )
    deps = bind_managed_secret_metadata_store(dependencies=deps, store=secret_store)
    deps = bind_provider_binding_store(dependencies=deps, store=binding_store)
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    put_response = client.put(
        '/api/workspaces/ws-001/provider-bindings/openai',
        headers=_session_headers(),
        json={'display_name': 'OpenAI GPT', 'secret_value': 'roundtrip-secret', 'enabled': True, 'default_model_ref': 'gpt-4.1'},
    )
    assert put_response.status_code == 200
    assert put_response.json()['binding']['secret_version_ref'] == 'v9'

    health_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/health', headers=_session_headers())
    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert health_payload['health']['health_status'] == 'healthy'
    assert health_payload['health']['secret_resolution_status'] == 'resolved'
    assert health_payload['provider_continuity']['provider_binding_count'] == 1

    probe_response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'requested_model_ref': 'gpt-4.1'},
    )
    assert probe_response.status_code == 200
    assert probe_response.json()['probe_status'] == 'reachable'

    history_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1', headers=_session_headers())
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload['items'][0]['probe_event_id'] == 'probe-secret-roundtrip'
    assert history_payload['items'][0]['secret_resolution_status'] == 'resolved'

    summary_response = client.get('/api/users/me/history-summary', headers=_session_headers())
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['provider_continuity']['provider_binding_count'] == 1
    assert summary_payload['activity_continuity']['recent_run_count'] == 0
    assert summary_payload['recent_provider_binding_count'] == 1
    assert summary_payload['recent_managed_secret_count'] == 1
    assert summary_payload['latest_provider_binding_id'] == 'binding-secret-roundtrip'
    assert summary_payload['latest_managed_secret_ref'] == 'secret://ws-001/openai'
    assert summary_payload['latest_activity_at'] == '2026-04-11T12:11:00+00:00'


def test_fastapi_binding_workspace_create_and_onboarding_round_trip() -> None:
    workspace_store = InMemoryWorkspaceRegistryStore()
    onboarding_store = InMemoryOnboardingStateStore()

    deps = FastApiRouteDependencies(
        workspace_id_factory=lambda: 'ws-roundtrip',
        membership_id_factory=lambda: 'membership-roundtrip',
        onboarding_state_id_factory=lambda: 'onboard-roundtrip',
        now_iso_provider=lambda: '2026-04-12T10:30:00+00:00',
    )
    deps = bind_workspace_registry_store(dependencies=deps, store=workspace_store)
    deps = bind_onboarding_state_store(dependencies=deps, store=onboarding_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    create_response = client.post(
        '/api/workspaces',
        headers=_session_headers(),
        json={'title': 'Roundtrip Workspace', 'description': 'Created in-process'},
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload['workspace']['workspace_id'] == 'ws-roundtrip'
    assert create_payload['owner_membership_id'] == 'membership-roundtrip'
    assert create_payload['provider_continuity'] is None
    assert create_payload['activity_continuity'] is None

    list_response = client.get('/api/workspaces', headers=_session_headers())
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload['returned_count'] == 1
    assert list_payload['workspaces'][0]['workspace_id'] == 'ws-roundtrip'

    detail_response = client.get('/api/workspaces/ws-roundtrip', headers=_session_headers())
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload['workspace_id'] == 'ws-roundtrip'
    assert detail_payload['role'] == 'owner'

    recent_response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert recent_response.status_code == 200
    recent_payload = recent_response.json()
    assert recent_payload['activities'][0]['activity_type'] == 'workspace_created'
    assert recent_payload['activities'][0]['workspace_id'] == 'ws-roundtrip'
    assert recent_payload['provider_continuity'] is None
    assert recent_payload['activity_continuity'] is None

    summary_response = client.get('/api/users/me/history-summary', headers=_session_headers())
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['provider_continuity'] is None
    assert summary_payload['activity_continuity'] is None
    assert summary_payload['visible_workspace_count'] == 1
    assert summary_payload['recent_workspace_count'] == 1
    assert summary_payload['latest_workspace_id'] == 'ws-roundtrip'

    onboarding_put = client.put(
        '/api/users/me/onboarding',
        headers=_session_headers(),
        json={'workspace_id': 'ws-roundtrip', 'first_success_achieved': True, 'advanced_surfaces_unlocked': True, 'current_step': 'workspace-ready'},
    )
    assert onboarding_put.status_code == 200
    onboarding_put_payload = onboarding_put.json()
    assert onboarding_put_payload['state']['workspace_id'] == 'ws-roundtrip'
    assert onboarding_put_payload['state']['first_success_achieved'] is True

    onboarding_get = client.get('/api/users/me/onboarding?workspace_id=ws-roundtrip', headers=_session_headers())
    assert onboarding_get.status_code == 200
    onboarding_get_payload = onboarding_get.json()
    assert onboarding_get_payload['state']['onboarding_state_id'] == 'onboard-roundtrip'
    assert onboarding_get_payload['state']['advanced_surfaces_unlocked'] is True
    assert onboarding_get_payload['state']['current_step'] == 'workspace-ready'

    recent_after_onboarding = client.get('/api/users/me/activity?workspace_id=ws-roundtrip&limit=5', headers=_session_headers())
    assert recent_after_onboarding.status_code == 200
    recent_after_onboarding_payload = recent_after_onboarding.json()
    onboarding_items = [item for item in recent_after_onboarding_payload['activities'] if item['activity_type'] == 'onboarding_updated']
    assert len(onboarding_items) == 1
    assert onboarding_items[0]['links']['onboarding'] == '/api/users/me/onboarding?workspace_id=ws-roundtrip'

    summary_after_onboarding = client.get('/api/users/me/history-summary?workspace_id=ws-roundtrip', headers=_session_headers())
    assert summary_after_onboarding.status_code == 200
    summary_after_onboarding_payload = summary_after_onboarding.json()
    assert summary_after_onboarding_payload['recent_onboarding_count'] == 1
    assert summary_after_onboarding_payload['latest_onboarding_state_id'] == 'onboard-roundtrip'
    assert summary_after_onboarding_payload['latest_activity_at'] == '2026-04-12T10:30:00+00:00'
