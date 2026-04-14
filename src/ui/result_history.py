from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from src.ui.i18n import ui_text


@dataclass(frozen=True)
class ResultHistoryItemView:
    run_id: str
    workspace_id: str
    status_key: str
    status_label: str
    timestamp_label: str
    result_title: str
    result_summary: str
    source_artifact: dict[str, object] | None = None
    output_preview: str | None = None
    output_label: str | None = None
    open_result_href: str | None = None
    continue_href: str | None = None
    summary_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResultHistoryViewModel:
    workspace_id: str | None = None
    workspace_title: str | None = None
    visible: bool = False
    history_status: str = "hidden"
    title: str | None = None
    subtitle: str | None = None
    returned_count: int = 0
    items: list[ResultHistoryItemView] = field(default_factory=list)
    selected_run_id: str | None = None
    empty_title: str | None = None
    empty_summary: str | None = None
    onboarding_incomplete: bool = False
    onboarding_step_id: str | None = None
    onboarding_title: str | None = None
    onboarding_summary: str | None = None
    onboarding_action_label: str | None = None
    onboarding_action_href: str | None = None
    explanation: str | None = None
    feedback_href: str | None = None
    feedback_label: str | None = None


_READY_SUCCESS = {"ready_success", "terminal_success", "completed"}
_READY_PARTIAL = {"ready_partial", "terminal_partial", "partial"}
_READY_FAILURE = {"ready_failure", "terminal_failure", "failed"}
_ACTIVE_STATES = {"pending", "active", "not_ready", "queued", "running"}


def _format_surface_timestamp(value: str | None) -> str | None:
    raw = str(value or "").strip() or None
    if raw is None:
        return None
    candidate = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw



_SYSTEM_RESULT_TITLES = {
    "Run completed": ("result_history.system_title.run_completed", "Run completed"),
    "Run failed": ("result_history.system_title.run_failed", "Run failed"),
    "Last successful result": ("result_history.title.success", "Last successful result"),
    "Latest partial result": ("result_history.title.partial", "Latest partial result"),
    "Latest run still in progress": ("result_history.title.running", "Latest run still in progress"),
    "Latest run result": ("result_history.title.unknown", "Latest run result"),
}

_SYSTEM_RESULT_SUMMARIES = {
    "Success.": ("result_history.system_summary.success", "Success."),
    "The run failed.": ("result_history.system_summary.failed", "The run failed."),
    "A recent result is available for this workflow.": ("result_history.summary.success", "A recent result is available for this workflow."),
    "A partial result is available for this workflow.": ("result_history.summary.partial", "A partial result is available for this workflow."),
    "The last run failed before producing a complete result.": ("result_history.summary.failed", "The last run failed before producing a complete result."),
    "This run is still progressing and does not have a final result yet.": ("result_history.summary.running", "This run is still progressing and does not have a final result yet."),
    "Recent result details are not available yet.": ("result_history.summary.unknown", "Recent result details are not available yet."),
}


def _localized_system_result_title(value: str, *, app_language: str) -> str:
    key_fallback = _SYSTEM_RESULT_TITLES.get(value)
    if key_fallback is None:
        return value
    key, fallback = key_fallback
    return ui_text(key, app_language=app_language, fallback_text=fallback)


def _localized_system_result_summary(value: str, *, app_language: str) -> str:
    key_fallback = _SYSTEM_RESULT_SUMMARIES.get(value)
    if key_fallback is None:
        return value
    key, fallback = key_fallback
    return ui_text(key, app_language=app_language, fallback_text=fallback)


def _field(source: object, name: str, default=None):
    return getattr(source, name, default)


def _normalized_onboarding_state(onboarding_state: object | None) -> Mapping[str, object] | None:
    if not isinstance(onboarding_state, Mapping):
        return None
    return onboarding_state


def _onboarding_incomplete(onboarding_state: object | None) -> bool:
    state = _normalized_onboarding_state(onboarding_state)
    if state is None:
        return False
    return not bool(state.get("first_success_achieved"))


