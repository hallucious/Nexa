from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from src.server import (
    FastApiBindingConfig,
    FastApiRouteBindings,
    FastApiRouteDependencies,
    HttpRouteRequest,
    RequestAuthResolver,
    RunAuthorizationContext,
    RunControlService,
    RunHttpRouteSurface,
    WorkspaceAuthorizationContext,
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


def _run_row(**overrides):
    row = {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "execution_target_type": "commit_snapshot",
        "execution_target_ref": "snap-001",
        "status": "failed",
        "status_family": "terminal_failure",
        "created_at": "2026-04-13T00:00:00+00:00",
        "updated_at": "2026-04-13T00:00:00+00:00",
        "requested_by_user_id": "user-owner",
        "queue_job_id": "job-001",
        "worker_attempt_number": 1,
        "latest_error_family": "worker_infrastructure_failure",
        "orphan_review_required": False,
        "claimed_by_worker_ref": None,
        "lease_expires_at": None,
    }
    row.update(overrides)
    return row


def test_run_control_service_retry_requeues_and_increments_attempt() -> None:
    written = {}

    def writer(row):
        written.update(row)
        return row

    outcome = RunControlService.apply_action(
        action="retry",
        request_auth=_auth(),
        run_context=_run_context(),
        run_record_row=_run_row(),
        run_record_writer=writer,
        now_iso_factory=lambda: "2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-002",
    )

    assert outcome.ok is True
    assert outcome.accepted is not None
    assert outcome.accepted.status == "queued"
    assert outcome.accepted.status_family == "pending"
    assert outcome.accepted.queue_job_id == "job-002"
    assert outcome.accepted.worker_attempt_number == 2
    assert outcome.accepted.actions is not None
    assert outcome.accepted.actions.can_retry is True
    assert outcome.accepted.source_artifact is not None
    assert outcome.accepted.source_artifact.storage_role == "commit_snapshot"
    assert outcome.accepted.source_artifact.canonical_ref == "snap-001"
    assert written["queue_job_id"] == "job-002"
    assert written["worker_attempt_number"] == 2
    assert len(written["action_log"]) == 1
    assert written["action_log"][0]["action"] == "retry"


def test_run_control_service_force_reset_requires_leased_run() -> None:
    leased = _run_row(
        status="running",
        status_family="active",
        claimed_by_worker_ref="worker-001",
        lease_expires_at="2026-04-13T01:05:00+00:00",
        latest_error_family=None,
    )
    outcome = RunControlService.apply_action(
        action="force_reset",
        request_auth=_auth(),
        run_context=_run_context(),
        run_record_row=leased,
        now_iso_factory=lambda: "2026-04-13T01:00:00+00:00",
    )

    assert outcome.ok is True
    assert outcome.accepted is not None
    assert outcome.accepted.recovery is not None
    assert outcome.accepted.recovery.recovery_state == "manual_review_required"
    assert outcome.accepted.recovery.orphan_review_required is True


def test_run_control_service_mark_reviewed_clears_manual_review() -> None:
    row = _run_row(status="queued", status_family="pending", orphan_review_required=True)
    outcome = RunControlService.apply_action(
        action="mark_reviewed",
        request_auth=_auth(user_id="user-reviewer", roles=("reviewer",)),
        run_context=RunAuthorizationContext(run_id="run-001", workspace_context=_workspace_context(), run_owner_user_ref="user-owner"),
        run_record_row=row,
        now_iso_factory=lambda: "2026-04-13T01:00:00+00:00",
    )

    assert outcome.ok is True
    assert outcome.accepted is not None
    assert outcome.accepted.recovery is not None
    assert outcome.accepted.recovery.orphan_review_required is False


def test_run_control_route_surface_round_trip() -> None:
    stored = {}

    def writer(row):
        stored.update(row)
        return row

    response = RunHttpRouteSurface.handle_retry_run(
        http_request=HttpRouteRequest(
            method="POST",
            path="/api/runs/run-001/retry",
            headers={"Authorization": "Bearer token"},
            session_claims={"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]},
            path_params={"run_id": "run-001"},
        ),
        run_context=_run_context(),
        run_record_row=_run_row(),
        run_record_writer=writer,
        now_iso_factory=lambda: "2026-04-13T01:00:00+00:00",
        queue_job_id_factory=lambda: "job-002",
    )
    assert response.status_code == 200
    assert response.body["queue_job_id"] == "job-002"
    assert response.body["source_artifact"]["storage_role"] == "commit_snapshot"
    assert response.body["source_artifact"]["canonical_ref"] == "snap-001"
    assert stored["queue_job_id"] == "job-002"


def test_fastapi_binding_exposes_run_control_routes() -> None:
    rows = {"run-001": _run_row()}

    def run_record_provider(run_id: str):
        return rows.get(run_id)

    def run_record_writer(row):
        rows[row["run_id"]] = dict(row)
        return row

    app = FastApiRouteBindings(
        config=FastApiBindingConfig(),
        dependencies=FastApiRouteDependencies(
            run_context_provider=lambda run_id: _run_context() if run_id == "run-001" else None,
            run_record_provider=run_record_provider,
            workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "title": "Primary Workspace"},
            run_record_writer=run_record_writer,
            now_iso_provider=lambda: "2026-04-13T01:00:00+00:00",
        ),
    ).build_app()

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/api/runs/run-001/retry",
        headers={"Authorization": "Bearer token", "X-Nexa-Session-Claims": '{"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]}'},
    )
    assert response.status_code == 200
    assert response.json()["queue_job_id"] is not None
    assert rows["run-001"]["status"] == "queued"


