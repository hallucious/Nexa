from __future__ import annotations

import json

from src.server import (
    EngineResultEnvelope,
    EngineRunStatusSnapshot,
    EngineArtifactReference,
    EngineFinalOutput,
    EngineSignal,
    ExecutionTargetCatalogEntry,
    FrameworkInboundRequest,
    FrameworkRouteBindings,
    RunAuthorizationContext,
    WorkspaceAuthorizationContext,
)


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _run_context(*, owner: str = "user-owner") -> RunAuthorizationContext:
    return RunAuthorizationContext(
        run_id="run-001",
        workspace_context=_workspace(),
        run_owner_user_ref=owner,
    )


def _commit_snapshot(ref: str = "snap-001") -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "commit_snapshot",
            "commit_id": ref,
        },
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "validation": {"validation_result": "passed", "summary": {}},
        "approval": {"approval_completed": True, "approval_status": "approved", "summary": {}},
        "lineage": {"parent_commit_id": None, "metadata": {}},
    }


def _run_row(*, status: str = "running", status_family: str = "active") -> dict:
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": status,
        "status_family": status_family,
        "created_at": "2026-04-11T12:00:00+00:00",
        "started_at": "2026-04-11T12:00:05+00:00",
        "updated_at": "2026-04-11T12:00:10+00:00",
        "finished_at": None,
        "requested_by_user_id": "user-owner",
        "trace_available": False,
    }


def _probe_row(*, probe_event_id: str = "probe-001", occurred_at: str = "2026-04-11T12:00:20+00:00", probe_status: str = "reachable") -> dict:
    return {
        "probe_event_id": probe_event_id,
        "workspace_id": "ws-001",
        "provider_key": "openai",
        "provider_family": "openai",
        "display_name": "OpenAI GPT",
        "probe_status": probe_status,
        "connectivity_state": "ok" if probe_status == "reachable" else "provider_error",
        "secret_resolution_status": "resolved",
        "requested_model_ref": "gpt-4.1",
        "effective_model_ref": "gpt-4.1",
        "occurred_at": occurred_at,
        "requested_by_user_id": "user-owner",
        "message": "Probe completed.",
    }


def _request(*, method: str, path: str, path_params: dict | None = None, query_params: dict | None = None, json_body=None, user_id: str = "user-owner") -> FrameworkInboundRequest:
    return FrameworkInboundRequest(
        method=method,
        path=path,
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-framework-1"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        path_params=path_params or {},
        query_params=query_params or {},
        json_body=json_body,
    )


def test_framework_binding_exposes_expected_route_definitions() -> None:
    definitions = FrameworkRouteBindings.route_definitions()
    assert [d.route_name for d in definitions] == [
        "get_recent_activity",
        "get_history_summary",
        "list_workspaces",
        "get_workspace",
        "create_workspace",
        "get_provider_catalog",
        "list_workspace_provider_bindings",
        "put_workspace_provider_binding",
        "list_workspace_provider_health",
        "get_workspace_provider_health",
        "probe_workspace_provider",
        "list_provider_probe_history",
        "get_onboarding",
        "put_onboarding",
        "list_workspace_runs",
        "get_workspace_shell",
        "launch_run",
        "get_run_status",
        "get_run_result",
        "get_run_actions",
        "retry_run",
        "force_reset_run",
        "mark_run_reviewed",
        "list_run_artifacts",
        "get_artifact_detail",
        "get_run_trace",
    ]
    assert definitions[0].path_template == "/api/users/me/activity"
    assert any(item.path_template == "/api/runs/{run_id}/retry" for item in definitions)
    assert any(item.path_template == "/api/runs/{run_id}/force-reset" for item in definitions)
    assert any(item.path_template == "/api/runs/{run_id}/mark-reviewed" for item in definitions)
    assert any(item.path_template == "/api/runs/{run_id}/actions" for item in definitions)
    assert any(item.path_template == "/api/runs/{run_id}/trace" for item in definitions)




def test_framework_route_definitions_are_unique() -> None:
    definitions = FrameworkRouteBindings.route_definitions()
    route_names = [definition.route_name for definition in definitions]
    route_identities = [(definition.route_name, definition.method, definition.path_template) for definition in definitions]

    assert len(route_names) == len(set(route_names))
    assert len(route_identities) == len(set(route_identities))


