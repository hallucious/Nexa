from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from src.server.fastapi_binding_models import FastApiRouteDependencies


def _normalize_allowed_model_refs(value: Any) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in value or ():
        text = str(item).strip()
        if text:
            normalized.append(text)
    return tuple(normalized)


@dataclass
class InMemoryProviderBindingStore:
    _rows_by_workspace_provider: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Sequence[Mapping[str, Any]] = ()) -> "InMemoryProviderBindingStore":
        store = cls()
        for row in rows:
            store.write(row)
        return store

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        binding_id = str(row.get("binding_id") or "").strip()
        workspace_id = str(row.get("workspace_id") or "").strip()
        provider_key = str(row.get("provider_key") or "").strip().lower()
        provider_family = str(row.get("provider_family") or provider_key).strip()
        display_name = str(row.get("display_name") or provider_key).strip()
        if not binding_id or not workspace_id or not provider_key or not provider_family or not display_name:
            raise ValueError("provider_binding_store.row_invalid")
        normalized = {
            "binding_id": binding_id,
            "workspace_id": workspace_id,
            "provider_key": provider_key,
            "provider_family": provider_family,
            "display_name": display_name,
            "credential_source": str(row.get("credential_source") or "managed").strip() or "managed",
            "secret_ref": str(row.get("secret_ref") or "").strip() or None,
            "secret_version_ref": str(row.get("secret_version_ref") or "").strip() or None,
            "enabled": bool(row.get("enabled", True)),
            "default_model_ref": str(row.get("default_model_ref") or "").strip() or None,
            "allowed_model_refs": _normalize_allowed_model_refs(row.get("allowed_model_refs")),
            "notes": str(row.get("notes") or "").strip() or None,
            "created_by_user_id": str(row.get("created_by_user_id") or "").strip() or None,
            "updated_by_user_id": str(row.get("updated_by_user_id") or "").strip() or None,
            "created_at": str(row.get("created_at") or "").strip() or None,
            "updated_at": str(row.get("updated_at") or "").strip() or None,
            "last_rotated_at": str(row.get("last_rotated_at") or "").strip() or None,
        }
        self._rows_by_workspace_provider[(workspace_id, provider_key)] = normalized
        return dict(normalized)

    def list_all_rows(self) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._rows_by_workspace_provider.values()]
        rows.sort(
            key=lambda item: (
                str(item.get("updated_at") or item.get("created_at") or ""),
                str(item.get("workspace_id") or ""),
                str(item.get("provider_key") or ""),
            ),
            reverse=True,
        )
        return tuple(rows)

    def list_workspace_rows(self, workspace_id: str) -> tuple[dict[str, Any], ...]:
        normalized_workspace_id = str(workspace_id or "").strip()
        rows = [
            dict(row)
            for (row_workspace_id, _provider_key), row in self._rows_by_workspace_provider.items()
            if row_workspace_id == normalized_workspace_id
        ]
        rows.sort(
            key=lambda item: (
                str(item.get("updated_at") or item.get("created_at") or ""),
                str(item.get("provider_key") or ""),
            ),
            reverse=True,
        )
        return tuple(rows)

    def get_workspace_provider_row(self, workspace_id: str, provider_key: str) -> dict[str, Any] | None:
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_provider_key = str(provider_key or "").strip().lower()
        row = self._rows_by_workspace_provider.get((normalized_workspace_id, normalized_provider_key))
        return dict(row) if row is not None else None


def bind_provider_binding_store(
    *,
    dependencies: FastApiRouteDependencies,
    store: InMemoryProviderBindingStore,
) -> FastApiRouteDependencies:
    return replace(
        dependencies,
        workspace_provider_binding_rows_provider=store.list_workspace_rows,
        workspace_provider_binding_row_provider=store.get_workspace_provider_row,
        recent_provider_binding_rows_provider=store.list_all_rows,
        provider_binding_writer=store.write,
    )
