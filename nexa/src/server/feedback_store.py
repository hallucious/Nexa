from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from src.server.fastapi_binding_models import FastApiRouteDependencies

_ALLOWED_CATEGORIES = {"confusing_screen", "friction_note", "bug_report"}
_ALLOWED_SURFACES = {"circuit_library", "result_history", "starter_templates", "workspace_shell", "unknown"}


@dataclass
class InMemoryFeedbackStore:
    _rows_by_feedback_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Sequence[Mapping[str, Any]] = ()) -> "InMemoryFeedbackStore":
        store = cls()
        for row in rows:
            store.write(row)
        return store

    def write(self, row: Mapping[str, Any]) -> dict[str, Any]:
        feedback_id = str(row.get("feedback_id") or "").strip()
        user_id = str(row.get("user_id") or "").strip()
        workspace_id = str(row.get("workspace_id") or "").strip()
        category = str(row.get("category") or "").strip().lower()
        surface = str(row.get("surface") or "").strip().lower() or "unknown"
        message = str(row.get("message") or "").strip()
        created_at = str(row.get("created_at") or "").strip()
        if not feedback_id or not user_id or not workspace_id or not message or not created_at:
            raise ValueError("feedback_store.row_invalid")
        if category not in _ALLOWED_CATEGORIES:
            raise ValueError("feedback_store.category_invalid")
        if surface not in _ALLOWED_SURFACES:
            raise ValueError("feedback_store.surface_invalid")
        normalized = {
            "feedback_id": feedback_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "workspace_title": str(row.get("workspace_title") or "").strip() or None,
            "category": category,
            "surface": surface,
            "message": message,
            "run_id": str(row.get("run_id") or "").strip() or None,
            "template_id": str(row.get("template_id") or "").strip() or None,
            "status": str(row.get("status") or "received").strip() or "received",
            "created_at": created_at,
        }
        self._rows_by_feedback_id[feedback_id] = normalized
        return dict(normalized)

    def list_rows(self) -> tuple[dict[str, Any], ...]:
        rows = [dict(row) for row in self._rows_by_feedback_id.values()]
        rows.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("feedback_id") or "")), reverse=True)
        return tuple(rows)


def bind_feedback_store(*, dependencies: FastApiRouteDependencies, store: InMemoryFeedbackStore) -> FastApiRouteDependencies:
    return replace(
        dependencies,
        feedback_rows_provider=store.list_rows,
        feedback_writer=store.write,
    )
