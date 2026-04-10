from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.runtime_monitoring_workspace import RuntimeMonitoringWorkspaceViewModel, read_runtime_monitoring_workspace_view_model
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.visual_editor_workspace import VisualEditorWorkspaceViewModel, read_visual_editor_workspace_view_model


@dataclass(frozen=True)
class ExecutionLaunchSummaryView:
    run_id: str | None = None
    commit_anchor_ref: str | None = None
    execution_status: str = "unknown"
    launch_mode: str = "idle"
    blocking_count: int = 0
    warning_count: int = 0
    visible_event_count: int = 0
    visible_artifact_count: int = 0
    next_step_label: str | None = None


@dataclass(frozen=True)
class ExecutionLaunchActionStateView:
    run_action: BuilderActionView | None = None
    cancel_action: BuilderActionView | None = None
    replay_action: BuilderActionView | None = None
    compare_action: BuilderActionView | None = None


@dataclass(frozen=True)
class ExecutionLaunchWorkflowViewModel:
    workflow_status: str = "ready"
    storage_role: str = "none"
    visual_editor: VisualEditorWorkspaceViewModel | None = None
    runtime_monitoring: RuntimeMonitoringWorkspaceViewModel | None = None
    storage: StoragePanelViewModel | None = None
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    summary: ExecutionLaunchSummaryView = field(default_factory=ExecutionLaunchSummaryView)
    action_state: ExecutionLaunchActionStateView = field(default_factory=ExecutionLaunchActionStateView)
    can_launch: bool = False
    can_cancel: bool = False
    can_replay: bool = False
    explanation: str | None = None


SourceLike = WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None


def _unwrap(source: SourceLike):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _find_action(action_schema: BuilderActionSchemaView, action_id: str) -> BuilderActionView | None:
    for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]:
        if action.action_id == action_id:
            return action
    return None


def read_execution_launch_workflow_view_model(
    source: SourceLike,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    live_events=None,
    selected_artifact_id: str | None = None,
    explanation: str | None = None,
) -> ExecutionLaunchWorkflowViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    visual_editor_vm = read_visual_editor_workspace_view_model(source_unwrapped, validation_report=validation_report) if source_unwrapped is not None else None
    monitoring_vm = (
        read_runtime_monitoring_workspace_view_model(
            source_unwrapped if source_unwrapped is not None else execution_record,
            validation_report=validation_report,
            execution_record=execution_record,
            live_events=live_events,
            selected_artifact_id=selected_artifact_id,
        )
        if (source_unwrapped is not None or execution_record is not None)
        else None
    )
    storage_vm = read_storage_view_model(source_unwrapped if source_unwrapped is not None else execution_record) if (source_unwrapped is not None or execution_record is not None) else None

    action_schema = read_builder_action_schema(
        source_unwrapped if source_unwrapped is not None else execution_record,
        storage_view=storage_vm,
        validation_view=monitoring_vm.validation if monitoring_vm is not None else None,
        execution_view=monitoring_vm.execution if monitoring_vm is not None else None,
    )

    run_action = _find_action(action_schema, "run_current") or _find_action(action_schema, "run_from_commit")
    cancel_action = _find_action(action_schema, "cancel_run")
    replay_action = _find_action(action_schema, "replay_latest") or _find_action(action_schema, "open_latest_run")
    compare_action = _find_action(action_schema, "open_diff") or _find_action(action_schema, "compare_runs")

    run_identity = monitoring_vm.execution.run_identity if monitoring_vm is not None and monitoring_vm.execution is not None else None
    execution_status = monitoring_vm.health.execution_status if monitoring_vm is not None else "unknown"
    if execution_status in {"running", "queued"}:
        launch_mode = "live_run"
        next_step_label = ui_text("launch.next.monitor_live", app_language=app_language, fallback_text="Monitor live execution")
    elif replay_action is not None and replay_action.enabled:
        launch_mode = "replay_ready"
        next_step_label = ui_text("launch.next.replay_latest", app_language=app_language, fallback_text="Replay or inspect latest run")
    elif run_action is not None and run_action.enabled:
        launch_mode = "run_ready"
        next_step_label = ui_text("launch.next.launch_current", app_language=app_language, fallback_text="Launch current structure")
    else:
        launch_mode = "idle"
        next_step_label = ui_text("launch.next.resolve_validation", app_language=app_language, fallback_text="Resolve validation or select a run target")

    summary = ExecutionLaunchSummaryView(
        run_id=run_identity.run_id if run_identity is not None else None,
        commit_anchor_ref=storage_vm.relationship_graph.latest_commit_ref if storage_vm is not None else None,
        execution_status=execution_status,
        launch_mode=launch_mode,
        blocking_count=monitoring_vm.health.blocking_issue_count if monitoring_vm is not None else 0,
        warning_count=monitoring_vm.health.warning_issue_count if monitoring_vm is not None else 0,
        visible_event_count=monitoring_vm.focus.visible_event_count if monitoring_vm is not None else 0,
        visible_artifact_count=monitoring_vm.focus.visible_artifact_count if monitoring_vm is not None else 0,
        next_step_label=next_step_label,
    )

    if monitoring_vm is None:
        workflow_status = "empty"
    elif summary.blocking_count > 0 and not (run_action and run_action.enabled):
        workflow_status = "blocked"
    elif execution_status in {"running", "queued"}:
        workflow_status = "live_monitoring"
    elif replay_action is not None and replay_action.enabled:
        workflow_status = "replay_ready"
    elif run_action is not None and run_action.enabled:
        workflow_status = "launch_ready"
    else:
        workflow_status = "idle"

    return ExecutionLaunchWorkflowViewModel(
        workflow_status=workflow_status,
        storage_role=storage_role,
        visual_editor=visual_editor_vm,
        runtime_monitoring=monitoring_vm,
        storage=storage_vm,
        action_schema=action_schema,
        summary=summary,
        action_state=ExecutionLaunchActionStateView(
            run_action=run_action,
            cancel_action=cancel_action,
            replay_action=replay_action,
            compare_action=compare_action,
        ),
        can_launch=bool(run_action and run_action.enabled),
        can_cancel=bool(cancel_action and cancel_action.enabled),
        can_replay=bool(replay_action and replay_action.enabled),
        explanation=explanation,
    )


__all__ = [
    "ExecutionLaunchSummaryView",
    "ExecutionLaunchActionStateView",
    "ExecutionLaunchWorkflowViewModel",
    "read_execution_launch_workflow_view_model",
]