def test_run_control_service_records_last_action_on_mark_reviewed() -> None:
    written = {}

    def writer(row):
        written.update(row)
        return row

    outcome = RunControlService.apply_action(
        action="mark_reviewed",
        request_auth=_auth(user_id="user-reviewer", roles=("reviewer",)),
        run_context=RunAuthorizationContext(run_id="run-001", workspace_context=_workspace_context(), run_owner_user_ref="user-owner"),
        run_record_row=_run_row(status="queued", status_family="pending", orphan_review_required=True),
        run_record_writer=writer,
        now_iso_factory=lambda: "2026-04-13T01:00:00+00:00",
    )

    assert outcome.ok is True
    assert written["action_log"][-1]["action"] == "mark_reviewed"
    assert written["action_log"][-1]["actor_user_id"] == "user-reviewer"


def test_fastapi_binding_exposes_run_actions_route() -> None:
    rows = {
        "run-001": _run_row(
            action_log=[
                {
                    "event_id": "act-001",
                    "action": "retry",
                    "actor_user_id": "user-owner",
                    "timestamp": "2026-04-13T01:00:00+00:00",
                    "before_state": {"status": "failed"},
                    "after_state": {"status": "queued"},
                }
            ]
        )
    }

    app = FastApiRouteBindings(
        config=FastApiBindingConfig(),
        dependencies=FastApiRouteDependencies(
            run_context_provider=lambda run_id: _run_context() if run_id == "run-001" else None,
            run_record_provider=lambda run_id: rows.get(run_id),
            workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "title": "Primary Workspace"},
            now_iso_provider=lambda: "2026-04-13T01:00:00+00:00",
        ),
    ).build_app()

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get(
        "/api/runs/run-001/actions",
        headers={"Authorization": "Bearer token", "X-Nexa-Session-Claims": '{"sub": "user-owner", "sid": "sess-001", "exp": 4102444800, "roles": ["admin"]}'},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["returned_count"] == 1
    assert body["actions"][0]["action"] == "retry"


def test_run_control_accepts_execution_target_fallback_for_source_artifact() -> None:
    request_auth = _auth()
    run_context = _run_context()
    run_row = {
        "run_id": "run-001",
        "workspace_id": "ws-001",
        "status": "failed",
        "execution_target_type": "working_save",
        "execution_target_ref": "ws-pause-001",
        "source_working_save_id": "ws-pause-001",
    }
    outcome = RunControlService.apply_action(
        request_auth=request_auth,
        run_context=run_context,
        action="retry",
        run_record_row=run_row,
        now_iso_factory=lambda: "2026-04-20T00:00:00Z",
    )
    assert outcome.accepted is not None
    assert outcome.accepted.source_artifact is not None
    assert outcome.accepted.source_artifact.storage_role == "working_save"
    assert outcome.accepted.source_artifact.canonical_ref == "ws-pause-001"
