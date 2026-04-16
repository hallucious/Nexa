from __future__ import annotations

import json

import pytest

from src.storage.lifecycle_api import create_commit_snapshot_from_working_save
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.storage.share_api import (
    archive_public_nex_link_shares_for_issuer,
    delete_public_nex_link_shares_for_issuer,
    describe_public_nex_link_share,
    ensure_public_nex_link_share_operation_allowed,
    export_public_nex_link_share,
    extend_public_nex_link_share_expiration,
    extend_public_nex_link_shares_for_issuer_expiration,
    get_public_nex_share_boundary,
    list_public_nex_link_share_audit_history,
    load_public_nex_link_share,
    revoke_public_nex_link_share,
    revoke_public_nex_link_shares_for_issuer,
    save_public_nex_link_share_file,
    summarize_issuer_public_share_governance_for_issuer,
    update_public_nex_link_share_archive,
)


def _working_save(*, name: str = "share_demo", description: str = "shareable artifact") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-share-1",
            name=name,
            description=description,
        ),
        circuit=CircuitModel(
            entry="node1",
            nodes=[
                {
                    "id": "node1",
                    "type": "plugin",
                    "resource_ref": {"plugin": "plugin.main"},
                    "inputs": {"text": "state.input.text"},
                    "outputs": {"result": "output.value"},
                }
            ],
            edges=[],
            outputs=[{"name": "result", "node_id": "node1", "path": "output.value"}],
        ),
        resources=ResourcesModel(
            prompts={},
            providers={},
            plugins={"plugin.main": {"entry": "plugins.example.run", "config": {}}},
        ),
        state=StateModel(input={"text": "hello"}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def test_get_public_nex_share_boundary_declares_bounded_link_surface() -> None:
    boundary = get_public_nex_share_boundary()

    assert boundary.share_family == "nex.public-link-share"
    assert boundary.transport_modes == ("link",)
    assert boundary.access_modes == ("public_readonly",)
    assert boundary.public_access_posture == "anonymous_readonly"
    assert boundary.management_access_posture == "issuer_authenticated_lifecycle_management"
    assert boundary.history_access_posture == "public_audit_history"
    assert boundary.artifact_access_posture == "capability_bounded_artifact_access"
    assert tuple(entry.operation for entry in boundary.public_operation_boundaries) == (
        "inspect_metadata",
        "download_artifact",
        "import_copy",
        "run_artifact",
        "checkout_working_copy",
    )
    assert boundary.public_operation_boundaries[0].posture == "anonymous_public_metadata_read"
    assert boundary.public_operation_boundaries[0].requires_authentication is False
    assert tuple(entry.operation for entry in boundary.management_operation_boundaries) == (
        "revoke",
        "extend_expiration",
        "delete",
        "archive",
    )
    assert all(entry.requires_authentication for entry in boundary.management_operation_boundaries)
    assert all(entry.requires_issuer_scope for entry in boundary.management_operation_boundaries)
    assert boundary.supported_roles == ("working_save", "commit_snapshot")
    assert boundary.artifact_format_family == ".nex"
    assert boundary.viewer_capabilities == ("inspect_metadata", "download_artifact", "import_copy")
    assert boundary.supported_operations == ("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy")
    assert boundary.supported_lifecycle_states == ("active", "expired", "revoked")
    assert boundary.terminal_lifecycle_states == ("expired", "revoked")
    assert boundary.management_operations == ("revoke", "extend_expiration", "delete", "archive")


def test_export_public_nex_link_share_is_deterministic_for_same_artifact() -> None:
    share_a = export_public_nex_link_share(_working_save(), created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner")
    share_b = export_public_nex_link_share(_working_save(), title="ignored title override", created_at="2026-04-15T12:00:00+00:00", issued_by_user_ref="user-owner")

    assert share_a["share"]["share_id"] == share_b["share"]["share_id"]
    assert share_a["share"]["transport"] == "link"
    assert share_a["share"]["access_mode"] == "public_readonly"
    assert share_a["share"]["storage_role"] == "working_save"
    assert share_a["share"]["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"]
    assert share_a["share"]["lifecycle"]["state"] == "active"
    assert share_a["share"]["lifecycle"]["created_at"] == "2026-04-15T12:00:00+00:00"
    assert share_a["share"]["lifecycle"]["issued_by_user_ref"] == "user-owner"
    assert share_a["share"]["management"]["archived"] is False
    assert share_a["share"]["audit"]["history"][0]["event_type"] == "created"
    assert share_a["artifact"]["meta"]["storage_role"] == "working_save"


def test_load_public_nex_link_share_round_trips_commit_snapshot() -> None:
    snapshot = create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-share-1")
    payload = export_public_nex_link_share(snapshot, title="Published snapshot")

    loaded = load_public_nex_link_share(payload)
    descriptor = describe_public_nex_link_share(loaded)

    assert loaded["artifact"]["meta"]["storage_role"] == "commit_snapshot"
    assert descriptor.share_id == payload["share"]["share_id"]
    assert descriptor.share_path == f"/share/{descriptor.share_id}"
    assert descriptor.storage_role == "commit_snapshot"
    assert descriptor.operation_capabilities == ("inspect_metadata", "download_artifact", "import_copy", "run_artifact", "checkout_working_copy")
    assert descriptor.canonical_ref == "commit-share-1"
    assert descriptor.lifecycle_state == "active"
    assert descriptor.source_working_save_id == "ws-share-1"


def test_load_public_nex_link_share_rejects_invalid_transport() -> None:
    payload = export_public_nex_link_share(_working_save())
    payload["share"]["transport"] = "file"

    with pytest.raises(ValueError, match="transport=link"):
        load_public_nex_link_share(payload)


def test_save_public_nex_link_share_file_writes_loadable_bundle(tmp_path) -> None:
    output_path = tmp_path / "public_share.json"

    written = save_public_nex_link_share_file(_working_save(), output_path)

    assert written == output_path
    raw = json.loads(output_path.read_text(encoding="utf-8"))
    loaded = load_public_nex_link_share(raw)
    assert loaded["share"]["share_id"].startswith("share_")
    assert loaded["share"]["title"] == "share_demo"


def test_load_public_nex_link_share_canonicalizes_operation_capabilities() -> None:
    payload = export_public_nex_link_share(_working_save())
    payload["share"]["operation_capabilities"] = ["checkout_working_copy"]

    loaded = load_public_nex_link_share(payload)

    assert loaded["share"]["operation_capabilities"] == ["inspect_metadata", "download_artifact", "import_copy", "run_artifact"]


def test_ensure_public_nex_link_share_operation_allowed_rejects_checkout_for_working_save() -> None:
    payload = export_public_nex_link_share(_working_save())

    with pytest.raises(ValueError, match="checkout_working_copy"):
        ensure_public_nex_link_share_operation_allowed(payload, "checkout_working_copy")


def test_ensure_public_nex_link_share_operation_allowed_accepts_checkout_for_commit_snapshot() -> None:
    payload = export_public_nex_link_share(create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-op-1"))

    descriptor = ensure_public_nex_link_share_operation_allowed(payload, "checkout_working_copy")

    assert descriptor.storage_role == "commit_snapshot"



def test_load_public_nex_link_share_canonicalizes_lifecycle_metadata() -> None:
    payload = export_public_nex_link_share(_working_save())
    payload["share"]["lifecycle"] = {
        "state": "active",
        "created_at": "2026-04-15T13:00:00+00:00",
        "updated_at": "2026-04-15T13:05:00+00:00",
        "expires_at": "2026-04-20T00:00:00+00:00",
        "issued_by_user_ref": "user-share",
    }

    loaded = load_public_nex_link_share(payload)
    descriptor = describe_public_nex_link_share(loaded)

    assert loaded["share"]["lifecycle"]["created_at"] == "2026-04-15T13:00:00+00:00"
    assert descriptor.updated_at == "2026-04-15T13:05:00+00:00"
    assert descriptor.expires_at == "2026-04-20T00:00:00+00:00"
    assert descriptor.issued_by_user_ref == "user-share"


def test_ensure_public_nex_link_share_operation_allowed_rejects_expired_share() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-expired-1"),
        lifecycle_state="expired",
    )

    with pytest.raises(ValueError, match="not active"):
        ensure_public_nex_link_share_operation_allowed(payload, "checkout_working_copy")


def test_describe_public_nex_link_share_marks_expired_when_expires_at_is_in_past() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-expiry-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-10T00:00:00+00:00",
    )

    descriptor = describe_public_nex_link_share(payload)

    assert descriptor.lifecycle_state == "expired"


def test_revoke_public_nex_link_share_updates_lifecycle_state_and_timestamp() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-revoke-1"),
        created_at="2026-04-15T12:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    revoked = revoke_public_nex_link_share(payload, now_iso="2026-04-15T14:00:00+00:00")
    descriptor = describe_public_nex_link_share(revoked, now_iso="2026-04-15T14:00:00+00:00")

    assert revoked["share"]["lifecycle"]["state"] == "revoked"
    assert revoked["share"]["lifecycle"]["updated_at"] == "2026-04-15T14:00:00+00:00"
    assert descriptor.lifecycle_state == "revoked"


def test_describe_public_nex_link_share_preserves_stored_state_when_effectively_expired() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-stored-expiry-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-10T00:00:00+00:00",
    )

    descriptor = describe_public_nex_link_share(payload)

    assert descriptor.stored_lifecycle_state == "active"
    assert descriptor.lifecycle_state == "expired"


