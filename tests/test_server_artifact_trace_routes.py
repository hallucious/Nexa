from __future__ import annotations

from src.server import HttpRouteRequest, RunAuthorizationContext, RunHttpRouteSurface, WorkspaceAuthorizationContext


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


def _auth_request(*, method: str, path: str, path_params: dict | None = None, query_params: dict | None = None, user_id: str = "user-owner") -> HttpRouteRequest:
    return HttpRouteRequest(
        method=method,
        path=path,
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-2"},
        session_claims={"sub": user_id, "sid": "sess-002", "exp": 4102444800, "roles": ["editor"]},
        path_params=path_params or {},
        query_params=query_params or {},
    )


def _run_row(*, status: str = "completed") -> dict:
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": status,
        "status_family": "terminal_success",
        "created_at": "2026-04-11T12:00:00+00:00",
        "updated_at": "2026-04-11T12:10:00+00:00",
        "trace_available": True,
    }


def test_run_artifacts_route_returns_product_projection() -> None:
    response = RunHttpRouteSurface.handle_run_artifacts(
        http_request=_auth_request(method="GET", path="/api/runs/run-001/artifacts", path_params={"run_id": "run-001"}),
        run_context=_run_context(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=[_run_row()],
        provider_binding_rows=[{"workspace_id": "ws-001", "binding_id": "binding-001", "provider_key": "openai", "updated_at": "2026-04-11T12:05:00+00:00"}],
        artifact_rows=[
            {
                "artifact_id": "art-001",
                "run_id": "run-001",
                "workspace_id": "ws-001",
                "artifact_type": "final_output",
                "payload_preview": "Reviewed answer",
                "created_at": "2026-04-11T12:10:00+00:00",
                "metadata_json": {"label": "Reviewed answer", "value_type": "text"},
            }
        ],
    )

    assert response.status_code == 200
    assert response.body["artifact_count"] == 1
    assert response.body["workspace_title"] == "Primary Workspace"
    assert response.body["provider_continuity"]["provider_binding_count"] == 1
    assert response.body["activity_continuity"]["recent_run_count"] == 1
    assert response.body["artifacts"][0]["artifact_id"] == "art-001"


def test_artifact_detail_route_returns_reference_payload_access_when_storage_ref_exists() -> None:
    response = RunHttpRouteSurface.handle_artifact_detail(
        http_request=_auth_request(method="GET", path="/api/artifacts/art-001", path_params={"artifact_id": "art-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=[_run_row()],
        provider_binding_rows=[{"workspace_id": "ws-001", "binding_id": "binding-001", "provider_key": "openai", "updated_at": "2026-04-11T12:05:00+00:00"}],
        artifact_row={
            "artifact_id": "art-001",
            "run_id": "run-001",
            "workspace_id": "ws-001",
            "artifact_type": "final_output",
            "payload_preview": "Reviewed answer",
            "storage_ref": "blob://art-001",
            "metadata_json": {"label": "Reviewed answer", "value_type": "text"},
            "created_at": "2026-04-11T12:10:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.body["artifact_id"] == "art-001"
    assert response.body["workspace_title"] == "Primary Workspace"
    assert response.body["provider_continuity"]["provider_binding_count"] == 1
    assert response.body["activity_continuity"]["recent_run_count"] == 1
    assert response.body["payload_access"]["mode"] == "reference_only"
    assert response.body["payload_access"]["reference"] == "blob://art-001"


def test_run_trace_route_preserves_sequence_and_paginates() -> None:
    response = RunHttpRouteSurface.handle_run_trace(
        http_request=_auth_request(
            method="GET",
            path="/api/runs/run-001/trace",
            path_params={"run_id": "run-001"},
            query_params={"limit": "1", "cursor": "0"},
        ),
        run_context=_run_context(),
        run_record_row=_run_row(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=[_run_row()],
        provider_binding_rows=[{"workspace_id": "ws-001", "binding_id": "binding-001", "provider_key": "openai", "updated_at": "2026-04-11T12:05:00+00:00"}],
        trace_rows=[
            {
                "trace_event_ref": "evt-001",
                "workspace_id": "ws-001",
                "run_id": "run-001",
                "event_type": "run_started",
                "sequence_number": 0,
                "node_id": None,
                "severity": "info",
                "message_preview": "Run started.",
                "occurred_at": "2026-04-11T12:00:02+00:00",
            },
            {
                "trace_event_ref": "evt-002",
                "workspace_id": "ws-001",
                "run_id": "run-001",
                "event_type": "node_completed",
                "sequence_number": 1,
                "node_id": "review_bundle",
                "severity": "info",
                "message_preview": "Review bundle completed.",
                "occurred_at": "2026-04-11T12:00:05+00:00",
            },
        ],
    )

    assert response.status_code == 200
    assert response.body["workspace_id"] == "ws-001"
    assert response.body["workspace_title"] == "Primary Workspace"
    assert response.body["provider_continuity"]["provider_binding_count"] == 1
    assert response.body["activity_continuity"]["recent_run_count"] == 1
    assert response.body["event_count"] == 2
    assert response.body["events"][0]["event_id"] == "evt-001"
    assert response.body["next_cursor"] == "1"


def test_run_trace_route_requires_authentication() -> None:
    request = HttpRouteRequest(method="GET", path="/api/runs/run-001/trace", path_params={"run_id": "run-001"}, headers={})
    response = RunHttpRouteSurface.handle_run_trace(
        http_request=request,
        run_context=_run_context(),
        run_record_row=_run_row(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=[_run_row()],
        provider_binding_rows=[{"workspace_id": "ws-001", "binding_id": "binding-001", "provider_key": "openai", "updated_at": "2026-04-11T12:05:00+00:00"}],
        trace_rows=[],
    )

    assert response.status_code == 401
    assert response.body["failure_family"] == "product_read_failure"
    assert response.body["workspace_title"] == "Primary Workspace"
    assert response.body["provider_continuity"]["provider_binding_count"] == 1
