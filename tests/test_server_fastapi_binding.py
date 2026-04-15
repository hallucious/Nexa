from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from src.server.managed_secret_metadata_store import InMemoryManagedSecretMetadataStore, bind_managed_secret_metadata_store
from src.server.onboarding_state_store import InMemoryOnboardingStateStore, bind_onboarding_state_store
from src.server.feedback_store import InMemoryFeedbackStore, bind_feedback_store
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
from src.storage.share_api import export_public_nex_link_share


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




def _valid_working_save_artifact() -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
        "circuit": {"nodes": [{"id": "n1", "type": "plugin", "plugin_ref": "plugin.main", "inputs": {}, "outputs": {"result": "output.value"}}], "edges": [], "entry": "n1", "outputs": [{"name": "result", "node_id": "n1", "path": "output.value"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.main": {"entrypoint": "demo.main"}}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
    }

def _share_payload(share_id: str = "share-fastapi-001") -> dict:
    return export_public_nex_link_share(
        _commit_snapshot("snap-fastapi-share-001"),
        share_id=share_id,
        title="FastAPI share",
        created_at="2026-04-15T12:00:00+00:00",
        issued_by_user_ref="user-owner",
    )


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


def _make_client(*, onboarding_store: InMemoryOnboardingStateStore | None = None, feedback_store: InMemoryFeedbackStore | None = None, artifact_source=None, public_share_payload_provider=None, public_share_payload_rows_provider=None, public_share_payload_writer=None, public_share_payload_deleter=None) -> TestClient:
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
    artifact_store = {'ws-001': artifact_source or _working_save_artifact()}

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
        workspace_artifact_source_provider=lambda workspace_id: artifact_store.get(workspace_id),
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
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
                "final_output": {"output_key": "answer", "value_preview": "Latest Hello", "value_type": "string"},
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
        public_share_payload_provider=public_share_payload_provider or (lambda share_id: _share_payload(share_id)),
        public_share_payload_rows_provider=public_share_payload_rows_provider or (lambda: (_share_payload('share-fastapi-001'),)),
        public_share_payload_writer=public_share_payload_writer or (lambda payload: dict(payload)),
        public_share_payload_deleter=public_share_payload_deleter or (lambda _share_id: False),
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
    if onboarding_store is not None:
        deps = bind_onboarding_state_store(dependencies=deps, store=onboarding_store)
    if feedback_store is not None:
        deps = bind_feedback_store(dependencies=deps, store=feedback_store)
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
    assert payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert payload["source_artifact"]["canonical_ref"] == "snap-001"


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
    assert artifact_list_payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert artifact_list_payload["source_artifact"]["canonical_ref"] == "snap-001"

    artifact_detail_response = client.get("/api/artifacts/artifact-1", headers=_session_headers())
    assert artifact_detail_response.status_code == 200
    artifact_detail_payload = artifact_detail_response.json()
    assert artifact_detail_payload["payload_access"]["mode"] == "inline"
    assert artifact_detail_payload["workspace_title"] == "Primary Workspace"
    assert artifact_detail_payload["provider_continuity"]["provider_binding_count"] == 1
    assert artifact_detail_payload["activity_continuity"]["recent_run_count"] == 1
    assert artifact_detail_payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert artifact_detail_payload["source_artifact"]["canonical_ref"] == "snap-001"

    trace_response = client.get("/api/runs/run-001/trace?limit=10", headers=_session_headers())
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["workspace_id"] == "ws-001"
    assert trace_payload["workspace_title"] == "Primary Workspace"
    assert trace_payload["provider_continuity"]["provider_binding_count"] == 1
    assert trace_payload["activity_continuity"]["recent_run_count"] == 1
    assert trace_payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert trace_payload["source_artifact"]["canonical_ref"] == "snap-001"
    assert [event["sequence"] for event in trace_payload["events"]] == [1, 2]




def test_fastapi_binding_circuit_library_routes_round_trip() -> None:
    client = _make_client()

    api_response = client.get('/api/workspaces/library', headers=_session_headers())
    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert api_payload['status'] == 'ready'
    assert api_payload['library']['returned_count'] == 1
    assert api_payload['library']['items'][0]['continue_href'] == '/app/workspaces/ws-001'
    assert api_payload['library']['items'][0]['result_history_href'] == '/app/workspaces/ws-001/results?run_id=run-001'

    page_response = client.get('/app/library', headers=_session_headers())
    assert page_response.status_code == 200
    assert 'My workflows' in page_response.text
    assert '/app/workspaces/ws-001' in page_response.text

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
    assert payload['routes']['onboarding_write'] == '/api/users/me/onboarding'
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
    assert payload['status_history_section']['summary']['headline'] == 'Status history'
    assert 'Recent runs: 2' in payload['status_history_section']['summary']['lines']
    assert 'run-001' in '\n'.join(payload['status_history_section']['detail']['items'])
    assert payload['result_history_section']['summary']['headline'] == 'Result history'
    assert 'Recent results: 2' in payload['result_history_section']['summary']['lines']
    assert 'run-001' in '\n'.join(payload['result_history_section']['detail']['items'])
    assert payload['designer_section']['summary']['headline'] == 'Designer workspace'
    assert 'Templates available:' in '\n'.join(payload['designer_section']['summary']['lines'])
    assert payload['designer_section']['detail']['title'] == 'Designer detail'
    assert payload['validation_section']['summary']['headline'] == 'Validation: unknown'
    assert payload['validation_section']['detail']['title'] == 'Validation detail'
    assert payload['navigation']['default_section'] == 'result'
    assert payload['navigation']['default_level'] == 'detail'
    assert payload['navigation']['guidance_label'] == 'Recommended next: Result'
    assert 'mobile first-run path should move to Result next' in payload['navigation']['guidance_summary']
    assert [section['section_id'] for section in payload['navigation']['sections']] == ['designer', 'validation', 'status', 'result', 'trace', 'artifacts']
    assert payload['step_state_banner']['title'] == 'Step 5 of 5 — Read result'
    assert payload['step_state_banner']['recommended_section'] == 'result'
    assert payload['step_state_banner']['action_label'] == 'Open Result'
    assert payload['step_state_banner']['action_target'] == 'runtime.result'
    assert payload['step_state_banner']['action_kind'] == 'focus_section'
    assert 'Result is ready.' in payload['step_state_banner']['summary']
    assert payload['client_continuity']['enabled'] is True
    assert payload['client_continuity']['storage_key'] == 'nexa.runtime_shell.ws-001'
    assert payload['client_continuity']['version'] == 'phase6-batch15'


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
    assert 'Run status history' in body
    assert 'Run result history' in body
    assert 'Latest trace' in body
    assert 'Latest artifacts' in body
    assert 'Open latest result' in body
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
    assert 'Designer workspace' in body
    assert 'Validation review' in body
    assert 'Designer detail layer' in body
    assert 'Validation detail layer' in body
    assert 'designer-controls' in body
    assert 'validation-controls' in body
    assert 'performShellAction' in body
    assert 'persistOnboardingState' in body
    assert '/api/users/me/onboarding' in body
    assert 'Use Text Summarizer' in body
    assert 'Open Validation detail' in body
    assert 'focus-state' in body
    assert 'focus-guidance' in body
    assert 'Recommended next: Result' in body
    assert 'Step state banner' in body
    assert 'step-state-banner-title' in body
    assert 'step-state-banner-summary' in body
    assert 'Step 5 of 5 — Read result' in body
    assert 'step-state-banner-action' in body
    assert 'step-state-banner-action-button' in body
    assert 'Open Result' in body
    assert 'runtime.result' in body
    assert 'performBannerAction' in body
    assert 'writeStepStateBanner' in body
    assert 'refreshStepStateBanner' in body
    assert 'readShellContinuity' in body
    assert 'writeShellContinuity' in body
    assert 'applyShellContinuity' in body
    assert 'nexa.runtime_shell.ws-001' in body
    assert 'writeFocusGuidance' in body
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

    artifact_store = {'ws-001': _working_save_artifact()}

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

    artifact_store = {'ws-001': _working_save_artifact()}

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

    artifact_store = {'ws-001': _working_save_artifact()}

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

    artifact_store = {'ws-001': _working_save_artifact()}

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


def test_fastapi_binding_workspace_shell_draft_write_persists_server_backed_state() -> None:
    client = _make_client()
    response = client.put(
        '/api/workspaces/ws-001/shell/draft',
        headers=_session_headers(),
        json={
            'template_id': 'text_summarizer',
            'template_display_name': 'Text Summarizer',
            'request_text': 'Summarize this article.',
            'designer_action': 'apply_template',
            'validation_action': 'open_validation_detail',
            'validation_status': 'blocked',
            'validation_message': 'Review validation before running.',
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['routes']['workspace_shell_draft_write'] == '/api/workspaces/ws-001/shell/draft'
    assert 'Persisted template: Text Summarizer' in '\n'.join(payload['designer_section']['summary']['lines'])
    assert 'Persisted request: Summarize this article.' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Persisted validation action: open_validation_detail' in '\n'.join(payload['validation_section']['summary']['lines'])
    assert 'Persisted validation status: blocked' in '\n'.join(payload['validation_section']['detail']['items'])


def test_fastapi_binding_workspace_result_history_routes_round_trip() -> None:
    client = _make_client()
    api_response = client.get('/api/workspaces/ws-001/result-history', headers=_session_headers())
    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert api_payload['result_history']['returned_count'] >= 1
    assert api_payload['result_history']['items'][0]['open_result_href'].startswith('/app/workspaces/ws-001/results?run_id=')
    page_response = client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert page_response.status_code == 200
    assert 'Recent results' in page_response.text
    assert 'Latest Hello' in page_response.text



def test_fastapi_binding_library_and_result_history_align_with_server_onboarding_progress() -> None:
    onboarding_store = InMemoryOnboardingStateStore()
    client = _make_client(onboarding_store=onboarding_store)

    onboarding_put = client.put(
        '/api/users/me/onboarding',
        headers=_session_headers(),
        json={'workspace_id': 'ws-001', 'first_success_achieved': False, 'advanced_surfaces_unlocked': False, 'current_step': 'read_result'},
    )
    assert onboarding_put.status_code == 200

    library_response = client.get('/api/workspaces/library', headers=_session_headers())
    assert library_response.status_code == 200
    library_payload = library_response.json()
    assert library_payload['library']['items'][0]['continue_href'] == '/app/workspaces/ws-001/results?run_id=run-001'
    assert library_payload['library']['items'][0]['onboarding_incomplete'] is True

    result_history_response = client.get('/api/workspaces/ws-001/result-history?run_id=run-001', headers=_session_headers())
    assert result_history_response.status_code == 200
    result_history_payload = result_history_response.json()
    assert result_history_payload['result_history']['onboarding_incomplete'] is True
    assert result_history_payload['result_history']['onboarding_step_id'] == 'read_result'
    assert result_history_payload['onboarding_banner']['action_href'] == '/app/workspaces/ws-001/results?run_id=run-001'


def test_fastapi_binding_workspace_feedback_routes_round_trip() -> None:
    feedback_store = InMemoryFeedbackStore()
    client = _make_client(feedback_store=feedback_store)

    get_response = client.get('/api/workspaces/ws-001/feedback?surface=result_history&run_id=run-001', headers=_session_headers())
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload['feedback_channel']['submit_path'] == '/api/workspaces/ws-001/feedback'
    assert get_payload['feedback_channel']['prefill_surface'] == 'result_history'
    assert get_payload['feedback_channel']['prefill_run_id'] == 'run-001'

    submit_response = client.post(
        '/api/workspaces/ws-001/feedback',
        headers=_session_headers(),
        json={
            'category': 'bug_report',
            'surface': 'result_history',
            'message': 'This result screen failed unexpectedly.',
            'run_id': 'run-001',
        },
    )
    assert submit_response.status_code == 202
    submit_payload = submit_response.json()
    assert submit_payload['feedback']['surface'] == 'result_history'
    assert submit_payload['feedback']['workspace_id'] == 'ws-001'

    get_after_submit = client.get('/api/workspaces/ws-001/feedback', headers=_session_headers())
    assert get_after_submit.status_code == 200
    after_payload = get_after_submit.json()
    assert after_payload['feedback_channel']['returned_count'] == 1
    assert after_payload['feedback_channel']['items'][0]['message'] == 'This result screen failed unexpectedly.'

    page_response = client.get('/app/workspaces/ws-001/feedback?surface=result_history&run_id=run-001', headers=_session_headers())
    assert page_response.status_code == 200
    body = page_response.text
    assert 'Help us improve this workflow' in body
    assert '/api/workspaces/ws-001/feedback' in body
    assert 'Report confusing screen' in body




def test_fastapi_binding_product_pages_support_korean_query_language() -> None:
    client = _make_client()

    library_page = client.get('/app/library?app_language=ko', headers=_session_headers())
    assert library_page.status_code == 200
    assert '<html lang="ko">' in library_page.text
    assert '워크플로우 라이브러리' in library_page.text
    assert '원본 워크스페이스 레지스트리' in library_page.text
    assert '실행 중' in library_page.text
    assert '업데이트됨: 2026-04-11 12:05' in library_page.text
    assert '최근 실행 기록이 있습니다.' in library_page.text
    assert '최근 실행: run-001' not in library_page.text
    assert '최근 결과 이력을 확인할 수 있습니다' in library_page.text
    assert '제품 화면에서 이 워크플로우를 바로 계속할 수 있습니다.' in library_page.text
    assert '제품 화면에서 최근 결과 이력을 바로 열 수 있습니다.' in library_page.text
    assert '이어서 사용 경로:' not in library_page.text
    assert '결과 이력 경로:' not in library_page.text

    result_page = client.get('/app/workspaces/ws-001/results?run_id=run-002&app_language=ko', headers=_session_headers())
    assert result_page.status_code == 200
    assert '<html lang="ko">' in result_page.text
    assert '최근 결과 이력' in result_page.text
    assert '라이브러리로 돌아가기' in result_page.text
    assert '결과 상세' in result_page.text
    assert '결과 열기' in result_page.text
    assert '최신 출력 (답변)' in result_page.text
    assert '실행 완료' in result_page.text
    assert '마지막 업데이트: 2026-04-11 12:01' in result_page.text
    assert '+00:00' not in result_page.text
    assert '성공적으로 완료되었습니다.' in result_page.text

    feedback_page = client.get('/app/workspaces/ws-001/feedback?surface=result_history&run_id=run-001&app_language=ko', headers=_session_headers())
    assert feedback_page.status_code == 200
    assert '<html lang="ko">' in feedback_page.text
    assert '피드백 유형' in feedback_page.text
    assert '피드백 보내기' in feedback_page.text
    assert '라이브러리로 돌아가기' in feedback_page.text
    assert '최근 피드백' in feedback_page.text
    assert '헷갈리는 화면 신고' in feedback_page.text
    assert '빠른 불편 메모' in feedback_page.text
    assert '버그 신고 바로가기' in feedback_page.text
    assert '실행 식별자 (선택)' in feedback_page.text


def test_fastapi_binding_feedback_submission_localizes_server_message() -> None:
    feedback_store = InMemoryFeedbackStore()
    client = _make_client(feedback_store=feedback_store)

    submit_response = client.post(
        '/api/workspaces/ws-001/feedback?app_language=ko',
        headers=_session_headers(),
        json={
            'category': 'bug_report',
            'surface': 'result_history',
            'message': '결과 화면이 예상과 다릅니다.',
            'run_id': 'run-001',
        },
    )
    assert submit_response.status_code == 202
    payload = submit_response.json()
    assert payload['message'] == '제품 학습용 피드백이 기록되었습니다.'
    assert payload['feedback']['category_label'] == '버그 신고 바로가기'
    assert payload['feedback']['surface_label'] == '결과 이력'


def test_fastapi_binding_workspace_shell_html_uses_localized_runtime_strings() -> None:
    client = _make_client()
    page_response = client.get('/app/workspaces/ws-001?app_language=ko', headers=_session_headers())

    assert page_response.status_code == 200
    body = page_response.text
    assert '<html lang="ko">' in body
    assert 'Nexa 런타임 셸' in body
    assert '<p><strong>Primary Workspace</strong></p>' in body
    assert '(<code>ws-001</code>)' not in body
    assert '초안 실행' in body
    assert '최신 실행 결과' in body
    assert '디자이너 작업공간' in body
    assert '단계 상태 배너' in body
    assert '추천 다음 단계:' in body
    assert '실행 ID:' in body
    assert '상태 상세' in body
    assert '최근 실행이 아직 없습니다.' in body
    assert '최근 결과 이력' in body
    assert '연결된 제공자 수:' in body
    assert '실행 추적 이력' in body
    assert '최근 실행 추적 이력이 여기에 표시됩니다.' in body
    assert '포커스:' in body
    assert '상황별 도움말' in body
    assert '마지막 작업 로그' in body
    assert '준비됨.' in body
    assert '최신 실행 추적' in body
    assert '최신 실행 추적 열기' in body
    assert '최근 산출물 이력' in body
    assert '최신 산출물 열기' in body
    assert '실행 추적 상세 레이어' in body
    assert '산출물 상세 레이어' in body
    assert '개인정보와 데이터 처리' in body
    assert '제공자 접근' in body
    assert '세션 전용 키' in body
    assert '외부 입력' in body
    assert '외부 파일이나 웹 주소 입력이 없습니다' in body
    assert '저장 경계' in body
    assert '세션 키' in body
    assert '로컬 작업 저장 연속성만 사용' in body
    assert '세션 키는 작업 저장 화면 상태에만 머물고 승인 스냅샷에는 기록되지 않습니다.' in body
    assert '목표부터 시작하세요' in body
    assert '텍스트 요약기' in body
    assert '진행 중' in body
    assert '대기 중' in body


def test_fastapi_binding_product_surfaces_expose_accessible_landmarks() -> None:
    client = _make_client()

    library_page = client.get('/app/library', headers=_session_headers())
    assert library_page.status_code == 200
    assert 'role="main" aria-labelledby="library-title"' in library_page.text
    assert 'aria-label="Workflow library"' in library_page.text
    assert 'aria-label="Open raw workspace registry JSON"' in library_page.text

    result_page = client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert result_page.status_code == 200
    assert 'role="main" aria-labelledby="result-history-title"' in result_page.text
    assert 'aria-label="Recent result history"' in result_page.text
    assert 'aria-current="true"' in result_page.text

    feedback_page = client.get('/app/workspaces/ws-001/feedback?surface=result_history&run_id=run-001', headers=_session_headers())
    assert feedback_page.status_code == 200
    assert 'role="main" aria-labelledby="feedback-title"' in feedback_page.text
    assert 'role="region" aria-labelledby="feedback-form-title"' in feedback_page.text
    assert 'aria-describedby="feedback-status"' in feedback_page.text
    assert 'aria-live="polite"' in feedback_page.text
    assert 'role="region" aria-labelledby="feedback-confirmation-title"' in feedback_page.text or 'role="region" aria-labelledby="recent-feedback-title"' in feedback_page.text


def test_fastapi_binding_workspace_shell_exposes_focus_and_live_region_semantics() -> None:
    client = _make_client()

    page_response = client.get('/app/workspaces/ws-001', headers=_session_headers())
    assert page_response.status_code == 200
    body = page_response.text
    assert 'role="main" aria-labelledby="workspace-shell-title"' in body
    assert 'role="toolbar" aria-label="Workspace shell actions"' in body
    assert 'aria-label="Runtime section navigation"' in body
    assert 'id="step-state-banner-summary" aria-live="polite"' in body
    assert 'id="browser-log" aria-live="polite"' in body
    assert 'id="designer-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="designer-detail-title"' in body
    assert 'id="privacy-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="privacy-title"' in body
    assert 'id="latest-run-trace-detail-card" tabindex="-1" class="card focus-target" role="region" aria-labelledby="latest-run-trace-detail-title"' in body


def test_fastapi_binding_workspace_shell_commit_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())
    response = client.post('/api/workspaces/ws-001/shell/commit', headers=_session_headers(), json={'commit_id': 'commit-fastapi-001'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['storage_role'] == 'commit_snapshot'
    assert payload['commit_id'] == 'commit-fastapi-001'
    assert payload['transition']['action'] == 'commit_workspace_shell'
    assert payload['routes']['workspace_shell_commit'] == '/api/workspaces/ws-001/shell/commit'


def test_fastapi_binding_workspace_shell_checkout_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())
    commit_response = client.post('/api/workspaces/ws-001/shell/commit', headers=_session_headers(), json={'commit_id': 'commit-fastapi-002'})
    assert commit_response.status_code == 200
    response = client.post('/api/workspaces/ws-001/shell/checkout', headers=_session_headers(), json={'working_save_id': 'ws-fastapi-restored'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['storage_role'] == 'working_save'
    assert payload['working_save_id'] == 'ws-fastapi-restored'
    assert payload['transition']['action'] == 'checkout_workspace_shell'
    assert payload['routes']['workspace_shell_checkout'] == '/api/workspaces/ws-001/shell/checkout'


def test_fastapi_binding_issuer_public_share_management_routes_round_trip() -> None:
    rows = (
        export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-active'),
            share_id='share-fastapi-owner-active',
            title='FastAPI Owner Active',
            created_at='2026-04-15T12:00:00+00:00',
            updated_at='2026-04-15T12:30:00+00:00',
            issued_by_user_ref='user-owner',
        ),
        export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-expired'),
            share_id='share-fastapi-owner-expired',
            title='FastAPI Owner Expired',
            created_at='2026-04-10T12:00:00+00:00',
            updated_at='2026-04-10T12:15:00+00:00',
            expires_at='2026-04-11T00:00:00+00:00',
            issued_by_user_ref='user-owner',
        ),
        export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-other-active'),
            share_id='share-fastapi-other-active',
            title='FastAPI Other Active',
            created_at='2026-04-16T12:00:00+00:00',
            updated_at='2026-04-16T12:30:00+00:00',
            issued_by_user_ref='user-other',
        ),
    )
    client = _make_client(public_share_payload_rows_provider=lambda: rows)

    list_response = client.get('/api/users/me/public-shares', headers=_session_headers())
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload['summary']['total_share_count'] == 2
    assert list_payload['summary']['active_share_count'] == 1
    assert list_payload['summary']['expired_share_count'] == 1
    assert [entry['share_id'] for entry in list_payload['shares']] == [
        'share-fastapi-owner-active',
        'share-fastapi-owner-expired',
    ]

    summary_response = client.get('/api/users/me/public-shares/summary', headers=_session_headers())
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['summary']['total_share_count'] == 2
    assert summary_payload['summary']['latest_updated_at'] == '2026-04-15T12:30:00+00:00'

    filtered_list_response = client.get('/api/users/me/public-shares?lifecycle_state=active&limit=1&offset=0', headers=_session_headers())
    assert filtered_list_response.status_code == 200
    filtered_list_payload = filtered_list_response.json()
    assert filtered_list_payload['summary']['total_share_count'] == 1
    assert filtered_list_payload['inventory_summary']['total_share_count'] == 2
    assert filtered_list_payload['pagination']['filtered_share_count'] == 1
    assert filtered_list_payload['pagination']['returned_count'] == 1
    assert filtered_list_payload['shares'][0]['share_id'] == 'share-fastapi-owner-active'

    filtered_summary_response = client.get('/api/users/me/public-shares/summary?storage_role=commit_snapshot&operation=checkout_working_copy', headers=_session_headers())
    assert filtered_summary_response.status_code == 200
    filtered_summary_payload = filtered_summary_response.json()
    assert filtered_summary_payload['summary']['total_share_count'] == 2
    assert filtered_summary_payload['applied_filters']['operation'] == 'checkout_working_copy'


def test_fastapi_binding_issuer_public_share_revoke_action_round_trip() -> None:
    share_store: dict[str, dict] = {
        "share-fastapi-owner-action-a": export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-action-a'),
            share_id='share-fastapi-owner-action-a',
            title='FastAPI Owner Action A',
            created_at='2026-04-15T12:00:00+00:00',
            issued_by_user_ref='user-owner',
        ),
        "share-fastapi-owner-action-b": export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-action-b'),
            share_id='share-fastapi-owner-action-b',
            title='FastAPI Owner Action B',
            created_at='2026-04-15T12:05:00+00:00',
            issued_by_user_ref='user-owner',
        ),
    }

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_writer=_writer,
    )
    response = client.post('/api/users/me/public-shares/actions/revoke', headers=_session_headers(), json={'share_ids': ['share-fastapi-owner-action-a', 'share-fastapi-owner-action-b']})

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'revoke'
    assert payload['affected_share_count'] == 2
    assert payload['summary']['revoked_share_count'] == 2
    assert share_store['share-fastapi-owner-action-a']['share']['lifecycle']['state'] == 'revoked'
    assert share_store['share-fastapi-owner-action-b']['share']['lifecycle']['state'] == 'revoked'

