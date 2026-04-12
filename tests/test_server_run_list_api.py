from __future__ import annotations

from src.server import (
    RequestAuthResolver,
    RunListReadService,
    WorkspaceAuthorizationContext,
)


def _workspace() -> WorkspaceAuthorizationContext:
    return WorkspaceAuthorizationContext(
        workspace_id="ws-001",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-collab",),
        viewer_user_refs=("user-viewer",),
    )


def _auth(user_id: str = "user-owner"):
    return RequestAuthResolver.resolve(
        headers={"Authorization": "Bearer token"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
    )


def _run_row(run_id: str, created_at: str, *, status: str = "running", status_family: str = "active", requested_by_user_id: str = "user-owner") -> dict:
    return {
        "run_id": run_id,
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": f"snap-{run_id}",
        "status": status,
        "status_family": status_family,
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": created_at,
        "finished_at": None,
        "requested_by_user_id": requested_by_user_id,
        "trace_available": status != "queued",
        "artifact_count": 1,
    }


def test_run_list_returns_sorted_paginated_workspace_runs() -> None:
    outcome = RunListReadService.list_workspace_runs(
        request_auth=_auth(),
        workspace_context=_workspace(),
        run_rows=(
            _run_row("run-001", "2026-04-11T12:00:00+00:00"),
            _run_row("run-002", "2026-04-11T12:01:00+00:00", status="completed", status_family="terminal_success"),
            _run_row("run-003", "2026-04-11T12:02:00+00:00", status="queued", status_family="pending"),
        ),
        result_rows_by_run_id={"run-002": {"final_status": "completed", "result_state": "ready_success", "result_summary": "Success."}},
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        recent_run_rows=(
            _run_row("run-003", "2026-04-11T12:02:00+00:00", status="queued", status_family="pending"),
        ),
        provider_binding_rows=({"workspace_id": "ws-001", "binding_id": "binding-001", "updated_at": "2026-04-11T12:03:00+00:00"},),
        managed_secret_rows=({"workspace_id": "ws-001", "secret_ref": "secret://ws-001/openai", "last_rotated_at": "2026-04-11T12:04:00+00:00"},),
        provider_probe_rows=({"workspace_id": "ws-001", "probe_event_id": "probe-001", "provider_key": "openai", "provider_family": "openai", "display_name": "OpenAI", "probe_status": "reachable", "connectivity_state": "ok", "occurred_at": "2026-04-11T12:05:00+00:00"},),
        onboarding_rows=({"workspace_id": "ws-001", "user_id": "user-owner", "onboarding_state_id": "onboard-001", "updated_at": "2026-04-11T12:06:00+00:00"},),
        limit=2,
    )

    assert outcome.ok is True
    response = outcome.response
    assert response is not None
    assert [item.run_id for item in response.runs] == ["run-003", "run-002"]
    assert response.next_cursor == "run-002"
    assert response.total_visible_count == 3
    assert response.workspace_title == "Primary Workspace"
    assert response.provider_continuity is not None
    assert response.provider_continuity.provider_binding_count == 1
    assert response.provider_continuity.managed_secret_count == 1
    assert response.activity_continuity is not None
    assert response.activity_continuity.recent_onboarding_count == 1
    assert response.runs[1].result_state == "ready_success"
    assert response.runs[1].result_summary is not None
    assert response.runs[1].links.status == "/api/runs/run-002"


def test_run_list_applies_filters_and_cursor() -> None:
    rows = (
        _run_row("run-001", "2026-04-11T12:00:00+00:00", status="queued", status_family="pending", requested_by_user_id="user-a"),
        _run_row("run-002", "2026-04-11T12:01:00+00:00", status="completed", status_family="terminal_success", requested_by_user_id="user-b"),
        _run_row("run-003", "2026-04-11T12:02:00+00:00", status="completed", status_family="terminal_success", requested_by_user_id="user-b"),
    )
    first_page = RunListReadService.list_workspace_runs(
        request_auth=_auth(),
        workspace_context=_workspace(),
        run_rows=rows,
        limit=1,
        status_family="terminal_success",
        requested_by_user_id="user-b",
    )
    assert first_page.ok is True
    assert first_page.response is not None
    assert [item.run_id for item in first_page.response.runs] == ["run-003"]
    assert first_page.response.next_cursor == "run-003"

    second_page = RunListReadService.list_workspace_runs(
        request_auth=_auth(),
        workspace_context=_workspace(),
        run_rows=rows,
        limit=1,
        status_family="terminal_success",
        requested_by_user_id="user-b",
        cursor=first_page.response.next_cursor,
    )
    assert second_page.ok is True
    assert second_page.response is not None
    assert [item.run_id for item in second_page.response.runs] == ["run-002"]
    assert second_page.response.next_cursor is None


def test_run_list_rejects_invalid_cursor_and_missing_auth() -> None:
    invalid_cursor = RunListReadService.list_workspace_runs(
        request_auth=_auth(),
        workspace_context=_workspace(),
        run_rows=(_run_row("run-001", "2026-04-11T12:00:00+00:00"),),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace"},
        provider_binding_rows=({"workspace_id": "ws-001", "binding_id": "binding-001", "updated_at": "2026-04-11T12:03:00+00:00"},),
        managed_secret_rows=({"workspace_id": "ws-001", "secret_ref": "secret://ws-001/openai", "last_rotated_at": "2026-04-11T12:04:00+00:00"},),
        provider_probe_rows=({"workspace_id": "ws-001", "probe_event_id": "probe-001", "provider_key": "openai", "provider_family": "openai", "display_name": "OpenAI", "probe_status": "reachable", "connectivity_state": "ok", "occurred_at": "2026-04-11T12:05:00+00:00"},),
        onboarding_rows=({"workspace_id": "ws-001", "user_id": "user-owner", "onboarding_state_id": "onboard-001", "updated_at": "2026-04-11T12:06:00+00:00"},),
        cursor="run-999",
    )
    assert invalid_cursor.ok is False
    assert invalid_cursor.rejected is not None
    assert invalid_cursor.rejected.reason_code == "run_list.cursor_invalid"
    assert invalid_cursor.rejected.workspace_title == "Primary Workspace"
    assert invalid_cursor.rejected.provider_continuity is not None
    assert invalid_cursor.rejected.activity_continuity is not None

    anonymous = RequestAuthResolver.resolve(headers={}, session_claims=None)
    auth_required = RunListReadService.list_workspace_runs(
        request_auth=anonymous,
        workspace_context=_workspace(),
        run_rows=(_run_row("run-001", "2026-04-11T12:00:00+00:00"),),
    )
    assert auth_required.ok is False
    assert auth_required.rejected is not None
    assert auth_required.rejected.reason_code == "run_list.authentication_required"
