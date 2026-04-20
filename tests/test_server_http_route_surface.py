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


def _auth_request(*, method: str, path: str, path_params: dict | None = None, query_params: dict | None = None, json_body=None, user_id: str = "user-owner") -> HttpRouteRequest:
    return HttpRouteRequest(
        method=method,
        path=path,
        headers={"Authorization": "Bearer token", "X-Request-Id": "req-http-1"},
        session_claims={"sub": user_id, "sid": "sess-001", "exp": 4102444800, "roles": ["editor"]},
        path_params=path_params or {},
        query_params=query_params or {},
        json_body=json_body,
    )




def _share_payload(share_id: str = "share-http-001") -> dict:
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
            _commit_snapshot("snap-share-owner-active"),
            share_id="share-owner-active",
            title="Owner Active Share",
            created_at="2026-04-15T12:00:00+00:00",
            updated_at="2026-04-15T12:30:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            _commit_snapshot("snap-share-owner-expired"),
            share_id="share-owner-expired",
            title="Owner Expired Share",
            created_at="2026-04-10T12:00:00+00:00",
            updated_at="2026-04-10T12:15:00+00:00",
            expires_at="2026-04-11T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            _commit_snapshot("snap-share-owner-revoked"),
            share_id="share-owner-revoked",
            title="Owner Revoked Share",
            created_at="2026-04-09T12:00:00+00:00",
            updated_at="2026-04-09T12:15:00+00:00",
            lifecycle_state="revoked",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            _commit_snapshot("snap-share-other-active"),
            share_id="share-other-active",
            title="Other Active Share",
            created_at="2026-04-16T12:00:00+00:00",
            updated_at="2026-04-16T12:30:00+00:00",
            issued_by_user_ref="user-other",
        ),
    )






def _saved_public_share_rows() -> tuple[dict, ...]:
    return (
        {"share_id": "share-owner-active", "saved_at": "2026-04-16T10:00:00+00:00", "saved_by_user_ref": "user-owner"},
    )

