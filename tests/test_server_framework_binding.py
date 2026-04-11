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
        "get_onboarding",
        "put_onboarding",
        "list_workspace_runs",
        "launch_run",
        "get_run_status",
        "get_run_result",
        "list_run_artifacts",
        "get_artifact_detail",
        "get_run_trace",
    ]
    assert definitions[0].path_template == "/api/users/me/activity"
    assert definitions[-1].path_template == "/api/runs/{run_id}/trace"


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


def test_framework_binding_handles_recent_activity_round_trip() -> None:
    activity_response = FrameworkRouteBindings.handle_recent_activity(
        request=_request(method="GET", path="/api/users/me/activity", query_params={"limit": 2}),
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
        run_rows=({**_run_row(status="completed", status_family="terminal_success"), "updated_at": "2026-04-11T12:06:00+00:00"},),
    )
    activity_payload = json.loads(activity_response.body_text)
    assert activity_response.status_code == 200
    assert activity_payload["returned_count"] == 2
    assert activity_payload["activities"][0]["activity_type"] == "run_completed"

    summary_response = FrameworkRouteBindings.handle_history_summary(
        request=_request(method="GET", path="/api/users/me/history-summary"),
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
        run_rows=({**_run_row(status="completed", status_family="terminal_success"), "updated_at": "2026-04-11T12:06:00+00:00"},),
    )
    summary_payload = json.loads(summary_response.body_text)
    assert summary_response.status_code == 200
    assert summary_payload["total_visible_runs"] == 1
    assert summary_payload["terminal_success_runs"] == 1
