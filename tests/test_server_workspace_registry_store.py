from __future__ import annotations

from src.server.auth_models import WorkspaceAuthorizationContext
from src.server.fastapi_binding_models import FastApiRouteDependencies
from src.server.workspace_registry_store import InMemoryWorkspaceRegistryStore, bind_workspace_registry_store


def test_workspace_registry_store_write_bundle_exposes_workspace_and_membership_rows() -> None:
    store = InMemoryWorkspaceRegistryStore()
    store.write_workspace_bundle(
        {
            "workspace_id": "ws-100",
            "owner_user_id": "user-owner",
            "title": "Workspace 100",
            "created_at": "2026-04-12T10:00:00+00:00",
            "updated_at": "2026-04-12T10:00:00+00:00",
        },
        {
            "membership_id": "membership-100",
            "workspace_id": "ws-100",
            "user_id": "user-owner",
            "role": "owner",
            "created_at": "2026-04-12T10:00:00+00:00",
            "updated_at": "2026-04-12T10:00:00+00:00",
        },
    )

    assert store.get_workspace_row("ws-100") is not None
    assert store.list_workspace_rows()[0]["workspace_id"] == "ws-100"
    assert store.list_membership_rows()[0]["membership_id"] == "membership-100"


def test_workspace_registry_store_derives_workspace_context_from_rows() -> None:
    store = InMemoryWorkspaceRegistryStore.from_rows(
        workspace_rows=(
            {
                "workspace_id": "ws-200",
                "owner_user_id": "user-owner",
                "title": "Workspace 200",
                "created_at": "2026-04-12T10:00:00+00:00",
                "updated_at": "2026-04-12T10:00:00+00:00",
            },
        ),
        membership_rows=(
            {
                "membership_id": "membership-editor",
                "workspace_id": "ws-200",
                "user_id": "user-editor",
                "role": "editor",
                "created_at": "2026-04-12T10:00:00+00:00",
                "updated_at": "2026-04-12T10:00:00+00:00",
            },
            {
                "membership_id": "membership-viewer",
                "workspace_id": "ws-200",
                "user_id": "user-viewer",
                "role": "viewer",
                "created_at": "2026-04-12T10:00:00+00:00",
                "updated_at": "2026-04-12T10:00:00+00:00",
            },
        ),
    )

    context = store.get_workspace_context("ws-200")
    assert context == WorkspaceAuthorizationContext(
        workspace_id="ws-200",
        owner_user_ref="user-owner",
        collaborator_user_refs=("user-editor",),
        viewer_user_refs=("user-viewer",),
    )


def test_bind_workspace_registry_store_wires_read_and_write_dependencies() -> None:
    deps = bind_workspace_registry_store(
        dependencies=FastApiRouteDependencies(),
        store=InMemoryWorkspaceRegistryStore(),
    )

    deps.workspace_registry_writer(
        {
            "workspace_id": "ws-300",
            "owner_user_id": "user-owner",
            "title": "Workspace 300",
            "created_at": "2026-04-12T10:00:00+00:00",
            "updated_at": "2026-04-12T10:00:00+00:00",
        },
        {
            "membership_id": "membership-300",
            "workspace_id": "ws-300",
            "user_id": "user-owner",
            "role": "owner",
            "created_at": "2026-04-12T10:00:00+00:00",
            "updated_at": "2026-04-12T10:00:00+00:00",
        },
    )

    assert deps.workspace_row_provider("ws-300") is not None
    assert deps.workspace_rows_provider()[0]["workspace_id"] == "ws-300"
    assert deps.workspace_context_provider("ws-300") is not None
