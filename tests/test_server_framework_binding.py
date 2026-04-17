from __future__ import annotations

import json

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
from src.storage.share_api import export_public_nex_link_share


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
        "list_issuer_public_shares",
        "get_issuer_public_share_summary",
        "list_issuer_public_share_action_reports",
        "get_issuer_public_share_action_report_summary",
        "revoke_issuer_public_shares",
        "extend_issuer_public_shares",
        "delete_issuer_public_shares",
        "archive_issuer_public_shares",
        "list_workspaces",
        "get_circuit_library",
        "list_starter_circuit_templates",
        "get_starter_circuit_template",
        "apply_starter_circuit_template",
        "get_public_nex_format",
        "get_public_mcp_manifest",
        "get_public_mcp_host_bridge",
        "get_workspace_result_history",
        "get_workspace_feedback",
        "submit_workspace_feedback",
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
        "put_workspace_shell_draft",
        "commit_workspace_shell",
        "checkout_workspace_shell",
        "create_workspace_shell_share",
        "launch_workspace_shell",
        "get_public_share",
        "get_public_share_history",
        "get_public_share_artifact",
        "extend_public_share",
        "revoke_public_share",
        "archive_public_share",
        "delete_public_share",
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




def _working_save(ref: str = "ws-001") -> dict:
    return {
        "meta": {
            "format_version": "0.1.0",
            "storage_role": "working_save",
            "working_save_id": ref,
        },
        "circuit": {"nodes": [], "edges": [], "entry": "n1", "outputs": [{"name": "x", "source": "state.working.x"}]},
        "resources": {"prompts": {}, "providers": {}, "plugins": {}},
        "state": {"input": {}, "working": {}, "memory": {}},
        "runtime": {"status": "draft", "last_run": {}},
        "ui": {"layout": {}, "metadata": {}},
        "designer": {},
    }

def _share_payload(share_id: str = "share-framework-001") -> dict:
    return export_public_nex_link_share(
        _commit_snapshot("snap-share-001"),
        share_id=share_id,
        title="Public share",
        created_at="2026-04-15T12:00:00+00:00",
        issued_by_user_ref="user-owner",
    )


def _issuer_share_rows() -> tuple[dict, ...]:
    return (
        export_public_nex_link_share(
            _commit_snapshot("snap-framework-owner-active"),
            share_id="share-framework-owner-active",
            title="Framework Owner Active",
            created_at="2026-04-15T12:00:00+00:00",
            updated_at="2026-04-15T12:30:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            _commit_snapshot("snap-framework-owner-expired"),
            share_id="share-framework-owner-expired",
            title="Framework Owner Expired",
            created_at="2026-04-10T12:00:00+00:00",
            updated_at="2026-04-10T12:15:00+00:00",
            expires_at="2026-04-11T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            _commit_snapshot("snap-framework-other-active"),
            share_id="share-framework-other-active",
            title="Framework Other Active",
            created_at="2026-04-16T12:00:00+00:00",
            updated_at="2026-04-16T12:30:00+00:00",
            issued_by_user_ref="user-other",
        ),
    )