def test_extend_public_nex_link_share_expiration_updates_future_expiry_for_active_share() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-extend-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-20T00:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    extended = extend_public_nex_link_share_expiration(
        payload,
        expires_at="2026-04-25T00:00:00+00:00",
        now_iso="2026-04-15T13:00:00+00:00",
    )
    descriptor = describe_public_nex_link_share(extended, now_iso="2026-04-15T13:00:00+00:00")

    assert extended["share"]["lifecycle"]["expires_at"] == "2026-04-25T00:00:00+00:00"
    assert descriptor.stored_lifecycle_state == "active"
    assert descriptor.lifecycle_state == "active"


def test_extend_public_nex_link_share_expiration_rejects_effectively_expired_share() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-expired-extend-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-10T00:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    with pytest.raises(ValueError, match="terminal"):
        extend_public_nex_link_share_expiration(
            payload,
            expires_at="2026-04-25T00:00:00+00:00",
            now_iso="2026-04-15T13:00:00+00:00",
        )


def test_extend_public_nex_link_share_expiration_rejects_non_forward_extension() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-forward-extend-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-20T00:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    with pytest.raises(ValueError, match="move forward"):
        extend_public_nex_link_share_expiration(
            payload,
            expires_at="2026-04-19T00:00:00+00:00",
            now_iso="2026-04-15T13:00:00+00:00",
        )


