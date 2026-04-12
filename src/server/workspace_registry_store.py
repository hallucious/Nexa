from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from src.server.auth_models import WorkspaceAuthorizationContext
from src.server.fastapi_binding_models import FastApiRouteDependencies

_ALLOWED_COLLABORATOR_ROLES = {"admin", "editor", "collaborator", "reviewer"}
_ALLOWED_VIEWER_ROLES = {"viewer"}


@dataclass
class InMemoryWorkspaceRegistryStore:
    _workspace_rows_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _membership_rows_by_key: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_rows(
        cls,
        *,
        workspace_rows: Sequence[Mapping[str, Any]] = (),
        membership_rows: Sequence[Mapping[str, Any]] = (),
    ) -> "InMemoryWorkspaceRegistryStore":
        store = cls()
        for row in workspace_rows:
            store.write_workspace_row(row)
        for row in membership_rows:
            store.write_membership_row(row)
        return store

    def write_workspace_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        workspace_id = str(row.get("workspace_id") or "").strip()
        owner_user_id = str(row.get("owner_user_id") or "").strip()
        title = str(row.get("title") or "").strip()
        updated_at = str(row.get("updated_at") or row.get("created_at") or "").strip()
        if not workspace_id or not owner_user_id or not title or not updated_at:
            raise ValueError("workspace_registry_store.workspace_row_invalid")
        normalized = {
            "workspace_id": workspace_id,
            "owner_user_id": owner_user_id,
            "title": title,
            "description": str(row.get("description") or "").strip() or None,
            "created_at": str(row.get("created_at") or "").strip() or None,
            "updated_at": updated_at,
            "last_run_id": str(row.get("last_run_id") or "").strip() or None,
            "last_result_status": str(row.get("last_result_status") or "").strip() or None,
            "continuity_source": str(row.get("continuity_source") or "server").strip() or "server",
            "archived": bool(row.get("archived", False)),
        }
        self._workspace_rows_by_id[workspace_id] = normalized
        return dict(normalized)

    def write_membership_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        workspace_id = str(row.get("workspace_id") or "").strip()
        user_id = str(row.get("user_id") or "").strip()
        membership_id = str(row.get("membership_id") or "").strip()
        role = str(row.get("role") or "").strip().lower()
        updated_at = str(row.get("updated_at") or row.get("created_at") or "").strip()
        if not workspace_id or not user_id or not membership_id or not role or not updated_at:
            raise ValueError("workspace_registry_store.membership_row_invalid")
        normalized = {
            "membership_id": membership_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": role,
            "created_at": str(row.get("created_at") or "").strip() or None,
            "updated_at": updated_at,
        }
        self._membership_rows_by_key[(workspace_id, user_id)] = normalized
        return dict(normalized)

    def write_workspace_bundle(self, workspace_row: Mapping[str, Any], membership_row: Mapping[str, Any]) -> dict[str, Any]:
        normalized_workspace = self.write_workspace_row(workspace_row)
        normalized_membership = self.write_membership_row(membership_row)
        return {
            "workspace": normalized_workspace,
            "membership": normalized_membership,
        }

    def list_workspace_rows(self) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._workspace_rows_by_id.values()]
        rows.sort(key=lambda item: (str(item.get("updated_at") or item.get("created_at") or ""), str(item.get("workspace_id") or "")), reverse=True)
        return tuple(rows)

    def get_workspace_row(self, workspace_id: str) -> dict[str, Any] | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        row = self._workspace_rows_by_id.get(normalized_workspace_id)
        return dict(row) if row is not None else None

    def list_membership_rows(self) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._membership_rows_by_key.values()]
        rows.sort(key=lambda item: (str(item.get("updated_at") or item.get("created_at") or ""), str(item.get("workspace_id") or ""), str(item.get("user_id") or "")), reverse=True)
        return tuple(rows)

    def get_workspace_context(self, workspace_id: str) -> WorkspaceAuthorizationContext | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        workspace_row = self._workspace_rows_by_id.get(normalized_workspace_id)
        if workspace_row is None:
            return None
        collaborator_user_refs: list[str] = []
        viewer_user_refs: list[str] = []
        for (row_workspace_id, user_id), row in self._membership_rows_by_key.items():
            if row_workspace_id != normalized_workspace_id:
                continue
            role = str(row.get("role") or "").strip().lower()
            if role in _ALLOWED_COLLABORATOR_ROLES:
                collaborator_user_refs.append(user_id)
            elif role in _ALLOWED_VIEWER_ROLES:
                viewer_user_refs.append(user_id)
        return WorkspaceAuthorizationContext(
            workspace_id=normalized_workspace_id,
            owner_user_ref=str(workspace_row.get("owner_user_id") or "").strip() or None,
            collaborator_user_refs=tuple(sorted(set(collaborator_user_refs))),
            viewer_user_refs=tuple(sorted(set(viewer_user_refs))),
        )


def bind_workspace_registry_store(
    *,
    dependencies: FastApiRouteDependencies,
    store: InMemoryWorkspaceRegistryStore,
) -> FastApiRouteDependencies:
    return replace(
        dependencies,
        workspace_context_provider=store.get_workspace_context,
        workspace_rows_provider=store.list_workspace_rows,
        workspace_row_provider=store.get_workspace_row,
        workspace_membership_rows_provider=store.list_membership_rows,
        workspace_registry_writer=store.write_workspace_bundle,
    )
