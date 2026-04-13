from __future__ import annotations

from dataclasses import dataclass, field
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


_READY_SUCCESS = {"ready_success", "terminal_success", "completed"}
_READY_PARTIAL = {"ready_partial", "terminal_partial", "partial"}
_READY_FAILURE = {"ready_failure", "terminal_failure", "failed"}
_ACTIVE_STATES = {"pending", "active", "not_ready", "queued", "running"}


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
    return ui_text("result_history.timestamp", app_language=app_language, fallback_text=f"Last updated: {timestamp}", updated_at=timestamp)


def _result_title(item: object, result: object | None, *, app_language: str) -> str:
    result_summary = _field(result, "result_summary") if result is not None else None
    item_summary = _field(item, "result_summary")
    if result_summary is not None:
        return str(_field(result_summary, "title") or "Result")
    if item_summary is not None:
        return str(_field(item_summary, "title") or "Result")
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
        return str(_field(result_summary, "description") or "")
    if item_summary is not None:
        return str(_field(item_summary, "description") or "")
    status_key = _result_history_status_key(item, result)
    fallback = {
        "success": "A recent result is available for this workflow.",
        "partial": "A partial result is available for this workflow.",
        "failed": "The last run failed before producing a complete result.",
        "running": "This run is still progressing and does not have a final result yet.",
        "unknown": "Recent result details are not available yet.",
    }[status_key]
    return ui_text(f"result_history.summary.{status_key}", app_language=app_language, fallback_text=fallback)


def _result_history_item(item: object, result: object | None, *, app_language: str) -> ResultHistoryItemView:
    status_key = _result_history_status_key(item, result)
    output_preview = None
    output_label = None
    final_output = _field(result, "final_output") if result is not None else None
    if final_output is not None:
        output_preview = _field(final_output, "value_preview")
        output_key = _field(final_output, "output_key")
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
    )