def test_describe_public_nex_link_share_exposes_audit_summary() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-audit-summary-1"),
        created_at="2026-04-15T12:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    descriptor = describe_public_nex_link_share(payload)

    assert descriptor.audit_event_count == 1
    assert descriptor.last_audit_event_type == "created"
    assert descriptor.last_audit_event_at == "2026-04-15T12:00:00+00:00"


def test_share_audit_history_appends_extend_and_revoke_events() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-audit-flow-1"),
        created_at="2026-04-15T12:00:00+00:00",
        expires_at="2026-04-20T00:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    payload = extend_public_nex_link_share_expiration(
        payload,
        expires_at="2026-04-25T00:00:00+00:00",
        now_iso="2026-04-15T13:00:00+00:00",
        actor_user_ref="user-owner",
    )
    payload = revoke_public_nex_link_share(payload, now_iso="2026-04-15T14:00:00+00:00", actor_user_ref="user-owner")

    history = list_public_nex_link_share_audit_history(payload)

    assert [entry["event_type"] for entry in history] == ["created", "expiration_extended", "revoked"]
    assert history[-1]["actor_user_ref"] == "user-owner"


def test_revoke_public_nex_link_shares_for_issuer_updates_all_requested_targets() -> None:
    sources = (
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_a"), commit_id="commit-owner-a"),
            share_id="share-owner-a",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:00:00+00:00",
        ),
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_b"), commit_id="commit-owner-b"),
            share_id="share-owner-b",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:05:00+00:00",
        ),
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="other_c"), commit_id="commit-other-c"),
            share_id="share-other-c",
            issued_by_user_ref="user-other",
            created_at="2026-04-15T12:10:00+00:00",
        ),
    )

    updated = revoke_public_nex_link_shares_for_issuer(
        sources,
        "user-owner",
        ["share-owner-a", "share-owner-b"],
        now_iso="2026-04-15T13:00:00+00:00",
        actor_user_ref="user-owner",
    )

    descriptors = [describe_public_nex_link_share(payload, now_iso="2026-04-15T13:00:00+00:00") for payload in updated]
    assert [descriptor.share_id for descriptor in descriptors] == ["share-owner-a", "share-owner-b"]
    assert all(descriptor.lifecycle_state == "revoked" for descriptor in descriptors)