def test_fastapi_binding_public_share_routes_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/public-shares/share-fastapi-001')
    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-001'
    assert payload['operation_capabilities'] == ['inspect_metadata', 'download_artifact', 'import_copy', 'run_artifact', 'checkout_working_copy']
    assert payload['lifecycle']['stored_state'] == 'active'
    assert payload['lifecycle']['state'] == 'active'
    assert payload['audit_summary']['event_count'] == 1
    assert payload['source_artifact']['storage_role'] == 'commit_snapshot'

    history_response = client.get('/api/public-shares/share-fastapi-001/history')
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload['audit_summary']['event_count'] == 1
    assert history_payload['history'][0]['event_type'] == 'created'

    artifact_response = client.get('/api/public-shares/share-fastapi-001/artifact')
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    assert artifact_payload['artifact']['meta']['commit_id'] == 'snap-fastapi-share-001'


def test_fastapi_binding_workspace_shell_share_creation_round_trip() -> None:
    share_store: dict[str, dict] = {}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        artifact_source=_commit_snapshot('snap-fastapi-created-share-001'),
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_writer=_writer,
    )
    response = client.post(
        '/api/workspaces/ws-001/shell/share',
        headers=_session_headers(),
        json={'share_id': 'share-fastapi-created-001', 'title': 'FastAPI Shared Snapshot', 'expires_at': '2026-04-20T00:00:00+00:00'},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-created-001'
    assert payload['lifecycle']['state'] == 'active'
    assert payload['lifecycle']['created_at'] == '2026-04-11T12:09:00+00:00'
    assert payload['lifecycle']['expires_at'] == '2026-04-20T00:00:00+00:00'
    assert payload['audit_summary']['event_count'] == 1
    assert payload['lifecycle']['issued_by_user_ref'] == 'user-owner'
    assert payload['audit_summary']['event_count'] == 1
    assert payload['source_artifact']['canonical_ref'] == 'snap-fastapi-created-share-001'

    get_response = client.get('/api/public-shares/share-fastapi-created-001')
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload['share_id'] == 'share-fastapi-created-001'
    assert get_payload['lifecycle']['issued_by_user_ref'] == 'user-owner'


def test_fastapi_binding_workspace_shell_checkout_accepts_public_share_snapshot() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())
    response = client.post('/api/workspaces/ws-001/shell/checkout', headers=_session_headers(), json={'share_id': 'share-fastapi-001', 'working_save_id': 'ws-share-fastapi-restored'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['storage_role'] == 'working_save'
    assert payload['working_save_id'] == 'ws-share-fastapi-restored'
    assert payload['transition']['source_share_id'] == 'share-fastapi-001'


def test_fastapi_binding_workspace_shell_launch_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())
    response = client.post('/api/workspaces/ws-001/shell/launch', headers=_session_headers(), json={'input_payload': {'question': 'hello from fastapi shell'}})
    assert response.status_code == 202
    payload = response.json()
    assert payload['execution_target']['target_type'] == 'working_save'
    assert payload['execution_target']['target_ref'] == 'ws-001-draft'
    assert payload['launch_context']['action'] == 'launch_workspace_shell'
    assert payload['source_artifact']['storage_role'] == 'working_save'
    assert payload['source_artifact']['canonical_ref'] == 'ws-001-draft'


def test_fastapi_binding_workspace_shell_draft_rejects_commit_snapshot_source() -> None:
    client = _make_client(artifact_source=_commit_snapshot('snap-fastapi-draft-001'))
    response = client.put('/api/workspaces/ws-001/shell/draft', headers=_session_headers(), json={'request_text': 'Revise this snapshot.'})
    assert response.status_code == 409
    payload = response.json()
    assert payload['reason_code'] == 'workspace_shell.draft_requires_working_save'


def test_fastapi_binding_workspace_shell_payload_exposes_role_aware_action_availability() -> None:
    client = _make_client(artifact_source=_commit_snapshot('snap-fastapi-actions-001'))
    response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['storage_role'] == 'commit_snapshot'
    assert payload['action_availability']['draft_write']['allowed'] is False
    assert payload['action_availability']['checkout']['allowed'] is True
    assert payload['action_availability']['launch']['allowed'] is True


def test_fastapi_binding_public_share_revoke_round_trip() -> None:
    share_store: dict[str, dict] = {"share-fastapi-revoke-001": _share_payload("share-fastapi-revoke-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_writer=_writer,
    )
    response = client.post('/api/public-shares/share-fastapi-revoke-001/revoke', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-revoke-001'
    assert payload['lifecycle']['state'] == 'revoked'
    assert payload['lifecycle']['updated_at'] == '2026-04-11T12:09:00+00:00'
    assert payload['audit_summary']['event_count'] == 2
    assert share_store['share-fastapi-revoke-001']['share']['lifecycle']['state'] == 'revoked'


def test_fastapi_binding_public_share_artifact_rejects_expired_share() -> None:
    client = _make_client(public_share_payload_provider=lambda share_id: export_public_nex_link_share(
        _commit_snapshot('snap-fastapi-expired-share-001'),
        share_id=share_id,
        title='Expired FastAPI Share',
        created_at='2026-04-15T12:00:00+00:00',
        expires_at='2026-04-10T00:00:00+00:00',
        issued_by_user_ref='user-owner',
    ))

    response = client.get('/api/public-shares/share-fastapi-expired/artifact')

    assert response.status_code == 409
    payload = response.json()
    assert payload['reason_code'] == 'public_share.download_not_allowed'


def test_fastapi_binding_public_share_extend_round_trip() -> None:
    share_store: dict[str, dict] = {"share-fastapi-extend-001": _share_payload("share-fastapi-extend-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_writer=_writer,
    )
    response = client.post(
        '/api/public-shares/share-fastapi-extend-001/extend',
        headers=_session_headers(),
        json={"expires_at": "2026-04-20T00:00:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-extend-001'
    assert payload['lifecycle']['stored_state'] == 'active'
    assert payload['lifecycle']['state'] == 'active'
    assert payload['lifecycle']['expires_at'] == '2026-04-20T00:00:00+00:00'
    assert payload['audit_summary']['event_count'] == 2



def test_fastapi_binding_delete_issuer_public_shares_round_trip() -> None:
    share_store = {
        "share-fastapi-delete-a": export_public_nex_link_share(_commit_snapshot("snap-fastapi-delete-a"), share_id="share-fastapi-delete-a", title="FastAPI Delete A", created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner"),
        "share-fastapi-delete-b": export_public_nex_link_share(_commit_snapshot("snap-fastapi-delete-b"), share_id="share-fastapi-delete-b", title="FastAPI Delete B", created_at="2026-04-15T12:05:00+00:00", issued_by_user_ref="user-owner"),
    }

    client = _make_client(
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
    )
    response = client.post('/api/users/me/public-shares/actions/delete', headers=_session_headers(), json={'share_ids': ['share-fastapi-delete-a', 'share-fastapi-delete-b']})

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'delete'
    assert payload['affected_share_count'] == 2
    assert payload['summary']['total_share_count'] == 0


def test_fastapi_binding_public_share_delete_round_trip() -> None:
    share_store = {"share-fastapi-delete-001": _share_payload("share-fastapi-delete-001")}

    client = _make_client(
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
    )
    response = client.delete('/api/public-shares/share-fastapi-delete-001', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'deleted'
    assert payload['share_id'] == 'share-fastapi-delete-001'
