from __future__ import annotations

import json

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
    FastApiBindingConfig,
    FastApiRouteDependencies,
    FrameworkRouteBindings,
    RunAuthorizationContext,
    RunHttpRouteSurface,
    WorkspaceAuthorizationContext,
    create_fastapi_app,
)
from src.storage.share_api import export_public_nex_link_share
from src.server.public_surface_registry import (
    PUBLIC_COMMUNITY_ASSET_SPECS,
    PUBLIC_COMMUNITY_ASSET_SURFACE_FAMILIES,
    app_href,
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




def _valid_working_save_artifact() -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
        "circuit": {"nodes": [{"id": "n1", "type": "plugin", "plugin_ref": "plugin.main", "inputs": {}, "outputs": {"result": "output.value"}}], "edges": [], "entry": "n1", "outputs": [{"name": "result", "node_id": "n1", "path": "output.value"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.main": {"entrypoint": "demo.main"}}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
        "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
    }

def _provider_backed_working_save_artifact(ref: str = "ws-001-provider-draft") -> dict:
    return {
        "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": ref, "name": "Primary Workspace"},
        "circuit": {
            "nodes": [
                {
                    "node_id": "n-provider",
                    "kind": "provider",
                    "resource_ref": {"provider": "openai", "prompt": "prompt.main"},
                    "execution": {"provider": {"provider_id": "openai:gpt", "prompt_ref": "prompt.main"}},
                }
            ],
            "edges": [],
            "entry": "n-provider",
            "outputs": [{"name": "result", "source": "state.working.result"}],
        },
        "resources": {
            "prompts": {"prompt.main": {"template": "Hello"}},
            "providers": {"openai": {"provider_family": "openai", "display_name": "OpenAI GPT"}},
            "plugins": {},
        },
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


def _issuer_action_report_rows() -> list[dict]:
    return [
        {
            "report_id": "report-fastapi-revoke-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T12:10:00+00:00",
            "requested_share_ids": ["share-fastapi-001"],
            "affected_share_ids": ["share-fastapi-001"],
            "affected_share_count": 1,
            "before_total_share_count": 3,
            "after_total_share_count": 3,
            "actor_user_ref": "user-owner",
        },
        {
            "report_id": "report-fastapi-archive-001",
            "issuer_user_ref": "user-owner",
            "action": "archive",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T12:20:00+00:00",
            "requested_share_ids": ["share-fastapi-002"],
            "affected_share_ids": ["share-fastapi-002"],
            "affected_share_count": 1,
            "before_total_share_count": 3,
            "after_total_share_count": 3,
            "actor_user_ref": "user-owner",
            "archived": True,
        },
    ]


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

    def get_secret_value(self, SecretId: str):
        return {"ARN": "arn:aws:secretsmanager:region:acct:secret:" + SecretId, "Name": SecretId, "SecretString": "aws-probe-key"}


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


def _make_client(*, onboarding_store: InMemoryOnboardingStateStore | None = None, feedback_store: InMemoryFeedbackStore | None = None, artifact_source=None, public_share_payload_provider=None, public_share_payload_rows_provider=None, public_share_payload_writer=None, public_share_payload_deleter=None, public_share_action_report_rows_provider=None, public_share_action_report_writer=None, saved_public_share_rows_provider=None, saved_public_share_writer=None, saved_public_share_deleter=None, workspace_run_rows=None, workspace_result_rows=None, workspace_provider_binding_rows=None, workspace_provider_probe_rows=None, recent_managed_secret_rows=None, fastapi_config: FastApiBindingConfig | None = None, edge_observation_writer=None) -> TestClient:
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
    workspace_provider_binding_rows = provider_binding_rows.get('ws-001', ()) if workspace_provider_binding_rows is None else workspace_provider_binding_rows
    workspace_provider_probe_rows = provider_probe_rows.get('ws-001', ()) if workspace_provider_probe_rows is None else workspace_provider_probe_rows
    recent_managed_secret_rows = recent_managed_secret_rows if recent_managed_secret_rows is not None else ({
        'workspace_id': 'ws-001',
        'provider_key': 'openai',
        'secret_ref': 'secret://ws-001/openai',
        'last_rotated_at': '2026-04-11T12:06:00+00:00',
    },)
    workspace_run_rows = workspace_run_rows if workspace_run_rows is not None else (
        _run_row(trace_available=True),
        {**_run_row(status='completed', trace_available=True), 'run_id': 'run-002', 'created_at': '2026-04-11T12:01:00+00:00', 'updated_at': '2026-04-11T12:01:00+00:00'},
    )
    workspace_result_rows = workspace_result_rows if workspace_result_rows is not None else {
        'run-002': {
            'run_id': 'run-002',
            'workspace_id': 'ws-001',
            'result_state': 'ready_success',
            'final_status': 'completed',
            'result_summary': 'Success.',
            'updated_at': '2026-04-11T12:01:05+00:00',
            'final_output': {'output_key': 'answer', 'value_preview': 'Latest Hello', 'value_type': 'string'},
        }
    }
    probe_store = InMemoryProviderProbeHistoryStore.from_rows(workspace_provider_probe_rows)

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
        workspace_provider_binding_rows_provider=lambda workspace_id: workspace_provider_binding_rows if workspace_id == 'ws-001' else (),
        workspace_provider_binding_row_provider=lambda workspace_id, provider_key: next((row for row in provider_binding_rows.get(workspace_id, ()) if row['provider_key'] == provider_key), None),
        workspace_provider_probe_rows_provider=lambda workspace_id: workspace_provider_probe_rows if workspace_id == 'ws-001' else (),
        recent_provider_binding_rows_provider=lambda: workspace_provider_binding_rows,
        recent_provider_probe_rows_provider=lambda: workspace_provider_probe_rows,
        recent_managed_secret_rows_provider=lambda: recent_managed_secret_rows,
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
        workspace_run_rows_provider=lambda workspace_id: workspace_run_rows if workspace_id == 'ws-001' else (),
        workspace_result_rows_provider=lambda workspace_id: workspace_result_rows if workspace_id == 'ws-001' else {},
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
        public_share_action_report_rows_provider=public_share_action_report_rows_provider or (lambda: ()),
        public_share_action_report_writer=public_share_action_report_writer or (lambda row: dict(row)),
        saved_public_share_rows_provider=saved_public_share_rows_provider or (lambda: ()),
        saved_public_share_writer=saved_public_share_writer or (lambda row: dict(row)),
        saved_public_share_deleter=saved_public_share_deleter or (lambda _share_id: False),
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
        edge_observation_writer=edge_observation_writer or (lambda event: dict(event)),
    )
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    if onboarding_store is not None:
        deps = bind_onboarding_state_store(dependencies=deps, store=onboarding_store)
    if feedback_store is not None:
        deps = bind_feedback_store(dependencies=deps, store=feedback_store)
    return TestClient(create_fastapi_app(dependencies=deps, config=fastapi_config))


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
    assert payload["identity_policy"]["surface_family"] == "run-status"
    assert payload["namespace_policy"]["family"] == "run-status"


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
    assert payload["identity_policy"]["surface_family"] == "run-result"
    assert payload["namespace_policy"]["family"] == "run-result"


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
    assert artifact_list_payload["identity_policy"]["surface_family"] == "run-artifacts"
    assert artifact_list_payload["namespace_policy"]["family"] == "run-artifacts"
    assert artifact_list_payload["artifacts"][0]["identity"]["canonical_key"] == "artifact_id"

    artifact_detail_response = client.get("/api/artifacts/artifact-1", headers=_session_headers())
    assert artifact_detail_response.status_code == 200
    artifact_detail_payload = artifact_detail_response.json()
    assert artifact_detail_payload["payload_access"]["mode"] == "inline"
    assert artifact_detail_payload["workspace_title"] == "Primary Workspace"
    assert artifact_detail_payload["provider_continuity"]["provider_binding_count"] == 1
    assert artifact_detail_payload["activity_continuity"]["recent_run_count"] == 1
    assert artifact_detail_payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert artifact_detail_payload["source_artifact"]["canonical_ref"] == "snap-001"
    assert artifact_detail_payload["identity_policy"]["surface_family"] == "artifact-detail"
    assert artifact_detail_payload["namespace_policy"]["family"] == "artifact-detail"
    assert artifact_detail_payload["identity"]["canonical_key"] == "artifact_id"

    trace_response = client.get("/api/runs/run-001/trace?limit=10", headers=_session_headers())
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["workspace_id"] == "ws-001"
    assert trace_payload["workspace_title"] == "Primary Workspace"
    assert trace_payload["provider_continuity"]["provider_binding_count"] == 1
    assert trace_payload["activity_continuity"]["recent_run_count"] == 1
    assert trace_payload["source_artifact"]["storage_role"] == "commit_snapshot"
    assert trace_payload["source_artifact"]["canonical_ref"] == "snap-001"
    assert trace_payload["identity_policy"]["surface_family"] == "run-trace"
    assert trace_payload["namespace_policy"]["family"] == "run-trace"
    assert trace_payload["events"][0]["identity"]["canonical_key"] == "event_id"
    assert [event["sequence"] for event in trace_payload["events"]] == [1, 2]

    actions_response = client.get("/api/runs/run-001/actions", headers=_session_headers())
    assert actions_response.status_code == 200
    actions_payload = actions_response.json()
    assert actions_payload["identity_policy"]["surface_family"] == "run-action-log"
    assert actions_payload["namespace_policy"]["family"] == "run-action-log"
    assert actions_payload["returned_count"] >= 0
    if actions_payload["actions"]:
        assert actions_payload["actions"][0]["identity"]["canonical_key"] == "event_id"






def test_fastapi_binding_starter_template_routes_round_trip() -> None:
    client = _make_client()

    catalog_response = client.get('/api/templates/starter-circuits')
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload['catalog']['family'] == 'starter-circuit-template-catalog'
    assert catalog_payload['catalog']['identity_policy']['canonical_key'] == 'template_ref'
    assert catalog_payload['identity_policy']['canonical_key'] == 'template_ref'
    assert catalog_payload['namespace_policy']['family'] == 'starter-template'
    assert catalog_payload['templates'][0]['template_ref'] == 'nexa-curated:text_summarizer@1.0'
    assert catalog_payload['templates'][0]['provenance']['family'] == 'starter-template'

    detail_response = client.get('/api/templates/starter-circuits/text_summarizer')
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload['template']['template_id'] == 'text_summarizer'
    assert detail_payload['template']['template_ref'] == 'nexa-curated:text_summarizer@1.0'
    assert detail_payload['template']['identity']['legacy_value'] == 'text_summarizer'
    assert detail_payload['template']['compatibility']['family'] == 'workspace-shell-draft'

    workspace_catalog_response = client.get('/api/workspaces/ws-001/starter-templates', headers=_session_headers())
    assert workspace_catalog_response.status_code == 200
    workspace_catalog_payload = workspace_catalog_response.json()
    assert workspace_catalog_payload['workspace_id'] == 'ws-001'
    assert workspace_catalog_payload['routes']['self'] == '/api/workspaces/ws-001/starter-templates'
    assert workspace_catalog_payload['templates'][0]['routes']['self'] == '/api/workspaces/ws-001/starter-templates/text_summarizer'

    workspace_detail_response = client.get('/api/workspaces/ws-001/starter-templates/text_summarizer', headers=_session_headers())
    assert workspace_detail_response.status_code == 200
    workspace_detail_payload = workspace_detail_response.json()
    assert workspace_detail_payload['workspace_id'] == 'ws-001'
    assert workspace_detail_payload['template']['routes']['workspace_catalog'] == '/api/workspaces/ws-001/starter-templates'

    apply_response = client.post('/api/workspaces/ws-001/starter-templates/text_summarizer/apply', headers=_session_headers())
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    assert apply_payload['template']['template_id'] == 'text_summarizer'
    assert apply_payload['template']['template_ref'] == 'nexa-curated:text_summarizer@1.0'
    assert apply_payload['template']['identity']['canonical_key'] == 'template_ref'
    assert apply_payload['template']['supported_storage_roles'] == ['working_save']





def test_fastapi_binding_public_plugin_catalog_route_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/integrations/public-plugins/catalog')

    assert response.status_code == 200
    payload = response.json()
    assert payload['catalog']['surface_family'] == 'public-plugin-catalog'
    assert payload['namespace_policy']['family'] == 'public-plugin-catalog'
    assert payload['plugins']

def test_fastapi_binding_public_community_catalog_route_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/integrations/public-community/catalog')

    assert response.status_code == 200
    payload = response.json()
    assert payload['catalog']['surface_family'] == 'public-community-catalog'
    assert payload['namespace_policy']['family'] == 'public-community-catalog'
    assert payload['assets']

def test_fastapi_binding_public_community_hub_page_renders_cross_linked_assets() -> None:
    client = _make_client()
    response = client.get('/app/community?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Community hub' in body
    assert app_href('starter_template_catalog_page', app_language='en') in body
    assert app_href('public_share_catalog_page', app_language='en') in body
    assert app_href('public_plugin_catalog_page', app_language='en') in body
    assert app_href('public_mcp_catalog_page', app_language='en') in body
    assert app_href('public_ecosystem_catalog_page', app_language='en') in body
    assert app_href('public_hub_page', app_language='en') in body
    assert app_href('public_integration_hub_page', app_language='en') in body

def test_fastapi_binding_public_plugin_catalog_page_renders_plugin_cards() -> None:
    client = _make_client()
    response = client.get('/app/plugins?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public plugin catalog' in body
    assert 'nexa.file_reader' in body
    assert '/api/integrations/public-plugins/catalog' in body
    assert '/app/community?app_language=en' in body
    assert '/app/public?app_language=en' in body
    assert '/app/integrations?app_language=en' in body

def test_fastapi_binding_public_sdk_catalog_page_renders_sdk_entrypoints() -> None:
    client = _make_client()
    response = client.get('/app/sdk?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public SDK catalog' in body
    assert 'import_public_nex_artifact' in body
    assert 'build_public_mcp_tools' in body
    assert 'describe_public_mcp_export_surface' in body
    assert app_href('public_ecosystem_catalog_page', app_language='en') in body
    assert app_href('community_hub_page', app_language='en') in body
    assert '/app/plugins?app_language=en' in body
    assert '/app/mcp?app_language=en' in body
    assert '/app/providers?app_language=en' in body
    assert app_href('public_nex_format_page', app_language='en') in body
    assert app_href('public_hub_page', app_language='en') in body
    assert app_href('public_integration_hub_page', app_language='en') in body

def test_fastapi_binding_public_ecosystem_catalog_page_renders_surface_cards() -> None:
    client = _make_client()
    response = client.get('/app/ecosystem?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public ecosystem catalog' in body
    assert 'public-community-catalog' in body
    assert app_href('community_hub_page', app_language='en') in body
    assert app_href('public_sdk_catalog_page', app_language='en') in body
    assert app_href('public_plugin_catalog_page', app_language='en') in body
    assert app_href('public_share_catalog_page', app_language='en') in body
    assert app_href('public_mcp_catalog_page', app_language='en') in body
    assert app_href('provider_catalog_page', app_language='en') in body
    assert app_href('public_nex_format_page', app_language='en') in body
    assert app_href('public_hub_page', app_language='en') in body
    assert app_href('public_integration_hub_page', app_language='en') in body

def test_fastapi_binding_public_ecosystem_catalog_route_round_trip() -> None:
    client = _make_client()

    api_response = client.get('/api/integrations/public-ecosystem/catalog')

    assert api_response.status_code == 200
    payload = api_response.json()
    assert payload["catalog"]["surface_family"] == "public-ecosystem-catalog"
    assert payload["identity_policy"]["canonical_key"] == "catalog.surface_family"
    assert payload["namespace_policy"]["family"] == "public-ecosystem-catalog"
    assert payload["routes"]["self"] == "/api/integrations/public-ecosystem/catalog"

def test_fastapi_binding_public_mcp_catalog_page_renders_manifest_and_bridge() -> None:
    client = _make_client()
    response = client.get('/app/mcp?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public MCP surface' in body
    assert 'nexa-public' in body
    assert 'FrameworkRouteBindings' in body
    assert '/api/integrations/public-mcp/manifest' in body
    assert app_href('public_nex_format_page', app_language='en') in body
    assert app_href('public_hub_page', app_language='en') in body
    assert app_href('public_integration_hub_page', app_language='en') in body


def test_fastapi_binding_public_provider_catalog_page_renders_provider_cards() -> None:
    client = _make_client()
    response = client.get('/app/providers?app_language=en', headers=_session_headers())

    assert response.status_code == 200
    body = response.text
    assert 'Provider catalog' in body
    assert 'OpenAI GPT' in body
    assert app_href('public_ecosystem_catalog_page', app_language='en') in body
    assert app_href('public_mcp_catalog_page', app_language='en') in body
    assert app_href('public_hub_page', app_language='en') in body
    assert app_href('public_integration_hub_page', app_language='en') in body


def test_fastapi_binding_public_nex_format_page_renders_role_boundaries() -> None:
    client = _make_client()
    response = client.get('/app/public-nex?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public .nex format' in body
    assert '.nex' in body
    assert 'working_save_id' in body
    assert 'commit_id' in body
    assert '/app/mcp?app_language=en' in body
    assert '/app/public?app_language=en' in body
    assert '/app/integrations?app_language=en' in body


def test_fastapi_binding_public_hub_page_renders_public_surface_cards() -> None:
    client = _make_client()
    response = client.get('/app/public?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public surface hub' in body
    assert '/app/community?app_language=en' in body
    assert '/app/ecosystem?app_language=en' in body
    assert '/app/public-shares?app_language=en' in body
    assert '/app/templates/starter-circuits?app_language=en' in body
    assert '/app/integrations?app_language=en' in body


def test_fastapi_binding_public_integration_hub_page_renders_integration_cards() -> None:
    client = _make_client()
    response = client.get('/app/integrations?app_language=en')

    assert response.status_code == 200
    body = response.text
    assert 'Public integration hub' in body
    assert '/app/sdk?app_language=en' in body
    assert '/app/plugins?app_language=en' in body
    assert '/app/mcp?app_language=en' in body
    assert '/app/providers?app_language=en' in body
    assert '/app/public-nex?app_language=en' in body


def test_fastapi_binding_public_nex_format_route_round_trip() -> None:
    client = _make_client()

    api_response = client.get('/api/formats/public-nex')

    assert api_response.status_code == 200
    payload = api_response.json()
    assert payload["format_boundary"]["format_family"] == ".nex"
    assert payload["identity_policy"]["canonical_key"] == "format_boundary.format_family"
    assert payload["namespace_policy"]["family"] == "public-nex-format"
    assert payload["routes"]["app_catalog_page"] == app_href("public_nex_format_page", app_language="en").split("?")[0]
    assert payload["routes"]["public_mcp_catalog_page"] == app_href("public_mcp_catalog_page", app_language="en").split("?")[0]
    assert payload["routes"]["provider_catalog_page"] == app_href("provider_catalog_page", app_language="en").split("?")[0]
    assert payload["role_boundaries"]["commit_snapshot"]["storage_role"] == "commit_snapshot"


def test_fastapi_binding_circuit_library_routes_round_trip() -> None:
    client = _make_client()

    api_response = client.get('/api/workspaces/library', headers=_session_headers())
    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert api_payload['status'] == 'ready'
    assert api_payload['identity_policy']['surface_family'] == 'circuit-library'
    assert api_payload['namespace_policy']['family'] == 'circuit-library'
    assert api_payload['library']['returned_count'] == 1
    assert api_payload['library']['items'][0]['continue_href'] == '/app/workspaces/ws-001'
    assert api_payload['library']['items'][0]['result_history_href'] == '/app/workspaces/ws-001/results?run_id=run-001'
    assert api_payload['item_sections'][0]['identity']['canonical_value'] == 'ws-001'

    api_workspace_response = client.get('/api/workspaces/ws-001/library', headers=_session_headers())
    assert api_workspace_response.status_code == 200
    api_workspace_payload = api_workspace_response.json()
    assert api_workspace_payload['workspace_id'] == 'ws-001'
    assert api_workspace_payload['identity_policy']['surface_family'] == 'workspace-circuit-library'
    assert api_workspace_payload['namespace_policy']['family'] == 'workspace-circuit-library'
    assert api_workspace_payload['routes']['self'] == '/api/workspaces/ws-001/library'
    assert api_workspace_payload['routes']['workspace_starter_template_catalog'] == '/api/workspaces/ws-001/starter-templates'

    page_response = client.get('/app/library', headers=_session_headers())
    assert page_response.status_code == 200
    assert 'My workflows' in page_response.text
    assert '/app/workspaces/ws-001' in page_response.text
    assert '/app/workspaces/ws-001/feedback?surface=circuit_library&amp;app_language=en' in page_response.text

def test_fastapi_binding_workspace_shell_route_round_trip() -> None:
    client = _make_client(
        feedback_store=InMemoryFeedbackStore.from_rows(({
            "feedback_id": "fb-shell-fastapi-001",
            "user_id": "user-owner",
            "workspace_id": "ws-001",
            "workspace_title": "Primary Workspace",
            "category": "friction_note",
            "surface": "workspace_shell",
            "message": "The shell should show my latest feedback.",
            "status": "received",
            "created_at": "2026-04-15T12:16:00+00:00",
        },)),
        public_share_payload_rows_provider=lambda: (
            export_public_nex_link_share(
                _valid_working_save_artifact(),
                share_id='share-shell-fastapi-001',
                title='FastAPI Working Save Share',
                created_at='2026-04-15T12:15:00+00:00',
                updated_at='2026-04-15T12:15:00+00:00',
                issued_by_user_ref='user-owner',
            ),
        )
    )
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
    assert payload['latest_run_result_preview']['result_summary'] == 'Success.'
    assert payload['latest_run_result_preview']['output_preview'] == 'Latest Hello'
    assert payload['routes']['latest_run_trace'] == '/api/runs/run-002/trace?limit=20'
    assert payload['routes']['workspace_shell_share'] == '/api/workspaces/ws-001/shares'
    assert payload['routes']['workspace_public_share_create'] == '/api/workspaces/ws-001/shares'
    assert payload['routes']['workspace_shell_share_legacy'] == '/api/workspaces/ws-001/shell/share'
    assert payload['routes']['workspace_share_history_page'] == '/app/workspaces/ws-001/shares?app_language=en'
    assert payload['routes']['workspace_share_create_page'] == '/app/workspaces/ws-001/shares/create?app_language=en'
    assert payload['routes']['public_share_page_template'] == '/app/public-shares/{share_id}?app_language=en&workspace_id=ws-001'
    assert payload['routes']['public_share_history_page_template'] == '/app/public-shares/{share_id}/history?app_language=en&workspace_id=ws-001'
    assert payload['routes']['workspace_result_history'] == '/api/workspaces/ws-001/result-history'
    assert payload['routes']['workspace_result_history_page'] == '/app/workspaces/ws-001/results?app_language=en'
    assert payload['routes']['circuit_library'] == '/api/workspaces/ws-001/library'
    assert payload['routes']['circuit_library_page'] == '/app/library?app_language=en'
    assert payload['routes']['starter_template_catalog'] == '/api/templates/starter-circuits'
    assert payload['routes']['starter_template_catalog_page'] == '/app/workspaces/ws-001/starter-templates?app_language=en'
    assert payload['routes']['workspace_recent_activity'] == '/api/users/me/activity?workspace_id=ws-001'
    assert payload['routes']['workspace_history_summary'] == '/api/users/me/history-summary?workspace_id=ws-001'
    assert payload['share_history_section']['summary']['headline'] == 'Share history'
    assert 'Recent shares: 1' in payload['share_history_section']['summary']['lines']
    assert 'share-shell-fastapi-001' in '\n'.join(payload['share_history_section']['detail']['items'])
    assert payload['share_history_section']['controls'][0]['action_kind'] == 'open_workspace_share_create'
    assert payload['recent_activity_section']['summary']['headline'] == 'Recent activity'
    assert 'Activity items: 5' in payload['recent_activity_section']['summary']['lines']
    assert payload['recent_activity_section']['history'][0]['activity_type'] == 'provider_probe'
    assert 'provider_probe — openai — reachable' in '\n'.join(payload['recent_activity_section']['detail']['items'])
    assert payload['recent_activity_section']['controls'][0]['action_target'] == '/api/users/me/activity?workspace_id=ws-001'
    assert payload['history_summary_section']['summary']['headline'] == 'History summary'
    assert 'Total runs: 2' in payload['history_summary_section']['summary']['lines']
    assert 'Successful runs: 1' in payload['history_summary_section']['summary']['lines']
    assert 'Share history entries: 1' in payload['history_summary_section']['detail']['items']
    assert 'Provider binding updates: 1' in payload['history_summary_section']['detail']['items']
    assert 'Managed secret updates: 1' in payload['history_summary_section']['detail']['items']
    assert 'Provider probe checks: 1' in payload['history_summary_section']['detail']['items']
    assert payload['history_summary_section']['controls'][0]['action_kind'] == 'open_route'
    assert payload['routes']['workspace_provider_bindings'] == '/api/workspaces/ws-001/provider-bindings'
    assert payload['routes']['workspace_provider_health'] == '/api/workspaces/ws-001/provider-bindings/health'
    assert payload['routes']['workspace_feedback'] == '/api/workspaces/ws-001/feedback'
    assert payload['routes']['workspace_feedback_page'] == '/app/workspaces/ws-001/feedback'
    assert payload['feedback_continuity_section']['summary']['headline'] == 'Feedback continuity'
    assert payload['feedback_continuity_section']['feedback_path_kind'] == 'feedback_thread_reentry'
    assert payload['feedback_continuity_section']['current_step_id'] == 'reopen_feedback_thread'
    assert any(line.startswith('Current path: Feedback thread reentry') for line in payload['feedback_continuity_section']['summary']['lines'])
    assert 'Feedback items: 1' in payload['feedback_continuity_section']['summary']['lines']
    assert 'friction_note — workspace_shell — received — fb-shell-fastapi-001' in '\n'.join(payload['feedback_continuity_section']['detail']['items'])
    assert payload['feedback_continuity_section']['controls'][0]['action_target'] == '/app/workspaces/ws-001/feedback'
    assert payload['feedback_continuity_section']['controls'][1]['action_target'] == '/api/workspaces/ws-001/feedback'
    assert payload['provider_readiness_section']['summary']['headline'] == 'Provider readiness'
    assert 'Configured providers: 1' in payload['provider_readiness_section']['summary']['lines']
    assert 'Recent provider probes: 1' in payload['provider_readiness_section']['summary']['lines']
    assert 'openai — reachable' in '\n'.join(payload['provider_readiness_section']['detail']['items'])
    assert payload['provider_readiness_section']['controls'][0]['action_target'] == '/api/workspaces/ws-001/provider-bindings'
    assert payload['provider_readiness_section']['controls'][1]['action_target'] == '/api/workspaces/ws-001/provider-bindings/health'
    assert payload['first_success_setup_section']['summary']['headline'] == 'First-success setup'
    assert any(line.startswith('Starter templates: ') for line in payload['first_success_setup_section']['summary']['lines'])
    assert any(line.startswith('Connected providers: ') for line in payload['first_success_setup_section']['summary']['lines'])
    assert payload['first_success_setup_section']['controls'][0]['action_target'] == 'designer'
    assert payload['first_success_setup_section']['controls'][1]['action_target'] == '/api/users/me/onboarding?workspace_id=ws-001'
    assert payload['first_success_setup_section']['entry_path_kind'] == 'goal_entry'
    assert payload['first_success_setup_section']['current_step_id'] == 'run'
    assert payload['first_success_run_section']['summary']['headline'] == 'First-success run'
    assert payload['first_success_run_section']['run_state'] == 'complete'
    assert 'Result summary: Success.' in payload['first_success_run_section']['detail']['items']
    assert payload['first_success_run_section']['run_path_kind'] == 'read_result'
    assert payload['first_success_run_section']['current_step_id'] == 'read_result'
    assert payload['first_success_run_section']['controls'][0]['action_target'] == 'runtime.result'
    assert payload['return_use_continuity_section']['summary']['headline'] == 'Return-use continuity'
    assert payload['return_use_continuity_section']['return_use_state'] == 'complete'
    assert payload['return_use_continuity_section']['return_path_kind'] == 'result_reentry'
    assert payload['return_use_continuity_section']['current_step_id'] == 'reopen_result'
    assert any(line.startswith('Current path: Result reentry') for line in payload['return_use_continuity_section']['summary']['lines'])
    assert payload['return_use_continuity_section']['controls'][0]['action_target'] == '/app/workspaces/ws-001/results?app_language=en'

    reentry_response = client.get('/api/workspaces/ws-001/shell?app_language=en&return_use=selected_result&run_id=run-002', headers=_session_headers())
    assert reentry_response.status_code == 200
    reentry_payload = reentry_response.json()
    assert reentry_payload['return_use_reentry_context']['source'] == 'result_history'
    assert reentry_payload['return_use_reentry_context']['run_id'] == 'run-002'
    assert reentry_payload['return_use_reentry_context']['output_ref'] == 'answer'
    assert reentry_payload['return_use_continuity_section']['selected_result_reentry_context']['run_id'] == 'run-002'
    assert 'Selected result: run-002' in reentry_payload['return_use_continuity_section']['summary']['lines']
    assert 'Selected output: answer' in reentry_payload['return_use_continuity_section']['summary']['lines']
    assert any(control['control_id'] == 'return-use-continue-selected-result' for control in reentry_payload['return_use_continuity_section']['controls'])
    assert any(control['control_id'] == 'return-use-reopen-selected-result' for control in reentry_payload['return_use_continuity_section']['controls'])

    assert payload['product_surface_review_section']['summary']['headline'] == 'Product surface review'
    assert payload['product_surface_review_section']['review_state'] == 'product_surface_stable'
    assert payload['product_surface_review_section']['product_path_family'] == 'feedback'
    assert payload['product_surface_review_section']['product_path_kind'] == 'feedback_thread_reentry'
    assert payload['product_surface_review_section']['current_step_id'] == 'reopen_feedback_thread'
    assert any(line.startswith('Current path: Feedback thread reentry') for line in payload['product_surface_review_section']['summary']['lines'])
    assert payload['product_surface_review_section']['controls'][0]['action_target'] == '/app/workspaces/ws-001/feedback'
    assert payload['identity_policy']['surface_family'] == 'workspace-shell'
    assert payload['namespace_policy']['family'] == 'workspace-shell'
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
    assert 'Summary: Success.' in payload['latest_run_result_detail']['items']
    assert 'Output preview: Latest Hello' in payload['latest_run_result_detail']['items']
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
    assert payload['designer_section']['controls'][0]['action_target'] == 'nexa-curated:text_summarizer@1.0'
    assert payload['designer_section']['controls'][0]['template_ref'] == 'nexa-curated:text_summarizer@1.0'
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
    assert payload['server_product_readiness_review']['authority'] == 'server'
    assert payload['server_product_readiness_review']['review_state'] == 'product_surface_stable'
    assert payload['server_product_readiness_review']['next_bottleneck_stage'] is None
    assert payload['server_product_readiness_review']['stages'][2]['stage_state'] == 'complete'
    assert payload['first_success_setup_section']['setup_state'] == 'complete'
    assert payload['first_success_run_section']['run_state'] == 'complete'
    assert payload['client_continuity']['enabled'] is True
    assert payload['client_continuity']['storage_key'] == 'nexa.runtime_shell.ws-001'
    assert payload['client_continuity']['version'] == 'phase6-batch15'


def test_fastapi_binding_starter_template_catalog_page_round_trip() -> None:
    client = _make_client()
    response = client.get('/app/templates/starter-circuits', headers=_session_headers())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    body = response.text
    assert 'Starter workflows' in body
    assert 'Choose a starter workflow to begin faster.' in body
    assert 'Open raw starter-template catalog' in body
    assert 'Open workflow library' in body
    assert 'Text Summarizer' in body
    assert '/api/templates/starter-circuits/text_summarizer' in body


def test_fastapi_binding_workspace_starter_template_catalog_page_round_trip() -> None:
    client = _make_client()
    response = client.get('/app/workspaces/ws-001/starter-templates', headers=_session_headers())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    body = response.text
    assert 'Starter workflows' in body
    assert 'Open workspace' in body
    assert '/app/workspaces/ws-001?app_language=en' in body
    assert '/app/workspaces/ws-001/starter-templates/text_summarizer?app_language=en' in body
    assert '/app/workspaces/ws-001/feedback?surface=starter_templates&amp;app_language=en' in body
    assert '/api/workspaces/ws-001/starter-templates' in body
    assert 'Review in workspace' in body


def test_fastapi_binding_workspace_starter_template_detail_page_round_trip() -> None:
    client = _make_client()
    response = client.get('/app/workspaces/ws-001/starter-templates/text_summarizer', headers=_session_headers())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    body = response.text
    assert 'Text Summarizer' in body
    assert 'Use template' in body
    assert '/app/workspaces/ws-001/starter-templates/text_summarizer/apply?app_language=en' in body
    assert '/app/workspaces/ws-001/feedback?surface=starter_templates&amp;template_id=text_summarizer&amp;app_language=en' in body
    assert '/api/workspaces/ws-001/starter-templates/text_summarizer' in body
    assert 'Back to starter templates' in body
    assert 'Open workspace' in body


def test_fastapi_binding_feedback_page_preserves_starter_template_origin_navigation() -> None:
    client = _make_client()

    response = client.get('/app/workspaces/ws-001/feedback?surface=starter_templates&app_language=en', headers=_session_headers())
    assert response.status_code == 200
    body = response.text
    assert '/app/workspaces/ws-001/starter-templates?app_language=en' in body
    assert 'Back to starter templates' in body


def test_fastapi_binding_feedback_page_preserves_starter_template_detail_origin_navigation() -> None:
    client = _make_client()

    response = client.get('/app/workspaces/ws-001/feedback?surface=starter_templates&template_id=text_summarizer&app_language=en', headers=_session_headers())
    assert response.status_code == 200
    body = response.text
    assert '/app/workspaces/ws-001/starter-templates/text_summarizer?app_language=en' in body
    assert 'Back to starter template' in body
    assert 'id=\"template_id\"' in body
    assert 'value=\"text_summarizer\"' in body


def test_fastapi_binding_workspace_starter_template_apply_page_redirects_to_workspace() -> None:
    client = _make_client()
    response = client.post('/app/workspaces/ws-001/starter-templates/text_summarizer/apply', headers=_session_headers(), follow_redirects=False)

    assert response.status_code == 303
    assert response.headers['location'] == '/app/workspaces/ws-001?app_language=en'


def test_fastapi_binding_workspace_result_history_page_round_trip() -> None:
    client = _make_client()
    response = client.get('/app/workspaces/ws-001/results', headers=_session_headers())

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    body = response.text
    assert 'Recent results' in body
    assert 'Back to library' in body
    assert 'Open workflow' in body
    assert 'Open starter templates' in body
    assert '/app/workspaces/ws-001/starter-templates?app_language=en' in body


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
    assert '/app/library?app_language=en' in body
    assert '/app/workspaces/ws-001/results?app_language=en' in body
    assert '/app/workspaces/ws-001/starter-templates?app_language=en' in body
    assert 'Open workflow library' in body
    assert 'Open result history page' in body
    assert 'Browse starter template page' in body
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
    assert workspace_payload['workspaces'][0]['identity']['canonical_key'] == 'workspace_id'
    assert workspace_payload['identity_policy']['surface_family'] == 'workspace-registry'
    assert workspace_payload['namespace_policy']['family'] == 'workspace-registry'

    workspace_detail = client.get('/api/workspaces/ws-001', headers=_session_headers())
    assert workspace_detail.status_code == 200
    workspace_detail_payload = workspace_detail.json()
    assert workspace_detail_payload['workspace_id'] == 'ws-001'
    assert workspace_detail_payload['provider_continuity']['latest_probe_event_id'] == 'probe-001'
    assert workspace_detail_payload['identity_policy']['surface_family'] == 'workspace-registry'
    assert workspace_detail_payload['namespace_policy']['family'] == 'workspace-registry'

    workspace_create = client.post('/api/workspaces', headers=_session_headers(), json={'title': 'Created Workspace'})
    assert workspace_create.status_code == 201
    workspace_create_payload = workspace_create.json()
    assert workspace_create_payload['workspace']['workspace_id'] == 'ws-new'
    assert workspace_create_payload['workspace']['identity']['canonical_key'] == 'workspace_id'
    assert workspace_create_payload['identity_policy']['surface_family'] == 'workspace-registry'
    assert workspace_create_payload['namespace_policy']['family'] == 'workspace-registry'

    onboarding_get = client.get('/api/users/me/onboarding', headers=_session_headers())
    assert onboarding_get.status_code == 200
    onboarding_get_payload = onboarding_get.json()
    assert onboarding_get_payload['state']['first_success_achieved'] is False
    assert onboarding_get_payload['provider_continuity']['provider_binding_count'] == 1
    assert onboarding_get_payload['activity_continuity']['latest_run_id'] == 'run-001'
    assert onboarding_get_payload['state']['identity']['canonical_key'] == 'continuity_scope'
    assert onboarding_get_payload['identity_policy']['surface_family'] == 'workspace-onboarding'
    assert onboarding_get_payload['namespace_policy']['family'] == 'workspace-onboarding'

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
    assert onboarding_put_payload['state']['identity']['canonical_key'] == 'onboarding_state_id'
    assert onboarding_put_payload['identity_policy']['surface_family'] == 'workspace-onboarding'
    assert onboarding_put_payload['namespace_policy']['family'] == 'workspace-onboarding'


def test_fastapi_binding_provider_catalog_and_workspace_bindings_round_trip() -> None:
    client = _make_client()

    catalog_response = client.get("/api/providers/catalog", headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload["returned_count"] == 1
    assert catalog_payload["providers"][0]["provider_key"] == "openai"
    assert catalog_payload["providers"][0]["identity"]["canonical_key"] == "provider_key"
    assert catalog_payload["provider_continuity"]["provider_binding_count"] >= 1
    assert catalog_payload["activity_continuity"]["recent_run_count"] >= 1
    assert catalog_payload["identity_policy"]["surface_family"] == "provider-catalog"
    assert catalog_payload["namespace_policy"]["family"] == "provider-catalog"

    bindings_response = client.get("/api/workspaces/ws-001/provider-bindings", headers=_session_headers())
    assert bindings_response.status_code == 200
    bindings_payload = bindings_response.json()
    assert bindings_payload["returned_count"] == 1
    assert bindings_payload["bindings"][0]["status"] == "configured"
    assert bindings_payload["bindings"][0]["identity"]["canonical_key"] == "binding_id"
    assert bindings_payload["identity_policy"]["surface_family"] == "workspace-provider-binding"
    assert bindings_payload["namespace_policy"]["family"] == "workspace-provider-binding"

    put_response = client.put(
        "/api/workspaces/ws-001/provider-bindings/openai",
        headers=_session_headers(),
        json={"display_name": "OpenAI GPT", "secret_value": "super-secret", "enabled": True},
    )
    assert put_response.status_code == 200
    put_payload = put_response.json()
    assert put_payload["binding"]["provider_key"] == "openai"
    assert put_payload["binding"]["secret_ref"] == "aws-secretsmanager://nexa/ws-001/providers/openai"
    assert put_payload["binding"]["identity"]["canonical_key"] == "binding_id"
    assert put_payload["identity_policy"]["surface_family"] == "workspace-provider-binding"
    assert put_payload["namespace_policy"]["family"] == "workspace-provider-binding"
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
    assert payload['identity_policy']['surface_family'] == 'workspace-provider-probe'
    assert payload['namespace_policy']['family'] == 'workspace-provider-probe'


def test_fastapi_binding_recent_activity_includes_provider_probe_event() -> None:
    client = _make_client()
    response = client.get('/api/users/me/activity?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['activities'][0]['activity_type'] == 'provider_probe_reachable'
    assert payload['activities'][0]['links']['provider_probe_history'].endswith('/probe-history')
    assert payload['activities'][0]['identity']['canonical_key'] == 'activity_id'
    assert payload['provider_continuity']['provider_binding_count'] == 1
    assert payload['activity_continuity']['recent_run_count'] == 1
    assert payload['identity_policy']['surface_family'] == 'recent-activity'
    assert payload['namespace_policy']['family'] == 'recent-activity'




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
    assert health_response.json()['health']['identity']['canonical_key'] == 'provider_key'
    assert health_response.json()['health']['health_status'] in {'healthy', 'warning', 'blocked', 'disabled', 'missing'}
    assert health_response.json()['provider_continuity']['provider_binding_count'] >= 1
    assert health_response.json()['identity_policy']['surface_family'] == 'workspace-provider-health'
    assert health_response.json()['namespace_policy']['family'] == 'workspace-provider-health'

    probe_response = client.post(
        '/api/workspaces/ws-001/provider-bindings/openai/probe',
        headers=_session_headers(),
        json={'requested_model_ref': 'gpt-4.1'},
    )
    assert probe_response.status_code == 200
    probe_payload = probe_response.json()
    assert probe_payload['probe_status'] == 'reachable'
    assert probe_payload['provider_continuity']['provider_binding_count'] >= 1
    assert probe_payload['identity_policy']['surface_family'] == 'workspace-provider-probe'
    assert probe_payload['namespace_policy']['family'] == 'workspace-provider-probe'

    history_response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history', headers=_session_headers())
    assert history_response.status_code == 200
    assert history_response.json()['returned_count'] == 1
    assert history_response.json()['items'][0]['probe_event_id'] == 'probe-created'
    history_payload = history_response.json()
    assert history_payload['items'][0]['provider_key'] == 'openai'
    assert history_payload['items'][0]['identity']['canonical_key'] == 'probe_event_id'
    assert history_payload['identity_policy']['surface_family'] == 'workspace-provider-probe-history'
    assert history_payload['namespace_policy']['family'] == 'workspace-provider-probe-history'
    assert history_payload['provider_continuity']['recent_probe_count'] >= 1



def test_fastapi_binding_provider_probe_history_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['returned_count'] == 1
    assert payload['items'][0]['probe_event_id'] == 'probe-001'
    assert payload['items'][0]['identity']['canonical_key'] == 'probe_event_id'
    assert payload['identity_policy']['surface_family'] == 'workspace-provider-probe-history'
    assert payload['namespace_policy']['family'] == 'workspace-provider-probe-history'


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
        public_share_payload_rows_provider=lambda: (
            export_public_nex_link_share(
                _provider_backed_working_save_artifact(ref='ws-001'),
                share_id='share-secret-roundtrip',
                title='Shared Workspace',
                created_at='2026-04-11T12:05:00+00:00',
                updated_at='2026-04-11T12:05:30+00:00',
                issued_by_user_ref='user-owner',
            ),
        ),
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
    assert summary_payload['recent_share_history_count'] == 1
    assert summary_payload['recent_provider_binding_count'] == 1
    assert summary_payload['recent_managed_secret_count'] == 1
    assert summary_payload['latest_share_id'] == 'share-secret-roundtrip'
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
            'template_ref': 'nexa-curated:text_summarizer@1.0',
            'template_lookup_aliases': ['text_summarizer', 'nexa-curated:text_summarizer@1.0'],
            'template_provenance_family': 'starter-template',
            'template_provenance_source': 'nexa-curated',
            'template_compatibility_family': 'workspace-shell-draft',
            'template_apply_behavior': 'replace_designer_request',
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
    assert 'Template ref: nexa-curated:text_summarizer@1.0' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Lookup aliases: text_summarizer, nexa-curated:text_summarizer@1.0' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Provenance: nexa-curated / starter-template' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Compatibility: workspace-shell-draft / replace_designer_request' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Persisted request: Summarize this article.' in '\n'.join(payload['designer_section']['detail']['items'])
    assert 'Persisted validation action: open_validation_detail' in '\n'.join(payload['validation_section']['summary']['lines'])
    assert 'Persisted validation status: blocked' in '\n'.join(payload['validation_section']['detail']['items'])



def test_fastapi_binding_workspace_shell_draft_write_marks_first_result_read() -> None:
    client = _make_client()
    response = client.put(
        '/api/workspaces/ws-001/shell/draft',
        headers=_session_headers(),
        json={
            'first_success_action': 'mark_first_result_read',
            'completion_metadata_patch': {
                'beginner_first_success_run_id': 'run-002',
                'beginner_first_success_output_ref': 'answer',
                'beginner_first_success_artifact_ref': 'artifact-2',
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['first_success_flow_section']['flow_state'] == 'complete'
    assert payload['first_success_flow_section']['current_step_id'] is None
    assert payload['first_success_flow_section']['advanced_surfaces_unlocked'] is True
    assert payload['first_success_flow_section']['result_reading']['read_complete'] is True
    assert payload['return_use_continuity_section']['return_use_state'] != 'inactive'

def test_fastapi_binding_workspace_result_history_routes_round_trip() -> None:
    client = _make_client()
    api_response = client.get('/api/workspaces/ws-001/result-history', headers=_session_headers())
    assert api_response.status_code == 200
    api_payload = api_response.json()
    assert api_payload['identity_policy']['surface_family'] == 'workspace-result-history'
    assert api_payload['namespace_policy']['family'] == 'workspace-result-history'
    assert api_payload['result_history']['returned_count'] >= 1
    assert api_payload['result_history']['items'][0]['open_result_href'].startswith('/app/workspaces/ws-001/results?run_id=')
    assert api_payload['item_sections'][0]['identity']['canonical_value'].startswith('run-')
    page_response = client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert page_response.status_code == 200
    assert 'Recent results' in page_response.text
    assert 'Latest Hello' in page_response.text
    assert 'first-success-result-read-panel' in page_response.text
    assert 'mark-selected-result-read' in page_response.text
    assert 'data-action-kind="first_success_completion"' in page_response.text
    assert 'data-first-success-action="mark_first_result_read"' in page_response.text
    assert 'data-shell-draft-path="/api/workspaces/ws-001/shell/draft"' in page_response.text
    assert 'data-run-id="run-002"' in page_response.text
    assert 'data-output-ref="answer"' in page_response.text
    assert 'data-artifact-ref="artifact-2"' in page_response.text
    assert api_payload['selected_result']['result_render_kind'] == 'plain_text'
    assert api_payload['selected_result']['copy_output_text'] == 'Latest Hello'
    assert 'beginner-result-screen' in page_response.text
    assert 'data-result-render-kind="plain_text"' in page_response.text
    assert 'copy-selected-result' in page_response.text
    assert 'data-copy-output="Latest Hello"' in page_response.text
    assert 'continue-from-selected-result' in page_response.text
    assert 'report-selected-result-issue' in page_response.text
    assert api_payload['selected_result']['return_use_context']['source'] == 'result_history'
    assert api_payload['selected_result']['return_use_context']['run_id'] == 'run-002'
    assert api_payload['selected_result']['return_use_context']['output_ref'] == 'answer'
    assert api_payload['selected_result']['continue_href'] == '/app/workspaces/ws-001?app_language=en&return_use=selected_result&run_id=run-002'
    assert 'return-use-reentry-panel' in page_response.text
    assert 'data-return-use-source="result_history"' in page_response.text
    assert 'data-return-use-run-id="run-002"' in page_response.text
    assert 'return-use-selected-result' in page_response.text
    assert '/app/workspaces/ws-001?app_language=en&amp;return_use=selected_result&amp;run_id=run-002' in page_response.text

    workspace_reentry_page = client.get('/app/workspaces/ws-001?app_language=en&return_use=selected_result&run_id=run-002', headers=_session_headers())
    assert workspace_reentry_page.status_code == 200
    assert 'return-use-selected-result-card' in workspace_reentry_page.text
    assert 'data-return-use-source="result_history"' in workspace_reentry_page.text
    assert 'data-return-use-run-id="run-002"' in workspace_reentry_page.text
    assert 'data-output-ref="answer"' in workspace_reentry_page.text
    assert 'continue-with-selected-result' in workspace_reentry_page.text
    assert 'reopen-selected-result' in workspace_reentry_page.text
    assert 'Selected result: run-002' in workspace_reentry_page.text


def test_fastapi_binding_workspace_result_history_renders_type_aware_result_shapes() -> None:
    structured_client = _make_client(
        workspace_result_rows={
            'run-002': {
                'run_id': 'run-002',
                'workspace_id': 'ws-001',
                'result_state': 'ready_success',
                'final_status': 'completed',
                'result_summary': 'Success.',
                'updated_at': '2026-04-11T12:01:05+00:00',
                'final_output': {
                    'output_key': 'answer',
                    'value_preview': 'Decision: Approve\nRisk: Low\nNext step: Send summary',
                    'value_type': 'object',
                },
            }
        }
    )
    structured_api = structured_client.get('/api/workspaces/ws-001/result-history?run_id=run-002', headers=_session_headers())
    assert structured_api.status_code == 200
    structured_payload = structured_api.json()
    assert structured_payload['selected_result']['result_render_kind'] == 'key_value'
    assert structured_payload['selected_result']['output_key_value_pairs'][0] == {'key': 'Decision', 'value': 'Approve'}
    structured_page = structured_client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert structured_page.status_code == 200
    assert 'data-result-render-kind="key_value"' in structured_page.text
    assert 'structured-result' in structured_page.text
    assert '<dt>Decision</dt><dd>Approve</dd>' in structured_page.text

    list_client = _make_client(
        workspace_result_rows={
            'run-002': {
                'run_id': 'run-002',
                'workspace_id': 'ws-001',
                'result_state': 'ready_success',
                'final_status': 'completed',
                'result_summary': 'Success.',
                'updated_at': '2026-04-11T12:01:05+00:00',
                'final_output': {
                    'output_key': 'answer',
                    'value_preview': '- First item\n- Second item',
                    'value_type': 'string',
                },
            }
        }
    )
    list_api = list_client.get('/api/workspaces/ws-001/result-history?run_id=run-002', headers=_session_headers())
    assert list_api.status_code == 200
    list_payload = list_api.json()
    assert list_payload['selected_result']['result_render_kind'] == 'list_text'
    assert list_payload['selected_result']['output_lines'] == ['First item', 'Second item']
    list_page = list_client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert list_page.status_code == 200
    assert 'data-result-render-kind="list_text"' in list_page.text
    assert 'list-result' in list_page.text
    assert '<li>First item</li>' in list_page.text


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
    assert get_payload['identity_policy']['surface_family'] == 'workspace-feedback'
    assert get_payload['namespace_policy']['family'] == 'workspace-feedback'
    assert get_payload['feedback_channel']['submit_path'] == '/api/workspaces/ws-001/feedback'
    assert get_payload['feedback_channel']['prefill_surface'] == 'result_history'
    assert get_payload['feedback_channel']['prefill_run_id'] == 'run-001'
    assert get_payload['routes']['origin_page'] == '/app/workspaces/ws-001/results?app_language=en&run_id=run-001'
    assert get_payload['routes']['origin_label'] == 'Back to results'

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
    assert submit_payload['workspace_id'] == 'ws-001'
    assert submit_payload['identity_policy']['surface_family'] == 'workspace-feedback'
    assert submit_payload['namespace_policy']['family'] == 'workspace-feedback'
    assert submit_payload['feedback']['surface'] == 'result_history'
    assert submit_payload['feedback']['workspace_id'] == 'ws-001'
    assert submit_payload['feedback']['identity']['canonical_key'] == 'feedback_id'
    assert submit_payload['feedback']['identity']['canonical_value']

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
    assert '/app/workspaces/ws-001/results?app_language=en&amp;run_id=run-001' in body
    assert 'Back to results' in body
    assert '/app/workspaces/ws-001/library?app_language=en' in body
    assert '/app/workspaces/ws-001/starter-templates?app_language=en' in body
    assert 'Report confusing screen' in body
    assert '<option value="starter_templates">Starter templates</option>' in body
    assert "const feedbackPageLanguage = currentQuery.get('app_language') || 'en';" in body
    assert "nextQuery.set('app_language', feedbackPageLanguage);" in body




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
    assert '<option value="starter_templates">시작 템플릿</option>' in feedback_page.text
    assert "const feedbackPageLanguage = currentQuery.get('app_language') || 'ko';" in feedback_page.text
    assert "nextQuery.set('app_language', feedbackPageLanguage);" in feedback_page.text


def test_fastapi_binding_workspace_feedback_starter_template_detail_round_trip() -> None:
    feedback_store = InMemoryFeedbackStore()
    client = _make_client(feedback_store=feedback_store)

    get_response = client.get('/api/workspaces/ws-001/feedback?surface=starter_templates&template_id=text_summarizer', headers=_session_headers())
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload['routes']['origin_page'] == '/app/workspaces/ws-001/starter-templates/text_summarizer?app_language=en'
    assert get_payload['routes']['origin_label'] == 'Back to starter template'

    submit_response = client.post(
        '/api/workspaces/ws-001/feedback',
        headers=_session_headers(),
        json={
            'category': 'friction_note',
            'surface': 'starter_templates',
            'template_id': 'text_summarizer',
            'message': 'This starter template needs clearer setup guidance.',
        },
    )
    assert submit_response.status_code == 202
    submit_payload = submit_response.json()
    assert submit_payload['feedback']['surface'] == 'starter_templates'
    assert submit_payload['feedback']['template_id'] == 'text_summarizer'
    assert submit_payload['links']['origin_page'] == '/app/workspaces/ws-001/starter-templates/text_summarizer?app_language=en'
    assert feedback_store.list_rows()[0]['template_id'] == 'text_summarizer'


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
    assert payload['identity_policy']['surface_family'] == 'workspace-shell'
    assert payload['namespace_policy']['family'] == 'workspace-shell'


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
    assert payload['identity_policy']['surface_family'] == 'workspace-shell'
    assert payload['namespace_policy']['family'] == 'workspace-shell'


def test_fastapi_binding_workspace_public_share_history_and_create_context_api_round_trip() -> None:
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
            _commit_snapshot('snap-fastapi-other-active'),
            share_id='share-fastapi-other-active',
            title='FastAPI Other Active',
            created_at='2026-04-16T12:00:00+00:00',
            updated_at='2026-04-16T12:30:00+00:00',
            issued_by_user_ref='user-other',
        ),
    )
    client = _make_client(artifact_source=_commit_snapshot('snap-fastapi-owner-active'), public_share_payload_rows_provider=lambda: rows)

    history_response = client.get('/api/workspaces/ws-001/shares', headers=_session_headers())
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload['workspace_id'] == 'ws-001'
    assert history_payload['share_count'] == 1
    assert history_payload['entries'][0]['share_id'] == 'share-fastapi-owner-active'
    assert history_payload['identity_policy']['surface_family'] == 'workspace-public-share-history'

    context_response = client.get('/api/workspaces/ws-001/shares/create-context', headers=_session_headers())
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload['workspace_id'] == 'ws-001'
    assert context_payload['share_count'] == 1
    assert context_payload['prefill_title'] == 'Primary Workspace snapshot'
    assert context_payload['namespace_policy']['family'] == 'workspace-public-share-create-context'


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
    client = _make_client(public_share_payload_rows_provider=lambda: rows, public_share_action_report_rows_provider=_issuer_action_report_rows)

    list_response = client.get('/api/users/me/public-shares', headers=_session_headers())
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload['summary']['total_share_count'] == 2
    assert list_payload['summary']['active_share_count'] == 1
    assert list_payload['summary']['expired_share_count'] == 1
    assert list_payload['identity_policy']['canonical_key'] == 'issuer_user_ref'
    assert list_payload['namespace_policy']['family'] == 'issuer-public-share-management'
    assert list_payload['namespace_policy']['member_namespace_policy']['public_path_format'] == '/share/{share_id}'
    assert list_payload['shares'][0]['identity']['canonical_key'] == 'share_id'
    assert [entry['share_id'] for entry in list_payload['shares']] == [
        'share-fastapi-owner-active',
        'share-fastapi-owner-expired',
    ]
    assert list_payload['management_capability_summary']['revokable_share_count'] == 1
    assert list_payload['bulk_action_availability']['revoke']['allowed'] is True
    assert list_payload['shares'][1]['management_action_availability']['revoke']['allowed'] is False

    summary_response = client.get('/api/users/me/public-shares/summary', headers=_session_headers())
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload['summary']['total_share_count'] == 2
    assert summary_payload['summary']['latest_updated_at'] == '2026-04-15T12:30:00+00:00'
    assert summary_payload['identity_policy']['canonical_key'] == 'issuer_user_ref'
    assert summary_payload['namespace_policy']['family'] == 'issuer-public-share-management'
    assert summary_payload['governance_summary']['total_action_report_count'] == 2
    assert summary_payload['governance_summary']['archive_action_report_count'] == 1
    assert summary_payload['management_capability_summary']['extendable_share_count'] == 1
    assert summary_payload['bulk_action_availability']['delete']['allowed'] is True
    assert summary_payload['governance_summary']['recent_action_reports'][0]['report_id'] == 'report-fastapi-archive-001'

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

    action_report_response = client.get('/api/users/me/public-shares/action-reports?action=archive', headers=_session_headers())
    assert action_report_response.status_code == 200
    action_report_payload = action_report_response.json()
    assert action_report_payload['summary']['total_report_count'] == 1
    assert action_report_payload['inventory_summary']['total_report_count'] == 2
    assert action_report_payload['governance_summary']['total_share_count'] == 2
    assert action_report_payload['reports'][0]['action'] == 'archive'

    action_report_summary_response = client.get('/api/users/me/public-shares/action-reports/summary?action=archive', headers=_session_headers())
    assert action_report_summary_response.status_code == 200
    action_report_summary_payload = action_report_summary_response.json()
    assert action_report_summary_payload['summary']['total_report_count'] == 1
    assert action_report_summary_payload['governance_summary']['archive_action_report_count'] == 1
    assert action_report_summary_payload['links']['share_summary'] == '/api/users/me/public-shares/summary'


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
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.post('/api/users/me/public-shares/actions/revoke', headers=_session_headers(), json={'share_ids': ['share-fastapi-owner-action-a', 'share-fastapi-owner-action-b']})

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'revoke'
    assert payload['affected_share_count'] == 2
    assert payload['summary']['revoked_share_count'] == 2
    assert payload['governance_summary']['revoke_action_report_count'] >= 1
    assert payload['action_report']['action'] == 'revoke'
    assert payload['links']['action_report_summary'] == '/api/users/me/public-shares/action-reports/summary'
    assert share_store['share-fastapi-owner-action-a']['share']['lifecycle']['state'] == 'revoked'
    assert share_store['share-fastapi-owner-action-b']['share']['lifecycle']['state'] == 'revoked'

def test_fastapi_binding_public_share_routes_round_trip() -> None:
    client = _make_client()
    response = client.get('/api/public-shares/share-fastapi-001')
    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-001'
    assert payload['operation_capabilities'] == ['inspect_metadata', 'download_artifact', 'import_copy', 'run_artifact', 'checkout_working_copy']
    assert payload['capability_summary']['can_create_workspace_from_share'] is True
    assert payload['action_availability']['create_workspace_from_share']['allowed'] is True
    assert payload['lifecycle']['stored_state'] == 'active'
    assert payload['lifecycle']['state'] == 'active'
    assert payload['audit_summary']['event_count'] == 1
    assert payload['source_artifact']['storage_role'] == 'commit_snapshot'
    assert payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert payload['share_boundary']['public_access_posture'] == 'anonymous_readonly'
    assert payload['share_boundary']['management_access_posture'] == 'issuer_authenticated_lifecycle_management'
    assert payload['share_boundary']['public_operation_boundaries'][0]['operation'] == 'inspect_metadata'
    assert payload['share_boundary']['public_operation_boundaries'][0]['allowed_effective_lifecycle_states'] == ['active', 'expired', 'revoked']
    assert payload['share_boundary']['public_operation_boundaries'][4]['allowed_storage_roles'] == ['commit_snapshot']
    assert payload['share_boundary']['management_operation_boundaries'][2]['operation'] == 'delete'
    assert payload['share_boundary']['management_operation_boundaries'][2]['denial_reason_code'] == 'public_share.management_not_allowed'
    assert payload['share_boundary']['history_boundary']['detail_payload_posture'] == 'optional_string_map'
    assert payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'
    assert payload['artifact_boundary']['role_boundary']['editor_continuity_posture'] == 'ui_forbidden_in_canonical_snapshot'
    assert payload['artifact_boundary']['role_boundary']['commit_boundary_posture'] == 'already_crossed_commit_boundary'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][0]['operation'] == 'load_artifact'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][4]['execution_anchor_posture'] == 'working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor'

    history_response = client.get('/api/public-shares/share-fastapi-001/history')
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload['audit_summary']['event_count'] == 1
    assert history_payload['history'][0]['event_type'] == 'created'
    assert history_payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert history_payload['share_boundary']['history_boundary']['canonical_http_method'] == 'GET'
    assert history_payload['share_boundary']['history_boundary']['canonical_route'] == '/api/public-shares/{share_id}/history'
    assert history_payload['share_boundary']['history_boundary']['result_surface'] == 'public_share_history'
    assert history_payload['share_boundary']['history_boundary']['entry_boundary']['entry_surface'] == 'public_share_audit_entry'
    assert history_payload['artifact_boundary']['role_boundary']['storage_role'] == 'commit_snapshot'

    artifact_response = client.get('/api/public-shares/share-fastapi-001/artifact')
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    assert artifact_payload['artifact']['meta']['commit_id'] == 'snap-fastapi-share-001'
    assert artifact_payload['share_boundary']['artifact_format_family'] == '.nex'
    assert artifact_payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'




def test_fastapi_binding_workspace_share_history_page_round_trip() -> None:
    client = _make_client(
        artifact_source=_valid_working_save_artifact(),
        public_share_payload_rows_provider=lambda: (
            export_public_nex_link_share(
                _valid_working_save_artifact(),
                share_id='share-workspace-history-001',
                title='Workspace History Share',
                created_at='2026-04-15T12:15:00+00:00',
                updated_at='2026-04-15T12:16:00+00:00',
                issued_by_user_ref='user-owner',
            ),
        ),
    )
    response = client.get('/app/workspaces/ws-001/shares?app_language=en', headers=_session_headers())
    assert response.status_code == 200
    body = response.text
    assert 'Share history' in body
    assert 'Workspace History Share' in body
    assert '/app/public-shares/share-workspace-history-001?app_language=en&amp;workspace_id=ws-001' in body
    assert '/app/public-shares/share-workspace-history-001/history?app_language=en&amp;workspace_id=ws-001' in body
    assert '/app/workspaces/ws-001/shares/create?app_language=en' in body


def test_fastapi_binding_public_share_api_catalog_saved_related_and_compare_round_trip() -> None:
    saved_rows = [{"share_id": "share-fastapi-001", "saved_at": "2026-04-16T08:00:00+00:00", "saved_by_user_ref": "user-owner"}]
    client = _make_client(
        public_share_payload_provider=lambda share_id: _share_payload(share_id),
        public_share_payload_rows_provider=lambda: (
            _share_payload("share-fastapi-001"),
            export_public_nex_link_share(
                _commit_snapshot("snap-fastapi-share-002"),
                share_id="share-fastapi-002",
                title="FastAPI share related",
                created_at="2026-04-15T13:00:00+00:00",
                updated_at="2026-04-15T13:30:00+00:00",
                issued_by_user_ref="user-owner",
            ),
        ),
        saved_public_share_rows_provider=lambda: list(saved_rows),
    )

    catalog_response = client.get('/api/public-shares?operation=run_artifact', headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_payload = catalog_response.json()
    assert catalog_payload['returned_count'] == 2
    assert catalog_payload['shares'][0]['identity']['canonical_key'] == 'share_id'

    summary_response = client.get('/api/public-shares/summary?operation=run_artifact', headers=_session_headers())
    assert summary_response.status_code == 200
    assert summary_response.json()['summary']['runnable_share_count'] == 2

    saved_response = client.get('/api/users/me/saved-public-shares', headers=_session_headers())
    assert saved_response.status_code == 200
    assert saved_response.json()['saved_by_user_ref'] == 'user-owner'

    related_response = client.get('/api/public-shares/share-fastapi-001/related', headers=_session_headers())
    assert related_response.status_code == 200
    assert related_response.json()['related_summary']['total_related_count'] == 1

    compare_full_response = client.get('/api/public-shares/share-fastapi-001/compare?workspace_id=ws-001', headers=_session_headers())
    assert compare_full_response.status_code == 200
    assert compare_full_response.json()['compare']['workspace_found'] is True
    assert compare_full_response.json()['compare']['share_artifact']['meta']['storage_role'] == 'commit_snapshot'

    compare_response = client.get('/api/public-shares/share-fastapi-001/compare-summary?workspace_id=ws-001', headers=_session_headers())
    assert compare_response.status_code == 200
    assert compare_response.json()['compare']['workspace_found'] is True




def test_fastapi_binding_public_share_issuer_catalog_api_round_trip() -> None:
    saved_rows = [{"share_id": "share-fastapi-001", "saved_at": "2026-04-16T08:00:00+00:00", "saved_by_user_ref": "user-owner"}]
    client = _make_client(
        public_share_payload_rows_provider=lambda: (
            _share_payload("share-fastapi-001"),
            export_public_nex_link_share(
                _commit_snapshot("snap-fastapi-share-002"),
                share_id="share-fastapi-002",
                title="FastAPI share related",
                created_at="2026-04-15T13:00:00+00:00",
                updated_at="2026-04-15T13:30:00+00:00",
                issued_by_user_ref="user-owner",
            ),
        ),
        saved_public_share_rows_provider=lambda: list(saved_rows),
    )

    response = client.get('/api/public-shares/issuers/user-owner?operation=run_artifact', headers=_session_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload['issuer_user_ref'] == 'user-owner'
    assert payload['returned_count'] == 2

    summary = client.get('/api/public-shares/issuers/user-owner/summary?operation=run_artifact', headers=_session_headers())
    assert summary.status_code == 200
    assert summary.json()['issuer_user_ref'] == 'user-owner'
    assert summary.json()['summary']['runnable_share_count'] == 2


def test_fastapi_binding_saved_public_share_mutation_api_round_trip() -> None:
    saved_rows = [{"share_id": "share-fastapi-saved-001", "saved_at": "2026-04-16T12:00:00+00:00", "saved_by_user_ref": "user-owner"}]
    client = _make_client(saved_public_share_rows_provider=lambda: list(saved_rows))

    save_response = client.post('/api/public-shares/share-fastapi-001/save', headers=_session_headers())
    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload['action'] == 'save'
    assert save_payload['saved'] is True
    assert save_payload['saved_by_user_ref'] == 'user-owner'

    unsave_response = client.post('/api/public-shares/share-fastapi-saved-001/unsave', headers=_session_headers())
    assert unsave_response.status_code == 200
    unsave_payload = unsave_response.json()
    assert unsave_payload['action'] == 'unsave'
    assert unsave_payload['saved'] is False

def test_fastapi_binding_public_share_consumer_action_api_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())

    checkout_response = client.post(
        '/api/public-shares/share-fastapi-001/checkout',
        headers=_session_headers(),
        json={'workspace_id': 'ws-001', 'working_save_id': 'ws-fastapi-checkout'},
    )
    assert checkout_response.status_code == 200
    checkout_payload = checkout_response.json()
    assert checkout_payload['action'] == 'checkout_working_copy'
    assert checkout_payload['workspace_id'] == 'ws-001'
    assert checkout_payload['working_save_id'] == 'ws-fastapi-checkout'

    import_response = client.post(
        '/api/public-shares/share-fastapi-001/import',
        headers=_session_headers(),
        json={'workspace_id': 'ws-001'},
    )
    assert import_response.status_code == 200
    import_payload = import_response.json()
    assert import_payload['action'] == 'import_copy'
    assert import_payload['storage_role'] == 'commit_snapshot'

    create_workspace_response = client.post(
        '/api/public-shares/share-fastapi-001/create-workspace',
        headers=_session_headers(),
        json={'title': 'Created from share', 'create_mode': 'checkout_working_copy', 'working_save_id': 'ws-share-created-draft'},
    )
    assert create_workspace_response.status_code == 201
    created_payload = create_workspace_response.json()
    assert created_payload['action'] == 'create_workspace_from_share'
    assert created_payload['workspace_id'] == 'ws-new'
    assert created_payload['create_mode'] == 'checkout_working_copy'
    assert created_payload['storage_role'] == 'working_save'

    run_response = client.post(
        '/api/public-shares/share-fastapi-001/run',
        headers=_session_headers(),
        json={'workspace_id': 'ws-001', 'input_payload': {'question': 'hello'}},
    )
    assert run_response.status_code == 202
    run_payload = run_response.json()
    assert run_payload['action'] == 'run_artifact'
    assert run_payload['run_id'] == 'run-001'
    assert run_payload['target_type'] == 'commit_snapshot'


def test_fastapi_binding_public_share_product_pages_round_trip() -> None:
    client = _make_client()
    detail_response = client.get('/app/public-shares/share-fastapi-001?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert detail_response.status_code == 200
    detail_body = detail_response.text
    assert 'FastAPI share' in detail_body
    assert '/app/workspaces/ws-001/shares?app_language=en' in detail_body
    assert '/app/public-shares/share-fastapi-001/history?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/api/public-shares/share-fastapi-001/artifact' in detail_body
    assert '/app/public-shares/share-fastapi-001/checkout?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/import?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/run?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/download?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/compare?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/revoke?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/archive?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/delete?app_language=en&amp;workspace_id=ws-001' in detail_body

    history_response = client.get('/app/public-shares/share-fastapi-001/history?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert history_response.status_code == 200
    history_body = history_response.text
    assert 'Share history' in history_body or 'Open history' in history_body
    assert 'created' in history_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/checkout?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/import?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/run?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/download?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/compare?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/revoke?app_language=en&amp;workspace_id=ws-001' in history_body


def test_fastapi_binding_public_share_checkout_product_flow_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())

    checkout_page = client.get('/app/public-shares/share-fastapi-001/checkout?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert checkout_page.status_code == 200
    checkout_body = checkout_page.text
    assert 'Restore share to workspace' in checkout_body
    assert 'name="workspace_id" value="ws-001"' in checkout_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in checkout_body

    post_response = client.post(
        '/app/public-shares/share-fastapi-001/checkout?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'working_save_id': 'ws-share-restored'},
        follow_redirects=False,
    )
    assert post_response.status_code == 303
    assert post_response.headers['location'] == '/app/workspaces/ws-001?app_language=en&action=checkout&status=done&source_share_id=share-fastapi-001&working_save_id=ws-share-restored'

    shell_response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())
    assert shell_response.status_code == 200
    shell_payload = shell_response.json()
    assert shell_payload['storage_role'] == 'working_save'
    assert shell_payload['working_save_id'] == 'ws-share-restored'


def test_fastapi_binding_public_share_import_product_flow_round_trip() -> None:
    share_payload = export_public_nex_link_share(
        _commit_snapshot('snap-fastapi-import-001'),
        share_id='share-fastapi-import-001',
        title='FastAPI import share',
        created_at='2026-04-15T12:00:00+00:00',
        issued_by_user_ref='user-owner',
    )
    client = _make_client(artifact_source=_valid_working_save_artifact(), public_share_payload_provider=lambda share_id: share_payload if share_id == 'share-fastapi-import-001' else None)

    import_page = client.get('/app/public-shares/share-fastapi-import-001/import?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert import_page.status_code == 200
    import_body = import_page.text
    assert 'Import share copy to workspace' in import_body
    assert 'name="workspace_id" value="ws-001"' in import_body
    assert '/app/public-shares/share-fastapi-import-001?app_language=en&amp;workspace_id=ws-001' in import_body

    post_response = client.post(
        '/app/public-shares/share-fastapi-import-001/import?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'workspace_id': 'ws-001'},
        follow_redirects=False,
    )
    assert post_response.status_code == 303
    assert post_response.headers['location'] == '/app/workspaces/ws-001?app_language=en&action=import_copy&status=done&source_share_id=share-fastapi-import-001&storage_role=commit_snapshot'

    shell_response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())
    assert shell_response.status_code == 200
    shell_payload = shell_response.json()
    assert shell_payload['storage_role'] == 'commit_snapshot'
    assert shell_payload['commit_id'] == 'snap-fastapi-import-001'


def test_fastapi_binding_public_share_create_workspace_product_flow_round_trip() -> None:
    workspace_store = InMemoryWorkspaceRegistryStore()
    artifact_store: dict[str, dict] = {}
    share_payload = _share_payload('share-fastapi-create-workspace-001')

    deps = FastApiRouteDependencies(
        workspace_id_factory=lambda: 'ws-share-created',
        membership_id_factory=lambda: 'membership-share-created',
        now_iso_provider=lambda: '2026-04-16T12:00:00+00:00',
        public_share_payload_provider=lambda share_id: share_payload if share_id == 'share-fastapi-create-workspace-001' else None,
        public_share_payload_rows_provider=lambda: (share_payload,),
        workspace_artifact_source_provider=lambda workspace_id: artifact_store.get(workspace_id),
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    deps = bind_workspace_registry_store(dependencies=deps, store=workspace_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    create_page = client.get('/app/public-shares/share-fastapi-create-workspace-001/create-workspace?app_language=en', headers=_session_headers())
    assert create_page.status_code == 200
    create_body = create_page.text
    assert 'Create workspace from share' in create_body
    assert 'name="title"' in create_body
    assert 'name="create_mode"' in create_body
    assert 'value="checkout_working_copy" selected' in create_body
    assert '/app/public-shares/share-fastapi-create-workspace-001?app_language=en' in create_body

    post_response = client.post(
        '/app/public-shares/share-fastapi-create-workspace-001/create-workspace?app_language=en',
        headers=_session_headers(),
        data={
            'title': 'Created from Share',
            'description': 'Imported from public share',
            'create_mode': 'checkout_working_copy',
            'working_save_id': 'ws-share-created-draft',
        },
        follow_redirects=False,
    )
    assert post_response.status_code == 303
    assert post_response.headers['location'] == '/app/workspaces/ws-share-created?app_language=en&action=create_workspace_from_share&status=done&source_share_id=share-fastapi-create-workspace-001&create_mode=checkout_working_copy&storage_role=working_save&target_ref=ws-share-created-draft'

    created_row = workspace_store.get_workspace_row('ws-share-created')
    assert created_row is not None
    assert created_row['title'] == 'Created from Share'

    created_source = artifact_store.get('ws-share-created')
    assert created_source is not None
    assert created_source['meta']['storage_role'] == 'working_save'
    assert created_source['meta']['working_save_id'] == 'ws-share-created-draft'
    assert created_source['meta'].get('source_working_save_id') in (None, '') or isinstance(created_source['meta'].get('source_working_save_id'), str)



def test_fastapi_binding_public_share_run_product_flow_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())

    run_page = client.get('/app/public-shares/share-fastapi-001/run?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert run_page.status_code == 200
    run_body = run_page.text
    assert 'Run public share in workspace' in run_body
    assert 'name="workspace_id" value="ws-001"' in run_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in run_body

    post_response = client.post(
        '/app/public-shares/share-fastapi-001/run?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'workspace_id': 'ws-001', 'input_payload_json': '{"question":"hello"}'},
        follow_redirects=False,
    )
    assert post_response.status_code == 303
    assert post_response.headers['location'] == '/app/workspaces/ws-001?app_language=en&action=run_artifact&status=accepted&source_share_id=share-fastapi-001&run_id=run-001'

    shell_response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())
    assert shell_response.status_code == 200
    shell_payload = shell_response.json()
    assert shell_payload['storage_role'] == 'working_save'
    assert shell_payload['working_save_id'] == 'ws-001-draft'



def test_fastapi_binding_public_share_catalog_compare_and_issuer_pages_round_trip() -> None:
    client = _make_client(artifact_source=_valid_working_save_artifact())

    catalog_response = client.get('/app/public-shares?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_body = catalog_response.text
    assert 'Browse public shares' in catalog_body
    assert '/app/public-shares/summary?app_language=en&amp;workspace_id=ws-001' in catalog_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in catalog_body
    assert '/app/public-shares/share-fastapi-001/compare?app_language=en&amp;workspace_id=ws-001' in catalog_body
    assert '/app/public-shares/share-fastapi-001/create-workspace?app_language=en&amp;workspace_id=ws-001' in catalog_body
    assert '/app/public-shares/issuers/user-owner?app_language=en&amp;workspace_id=ws-001' in catalog_body

    summary_response = client.get('/app/public-shares/summary?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert summary_response.status_code == 200
    summary_body = summary_response.text
    assert 'Open catalog summary' in summary_body or 'Public share catalog summary' in summary_body
    assert 'Checkoutable' in summary_body

    compare_response = client.get('/app/public-shares/share-fastapi-001/compare?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert compare_response.status_code == 200
    compare_body = compare_response.text
    assert 'Compare with workspace' in compare_body
    assert 'name="workspace_id" value="ws-001"' in compare_body
    assert 'Storage role match:' in compare_body
    assert '/app/public-shares/share-fastapi-001/create-workspace?app_language=en&amp;workspace_id=ws-001' in compare_body

    detail_response = client.get('/app/public-shares/share-fastapi-001?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert detail_response.status_code == 200
    detail_body = detail_response.text
    assert '/app/public-shares/issuers/user-owner?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/create-workspace?app_language=en&amp;workspace_id=ws-001' in detail_body

    history_response = client.get('/app/public-shares/share-fastapi-001/history?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert history_response.status_code == 200
    history_body = history_response.text
    assert '/app/public-shares/issuers/user-owner?app_language=en&amp;workspace_id=ws-001' in history_body
    assert '/app/public-shares/share-fastapi-001/create-workspace?app_language=en&amp;workspace_id=ws-001' in history_body

    issuer_response = client.get('/app/public-shares/issuers/user-owner?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert issuer_response.status_code == 200
    issuer_body = issuer_response.text
    assert 'More from this issuer' in issuer_body
    assert 'user-owner' in issuer_body
    assert '/app/public-shares/issuers/user-owner/summary?app_language=en&amp;workspace_id=ws-001' in issuer_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in issuer_body

    issuer_summary_response = client.get('/app/public-shares/issuers/user-owner/summary?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert issuer_summary_response.status_code == 200
    issuer_summary_body = issuer_summary_response.text
    assert 'Issuer summary' in issuer_summary_body or 'Open catalog summary' in issuer_summary_body
    assert 'user-owner' in issuer_summary_body
    assert 'Inventory total' in issuer_summary_body


def test_fastapi_binding_public_share_related_product_flow_round_trip() -> None:
    primary = _share_payload('share-fastapi-001')
    secondary = _share_payload('share-fastapi-002')
    secondary['share']['title'] = 'FastAPI share related'
    share_rows = (primary, secondary)
    share_map = {row['share']['share_id']: row for row in share_rows}
    client = _make_client(
        public_share_payload_provider=lambda share_id: share_map.get(share_id),
        public_share_payload_rows_provider=lambda: share_rows,
    )

    catalog_response = client.get('/app/public-shares?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_body = catalog_response.text
    assert '/app/public-shares/share-fastapi-001/related?app_language=en&amp;workspace_id=ws-001' in catalog_body

    detail_response = client.get('/app/public-shares/share-fastapi-001?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert detail_response.status_code == 200
    detail_body = detail_response.text
    assert '/app/public-shares/share-fastapi-001/related?app_language=en&amp;workspace_id=ws-001' in detail_body

    history_response = client.get('/app/public-shares/share-fastapi-001/history?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert history_response.status_code == 200
    history_body = history_response.text
    assert '/app/public-shares/share-fastapi-001/related?app_language=en&amp;workspace_id=ws-001' in history_body

    related_response = client.get('/app/public-shares/share-fastapi-001/related?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert related_response.status_code == 200
    related_body = related_response.text
    assert 'Related public shares' in related_body
    assert 'FastAPI share related' in related_body
    assert 'Match score' in related_body
    assert '/app/public-shares/share-fastapi-002?app_language=en&amp;workspace_id=ws-001' in related_body
    assert '/app/public-shares/share-fastapi-002/compare?app_language=en&amp;workspace_id=ws-001' in related_body
    assert '/app/public-shares/share-fastapi-002/create-workspace?app_language=en&amp;workspace_id=ws-001' in related_body


def test_fastapi_binding_public_share_download_product_flow_round_trip() -> None:
    client = _make_client()

    download_page = client.get('/app/public-shares/share-fastapi-001/download?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert download_page.status_code == 200
    download_body = download_page.text
    assert 'Download public share artifact' in download_body
    assert '/app/public-shares/share-fastapi-001?app_language=en&amp;workspace_id=ws-001' in download_body
    assert '/app/public-shares/share-fastapi-001/artifact/download?app_language=en' in download_body

    download_response = client.get('/app/public-shares/share-fastapi-001/artifact/download?app_language=en', headers=_session_headers())
    assert download_response.status_code == 200
    assert 'attachment; filename=' in download_response.headers['content-disposition']
    artifact_payload = download_response.json()
    assert artifact_payload['meta']['storage_role'] == 'commit_snapshot'
    assert artifact_payload['meta']['commit_id'] == 'snap-fastapi-share-001'



def test_fastapi_binding_saved_public_share_collection_round_trip() -> None:
    saved_rows: list[dict[str, str]] = []

    def _saved_rows_provider():
        return tuple(saved_rows)

    def _saved_writer(row: dict) -> dict:
        if not any(existing.get("share_id") == row.get("share_id") for existing in saved_rows):
            saved_rows.append(dict(row))
        return dict(row)

    def _saved_deleter(share_id: str) -> bool:
        before = len(saved_rows)
        saved_rows[:] = [row for row in saved_rows if row.get("share_id") != share_id]
        return len(saved_rows) != before

    client = _make_client(
        saved_public_share_rows_provider=_saved_rows_provider,
        saved_public_share_writer=_saved_writer,
        saved_public_share_deleter=_saved_deleter,
    )

    catalog_response = client.get('/app/public-shares?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert catalog_response.status_code == 200
    catalog_body = catalog_response.text
    assert '/app/users/me/saved-public-shares?app_language=en&amp;workspace_id=ws-001' in catalog_body
    assert '/app/public-shares/share-fastapi-001/save?app_language=en&amp;workspace_id=ws-001' in catalog_body

    save_response = client.post(
        '/app/public-shares/share-fastapi-001/save?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'return_to': '/app/public-shares?app_language=en&workspace_id=ws-001'},
        follow_redirects=False,
    )
    assert save_response.status_code == 303
    assert save_response.headers['location'] == '/app/public-shares?app_language=en&workspace_id=ws-001&action=save&status=done'
    assert saved_rows and saved_rows[0]['share_id'] == 'share-fastapi-001'

    saved_page = client.get('/app/users/me/saved-public-shares?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert saved_page.status_code == 200
    saved_body = saved_page.text
    assert 'Saved public shares' in saved_body
    assert 'FastAPI share' in saved_body
    assert '/app/public-shares/share-fastapi-001/unsave?app_language=en&amp;workspace_id=ws-001' in saved_body

    detail_response = client.get('/app/public-shares/share-fastapi-001?app_language=en&workspace_id=ws-001', headers=_session_headers())
    assert detail_response.status_code == 200
    detail_body = detail_response.text
    assert '/app/users/me/saved-public-shares?app_language=en&amp;workspace_id=ws-001' in detail_body
    assert '/app/public-shares/share-fastapi-001/unsave?app_language=en&amp;workspace_id=ws-001' in detail_body

    unsave_response = client.post(
        '/app/public-shares/share-fastapi-001/unsave?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'return_to': '/app/users/me/saved-public-shares?app_language=en&workspace_id=ws-001'},
        follow_redirects=False,
    )
    assert unsave_response.status_code == 303
    assert unsave_response.headers['location'] == '/app/users/me/saved-public-shares?app_language=en&workspace_id=ws-001&action=unsave&status=done'
    assert saved_rows == []


def test_fastapi_binding_issuer_public_share_product_pages_round_trip() -> None:
    rows = (
        export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-active-page'),
            share_id='share-fastapi-owner-active-page',
            title='FastAPI Owner Active Page',
            created_at='2026-04-15T12:00:00+00:00',
            updated_at='2026-04-15T12:30:00+00:00',
            issued_by_user_ref='user-owner',
        ),
        export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-archived-page'),
            share_id='share-fastapi-owner-archived-page',
            title='FastAPI Owner Archived Page',
            created_at='2026-04-10T12:00:00+00:00',
            updated_at='2026-04-10T12:15:00+00:00',
            archived=True,
            issued_by_user_ref='user-owner',
        ),
    )
    client = _make_client(public_share_payload_rows_provider=lambda: rows, public_share_action_report_rows_provider=_issuer_action_report_rows)

    portfolio_response = client.get('/app/users/me/public-shares?app_language=en', headers=_session_headers())
    assert portfolio_response.status_code == 200
    portfolio_body = portfolio_response.text
    assert 'My public shares' in portfolio_body
    assert 'FastAPI Owner Active Page' in portfolio_body
    assert '/app/users/me/public-shares/summary?app_language=en' in portfolio_body
    assert '/app/users/me/public-shares/action-reports?app_language=en' in portfolio_body
    assert '/app/users/me/public-shares/actions/revoke?app_language=en' in portfolio_body
    assert '/app/users/me/public-shares/actions/archive?app_language=en' in portfolio_body
    assert 'bulk-revoke-form' in portfolio_body
    assert 'bulk-archive-form' in portfolio_body
    assert 'bulk-extend-form' in portfolio_body
    assert 'bulk-delete-form' in portfolio_body
    assert 'share_ids_csv' in portfolio_body

    summary_response = client.get('/app/users/me/public-shares/summary?app_language=en', headers=_session_headers())
    assert summary_response.status_code == 200
    assert 'Public share summary' in summary_response.text or 'Share summary' in summary_response.text

    reports_response = client.get('/app/users/me/public-shares/action-reports?app_language=en', headers=_session_headers())
    assert reports_response.status_code == 200
    reports_body = reports_response.text
    assert 'Action reports' in reports_body
    assert 'Archive' in reports_body


def test_fastapi_binding_issuer_public_share_product_management_round_trip() -> None:
    share_store: dict[str, dict] = {
        'share-fastapi-owner-portfolio-001': export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-portfolio-001'),
            share_id='share-fastapi-owner-portfolio-001',
            title='FastAPI Owner Portfolio Share',
            created_at='2026-04-15T12:00:00+00:00',
            issued_by_user_ref='user-owner',
        ),
    }
    action_reports: list[dict] = []

    def _writer(payload: dict) -> dict:
        share_store[payload['share']['share_id']] = dict(payload)
        return dict(payload)

    def _deleter(share_id: str) -> bool:
        return share_store.pop(share_id, None) is not None

    def _action_report_writer(report: dict) -> dict:
        action_reports.append(dict(report))
        return dict(report)

    client = _make_client(
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_writer=_writer,
        public_share_payload_deleter=_deleter,
        public_share_action_report_rows_provider=lambda: tuple(action_reports),
        public_share_action_report_writer=_action_report_writer,
    )

    archive_response = client.post(
        '/app/users/me/public-shares/actions/archive?app_language=en',
        headers=_session_headers(),
        data={'share_id': 'share-fastapi-owner-portfolio-001', 'archived': 'true'},
        follow_redirects=False,
    )
    assert archive_response.status_code == 303
    assert archive_response.headers['location'].startswith('/app/users/me/public-shares?app_language=en')
    assert 'action=archive' in archive_response.headers['location']
    archived_page = client.get(archive_response.headers['location'], headers=_session_headers())
    assert archived_page.status_code == 200
    assert 'Unarchive share' in archived_page.text
    assert 'Action reports' in archived_page.text or 'action reports' in archived_page.text

    delete_response = client.post(
        '/app/users/me/public-shares/actions/delete?app_language=en',
        headers=_session_headers(),
        data={'share_id': 'share-fastapi-owner-portfolio-001'},
        follow_redirects=False,
    )
    assert delete_response.status_code == 303
    assert delete_response.headers['location'].startswith('/app/users/me/public-shares?app_language=en')
    assert 'action=delete' in delete_response.headers['location']
    assert 'share-fastapi-owner-portfolio-001' not in share_store


def test_fastapi_binding_issuer_public_share_bulk_management_round_trip() -> None:
    share_store: dict[str, dict] = {
        'share-fastapi-owner-bulk-001': export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-bulk-001'),
            share_id='share-fastapi-owner-bulk-001',
            title='FastAPI Owner Bulk Share 1',
            created_at='2026-04-15T12:00:00+00:00',
            issued_by_user_ref='user-owner',
        ),
        'share-fastapi-owner-bulk-002': export_public_nex_link_share(
            _commit_snapshot('snap-fastapi-owner-bulk-002'),
            share_id='share-fastapi-owner-bulk-002',
            title='FastAPI Owner Bulk Share 2',
            created_at='2026-04-15T12:05:00+00:00',
            issued_by_user_ref='user-owner',
        ),
    }
    action_reports: list[dict] = []

    def _writer(payload: dict) -> dict:
        share_store[payload['share']['share_id']] = dict(payload)
        return dict(payload)

    def _deleter(share_id: str) -> bool:
        return share_store.pop(share_id, None) is not None

    def _action_report_writer(report: dict) -> dict:
        action_reports.append(dict(report))
        return dict(report)

    client = _make_client(
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_writer=_writer,
        public_share_payload_deleter=_deleter,
        public_share_action_report_rows_provider=lambda: tuple(action_reports),
        public_share_action_report_writer=_action_report_writer,
    )

    archive_response = client.post(
        '/app/users/me/public-shares/actions/archive?app_language=en',
        headers=_session_headers(),
        data={'share_ids_csv': 'share-fastapi-owner-bulk-001,share-fastapi-owner-bulk-002', 'archived': 'true'},
        follow_redirects=False,
    )
    assert archive_response.status_code == 303
    assert archive_response.headers['location'].startswith('/app/users/me/public-shares?app_language=en')
    assert 'action=archive' in archive_response.headers['location']
    assert share_store['share-fastapi-owner-bulk-001']['share']['management']['archived'] is True
    assert share_store['share-fastapi-owner-bulk-002']['share']['management']['archived'] is True

    revoke_response = client.post(
        '/app/users/me/public-shares/actions/revoke?app_language=en',
        headers=_session_headers(),
        data={'share_ids_csv': 'share-fastapi-owner-bulk-001,share-fastapi-owner-bulk-002'},
        follow_redirects=False,
    )
    assert revoke_response.status_code == 303
    assert 'action=revoke' in revoke_response.headers['location']
    assert share_store['share-fastapi-owner-bulk-001']['share']['lifecycle']['state'] == 'revoked'
    assert share_store['share-fastapi-owner-bulk-002']['share']['lifecycle']['state'] == 'revoked'
    assert action_reports[-1]['affected_share_count'] == 2


def test_fastapi_binding_public_share_management_actions_round_trip() -> None:
    share_store: dict[str, dict] = {'share-fastapi-001': _share_payload('share-fastapi-001')}
    action_reports: list[dict] = []

    def _provider(share_id: str):
        return share_store.get(share_id)

    def _rows_provider():
        return tuple(share_store.values())

    def _writer(payload: dict) -> dict:
        share_store[payload['share']['share_id']] = dict(payload)
        return dict(payload)

    def _deleter(share_id: str) -> bool:
        return share_store.pop(share_id, None) is not None

    def _action_report_writer(report: dict) -> dict:
        action_reports.append(dict(report))
        return dict(report)

    client = _make_client(
        public_share_payload_provider=_provider,
        public_share_payload_rows_provider=_rows_provider,
        public_share_payload_writer=_writer,
        public_share_payload_deleter=_deleter,
        public_share_action_report_rows_provider=lambda: tuple(action_reports),
        public_share_action_report_writer=_action_report_writer,
    )

    archive_response = client.post(
        '/app/public-shares/share-fastapi-001/archive?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'archived': 'true', 'origin': 'detail'},
        follow_redirects=False,
    )
    assert archive_response.status_code == 303
    archive_location = archive_response.headers['location']
    assert archive_location.startswith('/app/public-shares/share-fastapi-001?app_language=en&workspace_id=ws-001')
    assert 'action=archive' in archive_location
    assert 'status=done' in archive_location
    archived_detail = client.get(archive_location, headers=_session_headers())
    assert archived_detail.status_code == 200
    assert 'Unarchive share' in archived_detail.text

    revoke_response = client.post(
        '/app/public-shares/share-fastapi-001/revoke?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'origin': 'history'},
        follow_redirects=False,
    )
    assert revoke_response.status_code == 303
    revoke_location = revoke_response.headers['location']
    assert revoke_location.startswith('/app/public-shares/share-fastapi-001/history?app_language=en&workspace_id=ws-001')
    assert 'action=revoke' in revoke_location
    assert 'status=done' in revoke_location

    delete_response = client.post(
        '/app/public-shares/share-fastapi-001/delete?app_language=en&workspace_id=ws-001',
        headers=_session_headers(),
        data={'origin': 'detail'},
        follow_redirects=False,
    )
    assert delete_response.status_code == 303
    delete_location = delete_response.headers['location']
    assert delete_location.startswith('/app/workspaces/ws-001/shares?app_language=en')
    assert 'action=delete' in delete_location
    assert 'status=done' in delete_location
    assert 'share-fastapi-001' not in share_store


def test_fastapi_binding_workspace_share_create_form_page_renders() -> None:
    client = _make_client(artifact_source=_commit_snapshot('snap-fastapi-created-share-page-form-001'))
    response = client.get('/app/workspaces/ws-001/shares/create?app_language=en', headers=_session_headers())
    assert response.status_code == 200
    body = response.text
    assert '<form method="post" action="/app/workspaces/ws-001/shares/create?app_language=en">' in body
    assert 'Current artifact' in body or 'Source artifact' in body
    assert 'Public share for Primary Workspace.' in body


def test_fastapi_binding_workspace_share_create_page_redirects_to_public_share_detail() -> None:
    share_store: dict[str, dict] = {}

    def _writer(payload: dict) -> dict:
        share_store[payload['share']['share_id']] = dict(payload)
        return dict(payload)

    client = _make_client(
        artifact_source=_commit_snapshot('snap-fastapi-created-share-page-001'),
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_writer=_writer,
    )
    response = client.post(
        '/app/workspaces/ws-001/shares/create?app_language=en',
        headers=_session_headers(),
        data={
            'title': 'Form Created Share',
            'summary': 'Share created from the product-facing form.',
            'expires_at': '2026-04-22T00:00:00+00:00',
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers['location']
    assert location.startswith('/app/public-shares/')
    assert 'workspace_id=ws-001' in location
    assert 'app_language=en' in location
    created_payload = next(iter(share_store.values()))
    assert created_payload['share']['title'] == 'Form Created Share'
    assert created_payload['share']['summary'] == 'Share created from the product-facing form.'
    assert created_payload['share']['lifecycle']['expires_at'] == '2026-04-22T00:00:00+00:00'


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
    assert payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'
    assert payload['artifact_boundary']['role_boundary']['editor_continuity_posture'] == 'ui_forbidden_in_canonical_snapshot'
    assert payload['artifact_boundary']['role_boundary']['commit_boundary_posture'] == 'already_crossed_commit_boundary'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][0]['operation'] == 'load_artifact'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][4]['execution_anchor_posture'] == 'working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor'

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
    assert payload['identity_policy']['surface_family'] == 'run-launch'
    assert payload['namespace_policy']['family'] == 'run-launch'


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
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.post('/api/public-shares/share-fastapi-revoke-001/revoke', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-revoke-001'
    assert payload['identity']['share_family'] == 'public_nex_link_share'
    assert payload['lifecycle']['state'] == 'revoked'
    assert payload['lifecycle']['updated_at'] == '2026-04-11T12:09:00+00:00'
    assert payload['audit_summary']['event_count'] == 2
    assert payload['action_report']['action'] == 'revoke'
    assert payload['governance_summary']['total_action_report_count'] == 3
    assert payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'
    assert payload['artifact_boundary']['role_boundary']['editor_continuity_posture'] == 'ui_forbidden_in_canonical_snapshot'
    assert payload['artifact_boundary']['role_boundary']['commit_boundary_posture'] == 'already_crossed_commit_boundary'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][0]['operation'] == 'load_artifact'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][4]['execution_anchor_posture'] == 'working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor'
    assert payload['links']['action_reports'] == '/api/users/me/public-shares/action-reports'
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
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.post(
        '/api/public-shares/share-fastapi-extend-001/extend',
        headers=_session_headers(),
        json={"expires_at": "2026-04-20T00:00:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-extend-001'
    assert payload['identity']['share_family'] == 'public_nex_link_share'
    assert payload['lifecycle']['stored_state'] == 'active'
    assert payload['lifecycle']['state'] == 'active'
    assert payload['lifecycle']['expires_at'] == '2026-04-20T00:00:00+00:00'
    assert payload['audit_summary']['event_count'] == 2
    assert payload['action_report']['action'] == 'extend_expiration'
    assert payload['governance_summary']['total_action_report_count'] == 3
    assert payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'
    assert payload['artifact_boundary']['role_boundary']['editor_continuity_posture'] == 'ui_forbidden_in_canonical_snapshot'
    assert payload['artifact_boundary']['role_boundary']['commit_boundary_posture'] == 'already_crossed_commit_boundary'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][0]['operation'] == 'load_artifact'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][4]['execution_anchor_posture'] == 'working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor'
    assert payload['links']['action_report_summary'] == '/api/users/me/public-shares/action-reports/summary'



def test_fastapi_binding_delete_issuer_public_shares_round_trip() -> None:
    share_store = {
        "share-fastapi-delete-a": export_public_nex_link_share(_commit_snapshot("snap-fastapi-delete-a"), share_id="share-fastapi-delete-a", title="FastAPI Delete A", created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner"),
        "share-fastapi-delete-b": export_public_nex_link_share(_commit_snapshot("snap-fastapi-delete-b"), share_id="share-fastapi-delete-b", title="FastAPI Delete B", created_at="2026-04-15T12:05:00+00:00", issued_by_user_ref="user-owner"),
    }

    client = _make_client(
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.post('/api/users/me/public-shares/actions/delete', headers=_session_headers(), json={'share_ids': ['share-fastapi-delete-a', 'share-fastapi-delete-b']})

    assert response.status_code == 200
    payload = response.json()
    assert payload['action'] == 'delete'
    assert payload['affected_share_count'] == 2
    assert payload['summary']['total_share_count'] == 0
    assert payload['governance_summary']['total_share_count'] == 0
    assert payload['links']['action_reports'] == '/api/users/me/public-shares/action-reports'


def test_fastapi_binding_public_share_archive_round_trip() -> None:
    share_store: dict[str, dict] = {"share-fastapi-archive-001": _share_payload("share-fastapi-archive-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.post('/api/public-shares/share-fastapi-archive-001/archive', headers=_session_headers(), json={'archived': True})

    assert response.status_code == 200
    payload = response.json()
    assert payload['management']['archived'] is True
    assert payload['action_report']['action'] == 'archive'
    assert payload['governance_summary']['total_share_count'] == 1
    assert payload['governance_summary']['total_action_report_count'] == 3
    assert payload['share_boundary']['share_family'] == 'nex.public-link-share'
    assert payload['artifact_boundary']['role_boundary']['identity_field'] == 'commit_id'
    assert payload['artifact_boundary']['role_boundary']['editor_continuity_posture'] == 'ui_forbidden_in_canonical_snapshot'
    assert payload['artifact_boundary']['role_boundary']['commit_boundary_posture'] == 'already_crossed_commit_boundary'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][0]['operation'] == 'load_artifact'
    assert payload['artifact_boundary']['artifact_operation_boundaries'][4]['execution_anchor_posture'] == 'working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor'
    assert payload['links']['action_reports'] == '/api/users/me/public-shares/action-reports'


def test_fastapi_binding_public_share_delete_round_trip() -> None:
    share_store = {"share-fastapi-delete-001": _share_payload("share-fastapi-delete-001")}

    client = _make_client(
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_writer=lambda row: dict(row),
    )
    response = client.delete('/api/public-shares/share-fastapi-delete-001', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'deleted'
    assert payload['share_id'] == 'share-fastapi-delete-001'
    assert payload['identity']['canonical_key'] == 'share_id'
    assert payload['action_report']['action'] == 'delete'
    assert payload['governance_summary']['total_share_count'] == 0
    assert payload['links']['action_reports'] == '/api/users/me/public-shares/action-reports'



def test_fastapi_binding_public_mcp_manifest_route_round_trip() -> None:
    client = _make_client()

    response = client.get('/api/integrations/public-mcp/manifest', params={'base_url': 'https://api.nexa.test'})

    assert response.status_code == 200
    assert response.json()['manifest']['server']['name'] == 'nexa-public'
    assert response.json()['identity_policy']['canonical_key'] == 'manifest.server.name'
    assert response.json()['namespace_policy']['family'] == 'public-mcp-manifest'


def test_fastapi_binding_public_mcp_host_bridge_route_round_trip() -> None:
    client = _make_client()

    response = client.get('/api/integrations/public-mcp/host-bridge', params={'base_url': 'https://api.nexa.test'})

    assert response.status_code == 200
    assert response.json()['host_bridge']['framework_binding_class'] == 'FrameworkRouteBindings'
    assert response.json()['identity_policy']['canonical_key'] == 'host_bridge.framework_binding_class'
    assert response.json()['namespace_policy']['family'] == 'public-mcp-host-bridge'


def test_fastapi_binding_workspace_public_share_creation_round_trip() -> None:
    share_store: dict[str, dict] = {}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    client = _make_client(
        artifact_source=_commit_snapshot('snap-fastapi-created-share-002'),
        public_share_payload_provider=lambda share_id: share_store.get(share_id),
        public_share_payload_writer=_writer,
    )
    response = client.post(
        '/api/workspaces/ws-001/shares',
        headers=_session_headers(),
        json={'share_id': 'share-fastapi-created-002', 'title': 'FastAPI Family Shared Snapshot', 'expires_at': '2026-04-21T00:00:00+00:00'},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['share_id'] == 'share-fastapi-created-002'
    assert payload['links']['workspace_public_share_create'] == '/api/workspaces/ws-001/shares'
    assert payload['links']['workspace_shell_share'] == '/api/workspaces/ws-001/shares'
    assert payload['links']['workspace_shell_share_legacy'] == '/api/workspaces/ws-001/shell/share'
    get_response = client.get('/api/public-shares/share-fastapi-created-002')
    assert get_response.status_code == 200


def test_fastapi_binding_workspace_shell_template_path_promotes_provider_setup_next() -> None:
    artifact_store = {
        'ws-001': {
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US", "viewport_tier": "mobile"}},
            "designer": {
                "server_backed_shell_state": {
                    "selected_template_id": "text_summarizer",
                    "selected_template_display_name": "Text Summarizer",
                    "selected_template_ref": "nexa-curated:text_summarizer@1.0",
                    "last_action": "apply_template",
                }
            },
        }
    }
    client = _make_client(
        artifact_source=artifact_store['ws-001'],
        workspace_run_rows=(),
        workspace_result_rows={},
        workspace_provider_binding_rows=(),
        workspace_provider_probe_rows=(),
        recent_managed_secret_rows=(),
    )

    response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['first_success_setup_section']['setup_state'] == 'provider_setup_needed'
    assert payload['first_success_setup_section']['entry_path_kind'] == 'starter_template'
    assert payload['first_success_setup_section']['current_step_id'] == 'connect_provider'
    assert payload['first_success_setup_section']['controls'][0]['action_target'] == '/api/workspaces/ws-001/provider-bindings'
    assert payload['first_success_setup_section']['controls'][1]['action_target'] == '/app/workspaces/ws-001/starter-templates?app_language=en'
    assert any(line.startswith('Selected starter template: Text Summarizer') for line in payload['first_success_setup_section']['summary']['lines'])
    assert payload['first_success_run_section']['run_state'] in {'waiting', 'inactive'}
    assert payload['first_success_run_section']['run_path_kind'] == 'setup_prerequisite'
    assert payload['first_success_run_section']['current_step_id'] == 'connect_provider'
    assert payload['first_success_run_section']['controls'][0]['action_target'] == '/api/workspaces/ws-001/provider-bindings'


def test_fastapi_binding_provider_probe_auto_resolves_aws_runner(monkeypatch) -> None:
    import urllib.request

    class _FakeHttpResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = json.dumps(payload).encode("utf-8")

        def read(self) -> bytes:
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(req, timeout=0):
        assert req.full_url == "https://api.openai.com/v1/responses"
        assert req.headers.get("Authorization") == "Bearer aws-probe-key"
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "gpt-4.1"
        return _FakeHttpResponse({"output_text": "OK", "usage": {"output_tokens": 1}})

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    probe_store = InMemoryProviderProbeHistoryStore()
    binding_store = InMemoryProviderBindingStore.from_rows((
        {
            "binding_id": "binding-auto-probe",
            "workspace_id": "ws-001",
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "credential_source": "managed",
            "secret_ref": "aws-secretsmanager://nexa/ws-001/providers/openai",
            "secret_version_ref": "v1",
            "enabled": True,
            "default_model_ref": "gpt-4.1",
            "allowed_model_refs": ("gpt-4.1",),
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "updated_by_user_id": "user-owner",
        },
    ))

    deps = FastApiRouteDependencies(
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_rows_provider=lambda: ({
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "continuity_source": "server",
            "archived": False,
        },),
        workspace_row_provider=lambda workspace_id: {
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "continuity_source": "server",
            "archived": False,
        } if workspace_id == "ws-001" else None,
        provider_catalog_rows_provider=lambda: ({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
        aws_secrets_manager_client_provider=lambda: _FakeSecretsClient(),
        aws_secrets_manager_config=AwsSecretsManagerBindingConfig(),
        recent_run_rows_provider=lambda: (),
        recent_managed_secret_rows_provider=lambda: ({
            "workspace_id": "ws-001",
            "provider_key": "openai",
            "secret_ref": "aws-secretsmanager://nexa/ws-001/providers/openai",
            "last_rotated_at": "2026-04-11T12:06:00+00:00",
        },),
        now_iso_provider=lambda: "2026-04-11T12:09:00+00:00",
        probe_event_id_factory=lambda: "probe-auto-aws",
    )
    deps = bind_provider_binding_store(dependencies=deps, store=binding_store)
    deps = bind_probe_history_store(dependencies=deps, store=probe_store)
    client = TestClient(create_fastapi_app(dependencies=deps))

    response = client.post(
        "/api/workspaces/ws-001/provider-bindings/openai/probe",
        headers=_session_headers(),
        json={"model_ref": "gpt-4.1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["probe_status"] == "reachable"
    assert payload["connectivity_state"] == "ok"
    assert payload["effective_model_ref"] == "gpt-4.1"

    history = client.get(
        "/api/workspaces/ws-001/provider-bindings/openai/probe-history?limit=1",
        headers=_session_headers(),
    )
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["items"][0]["probe_event_id"] == "probe-auto-aws"
    assert history_payload["items"][0]["probe_status"] == "reachable"


def test_fastapi_binding_workspace_shell_launch_rejects_when_required_provider_binding_is_missing() -> None:
    client = _make_client(
        artifact_source=_provider_backed_working_save_artifact('ws-fastapi-provider-001'),
        workspace_provider_binding_rows=(),
        recent_managed_secret_rows=(),
        workspace_provider_probe_rows=(),
    )

    response = client.post('/api/workspaces/ws-001/shell/launch', headers=_session_headers(), json={'input_payload': {'question': 'hello from provider shell'}})

    assert response.status_code == 409
    payload = response.json()
    assert payload['reason_code'] == 'launch.provider_binding_missing'
    assert payload['blocking_findings'][0]['provider_key'] == 'openai'


def test_fastapi_binding_workspace_shell_keeps_provider_setup_needed_when_required_provider_is_missing() -> None:
    client = _make_client(
        artifact_source=_provider_backed_working_save_artifact('ws-fastapi-provider-setup-001'),
        workspace_provider_binding_rows=({
            'binding_id': 'binding-001',
            'workspace_id': 'ws-001',
            'provider_key': 'anthropic',
            'provider_family': 'anthropic',
            'display_name': 'Anthropic Claude',
            'credential_source': 'managed',
            'secret_ref': 'secret://ws-001/anthropic',
            'secret_version_ref': 'v1',
            'enabled': True,
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:05:00+00:00',
            'updated_by_user_id': 'user-owner',
        },),
        recent_managed_secret_rows=({
            'workspace_id': 'ws-001',
            'provider_key': 'anthropic',
            'secret_ref': 'secret://ws-001/anthropic',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },),
        workspace_provider_probe_rows=(),
        workspace_run_rows=(),
        workspace_result_rows={},
    )

    response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload['first_success_setup_section']['setup_state'] == 'provider_setup_needed'
    assert payload['server_product_readiness_review']['stages'][0]['provider_setup_reason_code'] == 'launch.provider_binding_missing'
    assert payload['server_product_readiness_review']['stages'][0]['required_provider_keys'] == ['openai']


def test_fastapi_web_skeleton_dashboard_and_access_boundary() -> None:
    client = _make_client()

    unauth_entry = client.get("/app", follow_redirects=False)
    assert unauth_entry.status_code == 303
    assert unauth_entry.headers["location"].startswith("/app/sign-in")

    sign_in = client.get("/app/sign-in")
    assert sign_in.status_code == 200
    assert "Sign in to Nexa" in sign_in.text
    assert "access-boundary" in sign_in.text

    entry = client.get("/app", headers=_session_headers(), follow_redirects=False)
    assert entry.status_code == 303
    assert entry.headers["location"].startswith("/app/workspaces")

    dashboard = client.get("/app/workspaces", headers=_session_headers())
    assert dashboard.status_code == 200
    assert "workspace-dashboard" in dashboard.text
    assert "Primary Workspace" in dashboard.text
    assert "/app/workspaces/ws-001/upload" in dashboard.text
    assert "/app/workspaces/ws-001/run" in dashboard.text
    assert "/app/workspaces/ws-001/results" in dashboard.text


def test_fastapi_web_skeleton_upload_submit_result_entry_pages() -> None:
    client = _make_client()

    upload = client.get("/app/workspaces/ws-001/upload", headers=_session_headers())
    assert upload.status_code == 200
    assert "upload-entry" in upload.text
    assert "POST /api/workspaces/ws-001/uploads/presign" in upload.text
    assert "scanning" in upload.text
    assert "rejected" in upload.text
    assert "safe" in upload.text
    assert "upload-status-panel" in upload.text
    assert "data-presign-path=\"/api/workspaces/ws-001/uploads/presign\"" in upload.text
    assert "data-confirm-template=\"/api/workspaces/ws-001/uploads/{upload_id}/confirm\"" in upload.text
    assert "data-status-template=\"/api/workspaces/ws-001/uploads/{upload_id}\"" in upload.text
    assert "upload-run-gate" in upload.text
    assert "data-requires-upload-status=\"safe\"" in upload.text
    assert "Run remains gated until the upload status is safe." in upload.text

    run = client.get("/app/workspaces/ws-001/run", headers=_session_headers())
    assert run.status_code == 200
    assert "submit-run-entry" in run.text
    assert "POST /api/runs" in run.text
    assert "/api/workspaces/ws-001/runs" in run.text
    assert "result-screen-minimum" in run.text
    assert "run-submit-form" in run.text
    assert "data-submit-path=\"/api/runs\"" in run.text
    assert "data-run-status-template=\"/api/runs/{run_id}\"" in run.text
    assert "data-run-actions-template=\"/api/runs/{run_id}/actions\"" in run.text
    assert "run-result-handoff-panel" in run.text
    assert "data-run-result-template=\"/api/runs/{run_id}/result\"" in run.text
    assert "data-shell-draft-path=\"/api/workspaces/ws-001/shell/draft\"" in run.text
    assert "/app/workspaces/ws-001/results?app_language=en" in run.text

    contract_run = client.get("/app/workspaces/ws-001/run?app_language=en&use_case=contract_review&upload_id=upload-001&upload_status=safe&extraction_id=extract-001", headers=_session_headers())
    assert contract_run.status_code == 200
    assert "contract-review-run-input-handoff" in contract_run.text
    assert "data-upload-id=\"upload-001\"" in contract_run.text
    assert "data-upload-status=\"safe\"" in contract_run.text
    assert "data-extraction-id=\"extract-001\"" in contract_run.text
    assert "data-ready-for-run=\"true\"" in contract_run.text
    assert "web_contract_review_slice" in contract_run.text
    assert "contract_review_freelancer_v1" in contract_run.text

    workspace = client.get("/app/workspaces/ws-001", headers=_session_headers())
    assert workspace.status_code == 200
    assert "open-upload-page" in workspace.text
    assert "open-submit-run-page" in workspace.text
    assert "/app/workspaces/ws-001/upload?app_language=en" in workspace.text
    assert "/app/workspaces/ws-001/run?app_language=en" in workspace.text


def test_fastapi_workspace_shell_renders_first_success_flow_bridge() -> None:
    client = _make_client()

    api_response = client.get('/api/workspaces/ws-001/shell', headers=_session_headers())
    assert api_response.status_code == 200
    payload = api_response.json()
    assert 'first_success_flow_section' in payload
    assert payload['first_success_flow_section']['summary']['headline'] == 'First-success flow'
    assert 'flow_state' in payload['first_success_flow_section']
    assert 'current_step_id' in payload['first_success_flow_section']

    page_response = client.get('/app/workspaces/ws-001?app_language=en', headers=_session_headers())
    assert page_response.status_code == 200
    body = page_response.text
    assert 'first-success-flow-card' in body
    assert 'first-success-flow-summary' in body
    assert 'initialFirstSuccessFlowSection' in body
    assert 'writeFirstSuccessFlowSection' in body


def test_fastapi_binding_workspace_result_history_renders_contract_review_structured_result() -> None:
    contract_review_value = json.dumps(
        {
            "use_case": "contract_review",
            "template_id": "contract_review_freelancer_v1",
            "document_reference": {"upload_id": "upload-001", "extraction_id": "extract-001"},
            "clauses": [
                {
                    "clause_id": "payment",
                    "title": "Payment terms",
                    "risk_level": "medium",
                    "plain_language_explanation": "Payment timing is not explicit.",
                    "source_reference": {"start": 120, "end": 180, "label": "Section 3"},
                }
            ],
            "pre_signature_questions": ["When is payment due?"],
        },
        sort_keys=True,
    )
    client = _make_client(
        workspace_result_rows={
            'run-002': {
                'run_id': 'run-002',
                'workspace_id': 'ws-001',
                'result_state': 'ready_success',
                'final_status': 'completed',
                'result_summary': 'Success.',
                'updated_at': '2026-04-11T12:01:05+00:00',
                'final_output': {
                    'output_key': 'contract_review_result',
                    'value_preview': contract_review_value,
                    'value_type': 'contract_review',
                },
            }
        }
    )

    api_response = client.get('/api/workspaces/ws-001/result-history?run_id=run-002', headers=_session_headers())
    assert api_response.status_code == 200
    payload = api_response.json()
    structured = payload['selected_result']['contract_review_result']
    assert structured['render_kind'] == 'contract_review_structured'
    assert structured['document_reference']['upload_id'] == 'upload-001'
    assert structured['clauses'][0]['title'] == 'Payment terms'
    assert structured['clauses'][0]['source_reference']['start'] == 120
    assert structured['pre_signature_questions'] == ['When is payment due?']

    page_response = client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert page_response.status_code == 200
    assert 'contract-review-structured-result' in page_response.text
    assert 'data-render-kind="contract_review_structured"' in page_response.text
    assert 'contract-review-clause-list' in page_response.text
    assert 'Payment terms' in page_response.text
    assert 'Payment timing is not explicit.' in page_response.text
    assert 'data-source-start="120"' in page_response.text
    assert 'contract-review-pre-signature-questions' in page_response.text
    assert 'When is payment due?' in page_response.text
    assert 'contract-review-next-actions' in page_response.text
    assert 'id="copy_contract_review_result"' in page_response.text
    assert 'id="continue_from_contract_review_result"' in page_response.text
    assert 'return_use=contract_review_result' in page_response.text
    assert 'contract-review-question-actions' in page_response.text
    assert 'data-question-id="question-1"' in page_response.text
    assert 'id="ask_pre_signature_question_1"' in page_response.text
    assert 'return_use=contract_review_question' in page_response.text


def test_fastapi_binding_contract_review_vertical_slice_e2e_smoke_path() -> None:
    contract_review_value = json.dumps(
        {
            "use_case": "contract_review",
            "template_id": "contract_review_freelancer_v1",
            "document_reference": {"upload_id": "upload-001", "extraction_id": "extract-001"},
            "clauses": [
                {
                    "clause_id": "payment",
                    "title": "Payment terms",
                    "risk_level": "medium",
                    "plain_language_explanation": "Payment timing is not explicit.",
                    "source_reference": {"start": 120, "end": 180, "label": "Section 3"},
                }
            ],
            "pre_signature_questions": ["When is payment due?"],
        },
        sort_keys=True,
    )
    client = _make_client(
        workspace_result_rows={
            'run-002': {
                'run_id': 'run-002',
                'workspace_id': 'ws-001',
                'result_state': 'ready_success',
                'final_status': 'completed',
                'result_summary': 'Success.',
                'updated_at': '2026-04-11T12:01:05+00:00',
                'final_output': {
                    'output_key': 'contract_review_result',
                    'value_preview': contract_review_value,
                    'value_type': 'contract_review',
                },
            }
        }
    )

    dashboard = client.get('/app/workspaces?app_language=en', headers=_session_headers())
    assert dashboard.status_code == 200
    assert 'use_case=contract_review' in dashboard.text

    upload = client.get('/app/workspaces/ws-001/upload?app_language=en&use_case=contract_review', headers=_session_headers())
    assert upload.status_code == 200
    assert 'contract-review-upload-readiness' in upload.text
    assert 'data-required-upload-state="safe"' in upload.text

    run = client.get(
        '/app/workspaces/ws-001/run?app_language=en&use_case=contract_review&upload_id=upload-001&upload_status=safe&extraction_id=extract-001',
        headers=_session_headers(),
    )
    assert run.status_code == 200
    assert 'contract-review-run-input-handoff' in run.text
    assert 'data-ready-for-run="true"' in run.text
    assert 'web_contract_review_slice' in run.text

    result_api = client.get('/api/workspaces/ws-001/result-history?run_id=run-002', headers=_session_headers())
    assert result_api.status_code == 200
    result_payload = result_api.json()
    selected = result_payload['selected_result']
    assert selected['contract_review_result']['render_kind'] == 'contract_review_structured'
    assert selected['contract_review_result']['document_reference']['upload_id'] == 'upload-001'
    assert selected['contract_review_result']['clauses'][0]['source_reference']['mode'] == 'character_offsets'

    result_page = client.get('/app/workspaces/ws-001/results?run_id=run-002', headers=_session_headers())
    assert result_page.status_code == 200
    assert 'contract-review-structured-result' in result_page.text
    assert 'contract-review-next-actions' in result_page.text
    assert 'id="copy_contract_review_result"' in result_page.text
    assert 'id="continue_from_contract_review_result"' in result_page.text
    assert 'return_use=contract_review_result' in result_page.text
    assert 'id="ask_pre_signature_question_1"' in result_page.text
    assert 'return_use=contract_review_question' in result_page.text


def test_fastapi_binding_applies_security_headers_by_default() -> None:
    client = _make_client()
    response = client.get("/app/workspaces", headers=_session_headers())

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "camera=()" in response.headers["permissions-policy"]


def test_fastapi_binding_uses_explicit_cors_origin_policy() -> None:
    config = FastApiBindingConfig(cors_allowed_origins=("https://app.nexa.example",))
    client = _make_client(fastapi_config=config)

    allowed = client.get(
        "/api/workspaces",
        headers={**_session_headers(), "Origin": "https://app.nexa.example"},
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.nexa.example"
    assert allowed.headers["vary"] == "Origin"

    disallowed = client.get(
        "/api/workspaces",
        headers={**_session_headers(), "Origin": "https://evil.example"},
    )
    assert disallowed.status_code == 200
    assert "access-control-allow-origin" not in disallowed.headers

    preflight = client.options(
        "/api/runs",
        headers={
            "Origin": "https://app.nexa.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-nexa-session-claims",
        },
    )
    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == "https://app.nexa.example"
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "x-nexa-session-claims" in preflight.headers["access-control-allow-headers"]


def test_fastapi_binding_rate_limits_sensitive_run_endpoint_without_echoing_payload() -> None:
    config = FastApiBindingConfig(
        rate_limit_enabled=True,
        rate_limit_requests_per_window=2,
        rate_limit_window_seconds=60,
        rate_limit_path_prefixes=("/api/runs",),
    )
    client = _make_client(fastapi_config=config)
    request_body = {
        "workspace_id": "ws-001",
        "execution_target": {"target_type": "approved_snapshot", "target_ref": "snap-001"},
        "input_payload": {"question": "sensitive contract text should not be echoed"},
    }

    first = client.post("/api/runs", headers=_session_headers(), json=request_body)
    second = client.post("/api/runs", headers=_session_headers(), json=request_body)
    third = client.post("/api/runs", headers=_session_headers(), json=request_body)

    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    payload = third.json()
    assert payload == {"status": "rate_limited", "reason": "edge_rate_limit_exceeded"}
    assert "retry-after" in third.headers
    assert "sensitive contract text" not in third.text
    assert third.headers["x-content-type-options"] == "nosniff"


def test_fastapi_binding_emits_privacy_safe_edge_request_observation() -> None:
    events: list[dict] = []
    client = _make_client(edge_observation_writer=events.append)

    response = client.get(
        "/app/workspaces?token=sk-query-secret&safe=value",
        headers={
            **_session_headers(),
            "authorization": "Bearer sk-header-secret",
            "cookie": "session=secret-cookie",
            "x-nexa-request-id": "req-observe-001",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-nexa-request-id"] == "req-observe-001"
    completed = [event for event in events if event.get("event_type") == "edge.http_request_completed"]
    assert completed
    event = completed[-1]
    assert event["status_code"] == 200
    assert event["request"]["method"] == "GET"
    assert event["request"]["path"] == "/app/workspaces"
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-query-secret" not in event_text
    assert "sk-header-secret" not in event_text
    assert "secret-cookie" not in event_text
    assert event["request"]["query_params"]["token"] == "<redacted>"
    assert event["request"]["headers"]["authorization"] == "<redacted>"
    assert event["request"]["headers"]["cookie"] == "<redacted>"


def test_fastapi_binding_captures_edge_exception_without_leaking_sensitive_data() -> None:
    events: list[dict] = []
    client = _make_client(edge_observation_writer=events.append)

    @client.app.get("/test/edge-observability/boom")
    async def _boom():
        raise RuntimeError("provider secret sk-runtime-secret should not leak")

    response = client.get(
        "/test/edge-observability/boom?api_key=sk-query-secret",
        headers={
            **_session_headers(),
            "authorization": "Bearer sk-header-secret",
            "x-nexa-request-id": "req-exception-001",
        },
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        "status": "error",
        "reason": "edge_exception_captured",
        "request_id": "req-exception-001",
    }
    exception_events = [event for event in events if event.get("event_type") == "edge.http_exception_captured"]
    assert exception_events
    event = exception_events[-1]
    assert event["error_type"] == "RuntimeError"
    assert event["reason"] == "edge_exception_captured"
    event_text = json.dumps(event, sort_keys=True)
    assert "sk-runtime-secret" not in event_text
    assert "sk-query-secret" not in event_text
    assert "sk-header-secret" not in event_text
    assert event["request"]["query_params"]["api_key"] == "<redacted>"
    assert event["request"]["headers"]["authorization"] == "<redacted>"