def test_extend_public_nex_link_shares_for_issuer_expiration_updates_all_requested_targets() -> None:
    sources = (
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_a"), commit_id="commit-owner-a2"),
            share_id="share-owner-a2",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:00:00+00:00",
            expires_at="2026-04-20T00:00:00+00:00",
        ),
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_b"), commit_id="commit-owner-b2"),
            share_id="share-owner-b2",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:05:00+00:00",
            expires_at="2026-04-20T00:00:00+00:00",
        ),
    )

    updated = extend_public_nex_link_shares_for_issuer_expiration(
        sources,
        "user-owner",
        ["share-owner-a2", "share-owner-b2"],
        expires_at="2026-04-25T00:00:00+00:00",
        now_iso="2026-04-15T13:00:00+00:00",
        actor_user_ref="user-owner",
    )

    descriptors = [describe_public_nex_link_share(payload, now_iso="2026-04-15T13:00:00+00:00") for payload in updated]
    assert [descriptor.share_id for descriptor in descriptors] == ["share-owner-a2", "share-owner-b2"]
    assert all(descriptor.expires_at == "2026-04-25T00:00:00+00:00" for descriptor in descriptors)


def test_delete_public_nex_link_shares_for_issuer_returns_deleted_entries() -> None:
    sources = (
        export_public_nex_link_share(_working_save(name="owner a"), share_id="share-delete-a", issued_by_user_ref="user-owner", created_at="2026-04-15T12:00:00+00:00"),
        export_public_nex_link_share(_working_save(name="owner b"), share_id="share-delete-b", issued_by_user_ref="user-owner", created_at="2026-04-15T12:01:00+00:00"),
        export_public_nex_link_share(_working_save(name="other c"), share_id="share-delete-c", issued_by_user_ref="user-other", created_at="2026-04-15T12:02:00+00:00"),
    )

    deleted = delete_public_nex_link_shares_for_issuer(sources, "user-owner", ["share-delete-a", "share-delete-b"], now_iso="2026-04-15T13:00:00+00:00")

    assert [entry.share_id for entry in deleted] == ["share-delete-a", "share-delete-b"]
    assert all(entry.lifecycle_state == "active" for entry in deleted)


def test_update_public_nex_link_share_archive_sets_management_flag_and_audit() -> None:
    payload = export_public_nex_link_share(
        create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-archive-1"),
        created_at="2026-04-15T12:00:00+00:00",
        issued_by_user_ref="user-owner",
    )

    archived = update_public_nex_link_share_archive(
        payload,
        archived=True,
        updated_at="2026-04-15T15:00:00+00:00",
        actor_user_ref="user-owner",
    )
    descriptor = describe_public_nex_link_share(archived)

    assert archived["share"]["management"]["archived"] is True
    assert archived["share"]["management"]["archived_at"] == "2026-04-15T15:00:00+00:00"
    assert descriptor.archived is True
    assert descriptor.archived_at == "2026-04-15T15:00:00+00:00"
    assert list_public_nex_link_share_audit_history(archived)[-1]["event_type"] == "archived"


