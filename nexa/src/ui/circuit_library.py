from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from src.contracts.workspace_library_contract import (
    ProductActivityContinuitySummary,
    ProductWorkspaceListResponse,
    ProductWorkspaceSummaryView,
)
from src.ui.i18n import ui_text

_SUCCESS_RESULT_STATUSES = {"completed", "succeeded", "ready_success", "success", "terminal_success"}
_ONBOARDING_STEP_LABELS = {
    "enter_goal": ("circuit_library.onboarding.step.enter_goal", "enter your goal"),
    "review_preview": ("circuit_library.onboarding.step.review_preview", "review the workflow preview"),
    "approve": ("circuit_library.onboarding.step.approve", "approve the workflow"),
    "run": ("circuit_library.onboarding.step.run", "run the workflow"),
    "read_result": ("circuit_library.onboarding.step.read_result", "read the result"),
}

_ROLE_LABEL_KEYS = {
    "owner": ("circuit_library.role.owner", "Owner"),
    "admin": ("circuit_library.role.admin", "Admin"),
    "editor": ("circuit_library.role.editor", "Editor"),
    "collaborator": ("circuit_library.role.collaborator", "Collaborator"),
    "reviewer": ("circuit_library.role.reviewer", "Reviewer"),
    "viewer": ("circuit_library.role.viewer", "Viewer"),
}


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
    feedback_href: str | None = None
    feedback_label: str | None = None
    result_history_label: str | None = None
    result_history_href: str | None = None
    result_history_action_label: str | None = None
    has_recent_result_history: bool = False
    archived: bool = False
    latest_run_id: str | None = None
    latest_result_status: str | None = None
    onboarding_incomplete: bool = False
    onboarding_step_id: str | None = None
    onboarding_progress_label: str | None = None
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




def _format_surface_timestamp(value: str | None) -> str | None:
    raw = str(value or "").strip() or None
    if raw is None:
        return None
    candidate = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw

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


def _normalized_onboarding_state(onboarding_state: object | None) -> Mapping[str, object] | None:
    if not isinstance(onboarding_state, Mapping):
        return None
    return onboarding_state


def _onboarding_step_id(onboarding_state: object | None) -> str | None:
    state = _normalized_onboarding_state(onboarding_state)
    if state is None:
        return None
    step = str(state.get("current_step") or "").strip().lower()
    return step or None


def _onboarding_incomplete(onboarding_state: object | None) -> bool:
    state = _normalized_onboarding_state(onboarding_state)
    if state is None:
        return False
    return not bool(state.get("first_success_achieved"))


def _localized_onboarding_step_label(step_id: str, *, app_language: str) -> str:
    key, fallback = _ONBOARDING_STEP_LABELS.get(step_id, (None, step_id.replace("_", " ")))
    if key is None:
        return fallback
    return ui_text(key, app_language=app_language, fallback_text=fallback)


def _localized_role(role: str | None, *, app_language: str) -> str:
    normalized = str(role or "").strip().lower()
    if not normalized:
        return ""
    key, fallback = _ROLE_LABEL_KEYS.get(normalized, (None, normalized.replace("_", " ").title()))
    if key is None:
        return fallback
    return ui_text(key, app_language=app_language, fallback_text=fallback)


def _status_key(summary: ProductWorkspaceSummaryView, *, onboarding_state: object | None = None) -> str:
    activity = _activity(summary)
    if summary.archived:
        return "archived"
    if _onboarding_incomplete(onboarding_state):
        return "resume_onboarding"
    if summary.orphan_review_required or str(summary.recovery_state or "").strip().lower() == "manual_review_required":
        return "needs_review"
    if activity is not None and activity.active_run_count > 0:
        return "running"
    if _has_recent_result_history(summary):
        return "recent_result"
    return "draft"


def _status_label(summary: ProductWorkspaceSummaryView, *, app_language: str, onboarding_state: object | None = None) -> str:
    key = _status_key(summary, onboarding_state=onboarding_state)
    fallback = {
        "archived": "Archived",
        "resume_onboarding": "Resume onboarding",
        "needs_review": "Needs review",
        "running": "Run in progress",
        "recent_result": "Recent result available",
        "draft": "Draft",
    }[key]
    return ui_text(f"circuit_library.status.{key}", app_language=app_language, fallback_text=fallback)