def _issuer_action_report_rows() -> tuple[dict, ...]:
    return (
        {
            "report_id": "share-report-http-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T13:00:00+00:00",
            "requested_share_ids": ["share-owner-active"],
            "affected_share_ids": ["share-owner-active"],
            "affected_share_count": 1,
            "before_total_share_count": 3,
            "after_total_share_count": 2,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
        {
            "report_id": "share-report-http-002",
            "issuer_user_ref": "user-owner",
            "action": "delete",
            "scope": "single_share",
            "created_at": "2026-04-15T14:00:00+00:00",
            "requested_share_ids": ["share-owner-expired"],
            "affected_share_ids": ["share-owner-expired"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
    )



def _issuer_action_report_rows() -> tuple[dict, ...]:
    return (
        {
            "report_id": "share-report-http-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "issuer_bulk",
            "created_at": "2026-04-15T13:00:00+00:00",
            "requested_share_ids": ["share-owner-active"],
            "affected_share_ids": ["share-owner-active"],
            "affected_share_count": 1,
            "before_total_share_count": 3,
            "after_total_share_count": 2,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
        {
            "report_id": "share-report-http-002",
            "issuer_user_ref": "user-owner",
            "action": "delete",
            "scope": "single_share",
            "created_at": "2026-04-15T14:00:00+00:00",
            "requested_share_ids": ["share-owner-expired"],
            "affected_share_ids": ["share-owner-expired"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
            "actor_user_ref": "user-owner",
            "expires_at": None,
            "archived": None,
        },
    )

def test_http_route_definitions_are_unique() -> None:
    definitions = RunHttpRouteSurface.route_definitions()
    route_names = [route_name for route_name, _method, _path in definitions]

    assert len(route_names) == len(set(route_names))
    assert len(definitions) == len(set(definitions))




def test_public_share_catalog_route_returns_filtered_entries() -> None:
    response = RunHttpRouteSurface.handle_list_public_shares(
        http_request=_auth_request(method="GET", path="/api/public-shares", query_params={"operation": "run_artifact"}),
        share_payload_rows_provider=_issuer_share_rows,
        saved_public_share_rows_provider=_saved_public_share_rows,
        now_iso="2026-04-16T12:45:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["returned_count"] == 2
    assert response.body["summary"]["runnable_share_count"] == 2
    assert response.body["shares"][0]["capability_summary"]["can_create_workspace_from_share"] is True
    assert response.body["shares"][0]["action_availability"]["create_workspace_from_share"]["allowed"] is True
    assert response.body["shares"][0]["identity"]["canonical_key"] == "share_id"
    assert response.body["namespace_policy"]["family"] == "public-share-catalog"


def test_public_share_issuer_catalog_routes_return_issuer_filtered_entries() -> None:
    response = RunHttpRouteSurface.handle_list_public_shares_by_issuer(
        http_request=_auth_request(
            method="GET",
            path="/api/public-shares/issuers/user-owner",
            path_params={"issuer_user_ref": "user-owner"},
            query_params={"operation": "run_artifact"},
        ),
        share_payload_rows_provider=_issuer_share_rows,
        saved_public_share_rows_provider=_saved_public_share_rows,
        now_iso="2026-04-16T12:45:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["issuer_user_ref"] == "user-owner"
    assert response.body["returned_count"] == 1
    assert response.body["summary"]["runnable_share_count"] == 1
    assert response.body["links"]["summary"] == "/api/public-shares/issuers/user-owner/summary"

    summary_response = RunHttpRouteSurface.handle_get_public_share_issuer_catalog_summary(
        http_request=_auth_request(
            method="GET",
            path="/api/public-shares/issuers/user-owner/summary",
            path_params={"issuer_user_ref": "user-owner"},
            query_params={"operation": "run_artifact"},
        ),
        share_payload_rows_provider=_issuer_share_rows,
        saved_public_share_rows_provider=_saved_public_share_rows,
        now_iso="2026-04-16T12:45:00+00:00",
    )
    assert summary_response.status_code == 200
    assert summary_response.body["issuer_user_ref"] == "user-owner"
    assert summary_response.body["summary"]["runnable_share_count"] == 1


def test_saved_public_share_collection_requires_authentication() -> None:
    response = RunHttpRouteSurface.handle_list_saved_public_shares(
        http_request=HttpRouteRequest(method="GET", path="/api/users/me/saved-public-shares"),
        share_payload_provider=lambda share_id: _share_payload(share_id),
        saved_public_share_rows_provider=_saved_public_share_rows,
    )

    assert response.status_code == 401
    assert response.body["reason_code"] == "public_share.authentication_required"




def test_public_share_saved_state_mutation_routes_round_trip() -> None:
    saved_rows = [{"share_id": "share-owner-active", "saved_at": "2026-04-16T11:55:00+00:00", "saved_by_user_ref": "user-owner"}]
    written: list[dict] = []
    deleted: list[str] = []

    save_response = RunHttpRouteSurface.handle_save_public_share(
        http_request=_auth_request(method="POST", path="/api/public-shares/share-http-save-001/save", path_params={"share_id": "share-http-save-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
        saved_public_share_rows_provider=lambda: tuple(saved_rows),
        saved_public_share_writer=lambda row: written.append(dict(row)) or dict(row),
        now_iso="2026-04-16T13:10:00+00:00",
    )
    assert save_response.status_code == 200
    assert save_response.body["action"] == "save"
    assert save_response.body["saved"] is True
    assert save_response.body["saved_by_user_ref"] == "user-owner"
    assert written[0]["share_id"] == "share-http-save-001"

    unsave_response = RunHttpRouteSurface.handle_unsave_public_share(
        http_request=_auth_request(method="POST", path="/api/public-shares/share-owner-active/unsave", path_params={"share_id": "share-owner-active"}),
        saved_public_share_rows_provider=lambda: tuple(saved_rows),
        saved_public_share_deleter=lambda share_id: deleted.append(share_id) or True,
    )
    assert unsave_response.status_code == 200
    assert unsave_response.body["action"] == "unsave"
    assert unsave_response.body["saved"] is False
    assert deleted == ["share-owner-active"]

def test_public_share_related_and_compare_routes_return_summary() -> None:
    related = RunHttpRouteSurface.handle_get_related_public_shares(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-owner-active/related", path_params={"share_id": "share-owner-active"}),
        share_payload_provider=lambda share_id: next((row for row in _issuer_share_rows() if row["share"]["share_id"] == share_id), None),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-16T12:45:00+00:00",
    )
    assert related.status_code == 200
    assert related.body["related_summary"]["total_related_count"] == 1
    assert related.body["action_availability"]["create_workspace_from_share"]["allowed"] is True
    assert related.body["shares"][0]["same_storage_role"] is True
    assert related.body["shares"][0]["capability_summary"]["can_create_workspace_from_share"] is True

    compare = RunHttpRouteSurface.handle_get_public_share_compare_summary(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-owner-active/compare-summary", path_params={"share_id": "share-owner-active"}, query_params={"workspace_id": "ws-001"}),
        share_payload_provider=lambda share_id: next((row for row in _issuer_share_rows() if row["share"]["share_id"] == share_id), None),
        workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "owner_user_id": "user-owner", "title": "Workspace", "continuity_source": "server", "archived": False},
        workspace_artifact_source_provider=lambda _workspace_id: _working_save("ws-http-compare"),
    )
    assert compare.status_code == 200
    assert compare.body["compare"]["workspace_found"] is True
    assert compare.body["compare"]["storage_role_match"] is False
    assert compare.body["capability_summary"]["can_run_artifact"] is True
    assert compare.body["action_availability"]["run"]["allowed"] is True

    compare_full = RunHttpRouteSurface.handle_get_public_share_compare(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-owner-active/compare", path_params={"share_id": "share-owner-active"}, query_params={"workspace_id": "ws-001"}),
        share_payload_provider=lambda share_id: next((row for row in _issuer_share_rows() if row["share"]["share_id"] == share_id), None),
        workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "owner_user_id": "user-owner", "title": "Workspace", "continuity_source": "server", "archived": False},
        workspace_artifact_source_provider=lambda _workspace_id: _working_save("ws-http-compare"),
    )
    assert compare_full.status_code == 200
    assert compare_full.body["compare"]["workspace_found"] is True
    assert compare_full.body["compare"]["share_artifact"]["meta"]["storage_role"] == "commit_snapshot"
    assert compare_full.body["compare"]["workspace_artifact"]["meta"]["storage_role"] == "working_save"
    assert compare_full.body["namespace_policy"]["family"] == "public-share-compare"


def test_public_share_route_returns_descriptor_without_authentication() -> None:
    response = RunHttpRouteSurface.handle_get_public_share(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-http-001", path_params={"share_id": "share-http-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["share_id"] == "share-http-001"
    assert response.body["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy"]
    assert response.body["capability_summary"]["can_create_workspace_from_share"] is True
    assert response.body["capability_summary"]["preferred_create_workspace_mode"] == "checkout_working_copy"
    assert response.body["action_availability"]["checkout"]["allowed"] is True
    assert response.body["action_availability"]["create_workspace_from_share"]["supported_modes"] == ["checkout_working_copy", "import_copy"]
    assert response.body["lifecycle"]["stored_state"] == "active"
    assert response.body["lifecycle"]["state"] == "active"
    assert response.body["audit_summary"]["event_count"] == 1
    assert response.body["lifecycle"]["issued_by_user_ref"] == "user-owner"
    assert response.body["management"]["archived"] is False
    assert response.body["source_artifact"]["canonical_ref"] == "snap-share-001"
    assert response.body["share_boundary"]["share_family"] == "nex.public-link-share"
    assert response.body["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert response.body["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert response.body["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["result_surface"] == "public_share_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"


def test_public_share_artifact_route_returns_canonical_artifact_without_authentication() -> None:
    response = RunHttpRouteSurface.handle_get_public_share_artifact(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-http-001/artifact", path_params={"share_id": "share-http-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    assert response.body["artifact"]["meta"]["storage_role"] == "commit_snapshot"
    assert response.body["artifact"]["meta"]["commit_id"] == "snap-share-001"
    assert response.body["share_boundary"]["artifact_format_family"] == ".nex"
    assert response.body["share_boundary"]["public_access_posture"] == "anonymous_readonly"
    assert response.body["share_boundary"]["management_access_posture"] == "issuer_authenticated_lifecycle_management"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["operation"] == "inspect_metadata"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["result_surface"] == "public_share_detail"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["effect_posture"] == "read_only"
    assert response.body["share_boundary"]["public_operation_boundaries"][0]["allowed_effective_lifecycle_states"] == ["active", "expired", "revoked"]
    assert response.body["share_boundary"]["public_operation_boundaries"][4]["allowed_storage_roles"] == ["commit_snapshot"]
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["operation"] == "revoke"
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["canonical_http_method"] == "POST"
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/revoke"
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["result_surface"] == "single_share_mutation_result"
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["effect_posture"] == "lifecycle_transition"
    assert response.body["share_boundary"]["management_operation_boundaries"][0]["denial_reason_code"] == "public_share.transition_not_allowed"
    assert response.body["share_boundary"]["history_boundary"]["ordering"] == "ascending_sequence"
    assert response.body["share_boundary"]["history_boundary"]["canonical_http_method"] == "GET"
    assert response.body["identity"]["share_family"] == "public_nex_link_share"
    assert response.body["identity_policy"]["canonical_key"] == "share_id"
    assert response.body["namespace_policy"]["public_path_format"] == "/share/{share_id}"
    assert response.body["share_boundary"]["history_boundary"]["canonical_route"] == "/api/public-shares/{share_id}/history"
    assert response.body["share_boundary"]["history_boundary"]["result_surface"] == "public_share_history"
    assert response.body["share_boundary"]["history_boundary"]["entry_boundary"]["entry_surface"] == "public_share_audit_entry"
    assert response.body["share_boundary"]["history_boundary"]["entry_boundary"]["identity_field"] == "sequence"
    assert response.body["share_boundary"]["history_boundary"]["entry_boundary"]["timestamp_field"] == "at"
    assert response.body["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert response.body["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert response.body["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["result_surface"] == "public_share_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"


def test_issuer_public_share_management_routes_require_authentication() -> None:
    response = RunHttpRouteSurface.handle_list_issuer_public_shares(
        http_request=HttpRouteRequest(method="GET", path="/api/users/me/public-shares", headers={}, session_claims=None, path_params={}, query_params={}, json_body=None),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 401
    assert response.body["reason_code"] == "public_share.authentication_required"


def test_issuer_public_share_management_routes_return_bounded_summary_and_entries() -> None:
    response = RunHttpRouteSurface.handle_list_issuer_public_shares(
        http_request=_auth_request(method="GET", path="/api/users/me/public-shares"),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["issuer_user_ref"] == "user-owner"
    assert response.body["summary"]["total_share_count"] == 3
    assert response.body["summary"]["active_share_count"] == 1
    assert response.body["summary"]["expired_share_count"] == 1
    assert response.body["summary"]["revoked_share_count"] == 1
    assert response.body["summary"]["commit_snapshot_share_count"] == 3
    assert response.body["summary"]["checkoutable_share_count"] == 1
    assert response.body["identity_policy"]["canonical_key"] == "issuer_user_ref"
    assert response.body["namespace_policy"]["family"] == "issuer-public-share-management"
    assert response.body["namespace_policy"]["member_namespace_policy"]["public_path_format"] == "/share/{share_id}"
    assert response.body["namespace_policy"]["member_namespace_policy"]["public_path_format"] == "/share/{share_id}"
    assert response.body["shares"][0]["identity"]["canonical_key"] == "share_id"
    assert [entry["share_id"] for entry in response.body["shares"]] == [
        "share-owner-active",
        "share-owner-expired",
        "share-owner-revoked",
    ]
    assert response.body["shares"][1]["lifecycle"]["state"] == "expired"
    assert response.body["shares"][2]["lifecycle"]["state"] == "revoked"
    assert response.body["governance_summary"]["total_action_report_count"] == 2
    assert response.body["management_capability_summary"]["revokable_share_count"] == 1
    assert response.body["management_capability_summary"]["archivable_share_count"] == 3
    assert response.body["bulk_action_availability"]["revoke"]["allowed"] is True
    assert response.body["shares"][0]["management_capability_summary"]["can_revoke"] is True
    assert response.body["shares"][1]["management_action_availability"]["revoke"]["allowed"] is False
    assert response.body["governance_summary"]["latest_action_report_at"] == "2026-04-15T14:00:00+00:00"
    assert [report["report_id"] for report in response.body["governance_summary"]["recent_action_reports"]] == [
        "share-report-http-002",
        "share-report-http-001",
    ]


def test_issuer_public_share_summary_route_returns_compact_management_summary() -> None:
    response = RunHttpRouteSurface.handle_get_issuer_public_share_summary(
        http_request=_auth_request(method="GET", path="/api/users/me/public-shares/summary"),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["summary"]["total_share_count"] == 3
    assert response.body["summary"]["latest_updated_at"] == "2026-04-15T12:30:00+00:00"
    assert response.body["governance_summary"]["total_share_count"] == 3
    assert response.body["governance_summary"]["total_action_report_count"] == 2
    assert response.body["governance_summary"]["delete_action_report_count"] == 1
    assert response.body["management_capability_summary"]["extendable_share_count"] == 1
    assert response.body["bulk_action_availability"]["delete"]["allowed"] is True
    assert response.body["governance_summary"]["latest_action_report_at"] == "2026-04-15T14:00:00+00:00"
    assert response.body["links"]["shares"] == "/api/users/me/public-shares"


def test_issuer_public_share_management_routes_apply_filters_and_pagination() -> None:
    response = RunHttpRouteSurface.handle_list_issuer_public_shares(
        http_request=_auth_request(
            method="GET",
            path="/api/users/me/public-shares",
            query_params={"lifecycle_state": "active", "operation": "checkout_working_copy", "limit": "1", "offset": "0"},
        ),
        share_payload_rows_provider=_issuer_share_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["summary"]["total_share_count"] == 1
    assert response.body["inventory_summary"]["total_share_count"] == 3
    assert response.body["pagination"]["filtered_share_count"] == 1
    assert response.body["pagination"]["returned_count"] == 1
    assert response.body["pagination"]["has_more"] is False
    assert response.body["applied_filters"]["lifecycle_state"] == "active"
    assert response.body["applied_filters"]["operation"] == "checkout_working_copy"
    assert [entry["share_id"] for entry in response.body["shares"]] == ["share-owner-active"]


def test_issuer_public_share_action_report_routes_return_filtered_results() -> None:
    response = RunHttpRouteSurface.handle_list_issuer_public_share_action_reports(
        http_request=_auth_request(method="GET", path="/api/users/me/public-shares/action-reports", query_params={"action": "delete", "limit": "1", "offset": "0"}),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["summary"]["total_report_count"] == 1
    assert response.body["inventory_summary"]["total_report_count"] == 2
    assert response.body["governance_summary"]["total_share_count"] == 3
    assert response.body["governance_summary"]["total_action_report_count"] == 2
    assert response.body["management_capability_summary"]["total_share_count"] == 3
    assert response.body["bulk_action_availability"]["archive"]["allowed"] is True
    assert response.body["reports"][0]["action"] == "delete"
    assert response.body["links"]["share_summary"] == "/api/users/me/public-shares/summary"


def test_issuer_public_share_action_report_routes_return_filtered_results() -> None:
    response = RunHttpRouteSurface.handle_list_issuer_public_share_action_reports(
        http_request=_auth_request(method="GET", path="/api/users/me/public-shares/action-reports", query_params={"action": "delete", "limit": "1", "offset": "0"}),
        share_payload_rows_provider=_issuer_share_rows,
        action_report_rows_provider=_issuer_action_report_rows,
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["summary"]["total_report_count"] == 1
    assert response.body["inventory_summary"]["total_report_count"] == 2
    assert response.body["governance_summary"]["total_share_count"] == 3
    assert response.body["governance_summary"]["total_action_report_count"] == 2
    assert response.body["reports"][0]["action"] == "delete"
    assert response.body["links"]["share_summary"] == "/api/users/me/public-shares/summary"


def test_issuer_public_share_management_revoke_action_updates_selected_shares() -> None:
    share_store = {
        "share-owner-action-a": export_public_nex_link_share(
            _commit_snapshot("snap-owner-action-a"),
            share_id="share-owner-action-a",
            title="Owner Action A",
            created_at="2026-04-15T12:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        "share-owner-action-b": export_public_nex_link_share(
            _commit_snapshot("snap-owner-action-b"),
            share_id="share-owner-action-b",
            title="Owner Action B",
            created_at="2026-04-15T12:05:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        "share-other-action-c": export_public_nex_link_share(
            _commit_snapshot("snap-other-action-c"),
            share_id="share-other-action-c",
            title="Other Action C",
            created_at="2026-04-15T12:10:00+00:00",
            issued_by_user_ref="user-other",
        ),
    }

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_revoke_issuer_public_shares(
        http_request=_auth_request(method="POST", path="/api/users/me/public-shares/actions/revoke", json_body={"share_ids": ["share-owner-action-a", "share-owner-action-b"]}),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["action"] == "revoke"
    assert response.body["affected_share_count"] == 2
    assert response.body["summary"]["revoked_share_count"] == 2
    assert response.body["action_report"]["action"] == "revoke"
    assert response.body["action_report"]["action"] == "revoke"
    assert share_store["share-owner-action-a"]["share"]["lifecycle"]["state"] == "revoked"
    assert share_store["share-owner-action-b"]["share"]["lifecycle"]["state"] == "revoked"
    assert share_store["share-other-action-c"]["share"]["lifecycle"]["state"] == "active"

def test_workspace_shell_checkout_accepts_public_share_snapshot() -> None:
    response = RunHttpRouteSurface.handle_checkout_workspace_shell(
        http_request=_auth_request(
            method="POST",
            path="/api/workspaces/ws-001/shell/checkout",
            path_params={"workspace_id": "ws-001"},
            json_body={"share_id": "share-http-001", "working_save_id": "ws-share-restored"},
        ),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "continuity_source": "server",
            "archived": False,
        },
        public_share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    assert response.body["storage_role"] == "working_save"
    assert response.body["working_save_id"] == "ws-share-restored"
    assert response.body["transition"]["source_share_id"] == "share-http-001"


def test_workspace_shell_share_creation_returns_persisted_public_share_descriptor() -> None:
    share_store: dict[str, dict] = {}

    def _writer(payload: dict) -> dict:
        share = payload.get("share", {}) if isinstance(payload.get("share"), dict) else {}
        share_store[str(share.get("share_id"))] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_create_workspace_shell_share(
        http_request=_auth_request(
            method="POST",
            path="/api/workspaces/ws-001/shell/share",
            path_params={"workspace_id": "ws-001"},
            json_body={"share_id": "share-created-http-001", "title": "Shared Workspace", "expires_at": "2026-04-20T00:00:00+00:00"},
        ),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "continuity_source": "server",
            "archived": False,
        },
        artifact_source=_commit_snapshot("snap-create-share-001"),
        public_share_payload_writer=_writer,
        now_iso="2026-04-15T12:30:00+00:00",
    )

    assert response.status_code == 201
    assert response.body["share_id"] == "share-created-http-001"
    assert response.body["lifecycle"]["state"] == "active"
    assert response.body["lifecycle"]["created_at"] == "2026-04-15T12:30:00+00:00"
    assert response.body["audit_summary"]["event_count"] == 1
    assert response.body["lifecycle"]["expires_at"] == "2026-04-20T00:00:00+00:00"
    assert response.body["lifecycle"]["issued_by_user_ref"] == "user-owner"
    assert response.body["source_artifact"]["canonical_ref"] == "snap-create-share-001"
    assert "share-created-http-001" in share_store


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
    assert response.body["identity_policy"]["surface_family"] == "circuit-library"
    assert response.body["namespace_policy"]["family"] == "circuit-library"
    assert response.body["library"]["returned_count"] == 1
    assert response.body["library"]["items"][0]["has_recent_result_history"] is True
    assert response.body["library"]["items"][0]["identity"]["canonical_value"] == "ws-001"
    assert response.body["item_sections"][0]["identity"]["canonical_value"] == "ws-001"
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


def test_starter_template_catalog_route_returns_public_template_exchange_surface() -> None:
    response = RunHttpRouteSurface.handle_list_starter_circuit_templates(
        http_request=HttpRouteRequest(method="GET", path="/api/templates/starter-circuits", query_params={"app_language": "ko"}),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["catalog"]["family"] == "starter-circuit-template-catalog"
    assert response.body["identity_policy"]["canonical_key"] == "template_ref"
    assert response.body["namespace_policy"]["canonical_ref_format"] == "{source}:{template_id}@{template_version}"
    template = next(item for item in response.body["templates"] if item["template_id"] == "text_summarizer")
    assert template["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert template["lookup_aliases"] == ["text_summarizer", "nexa-curated:text_summarizer@1.0"]
    assert template["identity"] == {"canonical_key": "template_ref", "canonical_value": "nexa-curated:text_summarizer@1.0", "legacy_key": "template_id", "legacy_value": "text_summarizer", "lookup_mode": "template_id_or_template_ref"}
    assert template["template_version"] == "1.0"
    assert template["curation_status"] == "curated"
    assert template["provenance"]["family"] == "starter-template"
    assert template["provenance"]["source"] == "nexa-curated"
    assert template["compatibility"]["family"] == "workspace-shell-draft"
    assert template["supported_storage_roles"] == ["working_save"]


def test_starter_template_detail_route_returns_one_template() -> None:
    response = RunHttpRouteSurface.handle_get_starter_circuit_template(
        http_request=HttpRouteRequest(
            method="GET",
            path="/api/templates/starter-circuits/nexa-curated: text_summarizer@1.0".replace(" ", ""),
            path_params={"template_id": "nexa-curated:text_summarizer@1.0"},
        ),
    )

    assert response.status_code == 200
    assert response.body["template"]["template_id"] == "text_summarizer"
    assert response.body["identity_policy"]["canonical_key"] == "template_ref"
    assert response.body["namespace_policy"]["family"] == "starter-template"
    assert response.body["template"]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert response.body["template"]["identity"]["canonical_value"] == "nexa-curated:text_summarizer@1.0"
    assert response.body["template"]["identity"]["canonical_value"] == "nexa-curated:text_summarizer@1.0"
    assert response.body["template"]["provenance"]["source"] == "nexa-curated"
    assert response.body["template"]["compatibility"]["apply_behavior"] == "replace_designer_request"
    assert response.body["routes"]["catalog"] == "/api/templates/starter-circuits"


def test_workspace_starter_template_catalog_route_returns_workspace_scoped_template_exchange_surface() -> None:
    response = RunHttpRouteSurface.handle_list_workspace_starter_circuit_templates(
        http_request=HttpRouteRequest(
            method="GET",
            path="/api/workspaces/ws-001/starter-templates",
            path_params={"workspace_id": "ws-001"},
            query_params={"app_language": "ko"},
        ),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "owner_user_id": "user-owner", "title": "Primary Workspace", "artifact_source": _working_save("ws-template-001")},
    )

    assert response.status_code == 200
    assert response.body["workspace_id"] == "ws-001"
    assert response.body["routes"]["self"] == "/api/workspaces/ws-001/starter-templates"
    template = next(item for item in response.body["templates"] if item["template_id"] == "text_summarizer")
    assert template["routes"]["self"] == "/api/workspaces/ws-001/starter-templates/text_summarizer"
    assert template["routes"]["workspace_apply"] == "/api/workspaces/ws-001/starter-templates/text_summarizer/apply"
    assert template["routes"]["global_detail"] == "/api/templates/starter-circuits/text_summarizer"


def test_workspace_starter_template_detail_route_returns_workspace_scoped_template_detail() -> None:
    response = RunHttpRouteSurface.handle_get_workspace_starter_circuit_template(
        http_request=HttpRouteRequest(
            method="GET",
            path="/api/workspaces/ws-001/starter-templates/nexa-curated:text_summarizer@1.0",
            path_params={"workspace_id": "ws-001", "template_id": "nexa-curated:text_summarizer@1.0"},
        ),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "owner_user_id": "user-owner", "title": "Primary Workspace", "artifact_source": _working_save("ws-template-001")},
    )

    assert response.status_code == 200
    assert response.body["workspace_id"] == "ws-001"
    assert response.body["template"]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert response.body["template"]["routes"]["workspace_catalog"] == "/api/workspaces/ws-001/starter-templates"
    assert response.body["routes"]["global_detail"] == "/api/templates/starter-circuits/text_summarizer"


def test_apply_starter_template_route_updates_workspace_shell_draft() -> None:
    workspace_row = {
        "workspace_id": "ws-001",
        "owner_user_id": "user-owner",
        "title": "Primary Workspace",
        "description": "Main",
        "artifact_source": _working_save("ws-template-001"),
    }
    response = RunHttpRouteSurface.handle_apply_starter_circuit_template(
        http_request=_auth_request(
            method="POST",
            path="/api/workspaces/ws-001/starter-templates/text_summarizer/apply",
            path_params={"workspace_id": "ws-001", "template_id": "text_summarizer"},
        ),
        workspace_context=_workspace(),
        workspace_row=workspace_row,
        artifact_source=_working_save("ws-template-001"),
        recent_run_rows=(),
        result_rows_by_run_id={},
        onboarding_rows=(),
        artifact_rows_lookup={},
        trace_rows_lookup={},
    )

    assert response.status_code == 200
    assert response.body["status"] == "accepted"
    assert response.body["identity_policy"]["canonical_key"] == "template_ref"
    assert response.body["namespace_policy"]["family"] == "starter-template"
    assert response.body["workspace_id"] == "ws-001"
    assert response.body["template"]["template_id"] == "text_summarizer"
    assert response.body["identity_policy"]["canonical_key"] == "template_ref"
    assert response.body["namespace_policy"]["family"] == "starter-template"
    assert response.body["template"]["template_ref"] == "nexa-curated:text_summarizer@1.0"
    assert response.body["template"]["compatibility"]["family"] == "workspace-shell-draft"
    assert response.body["template"]["supported_entry_surfaces"] == ["designer", "template_gallery"]
    assert response.body["shell"]["workspace_id"] == "ws-001"


def test_public_nex_format_route_returns_role_aware_standardization_surface() -> None:
    response = RunHttpRouteSurface.handle_public_nex_format(
        http_request=HttpRouteRequest(method="GET", path="/api/formats/public-nex"),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["format_boundary"]["format_family"] == ".nex"
    assert response.body["role_boundaries"]["working_save"]["identity_field"] == "working_save_id"
    assert response.body["role_boundaries"]["commit_snapshot"]["identity_field"] == "commit_id"
    operations = response.body["format_boundary"]["artifact_operation_boundaries"]
    assert any(entry["operation"] == "load_artifact" for entry in operations)
    assert response.body["public_sdk_entrypoints"]["load_artifact"] == "load_nex"
    assert response.body["public_sdk_entrypoints"]["import_copy"] == "import_public_nex_artifact"
    assert response.body["public_sdk_entrypoints"]["checkout_working_copy"] == "checkout_public_nex_working_copy"
    assert response.body["identity_policy"]["canonical_key"] == "format_boundary.format_family"
    assert response.body["namespace_policy"]["family"] == "public-nex-format"
    assert response.body["routes"]["public_share_artifact"] == "/api/public-shares/{share_id}/artifact"


def test_public_nex_format_route_rejects_wrong_method() -> None:
    response = RunHttpRouteSurface.handle_public_nex_format(
        http_request=HttpRouteRequest(method="POST", path="/api/formats/public-nex"),
    )

    assert response.status_code == 405
    assert response.body["reason_code"] == "route.method_not_allowed"

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
    assert response.body["identity_policy"]["surface_family"] == "workspace-result-history"
    assert response.body["namespace_policy"]["family"] == "workspace-result-history"
    assert response.body["result_history"]["returned_count"] == 1
    assert response.body["result_history"]["items"][0]["output_preview"] == "Latest Hello"
    assert response.body["result_history"]["items"][0]["identity"]["canonical_value"] == "run-002"
    assert response.body["routes"]["starter_template_catalog_page"] == '/app/workspaces/ws-001/starter-templates?app_language=en'
    assert response.body["item_sections"][0]["identity"]["canonical_value"] == "run-002"


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
    assert payload["identity_policy"]["surface_family"] == "workspace-feedback"
    assert payload["namespace_policy"]["family"] == "workspace-feedback"
    assert payload["feedback_channel"]["submit_path"] == "/api/workspaces/ws-001/feedback"
    assert payload["routes"]["origin_page"] == "/app/workspaces/ws-001/results?app_language=en&run_id=run-001"
    assert payload["routes"]["origin_label"] == "Back to results"
    assert payload["feedback_channel"]["items"][0]["feedback_id"] == "fb-001"
    assert payload["feedback_channel"]["items"][0]["identity"]["canonical_value"] == "fb-001"

    written = {}
    post_response = RunHttpRouteSurface.handle_submit_workspace_feedback(
        http_request=_auth_request(method="POST", path="/api/workspaces/ws-001/feedback", path_params={"workspace_id": "ws-001"}, json_body={"category": "bug_report", "surface": "starter_templates", "message": "This screen failed unexpectedly.", "run_id": "run-001"}),
        workspace_context=_workspace(),
        workspace_row={"workspace_id": "ws-001", "title": "Primary Workspace", "owner_user_id": "user-owner", "created_at": "2026-04-11T11:59:00+00:00", "updated_at": "2026-04-11T12:01:00+00:00"},
        feedback_writer=lambda row: written.setdefault("row", dict(row)),
        feedback_id_factory=lambda: "fb-002",
        now_iso="2026-04-14T08:10:00+00:00",
    )
    assert post_response.status_code == 202
    submit_payload = post_response.body
    assert submit_payload["workspace_id"] == "ws-001"
    assert submit_payload["identity_policy"]["surface_family"] == "workspace-feedback"
    assert submit_payload["namespace_policy"]["family"] == "workspace-feedback"
    assert submit_payload["feedback"]["feedback_id"] == "fb-002"
    assert submit_payload["feedback"]["identity"]["canonical_value"] == "fb-002"
    assert written["row"]["surface"] == "starter_templates"


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


def test_workspace_feedback_payload_preserves_starter_template_detail_origin_navigation() -> None:
    payload = RunHttpRouteSurface.handle_workspace_feedback(
        http_request=_auth_request(method='GET', path='/api/workspaces/ws-001/feedback', path_params={'workspace_id': 'ws-001'}, query_params={'surface': 'starter_templates', 'template_id': 'text_summarizer'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        feedback_rows=(),
    ).body
    assert payload['routes']['origin_page'] == '/app/workspaces/ws-001/starter-templates/text_summarizer?app_language=en'
    assert payload['routes']['origin_label'] == 'Back to starter template'


def test_workspace_shell_payload_exposes_role_aware_action_availability() -> None:
    payload = RunHttpRouteSurface.handle_workspace_shell(
        http_request=_auth_request(method='GET', path='/api/workspaces/ws-001/shell', path_params={'workspace_id': 'ws-001'}),
        workspace_context=_workspace(),
        workspace_row={'workspace_id': 'ws-001', 'owner_user_id': 'user-owner', 'title': 'Primary Workspace', 'description': 'Main'},
        artifact_source=_commit_snapshot('snap-http-actions-001'),
        provider_binding_rows=({
            'binding_id': 'binding-http-001',
            'workspace_id': 'ws-001',
            'provider_key': 'openai',
            'provider_family': 'openai',
            'display_name': 'OpenAI GPT',
            'credential_source': 'managed',
            'enabled': True,
            'created_at': '2026-04-11T12:00:00+00:00',
            'updated_at': '2026-04-11T12:05:00+00:00',
            'updated_by_user_id': 'user-owner',
        },),
        managed_secret_rows=({
            'workspace_id': 'ws-001',
            'provider_key': 'openai',
            'secret_ref': 'secret://ws-001/openai',
            'last_rotated_at': '2026-04-11T12:06:00+00:00',
        },),
        provider_probe_rows=({
            'probe_event_id': 'probe-http-001',
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
        feedback_rows=({
            'feedback_id': 'fb-shell-http-001',
            'user_id': 'user-owner',
            'workspace_id': 'ws-001',
            'workspace_title': 'Primary Workspace',
            'category': 'friction_note',
            'surface': 'workspace_shell',
            'message': 'Please show recent feedback in the shell.',
            'status': 'received',
            'created_at': '2026-04-15T12:16:00+00:00',
        },),
    ).body
    assert payload['storage_role'] == 'commit_snapshot'
    assert payload['action_availability']['draft_write']['allowed'] is False
    assert payload['action_availability']['checkout']['allowed'] is True
    assert payload['action_availability']['launch']['allowed'] is True
    assert payload['routes']['workspace_recent_activity'] == '/api/users/me/activity?workspace_id=ws-001'
    assert payload['routes']['workspace_history_summary'] == '/api/users/me/history-summary?workspace_id=ws-001'
    assert payload['routes']['workspace_result_history'] == '/api/workspaces/ws-001/result-history'
    assert payload['routes']['workspace_result_history_page'] == '/app/workspaces/ws-001/results?app_language=en'
    assert payload['routes']['circuit_library'] == '/api/workspaces/ws-001/library'
    assert payload['routes']['circuit_library_page'] == '/app/library?app_language=en'
    assert payload['routes']['starter_template_catalog'] == '/api/templates/starter-circuits'
    assert payload['routes']['starter_template_catalog_page'] == '/app/workspaces/ws-001/starter-templates?app_language=en'
    assert payload['recent_activity_section']['summary']['headline'] == 'Recent activity'
    assert payload['history_summary_section']['summary']['headline'] == 'History summary'
    assert payload['routes']['workspace_provider_bindings'] == '/api/workspaces/ws-001/provider-bindings'
    assert payload['routes']['workspace_provider_health'] == '/api/workspaces/ws-001/provider-bindings/health'
    assert payload['routes']['workspace_feedback'] == '/api/workspaces/ws-001/feedback'
    assert payload['routes']['workspace_feedback_page'] == '/app/workspaces/ws-001/feedback'
    assert payload['feedback_continuity_section']['summary']['headline'] == 'Feedback continuity'
    assert 'Feedback items: 1' in payload['feedback_continuity_section']['summary']['lines']
    assert 'friction_note — workspace_shell — received — fb-shell-http-001' in '\n'.join(payload['feedback_continuity_section']['detail']['items'])
    assert payload['provider_readiness_section']['summary']['headline'] == 'Provider readiness'
    assert 'Configured providers: 1' in payload['provider_readiness_section']['summary']['lines']


def test_public_share_artifact_route_rejects_effectively_expired_share() -> None:
    response = RunHttpRouteSurface.handle_get_public_share_artifact(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-expired-http/artifact", path_params={"share_id": "share-expired-http"}),
        share_payload_provider=lambda share_id: export_public_nex_link_share(
            _commit_snapshot("snap-share-expired-http"),
            share_id=share_id,
            title="Expired share",
            created_at="2026-04-15T12:00:00+00:00",
            expires_at="2026-04-10T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
    )

    assert response.status_code == 409
    assert response.body["reason_code"] == "public_share.download_not_allowed"


def test_public_share_revoke_route_updates_lifecycle_for_issuer() -> None:
    share_store: dict[str, dict] = {"share-revoke-http-001": _share_payload("share-revoke-http-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_revoke_public_share(
        http_request=_auth_request(method="POST", path="/api/public-shares/share-revoke-http-001/revoke", path_params={"share_id": "share-revoke-http-001"}),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["lifecycle"]["state"] == "revoked"
    assert response.body["lifecycle"]["updated_at"] == "2026-04-15T13:00:00+00:00"
    assert response.body["action_report"]["action"] == "revoke"
    assert response.body["governance_summary"]["total_share_count"] == 1
    assert response.body["governance_summary"]["total_action_report_count"] == 3
    assert response.body["share_boundary"]["share_family"] == "nex.public-link-share"
    assert response.body["share_boundary"]["management_operation_boundaries"][3]["operation"] == "archive"
    assert response.body["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert response.body["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert response.body["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["result_surface"] == "public_share_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"
    assert response.body["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"
    assert share_store["share-revoke-http-001"]["share"]["lifecycle"]["state"] == "revoked"


def test_public_share_revoke_route_rejects_non_issuer() -> None:
    response = RunHttpRouteSurface.handle_revoke_public_share(
        http_request=_auth_request(method="POST", path="/api/public-shares/share-http-001/revoke", path_params={"share_id": "share-http-001"}, user_id="user-other"),
        share_payload_provider=lambda share_id: _share_payload(share_id),
        public_share_payload_writer=lambda payload: dict(payload),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 403
    assert response.body["reason_code"] == "public_share.forbidden"


def test_public_share_extend_route_updates_expiration_for_issuer() -> None:
    share_store: dict[str, dict] = {"share-extend-http-001": _share_payload("share-extend-http-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_extend_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-extend-http-001/extend",
            path_params={"share_id": "share-extend-http-001"},
            json_body={"expires_at": "2026-04-20T00:00:00+00:00"},
        ),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:30:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["lifecycle"]["stored_state"] == "active"
    assert response.body["lifecycle"]["state"] == "active"
    assert response.body["lifecycle"]["expires_at"] == "2026-04-20T00:00:00+00:00"
    assert response.body["action_report"]["action"] == "extend_expiration"
    assert response.body["governance_summary"]["total_share_count"] == 1
    assert response.body["governance_summary"]["total_action_report_count"] == 3
    assert response.body["share_boundary"]["share_family"] == "nex.public-link-share"
    assert response.body["share_boundary"]["public_operation_boundaries"][3]["operation"] == "run_artifact"
    assert response.body["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert response.body["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert response.body["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["result_surface"] == "public_share_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"
    assert response.body["links"]["action_report_summary"] == "/api/users/me/public-shares/action-reports/summary"


def test_public_share_extend_route_rejects_effectively_expired_share() -> None:
    response = RunHttpRouteSurface.handle_extend_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-expired-http/extend",
            path_params={"share_id": "share-expired-http"},
            json_body={"expires_at": "2026-04-25T00:00:00+00:00"},
        ),
        share_payload_provider=lambda share_id: export_public_nex_link_share(
            _commit_snapshot("snap-expired-http-extend-001"),
            share_id=share_id,
            title="Expired HTTP Share",
            created_at="2026-04-15T12:00:00+00:00",
            expires_at="2026-04-10T00:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        public_share_payload_writer=lambda payload: payload,
        now_iso="2026-04-15T13:30:00+00:00",
    )

    assert response.status_code == 409
    assert response.body["reason_code"] == "public_share.transition_not_allowed"



def test_public_share_archive_route_updates_archive_state_for_issuer() -> None:
    share_store: dict[str, dict] = {"share-archive-http-001": _share_payload("share-archive-http-001")}

    def _writer(payload: dict) -> dict:
        share_store[payload["share"]["share_id"]] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_archive_public_share(
        http_request=_auth_request(method="POST", path="/api/public-shares/share-archive-http-001/archive", path_params={"share_id": "share-archive-http-001"}, json_body={"archived": True}),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_writer=_writer,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:45:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["management"]["archived"] is True
    assert response.body["action_report"]["action"] == "archive"
    assert response.body["governance_summary"]["total_share_count"] == 1
    assert response.body["governance_summary"]["total_action_report_count"] == 3
    assert response.body["share_boundary"]["share_family"] == "nex.public-link-share"
    assert response.body["artifact_boundary"]["role_boundary"]["identity_field"] == "commit_id"
    assert response.body["artifact_boundary"]["role_boundary"]["editor_continuity_posture"] == "ui_forbidden_in_canonical_snapshot"
    assert response.body["artifact_boundary"]["role_boundary"]["commit_boundary_posture"] == "already_crossed_commit_boundary"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["operation"] == "load_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_http_method"] == "GET"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["canonical_route"] == "/api/public-shares/{share_id}/artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][0]["result_surface"] == "public_share_artifact"
    assert response.body["artifact_boundary"]["artifact_operation_boundaries"][4]["execution_anchor_posture"] == "working_save_runs_as_draft__commit_snapshot_runs_as_approved_anchor"
    assert response.body["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"


def test_public_share_history_route_returns_audit_entries() -> None:
    response = RunHttpRouteSurface.handle_get_public_share_history(
        http_request=HttpRouteRequest(method="GET", path="/api/public-shares/share-http-001/history", path_params={"share_id": "share-http-001"}),
        share_payload_provider=lambda share_id: _share_payload(share_id),
    )

    assert response.status_code == 200
    assert response.body["audit_summary"]["event_count"] == 1
    assert response.body["history"][0]["event_type"] == "created"
    assert response.body["share_boundary"]["share_family"] == "nex.public-link-share"
    assert response.body["share_boundary"]["history_access_posture"] == "public_audit_history"
    assert response.body["share_boundary"]["history_boundary"]["canonical_http_method"] == "GET"
    assert response.body["identity"]["share_family"] == "public_nex_link_share"
    assert response.body["share_boundary"]["history_boundary"]["canonical_route"] == "/api/public-shares/{share_id}/history"
    assert response.body["share_boundary"]["history_boundary"]["result_surface"] == "public_share_history"
    assert response.body["share_boundary"]["history_boundary"]["entry_boundary"]["entry_surface"] == "public_share_audit_entry"
    assert response.body["artifact_boundary"]["role_boundary"]["storage_role"] == "commit_snapshot"


def test_issuer_public_share_management_delete_action_removes_selected_shares() -> None:
    share_store = {
        "share-owner-delete-a": export_public_nex_link_share(_commit_snapshot("snap-owner-delete-a"), share_id="share-owner-delete-a", title="Owner Delete A", created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner"),
        "share-owner-delete-b": export_public_nex_link_share(_commit_snapshot("snap-owner-delete-b"), share_id="share-owner-delete-b", title="Owner Delete B", created_at="2026-04-15T12:05:00+00:00", issued_by_user_ref="user-owner"),
        "share-other-delete-c": export_public_nex_link_share(_commit_snapshot("snap-other-delete-c"), share_id="share-other-delete-c", title="Other Delete C", created_at="2026-04-15T12:10:00+00:00", issued_by_user_ref="user-other"),
    }

    response = RunHttpRouteSurface.handle_delete_issuer_public_shares(
        http_request=_auth_request(method="POST", path="/api/users/me/public-shares/actions/delete", json_body={"share_ids": ["share-owner-delete-a", "share-owner-delete-b"]}),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_writer=lambda row: dict(row),
        now_iso="2026-04-15T13:00:00+00:00",
    )

    assert response.status_code == 200
    assert response.body["action"] == "delete"
    assert response.body["affected_share_count"] == 2
    assert response.body["summary"]["total_share_count"] == 0
    assert response.body["governance_summary"]["total_share_count"] == 0
    assert response.body["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"
    assert "share-owner-delete-a" not in share_store
    assert "share-owner-delete-b" not in share_store
    assert "share-other-delete-c" in share_store


def test_public_share_delete_route_removes_share_for_issuer() -> None:
    share_store = {"share-delete-http-001": _share_payload("share-delete-http-001")}

    response = RunHttpRouteSurface.handle_delete_public_share(
        http_request=_auth_request(method="DELETE", path="/api/public-shares/share-delete-http-001", path_params={"share_id": "share-delete-http-001"}),
        share_payload_provider=lambda share_id: share_store.get(share_id),
        share_payload_rows_provider=lambda: tuple(share_store.values()),
        action_report_rows_provider=_issuer_action_report_rows,
        public_share_payload_deleter=lambda share_id: share_store.pop(share_id, None) is not None,
        public_share_action_report_writer=lambda row: dict(row),
    )

    assert response.status_code == 200
    assert response.body["status"] == "deleted"
    assert response.body["share_id"] == "share-delete-http-001"
    assert response.body["identity"]["canonical_key"] == "share_id"
    assert response.body["action_report"]["action"] == "delete"
    assert response.body["governance_summary"]["total_share_count"] == 0
    assert response.body["governance_summary"]["total_action_report_count"] == 3
    assert response.body["links"]["action_reports"] == "/api/users/me/public-shares/action-reports"
    assert "share-delete-http-001" not in share_store


def test_public_mcp_manifest_route_returns_manifest_export_surface() -> None:
    response = RunHttpRouteSurface.handle_public_mcp_manifest(
        http_request=HttpRouteRequest(method="GET", path="/api/integrations/public-mcp/manifest", query_params={"base_url": "https://api.nexa.test"}),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["manifest"]["server"]["name"] == "nexa-public"
    assert response.body["identity_policy"]["canonical_key"] == "manifest.server.name"
    assert response.body["namespace_policy"]["family"] == "public-mcp-manifest"
    assert response.body["routes"]["host_bridge"] == "/api/integrations/public-mcp/host-bridge"


def test_public_mcp_host_bridge_route_returns_host_bridge_export_surface() -> None:
    response = RunHttpRouteSurface.handle_public_mcp_host_bridge(
        http_request=HttpRouteRequest(method="GET", path="/api/integrations/public-mcp/host-bridge", query_params={"base_url": "https://api.nexa.test"}),
    )

    assert response.status_code == 200
    assert response.body["status"] == "ready"
    assert response.body["host_bridge"]["framework_binding_class"] == "FrameworkRouteBindings"
    assert response.body["identity_policy"]["canonical_key"] == "host_bridge.framework_binding_class"
    assert response.body["namespace_policy"]["family"] == "public-mcp-host-bridge"
    assert response.body["routes"]["manifest"] == "/api/integrations/public-mcp/manifest"


def test_workspace_public_share_creation_returns_persisted_public_share_descriptor() -> None:
    share_store: dict[str, dict] = {}

    def _writer(payload: dict) -> dict:
        share = payload.get("share", {}) if isinstance(payload.get("share"), dict) else {}
        share_store[str(share.get("share_id"))] = dict(payload)
        return dict(payload)

    response = RunHttpRouteSurface.handle_create_workspace_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/workspaces/ws-001/shares",
            path_params={"workspace_id": "ws-001"},
            json_body={"share_id": "share-created-http-002", "title": "Shared Workspace Family", "expires_at": "2026-04-21T00:00:00+00:00"},
        ),
        workspace_context=_workspace(),
        workspace_row={
            "workspace_id": "ws-001",
            "owner_user_id": "user-owner",
            "title": "Primary Workspace",
            "continuity_source": "server",
            "archived": False,
        },
        artifact_source=_commit_snapshot("snap-create-share-002"),
        public_share_payload_writer=_writer,
        now_iso="2026-04-15T12:31:00+00:00",
    )

    assert response.status_code == 201
    assert response.body["share_id"] == "share-created-http-002"
    assert response.body["links"]["workspace_public_share_create"] == "/api/workspaces/ws-001/shares"
    assert response.body["links"]["workspace_shell_share"] == "/api/workspaces/ws-001/shares"
    assert response.body["links"]["workspace_shell_share_legacy"] == "/api/workspaces/ws-001/shell/share"
    assert "share-created-http-002" in share_store


def test_import_public_share_route_uses_canonical_public_import_helper(monkeypatch) -> None:
    share_payload = _share_payload("share-import-route-001")

    import src.storage.nex_api as nex_api

    original = nex_api.import_public_nex_artifact
    calls = {"count": 0}

    def _wrapped(model_or_data, **kwargs):
        calls["count"] += 1
        return original(model_or_data, **kwargs)

    monkeypatch.setattr(nex_api, "import_public_nex_artifact", _wrapped)

    written: dict[str, dict] = {}

    response = RunHttpRouteSurface.handle_import_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-import-route-001/import",
            path_params={"share_id": "share-import-route-001"},
            json_body={"workspace_id": "ws-001"},
        ),
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "owner_user_id": "user-owner", "title": "Primary Workspace", "continuity_source": "server", "archived": False} if workspace_id == "ws-001" else None,
        workspace_artifact_source_writer=lambda workspace_id, source: written.setdefault(workspace_id, dict(source)),
        public_share_payload_provider=lambda share_id: share_payload if share_id == "share-import-route-001" else None,
    )

    assert response.status_code == 200
    assert calls["count"] == 1
    assert response.body["storage_role"] == "commit_snapshot"
    assert written["ws-001"]["meta"]["storage_role"] == "commit_snapshot"


def test_checkout_public_share_route_uses_canonical_public_checkout_helper(monkeypatch) -> None:
    share_payload = _share_payload("share-checkout-route-001")

    import src.storage.nex_api as nex_api

    original = nex_api.checkout_public_nex_working_copy
    calls = {"count": 0}

    def _wrapped(model_or_data, **kwargs):
        calls["count"] += 1
        return original(model_or_data, **kwargs)

    monkeypatch.setattr(nex_api, "checkout_public_nex_working_copy", _wrapped)

    written: dict[str, dict] = {}

    response = RunHttpRouteSurface.handle_checkout_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-checkout-route-001/checkout",
            path_params={"share_id": "share-checkout-route-001"},
            json_body={"workspace_id": "ws-001", "working_save_id": "ws-from-share-route"},
        ),
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "owner_user_id": "user-owner", "title": "Primary Workspace", "continuity_source": "server", "archived": False} if workspace_id == "ws-001" else None,
        workspace_run_rows_provider=lambda workspace_id: (),
        workspace_result_rows_provider=lambda workspace_id: {},
        onboarding_rows_provider=lambda: (),
        workspace_artifact_source_provider=lambda workspace_id: _commit_snapshot("snap-existing-workspace") if workspace_id == "ws-001" else None,
        workspace_artifact_source_writer=lambda workspace_id, source: written.setdefault(workspace_id, dict(source)),
        public_share_payload_provider=lambda share_id: share_payload if share_id == "share-checkout-route-001" else None,
        share_payload_rows_provider=lambda: (),
        provider_binding_rows_provider=lambda workspace_id: (),
        managed_secret_rows_provider=lambda: (),
        provider_probe_rows_provider=lambda workspace_id: (),
        feedback_rows_provider=lambda: (),
    )

    assert response.status_code == 200
    assert calls["count"] == 1
    assert response.body["storage_role"] == "working_save"
    assert written["ws-001"]["meta"]["storage_role"] == "working_save"


def test_create_workspace_from_public_share_checkout_mode_uses_canonical_public_checkout_helper(monkeypatch) -> None:
    share_payload = _share_payload("share-create-workspace-route-001")

    import src.storage.nex_api as nex_api

    original = nex_api.checkout_public_nex_working_copy
    calls = {"count": 0}

    def _wrapped(model_or_data, **kwargs):
        calls["count"] += 1
        return original(model_or_data, **kwargs)

    monkeypatch.setattr(nex_api, "checkout_public_nex_working_copy", _wrapped)

    written: dict[str, dict] = {}

    response = RunHttpRouteSurface.handle_create_workspace_from_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-create-workspace-route-001/create-workspace",
            path_params={"share_id": "share-create-workspace-route-001"},
            json_body={"create_mode": "checkout_working_copy", "working_save_id": "ws-created-from-share"},
        ),
        workspace_id_factory=lambda: "ws-created-001",
        membership_id_factory=lambda: "member-created-001",
        now_iso="2026-04-15T12:00:00+00:00",
        workspace_rows_provider=lambda: (),
        membership_rows_provider=lambda: (),
        recent_run_rows_provider=lambda: (),
        recent_provider_binding_rows_provider=lambda: (),
        managed_secret_rows_provider=lambda: (),
        recent_provider_probe_rows_provider=lambda: (),
        onboarding_rows_provider=lambda: (),
        workspace_registry_writer=lambda workspace, membership: {"workspace": dict(workspace), "membership": dict(membership)},
        workspace_artifact_source_writer=lambda workspace_id, source: written.setdefault(workspace_id, dict(source)),
        public_share_payload_provider=lambda share_id: share_payload if share_id == "share-create-workspace-route-001" else None,
    )

    assert response.status_code == 201
    assert calls["count"] == 1
    assert response.body["storage_role"] == "working_save"
    assert response.body["workspace_id"] == "ws-created-001"
    assert written["ws-created-001"]["meta"]["storage_role"] == "working_save"


def test_run_public_share_route_uses_canonical_public_runtime_target_helper(monkeypatch) -> None:
    share_payload = _share_payload("share-run-route-001")

    import src.storage.nex_api as nex_api

    original = nex_api.resolve_public_nex_execution_target
    calls = {"count": 0}

    def _wrapped(model_or_data, **kwargs):
        calls["count"] += 1
        return original(model_or_data, **kwargs)

    monkeypatch.setattr(nex_api, "resolve_public_nex_execution_target", _wrapped)

    response = RunHttpRouteSurface.handle_run_public_share(
        http_request=_auth_request(
            method="POST",
            path="/api/public-shares/share-run-route-001/run",
            path_params={"share_id": "share-run-route-001"},
            json_body={"workspace_id": "ws-001", "input_payload": {"text": "hello"}},
        ),
        workspace_context_provider=lambda workspace_id: _workspace() if workspace_id == "ws-001" else None,
        workspace_row_provider=lambda workspace_id: {"workspace_id": workspace_id, "owner_user_id": "user-owner", "title": "Primary Workspace", "continuity_source": "server", "archived": False} if workspace_id == "ws-001" else None,
        public_share_payload_provider=lambda share_id: share_payload if share_id == "share-run-route-001" else None,
        target_catalog_provider=lambda workspace_id: {},
        policy=ProductAdmissionPolicy(allow_working_save_execution=True),
        engine_launch_decider=lambda payload: EngineLaunchAdapter.accepted(run_id="run-public-share-001", initial_status="queued"),
        run_id_factory=lambda: "run-public-share-001",
    )

    assert response.status_code == 202
    assert calls["count"] == 1


def test_public_nex_format_route_exposes_runtime_target_sdk_entrypoint() -> None:
    response = RunHttpRouteSurface.handle_public_nex_format(http_request=HttpRouteRequest(method="GET", path="/api/formats/public-nex"))

    assert response.status_code == 200
    assert response.body["public_sdk_entrypoints"]["run_artifact"] == "resolve_public_nex_execution_target"
