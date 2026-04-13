from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from src.server.workspace_onboarding_models import (
    ProductActivityContinuitySummary,
    ProductWorkspaceListResponse,
    ProductWorkspaceSummaryView,
)
from src.ui.i18n import ui_text

_SUCCESS_RESULT_STATUSES = {"completed", "succeeded", "ready_success", "success", "terminal_success"}


@dataclass(frozen=True)
class CircuitLibraryItemView:
    workspace_id: str
    title: str
    updated_at: str
    status_key: str
    status_label: str
    updated_label: str
    continue_label: str
    continue_href: str
    role_label: str | None = None
    result_history_label: str | None = None
    has_recent_result_history: bool = False
    archived: bool = False
    latest_run_id: str | None = None
    latest_result_status: str | None = None
    summary_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CircuitLibraryViewModel:
    library_status: str = "hidden"
    visible: bool = False
    title: str | None = None
    subtitle: str | None = None
    returned_count: int = 0
    items: list[CircuitLibraryItemView] = field(default_factory=list)
    empty_title: str | None = None
    empty_summary: str | None = None
    explanation: str | None = None


def _activity(summary: ProductWorkspaceSummaryView) -> ProductActivityContinuitySummary | None:
    return summary.activity_continuity if isinstance(summary.activity_continuity, ProductActivityContinuitySummary) else None


def _has_recent_result_history(summary: ProductWorkspaceSummaryView) -> bool:
    status = str(summary.last_result_status or "").strip().lower()
    if status in _SUCCESS_RESULT_STATUSES:
        return True
    activity = _activity(summary)
    if activity is None:
        return bool(summary.last_run_id)
    return bool(activity.recent_run_count > 0 or activity.latest_run_id)


def _status_key(summary: ProductWorkspaceSummaryView) -> str:
    activity = _activity(summary)
    if summary.archived:
        return "archived"
    if summary.orphan_review_required or str(summary.recovery_state or "").strip().lower() == "manual_review_required":
        return "needs_review"
    if activity is not None and activity.active_run_count > 0:
        return "running"
    if _has_recent_result_history(summary):
        return "recent_result"
    return "draft"


def _status_label(summary: ProductWorkspaceSummaryView, *, app_language: str) -> str:
    key = _status_key(summary)
    fallback = {
        "archived": "Archived",
        "needs_review": "Needs review",
        "running": "Run in progress",
        "recent_result": "Recent result available",
        "draft": "Draft",
    }[key]
    return ui_text(f"circuit_library.status.{key}", app_language=app_language, fallback_text=fallback)


def _summary_lines(summary: ProductWorkspaceSummaryView, *, app_language: str) -> list[str]:
    lines: list[str] = []
    if summary.role:
        lines.append(
            ui_text(
                "circuit_library.summary.role",
                app_language=app_language,
                fallback_text=f"Access: {summary.role}",
                role=summary.role,
            )
        )
    if summary.latest_error_family:
        lines.append(
            ui_text(
                "circuit_library.summary.latest_error",
                app_language=app_language,
                fallback_text=f"Latest issue: {summary.latest_error_family}",
                error_family=summary.latest_error_family,
            )
        )
    elif summary.last_run_id:
        lines.append(
            ui_text(
                "circuit_library.summary.latest_run",
                app_language=app_language,
                fallback_text=f"Latest run: {summary.last_run_id}",
                run_id=summary.last_run_id,
            )
        )
    if summary.archived:
        lines.append(ui_text("circuit_library.summary.archived", app_language=app_language, fallback_text="This workflow is archived."))
    elif _has_recent_result_history(summary):
        lines.append(ui_text("circuit_library.summary.history_available", app_language=app_language, fallback_text="Recent result history is available."))
    else:
        lines.append(ui_text("circuit_library.summary.no_history", app_language=app_language, fallback_text="No recent result history yet."))
    return lines


def _items_from_summaries(summaries: Sequence[ProductWorkspaceSummaryView], *, app_language: str) -> list[CircuitLibraryItemView]:
    items: list[CircuitLibraryItemView] = []
    for summary in summaries:
        has_recent_result_history = _has_recent_result_history(summary)
        role_label = ui_text(
            "circuit_library.role_label",
            app_language=app_language,
            fallback_text=f"Role: {summary.role}",
            role=summary.role,
        )
        result_history_label = ui_text(
            "circuit_library.result_history.available" if has_recent_result_history else "circuit_library.result_history.empty",
            app_language=app_language,
            fallback_text="Recent result history available" if has_recent_result_history else "No recent result history yet",
        )
        items.append(
            CircuitLibraryItemView(
                workspace_id=summary.workspace_id,
                title=summary.title,
                updated_at=summary.updated_at,
                status_key=_status_key(summary),
                status_label=_status_label(summary, app_language=app_language),
                updated_label=ui_text(
                    "circuit_library.updated",
                    app_language=app_language,
                    fallback_text=f"Updated: {summary.updated_at}",
                    updated_at=summary.updated_at,
                ),
                continue_label=ui_text("circuit_library.action.continue", app_language=app_language, fallback_text="Continue"),
                continue_href=f"/app/workspaces/{summary.workspace_id}",
                role_label=role_label,
                result_history_label=result_history_label,
                has_recent_result_history=has_recent_result_history,
                archived=summary.archived,
                latest_run_id=summary.last_run_id,
                latest_result_status=summary.last_result_status,
                summary_lines=_summary_lines(summary, app_language=app_language),
            )
        )
    return items


def read_circuit_library_view_model(
    source: ProductWorkspaceListResponse | Sequence[ProductWorkspaceSummaryView] | None,
    *,
    app_language: str = "en",
    explanation: str | None = None,
) -> CircuitLibraryViewModel:
    if isinstance(source, ProductWorkspaceListResponse):
        summaries = list(source.workspaces)
    else:
        summaries = list(source or ())
    items = _items_from_summaries(summaries, app_language=app_language)
    is_empty = len(items) == 0
    return CircuitLibraryViewModel(
        library_status="empty" if is_empty else "ready",
        visible=True,
        title=ui_text("circuit_library.title", app_language=app_language, fallback_text="My workflows"),
        subtitle=ui_text(
            "circuit_library.subtitle",
            app_language=app_language,
            fallback_text="Continue a saved workflow without reopening files.",
        ),
        returned_count=len(items),
        items=items,
        empty_title=ui_text("circuit_library.empty.title", app_language=app_language, fallback_text="No workflows yet"),
        empty_summary=ui_text(
            "circuit_library.empty.summary",
            app_language=app_language,
            fallback_text="Create your first workflow, then return here to continue it later.",
        ),
        explanation=explanation,
    )


__all__ = [
    "CircuitLibraryItemView",
    "CircuitLibraryViewModel",
    "read_circuit_library_view_model",
]