def _issuer_action_report_rows() -> tuple[dict, ...]:
    return (
        {
            "report_id": "share-report-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T13:00:00+00:00",
            "requested_share_ids": ["share-framework-owner-active"],
            "affected_share_ids": ["share-framework-owner-active"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
        {
            "report_id": "share-report-002",
            "issuer_user_ref": "user-owner",
            "action": "archive",
            "scope": "single_share",
            "created_at": "2026-04-15T14:00:00+00:00",
            "requested_share_ids": ["share-framework-owner-expired"],
            "affected_share_ids": ["share-framework-owner-expired"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 2,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": True,
        },
    )



def _issuer_action_report_rows() -> tuple[dict, ...]:
    return (
        {
            "report_id": "share-report-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T13:00:00+00:00",
            "requested_share_ids": ["share-framework-owner-active"],
            "affected_share_ids": ["share-framework-owner-active"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
        {
            "report_id": "share-report-002",
            "issuer_user_ref": "user-owner",
            "action": "archive",
            "scope": "single_share",
            "created_at": "2026-04-15T14:00:00+00:00",
            "requested_share_ids": ["share-framework-owner-expired"],
            "affected_share_ids": ["share-framework-owner-expired"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 2,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": True,
        },
    )

def test_framework_binding_handles_issuer_public_share_management_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_issuer_public_shares(
        request=_request(method="GET", path="/api/users/me/public-shares"),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["summary"]["total_share_count"] == 2
    assert parsed["summary"]["active_share_count"] == 1
    assert parsed["summary"]["expired_share_count"] == 1
    assert parsed["identity_policy"]["canonical_key"] == "issuer_user_ref"
    assert parsed["namespace_policy"]["family"] == "issuer-public-share-management"
    assert parsed["namespace_policy"]["member_namespace_policy"]["public_path_format"] == "/share/{share_id}"
    assert parsed["shares"][0]["identity"]["canonical_key"] == "share_id"
    assert [entry["share_id"] for entry in parsed["shares"]] == [
        "share-framework-owner-active",
        "share-framework-owner-expired",
    ]


def test_framework_binding_handles_issuer_public_share_summary_round_trip() -> None:
    response = FrameworkRouteBindings.handle_get_issuer_public_share_summary(
        request=_request(method="GET", path="/api/users/me/public-shares/summary"),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["summary"]["total_share_count"] == 2
    assert parsed["summary"]["latest_updated_at"] == "2026-04-15T12:30:00+00:00"


def test_framework_binding_handles_issuer_public_share_action_report_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_issuer_public_share_action_reports(
        request=_request(method="GET", path="/api/users/me/public-shares/action-reports", query_params={"action": "archive"}),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["summary"]["total_report_count"] == 1
    assert parsed["inventory_summary"]["total_report_count"] == 2
    assert parsed["governance_summary"]["total_share_count"] == 2
    assert parsed["reports"][0]["action"] == "archive"
    assert parsed["links"]["share_summary"] == "/api/users/me/public-shares/summary"


def test_framework_binding_handles_issuer_public_share_action_report_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_issuer_public_share_action_reports(
        request=_request(method="GET", path="/api/users/me/public-shares/action-reports", query_params={"action": "archive"}),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["summary"]["total_report_count"] == 1
    assert parsed["inventory_summary"]["total_report_count"] == 2
    assert parsed["governance_summary"]["total_share_count"] == 2
    assert parsed["reports"][0]["action"] == "archive"
    assert parsed["links"]["share_summary"] == "/api/users/me/public-shares/summary"


def test_framework_binding_handles_filtered_paginated_issuer_public_share_management_round_trip() -> None:
    response = FrameworkRouteBindings.handle_list_issuer_public_shares(
        request=_request(
            method="GET",
            path="/api/users/me/public-shares",
            query_params={"stored_lifecycle_state": "active", "limit": "1", "offset": "1"},
        ),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["summary"]["total_share_count"] == 2
    assert parsed["inventory_summary"]["total_share_count"] == 2
    assert parsed["pagination"]["filtered_share_count"] == 2
    assert parsed["pagination"]["returned_count"] == 1
    assert parsed["pagination"]["has_more"] is False
    assert parsed["shares"][0]["share_id"] == "share-framework-owner-expired"


def test_framework_binding_handles_extend_issuer_public_shares_round_trip() -> None:
    share_store = {
        "share-framework-owner-a": export_public_nex_link_share(
            _commit_snapshot("snap-framework-owner-a"),
            share_id="share-framework-owner-a",
            title="Framework Owner A",
            created_at="2026-04-15T12:00:00+00:00",
            expires_at="2026-04-20T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        "share-framework-owner-b": export_public_nex_link_share(
            _commit_snapshot("snap-framework-owner-b"),
            share_id="share-framework-owner-b",
            title="Framework Owner B",
            created_at="2026-04-15T12:05:00+00:00",
            expires_at="2026-04-20T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
    }

    response = FrameworkRouteBindings.handle_extend_issuer_public_shares(
        request=_request(method="POST", path="/api/users/me/public-shares/actions/extend", json_body={"share_ids": ["share-framework-owner-a", "share-framework-owner-b"], "expires_at": "2026-04-25T00:00:00+00:00"}),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_writer=lambda payload: share_store.setdefault(payload["share"]["share_id"], dict(payload)) if payload["share"]["share_id"] not in share_store else share_store.__setitem__(payload["share"]["share_id"], dict(payload)) or dict(payload),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["action"] == "extend_expiration"
    assert parsed["affected_share_count"] == 2
    assert parsed["shares"][0]["lifecycle"]["expires_at"] == "2026-04-25T00:00:00+00:00"
    assert parsed["summary"]["active_share_count"] == 2
    assert parsed["governance_summary"]["extend_action_report_count"] >= 1
    assert parsed["action_report"]["action"] == "extend_expiration"
    assert parsed["links"]["action_report_summary"] == "/api/users/me/public-shares/action-reports/summary"

def test_framework_binding_handles_public_share_round_trip() -> None:
    response = FrameworkRouteBindings.handle_get_public_share(
        request=_request(method="GET", path="/api/public-shares/share-framework-001", path_params={"share_id": "share-framework-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["status"] == "ready"
    assert parsed["share_id"] == "share-framework-001"
    assert parsed["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy"]
    assert parsed["lifecycle"]["stored_state"] == "active"
    assert parsed["lifecycle"]["state"] == "active"
    assert parsed["audit_summary"]["event_count"] == 1
    assert parsed["source_artifact"]["storage_role"] == "commit_snapshot"
    assert parsed["share_boundary"]["share_family"] == "nex.public-link-share"
    assert parsed["share_boundary"]["public_access_posture"] == "anonymous_readonly"
    assert parsed["share_boundary"]["management_access_posture"] == "issuer_authenticated_lifecycle_management"
    assert parsed["share_boundary"]["public_operation_boundaries"][0]["operation"] == "inspect_metadata"
    assert parsed["share_boundary"]["management_operation_boundaries"][1]["operation"] == "extend_expiration"
    assert parsed["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert parsed["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert parsed["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"


def test_framework_binding_handles_public_share_history_round_trip() -> None:
    response = FrameworkRouteBindings.handle_get_public_share_history(
        request=_request(method="GET", path="/api/public-shares/share-framework-001/history", path_params={"share_id": "share-framework-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["audit_summary"]["event_count"] == 1
    assert parsed["history"][0]["event_type"] == "created"
    assert parsed["share_boundary"]["share_family"] == "nex.public-link-share"
    assert parsed["share_boundary"]["history_boundary"]["canonical_http_method"] == "GET"
    assert parsed["share_boundary"]["history_boundary"]["canonical_route"] == "/api/public-shares/{share_id}/history"
    assert parsed["share_boundary"]["history_boundary"]["result_surface"] == "public_share_history"
    assert parsed["share_boundary"]["history_boundary"]["entry_boundary"]["entry_surface"] == "public_share_audit_entry"
    assert parsed["artifact_boundary"]["role_boundary"]["storage_role"] == "commit_snapshot"


def test_framework_binding_handles_public_share_artifact_round_trip() -> None:
    response = FrameworkRouteBindings.handle_get_public_share_artifact(
        request=_request(method="GET", path="/api/public-shares/share-framework-001/artifact", path_params={"share_id": "share-framework-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["identity"]["public_path_value"] == "/share/share-framework-001"
    assert parsed["artifact"]["meta"]["storage_role"] == "commit_snapshot"
    assert parsed["artifact"]["meta"]["commit_id"] == "snap-share-001"
    assert parsed["share_boundary"]["artifact_format_family"] == ".nex"
    assert parsed["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert parsed["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert parsed["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"


def test_framework_binding_handles_workspace_shell_share_creation_round_trip() -> None:
    share_store: dict[str, dict] = {}

    response = FrameworkRouteBindings.handle_create_workspace_shell_share(
        request=_request(
            method="POST",
            path="/api/workspaces/ws-001/shell/share",
            path_params={"workspace_id": "ws-001"},
            json_body={"share_id": "share-framework-created-001", "title": "Framework Shared Snapshot"},
        ),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "continuity_source": "server",
            "archived": False,
        },
        artifact_source=_commit_snapshot("snap-framework-share-001"),
        public_share_payload_writer=lambda payload: share_store.setdefault(payload["share"]["share_id"], dict(payload)),
        now_iso="2026-04-15T12:15:00+00:00",
    )

    assert response.status_code == 201
    parsed = json.loads(response.body_text)
    assert parsed["share_id"] == "share-framework-created-001"
    assert parsed["identity"]["public_path_value"] == "/share/share-framework-created-001"
    assert parsed["lifecycle"]["created_at"] == "2026-04-15T12:15:00+00:00"
    assert parsed["lifecycle"]["issued_by_user_ref"] == "user-owner"
    assert parsed["source_artifact"]["canonical_ref"] == "snap-framework-share-001"
    assert "share-framework-created-001" in share_store


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
    assert parsed["identity_policy"]["surface_family"] == "run-status"
    assert parsed["namespace_policy"]["family"] == "run-status"


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
    assert parsed["source_artifact"]["storage_role"] == "commit_snapshot"
    assert parsed["source_artifact"]["canonical_ref"] == "snap-001"


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
    assert parsed["identity_policy"]["surface_family"] == "run-result"
    assert parsed["namespace_policy"]["family"] == "run-result"


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
    assert parsed["runs"][0]["identity"]["canonical_key"] == "run_id"
    assert parsed["identity_policy"]["surface_family"] == "workspace-run-list"
    assert parsed["namespace_policy"]["family"] == "workspace-run-list"


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
    assert workspace_payload["workspaces"][0]["identity"]["canonical_key"] == "workspace_id"
    assert workspace_payload["identity_policy"]["surface_family"] == "workspace-registry"
    assert workspace_payload["namespace_policy"]["family"] == "workspace-registry"

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
    assert onboarding_payload["state"]["identity"]["canonical_key"] == "onboarding_state_id"
    assert onboarding_payload["identity_policy"]["surface_family"] == "workspace-onboarding"
    assert onboarding_payload["namespace_policy"]["family"] == "workspace-onboarding"






def test_framework_binding_handles_starter_template_routes_round_trip() -> None:
    catalog_response = FrameworkRouteBindings.handle_list_starter_circuit_templates(
        request=_request(method="GET", path="/api/templates/starter-circuits"),
    )
    detail_response = FrameworkRouteBindings.handle_get_starter_circuit_template(
        request=_request(
            method="GET",
            path="/api/templates/starter-circuits/text_summarizer",
            path_params={"template_id": "text_summarizer"},
        ),
    )
    apply_response = FrameworkRouteBindings.handle_apply_starter_circuit_template(
        request=_request(
            method="POST",
            path="/api/workspaces/ws-001/starter-templates/text_summarizer/apply",
            path_params={"workspace_id": "ws-001", "template_id": "text_summarizer"},
        ),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "owner_user_id": "user-owner", "title": "Primary Workspace", "artifact_source": _working_save("ws-template-001")},
        artifact_source=_working_save("ws-template-001"),
        recent_run_rows=(),
        result_rows_by_run_id={},
        onboarding_rows=(),
        artifact_rows_lookup={},
        trace_rows_lookup={},
    )

    assert catalog_response.status_code == 200
    catalog_payload = json.loads(catalog_response.body_text)
    assert catalog_payload["catalog"]["family"] == "starter-circuit-template-catalog"
    assert catalog_payload["catalog"]["identity_policy"]["canonical_key"] == "template_ref"
    assert catalog_payload["identity_policy"]["canonical_key"] == "template_ref"
    assert catalog_payload["namespace_policy"]["family"] == "starter-template"
    assert catalog_payload["templates"][0]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert catalog_payload["templates"][0]["provenance"]["family"] == "starter-template"
    assert catalog_payload["templates"][0]["identity"]["canonical_value"] == "nexa-curated:text_summarizer@1.0"
    assert detail_response.status_code == 200
    detail_payload = json.loads(detail_response.body_text)
    assert detail_payload["template"]["template_id"] == "text_summarizer"
    assert detail_payload["template"]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert detail_payload["template"]["identity"]["legacy_value"] == "text_summarizer"
    assert detail_payload["template"]["compatibility"]["family"] == "workspace-shell-draft"
    assert apply_response.status_code == 200
    apply_payload = json.loads(apply_response.body_text)
    assert apply_payload["template"]["template_id"] == "text_summarizer"
    assert apply_payload["template"]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert apply_payload["template"]["identity"]["canonical_key"] == "template_ref"
    assert apply_payload["template"]["supported_storage_roles"] == ["working_save"]


def test_framework_binding_handles_public_nex_format_round_trip() -> None:
    response = FrameworkRouteBindings.handle_public_nex_format(
        request=_request(method="GET", path="/api/formats/public-nex"),
    )

    assert response.status_code == 200
    payload = json.loads(response.body_text)
    assert payload["format_boundary"]["format_family"] == ".nex"
    assert payload["identity_policy"]["canonical_key"] == "format_boundary.format_family"
    assert payload["namespace_policy"]["family"] == "public-nex-format"
    assert payload["role_boundaries"]["working_save"]["storage_role"] == "working_save"


def test_framework_binding_handles_circuit_library_round_trip() -> None:
    response = FrameworkRouteBindings.handle_circuit_library(
        request=_request(method="GET", path="/api/workspaces/library"),
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
        onboarding_rows=({
            "onboarding_state_id": "onboard-001",
            "user_id": "user-owner",
            "workspace_id": "ws-001",
            "first_success_achieved": False,
            "advanced_surfaces_unlocked": False,
            "current_step": "read_result",
            "updated_at": "2026-04-11T12:09:00+00:00",
        },),
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed["status"] == "ready"
    assert parsed["identity_policy"]["surface_family"] == "circuit-library"
    assert parsed["namespace_policy"]["family"] == "circuit-library"
    assert parsed["library"]["returned_count"] == 1
    assert parsed["library"]["items"][0]["continue_href"] == "/app/workspaces/ws-001/results?run_id=run-001"
    assert parsed["item_sections"][0]["identity"]["canonical_value"] == "ws-001"
    assert parsed["library"]["items"][0]["onboarding_incomplete"] is True

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
    assert catalog_payload["providers"][0]["identity"]["canonical_key"] == "provider_key"
    assert catalog_payload["identity_policy"]["surface_family"] == "provider-catalog"
    assert catalog_payload["namespace_policy"]["family"] == "provider-catalog"

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
    assert list_payload["bindings"][0]["identity"]["canonical_key"] == "binding_id"
    assert list_payload["identity_policy"]["surface_family"] == "workspace-provider-binding"
    assert list_payload["namespace_policy"]["family"] == "workspace-provider-binding"

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
    assert put_payload["binding"]["identity"]["canonical_key"] == "binding_id"
    assert put_payload["identity_policy"]["surface_family"] == "workspace-provider-binding"
    assert put_payload["namespace_policy"]["family"] == "workspace-provider-binding"
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
    assert parsed["items"][0]["identity"]["canonical_key"] == "probe_event_id"
    assert parsed["identity_policy"]["surface_family"] == "workspace-provider-probe-history"
    assert parsed["namespace_policy"]["family"] == "workspace-provider-probe-history"


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
    assert parsed['designer_section']['summary']['headline'] == 'Designer workspace'
    assert parsed['designer_section']['detail']['title'] == 'Designer detail'
    assert parsed['designer_section']['controls'][0]['action_kind'] == 'apply_template'
    assert parsed['designer_section']['controls'][0]['action_target'] == 'nexa-curated:text_summarizer@1.0'
    assert parsed['designer_section']['controls'][0]['template_ref'] == 'nexa-curated:text_summarizer@1.0'
    assert parsed['designer_section']['controls'][0]['template_provenance']['source'] == 'nexa-curated'
    assert parsed['designer_section']['controls'][1]['action_target'] == 'designer.detail'
    assert parsed['validation_section']['summary']['headline'] == 'Validation: unknown'
    assert parsed['validation_section']['detail']['title'] == 'Validation detail'
    assert parsed['validation_section']['controls'][0]['action_kind'] == 'run_draft'
    assert parsed['validation_section']['controls'][1]['action_kind'] == 'focus_section'
    assert parsed['validation_section']['controls'][2]['action_kind'] == 'focus_auxiliary'
    assert parsed['navigation']['default_section'] == 'result'
    assert parsed['navigation']['default_level'] == 'detail'
    assert parsed['navigation']['guidance_label'] == 'Recommended next: Result'
    assert [section['section_id'] for section in parsed['navigation']['sections']] == ['designer', 'validation', 'status', 'result', 'trace', 'artifacts']
    assert parsed['step_state_banner']['title'] == 'Step 5 of 5 — Read result'
    assert parsed['step_state_banner']['recommended_section'] == 'result'
    assert parsed['step_state_banner']['action_label'] == 'Open Result'
    assert parsed['step_state_banner']['action_target'] == 'runtime.result'
    assert parsed['step_state_banner']['action_kind'] == 'focus_section'
    assert 'Result is ready.' in parsed['step_state_banner']['summary']
    assert parsed['client_continuity']['enabled'] is True
    assert parsed['client_continuity']['storage_key'] == 'nexa.runtime_shell.ws-001'
    assert parsed['client_continuity']['version'] == 'phase6-batch15'


def test_framework_binding_workspace_shell_pre_run_banner_for_empty_mobile_workspace() -> None:
    response = FrameworkRouteBindings.handle_workspace_shell(
        request=_request(method="GET", path="/api/workspaces/ws-001/shell", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
        },
        recent_run_rows=(),
        result_rows_by_run_id={},
        artifact_rows_lookup=lambda run_id: (),
        trace_rows_lookup=lambda run_id: (),
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
    assert parsed['navigation']['default_section'] == 'designer'
    assert parsed['step_state_banner']['title'] == 'Step 1 of 5 — Enter goal'
    assert parsed['step_state_banner']['phase'] == 'pre_run'
    assert parsed['step_state_banner']['action_label'] == 'Open Designer'
    assert parsed['step_state_banner']['action_target'] == 'designer'
    assert parsed['step_state_banner']['action_kind'] == 'focus_section'
    assert 'prepare your first workflow' in parsed['step_state_banner']['summary']


def test_framework_binding_workspace_shell_uses_server_backed_onboarding_step_for_navigation() -> None:
    response = FrameworkRouteBindings.handle_workspace_shell(
        request=_request(method="GET", path="/api/workspaces/ws-001/shell", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "description": "Main",
        },
        onboarding_rows=({
            "onboarding_state_id": "onboard-001",
            "user_id": "user-owner",
            "workspace_id": "ws-001",
            "first_success_achieved": False,
            "advanced_surfaces_unlocked": False,
            "dismissed_guidance_state": {},
            "current_step": "review_preview",
            "created_at": "2026-04-11T12:00:00+00:00",
            "updated_at": "2026-04-11T12:05:00+00:00",
        },),
        recent_run_rows=(),
        result_rows_by_run_id={},
        artifact_rows_lookup=lambda run_id: (),
        trace_rows_lookup=lambda run_id: (),
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
    assert parsed['routes']['onboarding_write'] == '/api/users/me/onboarding'
    assert parsed['navigation']['default_section'] == 'validation'
    assert parsed['navigation']['default_level'] == 'detail'
    assert parsed['step_state_banner']['current_step_id'] == 'review_preview'
    assert parsed['step_state_banner']['action_target'] == 'validation.detail'
    assert parsed['continuity']['onboarding_state']['current_step'] == 'review_preview'


def test_framework_binding_put_workspace_shell_draft_persists_template_and_validation_state() -> None:
    artifact_store = {
        'ws-001': {
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-001-draft", "name": "Primary Workspace"},
            "circuit": {"nodes": [], "edges": [], "entry": None, "outputs": []},
            "resources": {"prompts": {}, "providers": {}, "plugins": {}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US", "viewport_tier": "mobile"}},
            "designer": {},
        }
    }

    response = FrameworkRouteBindings.handle_put_workspace_shell_draft(
        request=_request(method='PUT', path='/api/workspaces/ws-001/shell/draft', path_params={'workspace_id': 'ws-001'}, json_body={
            'template_id': 'text_summarizer',
            'template_display_name': 'Text Summarizer',
            'template_ref': 'nexa-curated:text_summarizer@1.0',
            'template_version': '1.0',
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
        }),
        workspace_context=_workspace(),
        workspace_row={
            'workspace_id': 'ws-001',
            'owner_user_id': 'user-owner',
            'title': 'Primary Workspace',
            'description': 'Main',
        },
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )

    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert artifact_store['ws-001']['designer']['server_backed_shell_state']['selected_template_id'] == 'text_summarizer'
    assert artifact_store['ws-001']['designer']['server_backed_shell_state']['selected_template_ref'] == 'nexa-curated:text_summarizer@1.0'
    assert artifact_store['ws-001']['designer']['server_backed_shell_state']['selected_template_lookup_aliases'] == ['text_summarizer', 'nexa-curated:text_summarizer@1.0']
    assert artifact_store['ws-001']['designer']['draft_request_text'] == 'Summarize this article.'
    assert artifact_store['ws-001']['ui']['metadata']['runtime_shell_server_state']['validation_action'] == 'open_validation_detail'
    assert 'Persisted template: Text Summarizer' in '\n'.join(parsed['designer_section']['summary']['lines'])
    assert 'Template ref: nexa-curated:text_summarizer@1.0' in '\n'.join(parsed['designer_section']['detail']['items'])
    assert 'Lookup aliases: text_summarizer, nexa-curated:text_summarizer@1.0' in '\n'.join(parsed['designer_section']['detail']['items'])
    assert 'Provenance: nexa-curated / starter-template' in '\n'.join(parsed['designer_section']['detail']['items'])
    assert 'Compatibility: workspace-shell-draft / replace_designer_request' in '\n'.join(parsed['designer_section']['detail']['items'])
    assert 'Persisted validation action: open_validation_detail' in '\n'.join(parsed['validation_section']['summary']['lines'])
    assert parsed['status_history_section']['summary']['headline'] == 'Status history'
    assert parsed['result_history_section']['summary']['headline'] == 'Result history'
    assert parsed['routes']['workspace_shell_draft_write'] == '/api/workspaces/ws-001/shell/draft'


def test_framework_binding_handles_workspace_result_history_round_trip() -> None:
    response = FrameworkRouteBindings.handle_workspace_result_history(
        request=_request(method="GET", path="/api/workspaces/ws-001/result-history", path_params={"workspace_id": "ws-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "owner_user_id": "user-owner", "title": "Primary Workspace", "updated_at": "2026-04-11T12:05:00+00:00", "created_at": "2026-04-11T12:00:00+00:00", "archived": False},
        run_rows=({**_run_row(status="completed", status_family="terminal_success"), "run_id": "run-002", "updated_at": "2026-04-11T12:01:00+00:00", "finished_at": "2026-04-11T12:01:00+00:00"},),
        result_rows_by_run_id={"run-002": {"run_id": "run-002", "workspace_id": "ws-001", "result_state": "ready_success", "final_status": "completed", "result_summary": "Success.", "final_output": {"output_key": "answer", "value_preview": "Latest Hello", "value_type": "string"}}},
        artifact_rows_lookup=lambda _run_id: (),
        recent_run_rows=(), provider_binding_rows=(), managed_secret_rows=(), provider_probe_rows=(), onboarding_rows=(),
    )
    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["identity_policy"]["surface_family"] == "workspace-result-history"
    assert parsed["namespace_policy"]["family"] == "workspace-result-history"
    assert parsed["result_history"]["returned_count"] == 1
    assert parsed["result_history"]["items"][0]["output_preview"] == "Latest Hello"
    assert parsed["item_sections"][0]["identity"]["canonical_value"] == "run-002"


def test_framework_binding_workspace_feedback_route_round_trip() -> None:
    request = _request(method="GET", path="/api/workspaces/ws-001/feedback", path_params={"workspace_id": "ws-001"}, query_params={"surface": "circuit_library"})
    response = FrameworkRouteBindings.handle_workspace_feedback(
        request=request,
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_rows=(
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
        ),
    )
    assert response.status_code == 200
    payload = json.loads(response.body_text)
    assert payload["identity_policy"]["surface_family"] == "workspace-feedback"
    assert payload["namespace_policy"]["family"] == "workspace-feedback"
    assert payload["feedback_channel"]["prefill_surface"] == "circuit_library"
    assert payload["feedback_channel"]["items"][0]["identity"]["canonical_value"] == "fb-001"


def test_framework_binding_workspace_feedback_submit_round_trip() -> None:
    request = _request(method="POST", path="/api/workspaces/ws-001/feedback", path_params={"workspace_id": "ws-001"}, json_body={"category": "confusing_screen", "surface": "workspace_shell", "message": "I do not understand this workflow screen."})
    response = FrameworkRouteBindings.handle_submit_workspace_feedback(
        request=request,
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_writer=lambda row: row,
        feedback_id_factory=lambda: "fb-010",
        now_iso="2026-04-14T08:20:00+00:00",
    )
    assert response.status_code == 202
    payload = json.loads(response.body_text)
    assert payload["workspace_id"] == "ws-001"
    assert payload["identity_policy"]["surface_family"] == "workspace-feedback"
    assert payload["namespace_policy"]["family"] == "workspace-feedback"
    assert payload["feedback"]["feedback_id"] == "fb-010"
    assert payload["feedback"]["identity"]["canonical_value"] == "fb-010"
    assert payload["feedback"]["surface"] == "workspace_shell"


def test_framework_binding_commit_workspace_shell_persists_commit_snapshot() -> None:
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
    response = FrameworkRouteBindings.handle_commit_workspace_shell(
        request=_request(method='POST', path='/api/workspaces/ws-001/shell/commit', path_params={'workspace_id': 'ws-001'}, json_body={'commit_id': 'commit-ws-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert artifact_store['ws-001']['meta']['storage_role'] == 'commit_snapshot'
    assert artifact_store['ws-001']['meta']['commit_id'] == 'commit-ws-001'
    assert parsed['storage_role'] == 'commit_snapshot'
    assert parsed['transition']['action'] == 'commit_workspace_shell'
    assert parsed['routes']['workspace_shell_commit'] == '/api/workspaces/ws-001/shell/commit'


def test_framework_binding_checkout_workspace_shell_restores_working_save() -> None:
    artifact_store = {'ws-001': _commit_snapshot('snap-checkout-001')}
    response = FrameworkRouteBindings.handle_checkout_workspace_shell(
        request=_request(method='POST', path='/api/workspaces/ws-001/shell/checkout', path_params={'workspace_id': 'ws-001'}, json_body={'working_save_id': 'ws-restored-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert artifact_store['ws-001']['meta']['storage_role'] == 'working_save'
    assert artifact_store['ws-001']['meta']['working_save_id'] == 'ws-restored-001'
    assert parsed['storage_role'] == 'working_save'
    assert parsed['transition']['action'] == 'checkout_workspace_shell'
    assert parsed['routes']['workspace_shell_checkout'] == '/api/workspaces/ws-001/shell/checkout'


def test_framework_binding_launch_workspace_shell_round_trip() -> None:
    response = FrameworkRouteBindings.handle_launch_workspace_shell(
        request=_request(method='POST', path='/api/workspaces/ws-001/shell/launch', path_params={'workspace_id': 'ws-001'}, json_body={'input_payload': {'question': 'hello from framework shell'}}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source={
            "meta": {"format_version": "1.0.0", "storage_role": "working_save", "working_save_id": "ws-framework-launch", "name": "Primary Workspace"},
            "circuit": {"nodes": [{"id": "n1", "type": "plugin", "plugin_ref": "plugin.main", "inputs": {}, "outputs": {"result": "output.value"}}], "edges": [], "entry": "n1", "outputs": [{"name": "result", "node_id": "n1", "path": "output.value"}]},
            "resources": {"prompts": {}, "providers": {}, "plugins": {"plugin.main": {"entrypoint": "demo.main"}}},
            "state": {"input": {}, "working": {}, "memory": {}},
            "runtime": {"status": "draft", "validation_summary": {}, "last_run": {}, "errors": []},
            "ui": {"layout": {}, "metadata": {"app_language": "en-US"}},
        },
        run_id_factory=lambda: 'run-framework-shell-001',
        run_request_id_factory=lambda: 'req-framework-shell-001',
        now_iso='2026-04-14T09:10:00+00:00',
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 202
    assert parsed['run_id'] == 'run-framework-shell-001'
    assert parsed['execution_target']['target_type'] == 'working_save'
    assert parsed['execution_target']['target_ref'] == 'ws-framework-launch'
    assert parsed['launch_context']['action'] == 'launch_workspace_shell'
    assert parsed['source_artifact']['storage_role'] == 'working_save'
    assert parsed['source_artifact']['canonical_ref'] == 'ws-framework-launch'


def test_framework_binding_workspace_shell_draft_rejects_commit_snapshot_source() -> None:
    artifact_store = {'ws-001': _commit_snapshot('snap-framework-draft-001')}
    response = FrameworkRouteBindings.handle_put_workspace_shell_draft(
        request=_request(method='PUT', path='/api/workspaces/ws-001/shell/draft', path_params={'workspace_id': 'ws-001'}, json_body={'request_text': 'Revise this snapshot.'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=artifact_store['ws-001'],
        workspace_artifact_source_writer=lambda workspace_id, artifact_source: artifact_store.__setitem__(workspace_id, artifact_source) or artifact_source,
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 409
    assert parsed['reason_code'] == 'workspace_shell.draft_requires_working_save'
    assert artifact_store['ws-001']['meta']['storage_role'] == 'commit_snapshot'


def test_framework_binding_workspace_shell_payload_exposes_role_aware_action_availability() -> None:
    response = FrameworkRouteBindings.handle_workspace_shell(
        request=_request(method='GET', path='/api/workspaces/ws-001/shell', path_params={'workspace_id': 'ws-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=_commit_snapshot('snap-framework-actions-001'),
    )
    parsed = json.loads(response.body_text)
    assert response.status_code == 200
    assert parsed['storage_role'] == 'commit_snapshot'
    assert parsed['action_availability']['draft_write']['allowed'] is False
    assert parsed['action_availability']['checkout']['allowed'] is True
    assert parsed['action_availability']['launch']['allowed'] is True


def test_framework_binding_revoke_public_share_round_trip() -> None:
    share_store: dict[str, dict] = {"share-framework-revoke-001": _share_payload("share-framework-revoke-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = FrameworkRouteBindings.handle_revoke_public_share(
        request=_request(method="POST", path="/api/public-shares/share-framework-revoke-001/revoke", path_params={"share_id": "share-framework-revoke-001"}),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:30:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["share_id"] == "share-framework-revoke-001"
    assert parsed["identity"]["share_family"] == "public_nex_link_share"
    assert parsed["lifecycle"]["state"] == "revoked"
    assert parsed["lifecycle"]["updated_at"] == "2026-04-15T13:30:00+00:00"
    assert parsed["action_report"]["action"] == "revoke"
    assert parsed["governance_summary"]["total_action_report_count"] == 3
    assert parsed["share_boundary"]["share_family"] == "nex.public-link-share"
    assert parsed["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert parsed["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert parsed["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"
    assert parsed["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"
    assert share_store["share-framework-revoke-001"]["share"]["lifecycle"]["state"] == "revoked"


def test_framework_binding_extend_public_share_round_trip() -> None:
    share_store: dict[str, dict] = {"share-framework-extend-001": _share_payload("share-framework-extend-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = FrameworkRouteBindings.handle_extend_public_share(
        request=_request(
            method="POST",
            path="/api/public-shares/share-framework-extend-001/extend",
            path_params={"share_id": "share-framework-extend-001"},
            json_body={"expires_at": "2026-04-20T00:00:00+00:00"},
        ),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:30:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["share_id"] == "share-framework-extend-001"
    assert parsed["identity"]["share_family"] == "public_nex_link_share"
    assert parsed["lifecycle"]["stored_state"] == "active"
    assert parsed["lifecycle"]["state"] == "active"
    assert parsed["lifecycle"]["expires_at"] == "2026-04-20T00:00:00+00:00"
    assert parsed["action_report"]["action"] == "extend_expiration"
    assert parsed["governance_summary"]["total_action_report_count"] == 3
    assert parsed["share_boundary"]["share_family"] == "nex.public-link-share"
    assert parsed["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert parsed["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert parsed["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert parsed["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"
    assert parsed["links"]["action_report_summary"] == "/api/users/me/public-shares/action-reports/summary"
    assert share_store["share-framework-extend-001"]["share"]["lifecycle"]["expires_at"] == "2026-04-20T00:00:00+00:00"



def test_framework_binding_handles_delete_issuer_public_shares_round_trip() -> None:
    share_store = {
        "share-framework-delete-a": export_public_nex_link_share(_commit_snapshot("snap-framework-delete-a"), share_id="share-framework-delete-a", title="Framework Delete A", created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner"),
        "share-framework-delete-b": export_public_nex_link_share(_commit_snapshot("snap-framework-delete-b"), share_id="share-framework-delete-b", title="Framework Delete B", created_at="2026-04-15T12:05:00+00:00", issued_by_user_ref="user-owner"),
    }

    response = FrameworkRouteBindings.handle_delete_issuer_public_shares(
        request=_request(method="POST", path="/api/users/me/public-shares/actions/delete", json_body={"share_ids": ["share-framework-delete-a", "share-framework-delete-b"]}),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["action"] == "delete"
    assert parsed["affected_share_count"] == 2
    assert parsed["summary"]["total_share_count"] == 0
    assert parsed["governance_summary"]["total_share_count"] == 0
    assert parsed["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"


def test_framework_binding_handles_public_share_delete_round_trip() -> None:
    share_store = {"share-framework-delete-001": _share_payload("share-framework-delete-001")}

    response = FrameworkRouteBindings.handle_delete_public_share(
        request=_request(method="DELETE", path="/api/public-shares/share-framework-delete-001", path_params={"share_id": "share-framework-delete-001"}),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        public_share_action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_writer=lambda row: dict(row),
    )

    assert response.status_code == 200
    parsed = json.loads(response.body_text)
    assert parsed["status"] == "deleted"
    assert parsed["share_id"] == "share-framework-delete-001"
    assert parsed["identity"]["canonical_key"] == "share_id"
    assert parsed["action_report"]["action"] == "delete"
    assert parsed["governance_summary"]["total_share_count"] == 0
    assert parsed["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"



def test_framework_binding_handles_public_mcp_manifest_round_trip() -> None:
    response = FrameworkRouteBindings.handle_public_mcp_manifest(
        request=_request(method="GET", path="/api/integrations/public-mcp/manifest", query_params={"base_url": "https://api.nexa.test"}),
    )

    assert response.status_code == 200
    payload = json.loads(response.body_text)
    assert payload["manifest"]["server"]["name"] == "nexa-public"
    assert payload["identity_policy"]["canonical_key"] == "manifest.server.name"
    assert payload["namespace_policy"]["family"] == "public-mcp-manifest"


def test_framework_binding_handles_public_mcp_host_bridge_round_trip() -> None:
    response = FrameworkRouteBindings.handle_public_mcp_host_bridge(
        request=_request(method="GET", path="/api/integrations/public-mcp/host-bridge", query_params={"base_url": "https://api.nexa.test"}),
    )

    assert response.status_code == 200
    payload = json.loads(response.body_text)
    assert payload["host_bridge"]["framework_binding_class"] == "FrameworkRouteBindings"
    assert payload["identity_policy"]["canonical_key"] == "host_bridge.framework_binding_class"
    assert payload["namespace_policy"]["family"] == "public-mcp-host-bridge"
