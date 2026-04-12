from __future__ import annotations

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
