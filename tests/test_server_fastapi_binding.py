from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
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
    RunAuthorizationContext,
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
        recent_provider_probe_rows_provider=lambda: provider_probe_rows.get('ws-001', ()),
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
        now_iso_provider=lambda: "2026-04-11T12:00:00+00:00",
    )
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


def test_fastapi_binding_status_endpoint_round_trip() -> None:
    client = _make_client()
    response = client.get("/api/runs/run-001", headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["progress"]["percent"] == 25


def test_fastapi_binding_result_endpoint_round_trip() -> None:
    client = _make_client()
    response = client.get("/api/runs/run-001/result", headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_state"] == "ready_success"
    assert payload["final_output"]["output_key"] == "answer"


def test_fastapi_binding_artifact_and_trace_routes_round_trip() -> None:
    client = _make_client()

    artifact_list_response = client.get("/api/runs/run-001/artifacts", headers=_session_headers())
    assert artifact_list_response.status_code == 200
    artifact_list_payload = artifact_list_response.json()
    assert artifact_list_payload["artifact_count"] == 1

    artifact_detail_response = client.get("/api/artifacts/artifact-1", headers=_session_headers())
    assert artifact_detail_response.status_code == 200
    artifact_detail_payload = artifact_detail_response.json()
    assert artifact_detail_payload["payload_access"]["mode"] == "inline"

    trace_response = client.get("/api/runs/run-001/trace?limit=10", headers=_session_headers())
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert [event["sequence"] for event in trace_payload["events"]] == [1, 2]


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
    assert payload["returned_count"] == 2
    assert payload["runs"][0]["run_id"] == "run-002"


def test_fastapi_binding_workspace_and_onboarding_routes_round_trip() -> None:
    client = _make_client()

    workspace_list = client.get('/api/workspaces', headers=_session_headers())
    assert workspace_list.status_code == 200
    workspace_payload = workspace_list.json()
    assert workspace_payload['returned_count'] == 1
    assert workspace_payload['workspaces'][0]['workspace_id'] == 'ws-001'

    workspace_detail = client.get('/api/workspaces/ws-001', headers=_session_headers())
    assert workspace_detail.status_code == 200
    assert workspace_detail.json()['workspace_id'] == 'ws-001'

    workspace_create = client.post('/api/workspaces', headers=_session_headers(), json={'title': 'Created Workspace'})
    assert workspace_create.status_code == 201
    assert workspace_create.json()['workspace']['workspace_id'] == 'ws-new'

    onboarding_get = client.get('/api/users/me/onboarding', headers=_session_headers())
    assert onboarding_get.status_code == 200
    assert onboarding_get.json()['state']['first_success_achieved'] is False

    onboarding_put = client.put(
        '/api/users/me/onboarding',
        headers=_session_headers(),
        json={'first_success_achieved': True, 'advanced_surfaces_unlocked': True},
    )
    assert onboarding_put.status_code == 200
    assert onboarding_put.json()['state']['advanced_surfaces_unlocked'] is True


def test_fastapi_binding_provider_catalog_and_workspace_bindings_round_trip() -> None:
    client = _make_client()

    catalog_response = client.get("/api/providers/catalog", headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload["returned_count"] == 1
    assert catalog_payload["providers"][0]["provider_key"] == "openai"

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


def test_fastapi_binding_recent_activity_includes_provider_probe_event() -> None:
    client = _make_client()
    response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['activities'][0]['activity_type'] == 'provider_probe_reachable'
    assert payload['activities'][0]['links']['provider_probe_history'].endswith('/probe-history')


def test_fastapi_binding_provider_probe_history_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['returned_count'] == 1
    assert payload['items'][0]['probe_event_id'] == 'probe-001'