def _onboarding_progress_label(onboarding_state: object | None, *, app_language: str) -> str | None:
    if not _onboarding_incomplete(onboarding_state):
        return None
    step_id = _onboarding_step_id(onboarding_state)
    if step_id == "read_result":
        return ui_text(
            "circuit_library.onboarding.read_result",
            app_language=app_language,
            fallback_text="Resume the first-result step from where you left off.",
        )
    if step_id == "run":
        return ui_text(
            "circuit_library.onboarding.run",
            app_language=app_language,
            fallback_text="Resume the run step without restarting onboarding.",
        )
    if step_id in {"review_preview", "approve"}:
        return ui_text(
            "circuit_library.onboarding.review",
            app_language=app_language,
            fallback_text="Resume the review and approval step without starting over.",
        )
    if step_id == "enter_goal":
        return ui_text(
            "circuit_library.onboarding.start",
            app_language=app_language,
            fallback_text="Resume your first workflow setup from the start step.",
        )
    return ui_text(
        "circuit_library.onboarding.resume",
        app_language=app_language,
        fallback_text="Resume onboarding from where you left off.",
    )


def _continue_target(summary: ProductWorkspaceSummaryView, *, onboarding_state: object | None, app_language: str) -> tuple[str, str]:
    workspace_href = f"/app/workspaces/{summary.workspace_id}"
    history_href = None
    if _has_recent_result_history(summary):
        history_href = f"/app/workspaces/{summary.workspace_id}/results"
        if summary.last_run_id:
            history_href = f"{history_href}?run_id={summary.last_run_id}"
    step_id = _onboarding_step_id(onboarding_state)
    if _onboarding_incomplete(onboarding_state):
        if step_id == "read_result" and history_href:
            return (
                ui_text("circuit_library.action.resume_result", app_language=app_language, fallback_text="Resume first result"),
                history_href,
            )
        if step_id in {"review_preview", "approve"}:
            return (
                ui_text("circuit_library.action.resume_review", app_language=app_language, fallback_text="Resume review"),
                workspace_href,
            )
        if step_id == "run":
            return (
                ui_text("circuit_library.action.resume_run", app_language=app_language, fallback_text="Resume run"),
                workspace_href,
            )
        return (
            ui_text("circuit_library.action.resume_onboarding", app_language=app_language, fallback_text="Resume onboarding"),
            workspace_href,
        )
    return ui_text("circuit_library.action.continue", app_language=app_language, fallback_text="Continue"), workspace_href


def _summary_lines(summary: ProductWorkspaceSummaryView, *, app_language: str, onboarding_state: object | None = None) -> list[str]:
    lines: list[str] = []
    if summary.role:
        lines.append(
            ui_text(
                "circuit_library.summary.role",
                app_language=app_language,
                fallback_text=f"Access: {_localized_role(summary.role, app_language=app_language) or summary.role}",
                role=_localized_role(summary.role, app_language=app_language) or summary.role,
            )
        )
    onboarding_progress_label = _onboarding_progress_label(onboarding_state, app_language=app_language)
    if onboarding_progress_label:
        lines.append(onboarding_progress_label)
    elif summary.latest_error_family:
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
                fallback_text="A recent run is available.",
                run_id=summary.last_run_id,
            )
        )
    if summary.archived:
        lines.append(ui_text("circuit_library.summary.archived", app_language=app_language, fallback_text="This workflow is archived."))
    elif _has_recent_result_history(summary):
        lines.append(ui_text("circuit_library.summary.history_available", app_language=app_language, fallback_text="Recent result history is available."))
    else:
        lines.append(ui_text("circuit_library.summary.no_history", app_language=app_language, fallback_text="No recent result history yet."))
    step_id = _onboarding_step_id(onboarding_state)
    if _onboarding_incomplete(onboarding_state) and step_id:
        step_label = _localized_onboarding_step_label(step_id, app_language=app_language)
        lines.append(
            ui_text(
                "circuit_library.summary.resume_step",
                app_language=app_language,
                fallback_text=f"Server progress saved your place at: {step_label}.",
                step_label=step_label,
            )
        )
    return lines


