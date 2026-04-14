from __future__ import annotations

import json

from src.server import (
    EngineLaunchAdapter,
    EngineResultEnvelope,
    EngineRunStatusSnapshot,
    EngineSignal,
    EngineValidationFinding,
    ExecutionTargetCatalogEntry,
    HttpRouteRequest,
    ProductAdmissionPolicy,
    RunAuthorizationContext,
    RunHttpRouteSurface,
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


def _auth_request(*, method: str, path: str, path_params: dict | None = None, json_body=None, user_id: str = "user-owner") -> HttpRouteRequest:
    return HttpRouteRequest(
        method=method,
        path=path,
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-1"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        path_params=path_params or {},
        json_body=json_body,
    )




def test_http_route_definitions_are_unique() -> None:
    definitions = RunHttpRouteSurface.route_definitions()
    route_names = [route_name for route_name, _method, _path in definitions]

    assert len(route_names) == len(set(route_names))
    assert len(definitions) == len(set(definitions))




def test_circuit_library_route_returns_registry_backed_return_use_payload() -> None:
    response = RunHttpRouteSurface.handle_circuit_library(
        http_request=_auth_request(method="GET", path="/api/workspaces/library"),
        workspace_rows=({
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
            "last_run_id": "run-001",
            "last_result_status": "completed",
            "continuity_source": "server",
            "archived": False,
        },),
        membership_rows=(),
        recent_run_rows=(_run_row(status="completed", status_family="terminal_success"),),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["library"]["returned_count"] == 1
    assert response.body["library"]["items"][0]["has_recent_result_history"] is True
    assert response.body["item_sections"][0]["continue_href"] == "/app/workspaces/ws-001"


def test_circuit_library_route_requires_authentication() -> None:
    response = RunHttpRouteSurface.handle_circuit_library(
        http_request=HttpRouteRequest(method="GET", path="/api/workspaces/library"),
        workspace_rows=(),
        membership_rows=(),
        recent_run_rows=(),
    )

    assert response.status_code == 401
    assert response.body["reason_code"] == "circuit_library.authentication_required"

def test_launch_route_returns_accepted_http_response() -> None:
    response = RunHttpRouteSurface.handle_launch(
        http_request=_auth_request(
            method="POST",
            path="/api/runs",
            json_body={
                "workspace_id": "ws-001",
                "execution_target": {"target_type": "approved_snapshot", "target_ref": "snap-001"},
                "input_payload": {"question": "hello"},
                "client_context": {"source": "web", "request_id": "req-client-1"},
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

    assert response.status_code == 202
    assert response.body["status"] == "accepted"
    assert response.body["run_id"] == "run-001"
    assert response.body["links"]["run_status"] == "/api/runs/run-001"
    assert response.body["source_artifact"]["storage_role"] == "commit_snapshot"
    assert response.body["source_artifact"]["canonical_ref"] == "snap-001"


def test_launch_route_returns_engine_rejection_with_distinct_http_shape() -> None:
    def _engine_reject(_request):
        return EngineLaunchAdapter.rejected(
            findings=[
                EngineValidationFinding(
                    code="VAL_BLOCK",
                    category="structural",
                    severity="high",
                    blocking=True,
                    message="Entry missing",
                    location="circuit.entry",
                )
            ],
            engine_error_code="engine.validation.blocked",
            engine_message="Engine refused launch",
        )

    response = RunHttpRouteSurface.handle_launch(
        http_request=_auth_request(
            method="POST",
            path="/api/runs",
            json_body={
                "workspace_id": "ws-001",
                "execution_target": {"target_type": "approved_snapshot", "target_ref": "snap-001"},
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
        engine_launch_decider=_engine_reject,
    )

    assert response.status_code == 409
    assert response.body["status"] == "rejected_by_engine"
    assert response.body["error_family"] == "engine_launch_rejection"
    assert response.body["engine_error_code"] == "engine.validation.blocked"


def test_launch_route_rejects_invalid_body_before_admission() -> None:
    response = RunHttpRouteSurface.handle_launch(
        http_request=_auth_request(method="POST", path="/api/runs", json_body={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        target_catalog={},
    )

    assert response.status_code == 400
    assert response.body["status"] == "rejected"
    assert response.body["error_family"] == "product_rejection"


def test_status_route_returns_status_projection() -> None:
    response = RunHttpRouteSurface.handle_run_status(
        http_request=_auth_request(method="GET", path="/api/runs/run-001", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        run_record_row=_run_row(status="running", status_family="active"),
        engine_status=EngineRunStatusSnapshot(
            run_id="run-001",
            status="running",
            active_node_id="review_bundle",
            active_node_label="Review Bundle",
            progress_percent=42,
            progress_summary="Running review stage",
            latest_signal=EngineSignal(severity="info", code="NODE_RUNNING", message="Review Bundle is currently executing."),
            trace_ref="trace://run-001",
            artifact_count=0,
        ),
    )

    assert response.status_code == 200
    assert response.body["status"] == "running"
    assert response.body["progress"]["percent"] == 42
    assert response.body["links"]["result"] == "/api/runs/run-001/result"


def test_status_route_returns_unauthorized_when_identity_missing() -> None:
    request = HttpRouteRequest(method="GET", path="/api/runs/run-001", path_params={"run_id": "run-001"}, headers={})
    response = RunHttpRouteSurface.handle_run_status(
        http_request=request,
        run_context=_run_context(),
        run_record_row=_run_row(),
    )

    assert response.status_code == 401
    assert response.body["failure_family"] == "product_read_failure"


def test_result_route_returns_not_ready_projection() -> None:
    response = RunHttpRouteSurface.handle_run_result(
        http_request=_auth_request(method="GET", path="/api/runs/run-001/result", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        run_record_row=_run_row(status="running", status_family="active"),
        result_row=None,
    )

    assert response.status_code == 200
    assert response.body["result_state"] == "not_ready"
    assert response.body["message"] == "The run result is not available yet."


def test_result_route_can_project_ready_failure_from_engine_result() -> None:
    response = RunHttpRouteSurface.handle_run_result(
        http_request=_auth_request(method="GET", path="/api/runs/run-001/result", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        run_record_row=_run_row(status="failed", status_family="terminal_failure"),
        engine_result=EngineResultEnvelope(
            run_id="run-001",
            final_status="failed",
            result_state="ready_failure",
            result_summary="Final node failed.",
            trace_ref="trace://run-001",
            metrics={"duration_ms": 2000},
            failure_info=None,
        ),
    )

    assert response.status_code == 200
    assert response.body["result_state"] == "ready_failure"
    assert response.body["final_status"] == "failed"
    assert response.body["result_summary"]["title"] == "Run failed"


def test_workspace_result_history_route_returns_beginner_facing_result_cards() -> None:
    response = RunHttpRouteSurface.handle_workspace_result_history(
        http_request=_auth_request(method="GET", path="/api/workspaces/ws-001/result-history", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "owner_user_id": "user-owner", "title": "Primary Workspace", "created_at": "2026-04-11T12:00:00+00:00", "updated_at": "2026-04-11T12:05:00+00:00", "archived": False},
        run_rows=({**_run_row(status="completed", status_family="terminal_success"), "run_id": "run-002", "updated_at": "2026-04-11T12:01:00+00:00", "finished_at": "2026-04-11T12:01:00+00:00"},),
        result_rows_by_run_id={"run-002": {"run_id": "run-002", "workspace_id": "ws-001", "result_state": "ready_success", "final_status": "completed", "result_summary": "Success.", "final_output": {"output_key": "answer", "value_preview": "Latest Hello", "value_type": "string"}}},
        artifact_rows_lookup=lambda _run_id: (),
        recent_run_rows=(), provider_binding_rows=(), managed_secret_rows=(), provider_probe_rows=(), onboarding_rows=(),
    )
    assert response.status_code == 200
    assert response.body["result_history"]["returned_count"] == 1
    assert response.body["result_history"]["items"][0]["output_preview"] == "Latest Hello"


def test_http_route_surface_workspace_feedback_read_and_submit_round_trip() -> None:
    feedback_rows = [
        {
            "feedback_id": "fb-001",
            "user_id": "user-owner",
            "workspace_id": "ws-001",
            "workspace_title": "Primary Workspace",
            "category": "friction_note",
            "surface": "circuit_library",
            "message": "The library did not make the next step obvious.",
            "status": "received",
            "created_at": "2026-04-14T08:00:00+00:00",
        },
    ]
    get_response = RunHttpRouteSurface.handle_workspace_feedback(
        http_request=HttpRouteRequest(method="GET", path="/api/workspaces/ws-001/feedback", headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-1"}, session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]}, path_params={"workspace_id": "ws-001"}, query_params={"surface": "result_history", "run_id": "run-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_rows=feedback_rows,
    )
    assert get_response.status_code == 200
    payload = get_response.body
    assert payload["feedback_channel"]["submit_path"] == "/api/workspaces/ws-001/feedback"
    assert payload["feedback_channel"]["items"][0]["feedback_id"] == "fb-001"

    written = {}
    post_response = RunHttpRouteSurface.handle_submit_workspace_feedback(
        http_request=_auth_request(method="POST", path="/api/workspaces/ws-001/feedback", path_params={"workspace_id": "ws-001"}, json_body={"category": "bug_report", "surface": "result_history", "message": "This screen failed unexpectedly.", "run_id": "run-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_writer=lambda row: written.setdefault("row", dict(row)),
        feedback_id_factory=lambda: "fb-002",
        now_iso="2026-04-14T08:10:00+00:00",
    )
    assert post_response.status_code == 202
    submit_payload = post_response.body
    assert submit_payload["feedback"]["feedback_id"] == "fb-002"
    assert written["row"]["surface"] == "result_history"


def test_http_route_surface_workspace_feedback_rejects_empty_message() -> None:
    response = RunHttpRouteSurface.handle_submit_workspace_feedback(
        http_request=_auth_request(method="POST", path="/api/workspaces/ws-001/feedback", path_params={"workspace_id": "ws-001"}, json_body={"category": "bug_report", "surface": "result_history", "message": "   "}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_writer=lambda row: row,
        feedback_id_factory=lambda: "fb-003",
        now_iso="2026-04-14T08:10:00+00:00",
    )
    assert response.status_code == 400
    payload = response.body
    assert payload["reason_code"] == "workspace_feedback.message_missing"


def test_commit_workspace_shell_route_persists_commit_snapshot() -> None:
    artifact_store = {
        'ws-001': {
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
            "circuit": {"nodes": [{"id": "n1", "type": "plugin", "plugin_ref": "plugin.main", "inputs": {}, "outputs": {"result": "output.value"}}], "edges": [], "entry": "n1", "outputs": [{"name": "result", "node_id": "n1", "path": "output.value"}]},
            "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.main": {"entrypoint": "demo.main"}}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        }
    }
    response = RunHttpRouteSurface.handle_commit_workspace_shell(
        http_request=_auth_request(method='POST', path='/api/workspaces/ws-001/shell/commit', path_params={'workspace_id': 'ws-001'}, json_body={'commit_id': 'commit-http-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    assert response.status_code == 200
    assert artifact_store['ws-001']['meta']['storage_role'] == 'commit_snapshot'
    assert artifact_store['ws-001']['meta']['commit_id'] == 'commit-http-001'
    assert response.body['storage_role'] == 'commit_snapshot'
    assert response.body['transition']['action'] == 'commit_workspace_shell'


def test_checkout_workspace_shell_route_restores_working_save() -> None:
    artifact_store = {'ws-001': _commit_snapshot('snap-http-001')}
    response = RunHttpRouteSurface.handle_checkout_workspace_shell(
        http_request=_auth_request(method='POST', path='/api/workspaces/ws-001/shell/checkout', path_params={'workspace_id': 'ws-001'}, json_body={'working_save_id': 'ws-http-restored'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    assert response.status_code == 200
    assert artifact_store['ws-001']['meta']['storage_role'] == 'working_save'
    assert artifact_store['ws-001']['meta']['working_save_id'] == 'ws-http-restored'
    assert response.body['storage_role'] == 'working_save'
    assert response.body['transition']['action'] == 'checkout_workspace_shell'


def test_launch_workspace_shell_route_uses_current_public_working_save() -> None:
    response = RunHttpRouteSurface.handle_launch_workspace_shell(
        http_request=_auth_request(method='POST', path='/api/workspaces/ws-001/shell/launch', path_params={'workspace_id': 'ws-001'}, json_body={'input_payload': {'question': 'hello from shell'}}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source={
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-shell-launch", "name": "Primary Workspace"},
            "circuit": {"nodes": [{"id": "n1", "type": "plugin", "plugin_ref": "plugin.main", "inputs": {}, "outputs": {"result": "output.value"}}], "edges": [], "entry": "n1", "outputs": [{"name": "result", "node_id": "n1", "path": "output.value"}]},
            "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.main": {"entrypoint": "demo.main"}}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        },
        run_id_factory=lambda: 'run-shell-001',
        run_request_id_factory=lambda: 'req-shell-001',
        now_iso='2026-04-14T09:00:00+00:00',
    )
    assert response.status_code == 202
    assert response.body['status'] == 'accepted'
    assert response.body['run_id'] == 'run-shell-001'
    assert response.body['execution_target']['target_type'] == 'working_save'
    assert response.body['execution_target']['target_ref'] == 'ws-shell-launch'
    assert response.body['launch_context']['action'] == 'launch_workspace_shell'
    assert response.body['source_artifact']['storage_role'] == 'working_save'
    assert response.body['source_artifact']['canonical_ref'] == 'ws-shell-launch'


def test_launch_workspace_shell_route_uses_current_public_commit_snapshot() -> None:
    response = RunHttpRouteSurface.handle_launch_workspace_shell(
        http_request=_auth_request(method='POST', path='/api/workspaces/ws-001/shell/launch', path_params={'workspace_id': 'ws-001'}, json_body={'input_payload': {'question': 'hello from snapshot'}}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=_commit_snapshot('snap-shell-launch-001'),
        run_id_factory=lambda: 'run-shell-002',
        run_request_id_factory=lambda: 'req-shell-002',
        now_iso='2026-04-14T09:01:00+00:00',
    )
    assert response.status_code == 202
    assert response.body['status'] == 'accepted'
    assert response.body['execution_target']['target_type'] == 'commit_snapshot'
    assert response.body['execution_target']['target_ref'] == 'snap-shell-launch-001'
    assert response.body['launch_context']['storage_role'] == 'commit_snapshot'
    assert response.body['source_artifact']['storage_role'] == 'commit_snapshot'
    assert response.body['source_artifact']['canonical_ref'] == 'snap-shell-launch-001'


def test_workspace_shell_draft_route_rejects_commit_snapshot_source() -> None:
    artifact_store = {'ws-001': _commit_snapshot('snap-http-draft-001')}
    response = RunHttpRouteSurface.handle_put_workspace_shell_draft(
        http_request=_auth_request(method='PUT', path='/api/workspaces/ws-001/shell/draft', path_params={'workspace_id': 'ws-001'}, json_body={'request_text': 'Revise this snapshot.'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    assert response.status_code == 409
    assert response.body['reason_code'] == 'workspace_shell.draft_requires_working_save'
    assert artifact_store['ws-001']['meta']['storage_role'] == 'commit_snapshot'


def test_workspace_shell_payload_exposes_role_aware_action_availability() -> None:
    payload = RunHttpRouteSurface.handle_workspace_shell(
        http_request=_auth_request(method='GET', path='/api/workspaces/ws-001/shell', path_params={'workspace_id': 'ws-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=_commit_snapshot('snap-http-actions-001'),
    ).body
    assert payload['storage_role'] == 'commit_snapshot'
    assert payload['action_availability']['draft_write']['allowed'] is False
    assert payload['action_availability']['checkout']['allowed'] is True
    assert payload['action_availability']['launch']['allowed'] is True
