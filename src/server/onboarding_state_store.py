from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from src.server.fastapi_binding_models import FastApiRouteDependencies


@dataclass
class InMemoryOnboardingStateStore:
    _rows_by_user_workspace: dict[tuple[str, str | None], dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Sequence[Mapping[str, Any]] = ()) -> "InMemoryOnboardingStateStore":
        store = cls()
        for row in rows:
            store.write(row)
        return store

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        onboarding_state_id = str(row.get("onboarding_state_id") or "").strip()
        user_id = str(row.get("user_id") or "").strip()
        workspace_id = str(row.get("workspace_id") or "").strip() or None
        updated_at = str(row.get("updated_at") or "").strip()
        if not onboarding_state_id or not user_id or not updated_at:
            raise ValueError("onboarding_state_store.row_invalid")
        normalized = {
            "onboarding_state_id": onboarding_state_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "first_success_achieved": bool(row.get("first_success_achieved", False)),
            "advanced_surfaces_unlocked": bool(row.get("advanced_surfaces_unlocked", False)),
            "dismissed_guidance_state": dict(row.get("dismissed_guidance_state") or {}),
            "current_step": str(row.get("current_step") or "").strip() or None,
            "updated_at": updated_at,
        }
        self._rows_by_user_workspace[(user_id, workspace_id)] = normalized
        return dict(normalized)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._rows_by_user_workspace.values()]
        rows.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("user_id") or ""), str(item.get("workspace_id") or "")), reverse=True)
        return tuple(rows)


def bind_onboarding_state_store(
    *,
    dependencies: FastApiRouteDependencies,
    store: InMemoryOnboardingStateStore,
) -> FastApiRouteDependencies:
    return replace(
        dependencies,
        onboarding_rows_provider=store.list_rows,
        onboarding_state_writer=store.write,
    )