def test_archive_public_nex_link_shares_for_issuer_updates_requested_targets() -> None:
    sources = (
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_archive_a"), commit_id="commit-owner-archive-a"),
            share_id="share-owner-archive-a",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:00:00+00:00",
        ),
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(name="owner_archive_b"), commit_id="commit-owner-archive-b"),
            share_id="share-owner-archive-b",
            issued_by_user_ref="user-owner",
            created_at="2026-04-15T12:05:00+00:00",
        ),
    )

    updated = archive_public_nex_link_shares_for_issuer(
        sources,
        "user-owner",
        ["share-owner-archive-a", "share-owner-archive-b"],
        archived=True,
        now_iso="2026-04-15T13:00:00+00:00",
        actor_user_ref="user-owner",
    )

    descriptors = [describe_public_nex_link_share(payload, now_iso="2026-04-15T13:00:00+00:00") for payload in updated]
    assert [descriptor.share_id for descriptor in descriptors] == ["share-owner-archive-a", "share-owner-archive-b"]
    assert all(descriptor.archived is True for descriptor in descriptors)


def test_summarize_issuer_public_share_governance_for_issuer_combines_inventory_and_recent_activity() -> None:
    shares = (
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-gov-a"),
            share_id="share-gov-a",
            created_at="2026-04-15T12:00:00+00:00",
            updated_at="2026-04-15T12:30:00+00:00",
            issued_by_user_ref="user-owner",
        ),
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-gov-b"),
            share_id="share-gov-b",
            created_at="2026-04-14T12:00:00+00:00",
            updated_at="2026-04-14T12:15:00+00:00",
            lifecycle_state="revoked",
            issued_by_user_ref="user-owner",
        ),
    )
    action_reports = (
        {
            "report_id": "gov-report-001",
            "issuer_user_ref": "user-owner",
            "action": "revoke",
            "scope": "single_share",
            "created_at": "2026-04-15T13:00:00+00:00",
            "requested_share_ids": ["share-gov-a"],
            "affected_share_ids": ["share-gov-a"],
            "affected_share_count": 1,
            "before_total_share_count": 2,
            "after_total_share_count": 1,
        },
        {
            "report_id": "gov-report-002",
            "issuer_user_ref": "user-owner",
            "action": "archive",
            "scope": "single_share",
            "created_at": "2026-04-15T14:00:00+00:00",
            "requested_share_ids": ["share-gov-b"],
            "affected_share_ids": ["share-gov-b"],
            "affected_share_count": 1,
            "before_total_share_count": 1,
            "after_total_share_count": 1,
            "archived": True,
        },
    )

    summary = summarize_issuer_public_share_governance_for_issuer(
        shares,
        action_reports,
        "user-owner",
        now_iso="2026-04-15T15:00:00+00:00",
    )

    assert summary.total_share_count == 2
    assert summary.revoked_share_count == 1
    assert summary.total_action_report_count == 2
    assert summary.revoke_action_report_count == 1
    assert summary.archive_action_report_count == 1
    assert summary.latest_updated_at == "2026-04-15T12:30:00+00:00"
    assert summary.latest_action_report_at == "2026-04-15T14:00:00+00:00"
    assert [report.report_id for report in summary.recent_action_reports] == ["gov-report-002", "gov-report-001"]


def test_summarize_issuer_public_share_governance_for_issuer_bounds_recent_activity_slice() -> None:
    shares = (
        export_public_nex_link_share(
            create_commit_snapshot_from_working_save(_working_save(), commit_id="commit-gov-bound"),
            share_id="share-gov-bound",
            created_at="2026-04-15T12:00:00+00:00",
            issued_by_user_ref="user-owner",
        ),
    )
    action_reports = tuple(
        {
            "report_id": f"gov-report-{index:03d}",
            "issuer_user_ref": "user-owner",
            "action": "delete" if index % 2 else "revoke",
            "scope": "single_share",
            "created_at": f"2026-04-15T{12 + index:02d}:00:00+00:00",
            "requested_share_ids": ["share-gov-bound"],
            "affected_share_ids": ["share-gov-bound"],
            "affected_share_count": 1,
            "before_total_share_count": 1,
            "after_total_share_count": 1,
        }
        for index in range(1, 8)
    )

    summary = summarize_issuer_public_share_governance_for_issuer(
        shares,
        action_reports,
        "user-owner",
        recent_action_report_limit=5,
    )

    assert len(summary.recent_action_reports) == 5
    assert [report.report_id for report in summary.recent_action_reports] == [
        "gov-report-007",
        "gov-report-006",
        "gov-report-005",
        "gov-report-004",
        "gov-report-003",
    ]