def _onboarding_step_id(onboarding_state: object | None) -> str | None:
    state = _normalized_onboarding_state(onboarding_state)
    if state is None:
        return None
    step = str(state.get("current_step") or "").strip().lower()
    return step or None


def _result_history_status_key(item: object, result: object | None) -> str:
    result_state = str((_field(result, "result_state") if result is not None else _field(item, "result_state")) or "").strip().lower()
    final_status = str((_field(result, "final_status") if result is not None else None) or "").strip().lower()
    status_family = str(_field(item, "status_family") or "").strip().lower()
    combined = {result_state, final_status, status_family}
    if combined & _READY_SUCCESS:
        return "success"
    if combined & _READY_PARTIAL:
        return "partial"
    if combined & _READY_FAILURE:
        return "failed"
    if combined & _ACTIVE_STATES:
        return "running"
    return "unknown"




def _normalized_source_artifact(source: object | None) -> dict[str, object] | None:
    if source is None:
        return None
    if isinstance(source, Mapping):
        payload = dict(source)
    else:
        storage_role = _field(source, "storage_role")
        canonical_ref = _field(source, "canonical_ref")
        if not storage_role or not canonical_ref:
            return None
        payload = {
            "storage_role": storage_role,
            "canonical_ref": canonical_ref,
            "working_save_id": _field(source, "working_save_id"),
            "commit_id": _field(source, "commit_id"),
            "source_working_save_id": _field(source, "source_working_save_id"),
        }
    storage_role = str(payload.get("storage_role") or "").strip()
    canonical_ref = str(payload.get("canonical_ref") or "").strip()
    if storage_role not in {"working_save", "commit_snapshot"} or not canonical_ref:
        return None
    normalized = {
        "storage_role": storage_role,
        "canonical_ref": canonical_ref,
    }
    for key in ("working_save_id", "commit_id", "source_working_save_id"):
        value = payload.get(key)
        if value not in (None, ""):
            normalized[key] = value
    return normalized


def _result_history_source_artifact(item: object, result: object | None) -> dict[str, object] | None:
    resolved = _normalized_source_artifact(_field(result, "source_artifact") if result is not None else None)
    if resolved is not None:
        return resolved
    return _normalized_source_artifact(_field(item, "source_artifact"))

def _result_history_status_label(status_key: str, *, app_language: str) -> str:
    fallback = {
        "success": "Result ready",
        "partial": "Partial result",
        "failed": "Run failed",
        "running": "Run in progress",
        "unknown": "Result status unknown",
    }[status_key]
    return ui_text(f"result_history.status.{status_key}", app_language=app_language, fallback_text=fallback)


def _run_timestamp_label(item: object, result: object | None, *, app_language: str) -> str:
    timestamp = _field(item, "completed_at") or (_field(result, "updated_at") if result is not None else None) or _field(item, "updated_at") or _field(item, "created_at")
    formatted_timestamp = _format_surface_timestamp(timestamp) or str(timestamp or "")
    return ui_text("result_history.timestamp", app_language=app_language, fallback_text=f"Last updated: {formatted_timestamp}", updated_at=formatted_timestamp)


def _result_title(item: object, result: object | None, *, app_language: str) -> str:
    result_summary = _field(result, "result_summary") if result is not None else None
    item_summary = _field(item, "result_summary")
    if result_summary is not None:
        return _localized_system_result_title(str(_field(result_summary, "title") or "Result"), app_language=app_language)
    if item_summary is not None:
        return _localized_system_result_title(str(_field(item_summary, "title") or "Result"), app_language=app_language)
    status_key = _result_history_status_key(item, result)
    fallback = {
        "success": "Last successful result",
        "partial": "Latest partial result",
        "failed": "Latest failed run",
        "running": "Latest run still in progress",
        "unknown": "Latest run result",
    }[status_key]
    return ui_text(f"result_history.title.{status_key}", app_language=app_language, fallback_text=fallback)