def _items_from_summaries(
    summaries: Sequence[ProductWorkspaceSummaryView],
    *,
    app_language: str,
    onboarding_state_by_workspace_id: Mapping[str, object] | None = None,
) -> list[CircuitLibraryItemView]:
    items: list[CircuitLibraryItemView] = []
    onboarding_state_by_workspace_id = dict(onboarding_state_by_workspace_id or {})
    for summary in summaries:
        onboarding_state = onboarding_state_by_workspace_id.get(summary.workspace_id)
        has_recent_result_history = _has_recent_result_history(summary)
        role_label = ui_text(
            "circuit_library.role_label",
            app_language=app_language,
            fallback_text=f"Role: {_localized_role(summary.role, app_language=app_language) or summary.role}",
            role=_localized_role(summary.role, app_language=app_language) or summary.role,
        )
        result_history_label = ui_text(
            "circuit_library.result_history.available" if has_recent_result_history else "circuit_library.result_history.empty",
            app_language=app_language,
            fallback_text="Recent result history available" if has_recent_result_history else "No recent result history yet",
        )
        result_history_href = None
        if has_recent_result_history:
            result_history_href = f"/app/workspaces/{summary.workspace_id}/results"
            if summary.last_run_id:
                result_history_href = f"{result_history_href}?run_id={summary.last_run_id}"
        continue_label, continue_href = _continue_target(summary, onboarding_state=onboarding_state, app_language=app_language)
        items.append(
            CircuitLibraryItemView(
                workspace_id=summary.workspace_id,
                title=summary.title,
                updated_at=summary.updated_at,
                status_key=_status_key(summary, onboarding_state=onboarding_state),
                status_label=_status_label(summary, app_language=app_language, onboarding_state=onboarding_state),
                updated_label=ui_text(
                    "circuit_library.updated",
                    app_language=app_language,
                    fallback_text=f"Updated: {_format_surface_timestamp(summary.updated_at) or summary.updated_at}",
                    updated_at=_format_surface_timestamp(summary.updated_at) or summary.updated_at,
                ),
                continue_label=continue_label,
                continue_href=continue_href,
                role_label=role_label,
                feedback_href=f"/app/workspaces/{summary.workspace_id}/feedback?surface=circuit_library",
                feedback_label=ui_text("circuit_library.action.feedback", app_language=app_language, fallback_text="Report an issue"),
                result_history_label=result_history_label,
                result_history_href=result_history_href,
                result_history_action_label=(
                    ui_text("circuit_library.action.open_results", app_language=app_language, fallback_text="Open results")
                    if has_recent_result_history else None
                ),
                has_recent_result_history=has_recent_result_history,
                archived=summary.archived,
                latest_run_id=summary.last_run_id,
                latest_result_status=summary.last_result_status,
                onboarding_incomplete=_onboarding_incomplete(onboarding_state),
                onboarding_step_id=_onboarding_step_id(onboarding_state),
                onboarding_progress_label=_onboarding_progress_label(onboarding_state, app_language=app_language),
                summary_lines=_summary_lines(summary, app_language=app_language, onboarding_state=onboarding_state),
            )
        )
    return items


def read_circuit_library_view_model(
    source: ProductWorkspaceListResponse | Sequence[ProductWorkspaceSummaryView] | None,
    *,
    app_language: str = "en",
    explanation: str | None = None,
    onboarding_state_by_workspace_id: Mapping[str, object] | None = None,
) -> CircuitLibraryViewModel:
    if isinstance(source, ProductWorkspaceListResponse):
        summaries = list(source.workspaces)
    else:
        summaries = list(source or ())
    items = _items_from_summaries(
        summaries,
        app_language=app_language,
        onboarding_state_by_workspace_id=onboarding_state_by_workspace_id,
    )
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
