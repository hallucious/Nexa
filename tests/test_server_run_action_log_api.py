from __future__ import annotations

from src.server import (
    HttpRouteRequest,
    RequestAuthResolver,
    RunActionLogReadService,
    RunAuthorizationContext,
    RunHttpRouteSurface,
    WorkspaceAuthorizationContext,
    latest_action_from_run_record,
)


def _workspace_context() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        reviewer_user_refs=("user-reviewer",),
    )


def _run_context() -> RunAuthorizationContext:
    return RunAuthorizationContext(
        run_id="run-001",
        workspace_context=_workspace_context(),
        run_owner_user_ref="user-owner",
    )


def _auth(user_id: str = "user-owner", roles=("admin",)):
    return RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": list(roles)},
    )


def _run_row():
    return {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": "queued",
        "status_family": "pending",
        "created_at": "2026-04-13T00:00:00+00:00",
        "updated_at": "2026-04-13T01:00:00+00:00",
        "requested_by_user_id": "user-owner",
        "action_log": [
            {
                "event_id": "act-001",
                "action": "retry",
                "actor_user_id": "user-owner",
                "timestamp": "2026-04-13T01:00:00+00:00",
                "before_state": {"status": "failed", "worker_attempt_number": 1},
                "after_state": {"status": "queued", "worker_attempt_number": 2},
            }
        ],
    }


def test_latest_action_from_run_record_returns_summary() -> None:
    latest = latest_action_from_run_record(_run_row())
    assert latest is not None
    assert latest.action == "retry"
    assert latest.actor_user_id == "user-owner"


def test_run_action_log_read_service_returns_events() -> None:
    outcome = RunActionLogReadService.read_actions(
        request_auth=_auth(),
        run_context=_run_context(),
        run_record_row=_run_row(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
    )
    assert outcome.ok is True
    assert outcome.response is not None
    assert outcome.response.returned_count == 1
    assert outcome.response.actions[0].action == "retry"
    assert outcome.response.source_artifact is not None
    assert outcome.response.source_artifact["storage_role"] == "commit_snapshot"
    assert outcome.response.source_artifact["canonical_ref"] == "snap-001"


def test_run_http_route_surface_returns_action_log() -> None:
    response = RunHttpRouteSurface.handle_run_actions(
        http_request=HttpRouteRequest(
            method="GET",
            path="/api/runs/run-001/actions",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"run_id": "run-001"},
        ),
        run_context=_run_context(),
        run_record_row=_run_row(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
    )
    assert response.status_code == 200
    assert response.body["returned_count"] == 1
    assert response.body["actions"][0]["event_id"] == "act-001"
    assert response.body["source_artifact"]["storage_role"] == "commit_snapshot"
    assert response.body["source_artifact"]["canonical_ref"] == "snap-001"