def _result_summary_text(item: object, result: object | None, *, app_language: str) -> str:
    result_summary = _field(result, "result_summary") if result is not None else None
    item_summary = _field(item, "result_summary")
    if result_summary is not None:
        return _localized_system_result_summary(str(_field(result_summary, "description") or ""), app_language=app_language)
    if item_summary is not None:
        return _localized_system_result_summary(str(_field(item_summary, "description") or ""), app_language=app_language)
    status_key = _result_history_status_key(item, result)
    fallback = {
        "success": "A recent result is available for this workflow.",
        "partial": "A partial result is available for this workflow.",
        "failed": "The last run failed before producing a complete result.",
        "running": "This run is still progressing and does not have a final result yet.",
        "unknown": "Recent result details are not available yet.",
    }[status_key]
    return ui_text(f"result_history.summary.{status_key}", app_language=app_language, fallback_text=fallback)




def _localized_output_key(value: object, *, app_language: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return raw
    return ui_text(
        f"result_history.output_key.{raw}",
        app_language=app_language,
        fallback_text=raw,
    )

def _result_history_item(item: object, result: object | None, *, app_language: str) -> ResultHistoryItemView:
    status_key = _result_history_status_key(item, result)
    output_preview = None
    output_label = None
    final_output = _field(result, "final_output") if result is not None else None
    if final_output is not None:
        output_preview = _field(final_output, "value_preview")
        output_key = _localized_output_key(_field(final_output, "output_key"), app_language=app_language)
        output_label = ui_text("result_history.output_label", app_language=app_language, fallback_text=f"Latest output ({output_key})", output_key=output_key)
    workspace_id = str(_field(item, "workspace_id") or "")
    run_id = str(_field(item, "run_id") or "")
    open_result_href = f"/app/workspaces/{workspace_id}/results?run_id={run_id}"
    continue_href = f"/app/workspaces/{workspace_id}"
    summary_lines = [_run_timestamp_label(item, result, app_language=app_language), _result_summary_text(item, result, app_language=app_language)]
    if output_preview:
        summary_lines.append(ui_text("result_history.summary.output_preview", app_language=app_language, fallback_text=f"Latest output preview: {output_preview}", output_preview=output_preview))
    return ResultHistoryItemView(
        run_id=run_id,
        workspace_id=workspace_id,
        status_key=status_key,
        status_label=_result_history_status_label(status_key, app_language=app_language),
        timestamp_label=_run_timestamp_label(item, result, app_language=app_language),
        result_title=_result_title(item, result, app_language=app_language),
        result_summary=_result_summary_text(item, result, app_language=app_language),
        source_artifact=_result_history_source_artifact(item, result),
        output_preview=output_preview,
        output_label=output_label,
        open_result_href=open_result_href,
        continue_href=continue_href,
        summary_lines=summary_lines,
    )


def _onboarding_banner(*, onboarding_state: object | None, app_language: str, workspace_id: str | None, selected_run_id: str | None) -> tuple[bool, str | None, str | None, str | None, str | None, str | None]:
    incomplete = _onboarding_incomplete(onboarding_state)
    step_id = _onboarding_step_id(onboarding_state)
    workspace_href = f"/app/workspaces/{workspace_id}" if workspace_id else None
    result_href = None
    if workspace_id and selected_run_id:
        result_href = f"/app/workspaces/{workspace_id}/results?run_id={selected_run_id}"
    elif workspace_id:
        result_href = f"/app/workspaces/{workspace_id}/results"
    if not incomplete:
        return False, step_id, None, None, None, None
    if step_id == "read_result":
        return (
            True,
            step_id,
            ui_text("result_history.onboarding.title", app_language=app_language, fallback_text="Finish your first result"),
            ui_text("result_history.onboarding.read_result", app_language=app_language, fallback_text="Server-backed onboarding says reading this result is your next beginner step."),
            ui_text("result_history.onboarding.action.read_result", app_language=app_language, fallback_text="Stay on this result"),
            result_href,
        )
    if step_id == "run":
        return (
            True,
            step_id,
            ui_text("result_history.onboarding.title", app_language=app_language, fallback_text="Resume onboarding"),
            ui_text("result_history.onboarding.run", app_language=app_language, fallback_text="Server-backed onboarding says the run step is next, so keep this result history as reference and continue the workflow."),
            ui_text("result_history.onboarding.action.continue_workflow", app_language=app_language, fallback_text="Continue workflow"),
            workspace_href,
        )
    if step_id in {"review_preview", "approve", "enter_goal"}:
        return (
            True,
            step_id,
            ui_text("result_history.onboarding.title", app_language=app_language, fallback_text="Resume onboarding"),
            ui_text("result_history.onboarding.review", app_language=app_language, fallback_text="Your onboarding progress is still mid-flow, so return to the workflow and continue from the saved beginner step."),
            ui_text("result_history.onboarding.action.continue_workflow", app_language=app_language, fallback_text="Continue workflow"),
            workspace_href,
        )
    return (
        True,
        step_id,
        ui_text("result_history.onboarding.title", app_language=app_language, fallback_text="Resume onboarding"),
        ui_text("result_history.onboarding.resume", app_language=app_language, fallback_text="Server-backed onboarding progress was preserved, so you can continue from where you left off."),
        ui_text("result_history.onboarding.action.continue_workflow", app_language=app_language, fallback_text="Continue workflow"),
        workspace_href,
    )


def read_result_history_view_model(
    source: object | Sequence[object] | None,
    *,
    result_rows_by_run_id: dict[str, object] | None = None,
    app_language: str = "en",
    selected_run_id: str | None = None,
    explanation: str | None = None,
    onboarding_state: object | None = None,
) -> ResultHistoryViewModel:
    if source is not None and hasattr(source, "runs") and hasattr(source, "workspace_id"):
        workspace_id = _field(source, "workspace_id")
        workspace_title = _field(source, "workspace_title")
        run_items = list(_field(source, "runs") or ())
    else:
        workspace_id = None
        workspace_title = None
        run_items = list(source or ())
    result_rows_by_run_id = dict(result_rows_by_run_id or {})
    visible_runs = [item for item in run_items if _field(item, "result_summary") is not None or _field(item, "result_state") is not None or str(_field(item, "status_family") or "").strip().lower() in {"active", "pending", "terminal_success", "terminal_failure", "terminal_partial"}]
    items = [_result_history_item(item, result_rows_by_run_id.get(str(_field(item, "run_id") or "")), app_language=app_language) for item in visible_runs]
    selected = selected_run_id if any(item.run_id == selected_run_id for item in items) else (items[0].run_id if items else None)
    onboarding_incomplete, onboarding_step_id, onboarding_title, onboarding_summary, onboarding_action_label, onboarding_action_href = _onboarding_banner(
        onboarding_state=onboarding_state,
        app_language=app_language,
        workspace_id=workspace_id,
        selected_run_id=selected,
    )
    return ResultHistoryViewModel(
        workspace_id=workspace_id,
        workspace_title=workspace_title,
        visible=True,
        history_status="empty" if not items else "ready",
        title=ui_text("result_history.title", app_language=app_language, fallback_text="Recent results"),
        subtitle=ui_text("result_history.subtitle", app_language=app_language, fallback_text="Reopen a recent result without entering advanced trace tools."),
        returned_count=len(items),
        items=items,
        selected_run_id=selected,
        empty_title=ui_text("result_history.empty.title", app_language=app_language, fallback_text="No recent results yet"),
        empty_summary=ui_text("result_history.empty.summary", app_language=app_language, fallback_text="Run a workflow once, then return here to reopen its latest result."),
        onboarding_incomplete=onboarding_incomplete,
        onboarding_step_id=onboarding_step_id,
        onboarding_title=onboarding_title,
        onboarding_summary=onboarding_summary,
        onboarding_action_label=onboarding_action_label,
        onboarding_action_href=onboarding_action_href,
        explanation=explanation,
        feedback_href=(f"/app/workspaces/{workspace_id}/feedback?surface=result_history" + (f"&run_id={selected}" if selected else "")) if workspace_id else None,
        feedback_label=ui_text("result_history.action.feedback", app_language=app_language, fallback_text="Report a problem on this screen"),
    )
