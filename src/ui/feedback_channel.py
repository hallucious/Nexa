from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from src.ui.i18n import ui_text

_CATEGORY_LABELS = {
    "confusing_screen": ("Report confusing screen", "Tell us which part of this screen felt confusing."),
    "friction_note": ("Quick friction note", "Leave a short note about what slowed you down."),
    "bug_report": ("Bug report shortcut", "Report an unexpected failure or broken behavior."),
}
_SURFACE_LABELS = {
    "circuit_library": "Library",
    "result_history": "Result history",
    "workspace_shell": "Workflow",
    "unknown": "Current screen",
}


@dataclass(frozen=True)
class FeedbackOptionView:
    category_key: str
    title: str
    summary: str


@dataclass(frozen=True)
class FeedbackItemView:
    feedback_id: str
    category_key: str
    category_label: str
    surface_key: str
    surface_label: str
    message: str
    created_at_label: str
    run_id: str | None = None
    status_label: str | None = None


@dataclass(frozen=True)
class FeedbackChannelViewModel:
    workspace_id: str
    workspace_title: str
    visible: bool = False
    channel_status: str = "hidden"
    title: str | None = None
    subtitle: str | None = None
    submit_path: str | None = None
    prefill_category: str | None = None
    prefill_surface: str | None = None
    prefill_run_id: str | None = None
    options: list[FeedbackOptionView] = field(default_factory=list)
    items: list[FeedbackItemView] = field(default_factory=list)
    returned_count: int = 0
    empty_title: str | None = None
    empty_summary: str | None = None
    confirmation_title: str | None = None
    confirmation_summary: str | None = None


def _normalized_rows(rows: Sequence[Mapping[str, object]] | None, *, workspace_id: str, user_id: str | None = None) -> list[Mapping[str, object]]:
    filtered: list[Mapping[str, object]] = []
    for row in rows or ():
        if str(row.get("workspace_id") or "").strip() != workspace_id:
            continue
        if user_id is not None and str(row.get("user_id") or "").strip() != user_id:
            continue
        filtered.append(row)
    filtered.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("feedback_id") or "")), reverse=True)
    return filtered


def _feedback_item(row: Mapping[str, object], *, app_language: str) -> FeedbackItemView:
    category = str(row.get("category") or "friction_note").strip().lower()
    surface = str(row.get("surface") or "unknown").strip().lower() or "unknown"
    category_title = _CATEGORY_LABELS.get(category, (category.replace("_", " ").title(), ""))[0]
    surface_label = _SURFACE_LABELS.get(surface, surface.replace("_", " ").title())
    created_at = str(row.get("created_at") or "").strip()
    return FeedbackItemView(
        feedback_id=str(row.get("feedback_id") or ""),
        category_key=category,
        category_label=ui_text(f"feedback.category.{category}", app_language=app_language, fallback_text=category_title),
        surface_key=surface,
        surface_label=ui_text(f"feedback.surface.{surface}", app_language=app_language, fallback_text=surface_label),
        message=str(row.get("message") or "").strip(),
        created_at_label=ui_text("feedback.created_at", app_language=app_language, fallback_text=f"Sent: {created_at}", created_at=created_at),
        run_id=str(row.get("run_id") or "").strip() or None,
        status_label=ui_text("feedback.status.received", app_language=app_language, fallback_text=str(row.get("status") or "received").replace("_", " ").title()),
    )


def read_feedback_channel_view_model(
    *,
    workspace_id: str,
    workspace_title: str,
    feedback_rows: Sequence[Mapping[str, object]] = (),
    current_user_id: str | None = None,
    app_language: str = "en",
    prefill_category: str | None = None,
    prefill_surface: str | None = None,
    prefill_run_id: str | None = None,
    confirmation_feedback_id: str | None = None,
) -> FeedbackChannelViewModel:
    rows = _normalized_rows(feedback_rows, workspace_id=workspace_id, user_id=current_user_id)
    items = [_feedback_item(row, app_language=app_language) for row in rows]
    options = [
        FeedbackOptionView(
            category_key=key,
            title=ui_text(f"feedback.option.{key}.title", app_language=app_language, fallback_text=title),
            summary=ui_text(f"feedback.option.{key}.summary", app_language=app_language, fallback_text=summary),
        )
        for key, (title, summary) in _CATEGORY_LABELS.items()
    ]
    confirmation_title = None
    confirmation_summary = None
    if confirmation_feedback_id:
        confirmation_title = ui_text("feedback.confirmation.title", app_language=app_language, fallback_text="Feedback received")
        confirmation_summary = ui_text(
            "feedback.confirmation.summary",
            app_language=app_language,
            fallback_text=f"Your note was saved as {confirmation_feedback_id}.",
            feedback_id=confirmation_feedback_id,
        )
    return FeedbackChannelViewModel(
        workspace_id=workspace_id,
        workspace_title=workspace_title,
        visible=True,
        channel_status="empty" if not items else "ready",
        title=ui_text("feedback.title", app_language=app_language, fallback_text="Help us improve this workflow"),
        subtitle=ui_text(
            "feedback.subtitle",
            app_language=app_language,
            fallback_text="Send a quick note when this screen is confusing, friction-heavy, or unexpectedly broken.",
        ),
        submit_path=f"/api/workspaces/{workspace_id}/feedback",
        prefill_category=prefill_category,
        prefill_surface=prefill_surface,
        prefill_run_id=prefill_run_id,
        options=options,
        items=items,
        returned_count=len(items),
        empty_title=ui_text("feedback.empty.title", app_language=app_language, fallback_text="No feedback sent yet"),
        empty_summary=ui_text("feedback.empty.summary", app_language=app_language, fallback_text="Send a quick note here instead of leaving the product to report friction."),
        confirmation_title=confirmation_title,
        confirmation_summary=confirmation_summary,
    )


__all__ = [
    "FeedbackChannelViewModel",
    "FeedbackItemView",
    "FeedbackOptionView",
    "read_feedback_channel_view_model",
]