def test_framework_binding_normalizes_request_to_http_route_request() -> None:
    http_request = FrameworkRouteBindings.to_http_route_request(
        _request(method="GET", path="/api/runs/run-001", path_params={"run_id": "run-001"}, query_params={"limit": 5})
    )

    assert http_request.method == "GET"
    assert http_request.path == "/api/runs/run-001"
    assert http_request.headers["Authorization"] == "Bearer token"
    assert http_request.path_params["run_id"] == "run-001"
    assert http_request.query_params["limit"] == 5


def test_framework_binding_serializes_http_response_into_json_text() -> None:
    response = FrameworkRouteBindings.handle_run_status(
        request=_request(method="GET", path="/api/runs/run-001", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        run_record_row=_run_row(),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="node-1",
            active_node_label="Node 1",
            progress_percent=20,
            progress_summary="Working",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Node 1 is executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert response.status_code == 200
    assert response.media_type == "application/json"
    parsed = json.loads(response.body_text)
    assert parsed["status"] == "running"
    assert parsed["progress"]["percent"] == 20


def test_framework_binding_handles_launch_round_trip() -> None:
    response = FrameworkRouteBindings.handle_launch(
        request=_request(
            method="POST",
            path="/api/runs",
            json_body={
                "workspace_id": "ws-001",
                "execution_target": {"target_type": "approved_snapshot", "target_ref": "snap-001"},
                "input_payload": {"question": "hello"},
            },
        ),
        workspace_context=_workspace(),
        target_catalog={
            "snap-001": ExecutionTargetCatalogEntry(
                workspace_id="ws-001",
                target_ref="snap-001",
                target_type="approved_snapshot",
                source=_commit_snapshot("snap-001"),
            )
        },
        run_id_factory=lambda: "run-001",
        now_iso="2026-04-11T12:00:00+00:00",
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 202
    assert parsed["status"] == "accepted"
    assert parsed["run_id"] == "run-001"
    assert parsed["workspace_title"] is None


def test_framework_binding_handles_result_route_round_trip() -> None:
    response = FrameworkRouteBindings.handle_run_result(
        request=_request(method="GET", path="/api/runs/run-001/result", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        run_record_row=_run_row(status="completed", status_family="terminal_success"),
        engine_result=EngineResultEnvelope(
            run_id="run-001",
            final_status="completed",
            result_state="ready_success",
            result_summary="Success.",
            trace_ref="trace://run-001",
            metrics={"duration_ms": 123},
            final_output=EngineFinalOutput(output_key="answer", value_preview="ok", value_type="string"),
            artifact_refs=(EngineArtifactReference(artifact_id="artifact-1", artifact_type="report", metadata={"label": "Primary artifact"}),),
            failure_info=None,
        ),
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed["result_state"] == "ready_success"
    assert parsed["final_output"]["output_key"] == "answer"
    assert parsed["final_output"]["value_preview"] == "ok"


def test_framework_binding_handles_workspace_run_list_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_workspace_runs(
        request=_request(
            method="GET",
            path="/api/workspaces/ws-001/runs",
            path_params={"workspace_id": "ws-001"},
            query_params={"limit": 2},
        ),
        workspace_context=_workspace(),
        run_rows=(
            _run_row(status="completed", status_family="terminal_success"),
            {**_run_row(), "run_id": "run-002", "created_at": "2026-04-11T12:01:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        ),
        result_rows_by_run_id={"run-001": {"final_status": "completed", "result_state": "ready_success", "result_summary": "Success."}},
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed["workspace_id"] == "ws-001"
    assert parsed["returned_count"] == 2
    assert parsed["runs"][0]["run_id"] == "run-002"


def test_framework_binding_handles_workspace_and_onboarding_round_trip() -> None:
    workspace_response = FrameworkRouteBindings.handle_list_workspaces(
        request=_request(method="GET", path="/api/workspaces"),
        workspace_rows=({
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "continuity_source": "server",
            "archived": False,
        },),
        membership_rows=(),
        recent_run_rows=(),
    )
    workspace_payload = json.loads(workspace_response.body_text)
    assert workspace_response.status_code == 200
    assert workspace_payload["returned_count"] == 1
    assert workspace_payload["workspaces"][0]["workspace_id"] == "ws-001"

    onboarding_response = FrameworkRouteBindings.handle_put_onboarding(
        request=_request(
            method="PUT",
            path="/api/users/me/onboarding",
            json_body={"first_success_achieved": True, "advanced_surfaces_unlocked": True},
        ),
        onboarding_rows=(),
        workspace_context=None,
        onboarding_state_id_factory=lambda: "onboard-001",
        now_iso="2026-04-11T12:10:00+00:00",
    )
    onboarding_payload = json.loads(onboarding_response.body_text)
    assert onboarding_response.status_code == 200
    assert onboarding_payload["state"]["first_success_achieved"] is True
    assert onboarding_payload["state"]["advanced_surfaces_unlocked"] is True


def test_framework_binding_handles_workspace_provider_health_round_trip() -> None:
    from src.server import AwsSecretsManagerBindingConfig, AwsSecretsManagerSecretAuthority

    class _FakeSecretsClient:
        def describe_secret(self, SecretId: str):
            return {"ARN": "arn:aws:secretsmanager:region:acct:secret:" + SecretId, "LastChangedDate": "2026-04-11T12:06:00+00:00"}

    response = FrameworkRouteBindings.handle_get_workspace_provider_health(
        request=_request(method="GET", path="/api/workspaces/ws-001/provider-bindings/openai/health", path_params={"workspace_id": "ws-001", "provider_key": "openai"}),
        workspace_context=_workspace(),
        binding_rows=({
            "binding_id": "binding-001",
            "workspace_id": "ws-001",
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "credential_source": "managed",
            "secret_ref": "aws-secretsmanager://nexa/ws-001/providers/openai",
            "enabled": True,
            "default_model_ref": "gpt-4.1",
            "allowed_model_refs": ("gpt-4.1",),
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
        },),
        provider_catalog_rows=({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
        },),
        secret_metadata_reader=AwsSecretsManagerSecretAuthority.build_secret_metadata_reader(client=_FakeSecretsClient(), config=AwsSecretsManagerBindingConfig()),
    )

    payload = json.loads(response.body_text)
    assert response.status_code == 200
    assert payload['health']['health_status'] == 'healthy'
    assert payload['provider_continuity'] is None or payload['provider_continuity']['provider_binding_count'] >= 1
    assert payload['health']['secret_resolution_status'] == 'resolved'


def test_framework_binding_handles_provider_catalog_and_workspace_provider_bindings_round_trip() -> None:
    catalog_response = FrameworkRouteBindings.handle_list_provider_catalog(
        request=_request(method="GET", path="/api/providers/catalog"),
        provider_catalog_rows=({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
            "local_env_var_hint": "OPENAI_API_KEY",
            "default_secret_name_template": "nexa/{workspace_id}/providers/openai",
        },),
    )
    catalog_payload = json.loads(catalog_response.body_text)
    assert catalog_response.status_code == 200
    assert catalog_payload["returned_count"] == 1
    assert catalog_payload["providers"][0]["provider_key"] == "openai"

    list_response = FrameworkRouteBindings.handle_list_workspace_provider_bindings(
        request=_request(method="GET", path="/api/workspaces/ws-001/provider-bindings", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        binding_rows=({
            "binding_id": "binding-001",
            "workspace_id": "ws-001",
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "credential_source": "managed",
            "secret_ref": "secret://ws-001/openai",
            "secret_version_ref": "v1",
            "enabled": True,
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "updated_by_user_id": "user-owner",
        },),
        provider_catalog_rows=({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
        },),
    )
    list_payload = json.loads(list_response.body_text)
    assert list_response.status_code == 200
    assert list_payload["returned_count"] == 1
    assert list_payload["bindings"][0]["status"] == "configured"

    put_response = FrameworkRouteBindings.handle_put_workspace_provider_binding(
        request=_request(
            method="PUT",
            path="/api/workspaces/ws-001/provider-bindings/openai",
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
            json_body={"display_name": "OpenAI GPT", "secret_value": "super-secret", "enabled": True},
        ),
        workspace_context=_workspace(),
        existing_binding_row=None,
        provider_catalog_rows=({
            "provider_key": "openai",
            "provider_family": "openai",
            "display_name": "OpenAI GPT",
            "managed_supported": True,
            "recommended_scope": "workspace",
        },),
        binding_id_factory=lambda: "binding-001",
        secret_writer=lambda workspace_id, provider_key, secret_value, metadata: {
            "secret_ref": f"secret://{workspace_id}/{provider_key}",
            "secret_version_ref": "v2",
            "last_rotated_at": "2026-04-11T12:06:00+00:00",
        },
        now_iso="2026-04-11T12:06:00+00:00",
    )
    put_payload = json.loads(put_response.body_text)
    assert put_response.status_code == 200
    assert put_payload["binding"]["provider_key"] == "openai"
    assert put_payload["binding"]["secret_ref"] == "secret://ws-001/openai"
    assert put_payload["secret_rotated"] is True
    assert "super-secret" not in put_response.body_text


def test_framework_binding_handles_provider_probe_history_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_provider_probe_history(
        request=_request(
            method="GET",
            path="/api/workspaces/ws-001/provider-bindings/openai/probe-history",
            path_params={"workspace_id": "ws-001", "provider_key": "openai"},
            query_params={"limit": 1},
        ),
        workspace_context=_workspace(),
        provider_key="openai",
        probe_history_rows=(
            _probe_row(probe_event_id="probe-001", occurred_at="2026-04-11T12:00:20+00:00"),
            _probe_row(probe_event_id="probe-002", occurred_at="2026-04-11T12:01:20+00:00"),
        ),
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed["returned_count"] == 1
    assert parsed["items"][0]["probe_event_id"] == "probe-002"


def test_framework_binding_workspace_shell_includes_latest_run_previews() -> None:
    response = FrameworkRouteBindings.handle_workspace_shell(
        request=_request(method="GET", path="/api/workspaces/ws-001/shell", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
        },
        recent_run_rows=(_run_row(status="completed", status_family="terminal_success"),),
        result_rows_by_run_id={"run-001": {"final_status": "completed", "result_state": "ready_success", "result_summary": "Success."}},
        artifact_rows_lookup=lambda run_id: ({
            "artifact_id": "artifact-1",
            "run_id": run_id,
            "workspace_id": "ws-001",
            "artifact_type": "report",
            "label": "Primary report",
            "payload_preview": "Hello",
        },) if run_id == "run-001" else (),
        trace_rows_lookup=lambda run_id: ({
            "trace_event_ref": "evt-1",
            "run_id": run_id,
            "sequence_number": 1,
            "event_type": "node.completed",
            "occurred_at": "2026-04-11T12:00:10+00:00",
            "node_id": "node-1",
            "message_preview": "Node completed",
        },) if run_id == "run-001" else (),
        artifact_source={
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US", "viewport_tier": "mobile"}},
        },
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed["latest_run_status_preview"]["run_id"] == "run-001"
    assert parsed["latest_run_result_preview"]["result_state"] == "ready_success"
    assert parsed["latest_run_trace_preview"]["event_count"] == 1
    assert parsed["latest_run_artifacts_preview"]["artifact_count"] == 1
    assert parsed["routes"]["latest_run_trace"] == "/api/runs/run-001/trace?limit=20"
    assert parsed["routes"]["latest_run_artifacts"] == "/api/runs/run-001/artifacts"
    assert parsed['latest_run_status_summary']['headline'] == 'Status: terminal_success'
    assert 'Run id: run-001' in parsed['latest_run_status_summary']['lines']
    assert parsed['latest_run_status_detail']['title'] == 'Status detail'
    assert 'Status: completed' in parsed['latest_run_status_detail']['items']
    assert parsed['latest_run_result_summary']['headline'] == 'Success.'
    assert parsed['latest_run_result_detail']['title'] == 'Result detail'
    assert 'Result state: ready_success' in parsed['latest_run_result_detail']['items']
    assert parsed['latest_run_trace_summary']['headline'] == 'Trace events: 1'
    assert 'Latest event: node.completed' in parsed['latest_run_trace_summary']['lines']
    assert parsed['latest_run_trace_detail']['title'] == 'Trace detail'
    assert 'Event count: 1' in parsed['latest_run_trace_detail']['items']
    assert parsed['latest_run_artifacts_summary']['headline'] == 'Artifacts: 1'
    assert 'First artifact id: artifact-1' in parsed['latest_run_artifacts_summary']['lines']
    assert parsed['latest_run_artifacts_detail']['title'] == 'Artifacts detail'
    assert 'Artifact count: 1' in parsed['latest_run_artifacts_detail']['items']
    assert parsed['navigation']['default_section'] == 'result'
    assert parsed['navigation']['default_level'] == 'detail'
    assert parsed['navigation']['guidance_label'] == 'Recommended next: Result'
    assert parsed['step_state_banner']['title'] == 'Step 5 of 5 — Read result'
    assert parsed['step_state_banner']['recommended_section'] == 'result'
    assert 'Result is ready.' in parsed['step_state_banner']['summary']
