from __future__ import annotations

from dataclasses import dataclass, field, replace

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, BuilderActionView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class MonitoringFocusView:
    run_id: str | None = None
    active_node_id: str | None = None
    selected_artifact_id: str | None = None
    visible_event_count: int = 0
    visible_artifact_count: int = 0


@dataclass(frozen=True)
class MonitoringHealthView:
    execution_status: str = "unknown"
    blocking_issue_count: int = 0
    warning_issue_count: int = 0
    replay_available: bool = False
    launch_available: bool = False
    cancel_available: bool = False
    partial_surface_count: int = 0


@dataclass(frozen=True)
class MonitoringReadinessView:
    posture: str = "unknown"
    posture_label: str | None = None
    live_execution: bool = False
    launch_available: bool = False
    replay_available: bool = False
    has_trace_events: bool = False
    has_artifacts: bool = False
    blocking_issue_count: int = 0
    warning_issue_count: int = 0
    partial_surface_count: int = 0
    enabled_local_action_count: int = 0


@dataclass(frozen=True)
class MonitoringFocusHintView:
    hint_kind: str = "overview"
    target_ref: str | None = None
    label: str | None = None
    explanation: str | None = None
    suggested_action_id: str | None = None


@dataclass(frozen=True)
class MonitoringWorkspaceHandoffView:
    destination_workspace: str = "runtime_monitoring"
    destination_panel: str | None = None
    target_ref: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class MonitoringActionShortcutView:
    action: BuilderActionView
    target_ref: str | None = None
    priority: str = "secondary"
    emphasis: str = "neutral"
    explanation: str | None = None


@dataclass(frozen=True)
class MonitoringAttentionTargetView:
    attention_kind: str = "general"
    urgency: str = "low"
    target_ref: str | None = None
    title: str | None = None
    summary: str | None = None
    destination_workspace: str = "runtime_monitoring"
    destination_panel: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    blocking: bool = False


@dataclass(frozen=True)
class MonitoringProgressStageView:
    stage_id: str = "launch"
    label: str | None = None
    state: str = "blocked"
    state_label: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    target_ref: str | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class MonitoringClosureBarrierView:
    barrier_kind: str = "general"
    severity: str = "medium"
    target_ref: str | None = None
    title: str | None = None
    summary: str | None = None
    action_id: str | None = None
    action_label: str | None = None
    destination_workspace: str = "runtime_monitoring"
    destination_panel: str | None = None
    blocking: bool = False


@dataclass(frozen=True)
class MonitoringClosureVerdictView:
    closure_state: str = "hold_runtime_monitoring"
    closure_label: str | None = None
    should_move_on: bool = False
    move_on_target_workspace: str | None = None
    pending_barrier_count: int = 0
    blocking_barrier_count: int = 0
    dominant_barrier_kind: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RuntimeMonitoringWorkspaceViewModel:
    workspace_status: str = "ready"
    workspace_status_label: str | None = None
    storage_role: str = "none"
    execution: ExecutionPanelViewModel | None = None
    trace_timeline: TraceTimelineViewerViewModel | None = None
    artifact: ArtifactViewerViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    focus: MonitoringFocusView = field(default_factory=MonitoringFocusView)
    health: MonitoringHealthView = field(default_factory=MonitoringHealthView)
    readiness: MonitoringReadinessView = field(default_factory=MonitoringReadinessView)
    focus_hint: MonitoringFocusHintView = field(default_factory=MonitoringFocusHintView)
    workspace_handoff: MonitoringWorkspaceHandoffView = field(default_factory=MonitoringWorkspaceHandoffView)
    local_actions: list[BuilderActionView] = field(default_factory=list)
    action_shortcuts: list[MonitoringActionShortcutView] = field(default_factory=list)
    attention_targets: list[MonitoringAttentionTargetView] = field(default_factory=list)
    progress_stages: list[MonitoringProgressStageView] = field(default_factory=list)
    closure_barriers: list[MonitoringClosureBarrierView] = field(default_factory=list)
    closure_verdict: MonitoringClosureVerdictView = field(default_factory=MonitoringClosureVerdictView)
    explanation: str | None = None
    suggested_actions: list[BuilderActionView] = field(default_factory=list)


_ACTION_META: dict[str, tuple[str, str, str]] = {
    "run_current": ("builder.action.run_current", "Run current", "execution"),
    "cancel_run": ("builder.action.cancel_run", "Cancel run", "execution"),
    "watch_run_progress": ("builder.action.watch_run_progress", "Watch progress", "execution"),
    "open_trace": ("builder.action.open_trace", "Open trace", "trace_timeline"),
    "open_artifacts": ("builder.action.open_artifacts", "Open artifacts", "artifact"),
    "replay_latest": ("builder.action.replay_latest", "Replay latest", "execution"),
    "open_result_history": ("builder.action.open_result_history", "Open recent results", "result_history"),
    "open_visual_editor": ("builder.action.open_visual_editor", "Open editor", "workspace_navigation"),
    "open_node_configuration": ("builder.action.open_node_configuration", "Open step settings", "workspace_navigation"),
    "open_feedback_channel": ("builder.action.open_feedback_channel", "Send feedback", "workspace_navigation"),
}



def _unwrap(source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None):
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



def _workspace_explanation(*, workspace_status: str, app_language: str) -> str | None:
    return ui_text(f"workspace.runtime.explanation.{workspace_status}", app_language=app_language, fallback_text=None)



def _workspace_suggested_actions(*, workspace_status: str, app_language: str) -> list[BuilderActionView]:
    if workspace_status == "launch_ready":
        return [
            BuilderActionView("run_current", ui_text("builder.action.run_current", app_language=app_language, fallback_text="Run current"), "execution", True),
            BuilderActionView("open_visual_editor", ui_text("builder.action.open_visual_editor", app_language=app_language, fallback_text="Open editor"), "navigation", True),
        ]
    if workspace_status == "live_monitoring":
        return [
            BuilderActionView("watch_run_progress", ui_text("builder.action.watch_run_progress", app_language=app_language, fallback_text="Watch progress"), "execution", True),
            BuilderActionView("cancel_run", ui_text("builder.action.cancel_run", app_language=app_language, fallback_text="Cancel run"), "execution", True),
            BuilderActionView("open_result_history", ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results"), "navigation", True),
        ]
    if workspace_status in {"terminal_review", "historical_review", "failed_review"}:
        return [
            BuilderActionView("open_result_history", ui_text("builder.action.open_result_history", app_language=app_language, fallback_text="Open recent results"), "navigation", True),
            BuilderActionView("replay_latest", ui_text("builder.action.replay_latest", app_language=app_language, fallback_text="Replay latest"), "execution", True),
            BuilderActionView("open_feedback_channel", ui_text("builder.action.open_feedback_channel", app_language=app_language, fallback_text="Send feedback"), "navigation", True),
        ]
    return []



def _action_lookup(action_schema: BuilderActionSchemaView) -> dict[str, BuilderActionView]:
    return {
        action.action_id: action
        for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    }



def _scoped_action(action: BuilderActionView) -> BuilderActionView:
    return replace(action, target_scope="runtime_monitoring")



def _manual_action(action_id: str, *, app_language: str, enabled: bool = True, reason_disabled: str | None = None) -> BuilderActionView:
    key, fallback, category = _ACTION_META[action_id]
    return BuilderActionView(
        action_id=action_id,
        label=ui_text(key, app_language=app_language, fallback_text=fallback),
        action_kind=category,
        enabled=enabled,
        reason_disabled=reason_disabled,
        target_scope="runtime_monitoring",
    )



def _action_or_manual(
    action_map: dict[str, BuilderActionView],
    action_id: str,
    *,
    app_language: str,
    enabled: bool = True,
    reason_disabled: str | None = None,
) -> BuilderActionView:
    if action_id in action_map:
        action = _scoped_action(action_map[action_id])
        if action.enabled == enabled and action.reason_disabled == reason_disabled:
            return action
        return replace(action, enabled=enabled, reason_disabled=reason_disabled)
    return _manual_action(action_id, app_language=app_language, enabled=enabled, reason_disabled=reason_disabled)



def _dedupe_actions(actions: list[BuilderActionView | None]) -> list[BuilderActionView]:
    seen: set[str] = set()
    deduped: list[BuilderActionView] = []
    for action in actions:
        if action is None or action.action_id in seen:
            continue
        seen.add(action.action_id)
        deduped.append(action)
    return deduped



def _workspace_status(
    *,
    execution_vm: ExecutionPanelViewModel | None,
    storage_role: str,
    launch_available: bool,
    blocking_issue_count: int,
) -> str:
    if execution_vm is None:
        return "empty"
    if execution_vm.execution_status in {"running", "queued"}:
        return "live_monitoring"
    if storage_role == "execution_record":
        return "terminal_review"
    if storage_role == "commit_snapshot" and launch_available:
        return "launch_ready"
    if blocking_issue_count:
        return "failed_review"
    return "historical_review"



def _readiness_view(
    *,
    workspace_status: str,
    app_language: str,
    health: MonitoringHealthView,
    has_trace_events: bool,
    has_artifacts: bool,
    enabled_local_action_count: int,
) -> MonitoringReadinessView:
    posture_map = {
        "empty": "await_launch",
        "launch_ready": "ready_to_launch",
        "live_monitoring": "active_monitoring",
        "failed_review": "failure_investigation",
        "historical_review": "history_review",
        "terminal_review": "terminal_inspection",
    }
    posture = posture_map.get(workspace_status, "overview")
    return MonitoringReadinessView(
        posture=posture,
        posture_label=ui_text(f"workspace.runtime.readiness.{posture}", app_language=app_language, fallback_text=posture.replace("_", " ")),
        live_execution=workspace_status == "live_monitoring",
        launch_available=health.launch_available,
        replay_available=health.replay_available,
        has_trace_events=has_trace_events,
        has_artifacts=has_artifacts,
        blocking_issue_count=health.blocking_issue_count,
        warning_issue_count=health.warning_issue_count,
        partial_surface_count=health.partial_surface_count,
        enabled_local_action_count=enabled_local_action_count,
    )



def _focus_hint_view(
    *,
    workspace_status: str,
    app_language: str,
    execution_vm: ExecutionPanelViewModel | None,
    artifact_vm: ArtifactViewerViewModel | None,
    trace_vm: TraceTimelineViewerViewModel | None,
) -> MonitoringFocusHintView:
    if workspace_status == "empty":
        return MonitoringFocusHintView(
            hint_kind="launch",
            explanation=ui_text("workspace.runtime.focus.empty", app_language=app_language, fallback_text="Start a run to see progress, trace, and artifacts here."),
            suggested_action_id="run_current",
        )
    if workspace_status == "launch_ready":
        label = execution_vm.run_identity.commit_id if execution_vm is not None else None
        return MonitoringFocusHintView(
            hint_kind="launch_ready",
            target_ref=label,
            label=label,
            explanation=ui_text("workspace.runtime.focus.launch_ready", app_language=app_language, fallback_text="This approved workflow is ready to launch. Start it to begin live monitoring."),
            suggested_action_id="run_current",
        )
    if workspace_status == "live_monitoring" and execution_vm is not None:
        node_label = execution_vm.active_context.active_node_label or execution_vm.active_context.active_node_id or execution_vm.run_identity.run_id
        return MonitoringFocusHintView(
            hint_kind="active_run",
            target_ref=execution_vm.active_context.active_node_id or execution_vm.run_identity.run_id,
            label=node_label,
            explanation=ui_text("workspace.runtime.focus.active_run", app_language=app_language, fallback_text="The live run is currently centered on {label}. Stay here to monitor progress.").format(label=node_label or "the active run"),
            suggested_action_id="watch_run_progress",
        )
    if artifact_vm is not None and artifact_vm.selected_artifact is not None:
        artifact_label = artifact_vm.selected_artifact.title
        return MonitoringFocusHintView(
            hint_kind="artifact_review",
            target_ref=artifact_vm.selected_artifact.artifact_id,
            label=artifact_label,
            explanation=ui_text("workspace.runtime.focus.artifact_review", app_language=app_language, fallback_text="Inspect artifact {label} to understand the current run outcome.").format(label=artifact_label),
            suggested_action_id="open_artifacts",
        )
    if workspace_status == "failed_review" and execution_vm is not None:
        failure_label = execution_vm.diagnostics.last_error_label or execution_vm.active_context.active_node_label or execution_vm.run_identity.run_id
        return MonitoringFocusHintView(
            hint_kind="failure_review",
            target_ref=execution_vm.active_context.active_node_id or execution_vm.run_identity.run_id,
            label=failure_label,
            explanation=ui_text("workspace.runtime.focus.failure_review", app_language=app_language, fallback_text="Review the failure around {label} before deciding what to rerun or repair.").format(label=failure_label or "this run"),
            suggested_action_id="replay_latest",
        )
    if trace_vm is not None and trace_vm.events:
        return MonitoringFocusHintView(
            hint_kind="timeline_overview",
            target_ref=trace_vm.events[0].event_id,
            label=trace_vm.summary.top_summary_label if trace_vm.summary.top_summary_label else None,
            explanation=ui_text("workspace.runtime.focus.history", app_language=app_language, fallback_text="Review the recent run timeline, outputs, and artifacts together from this monitoring surface."),
            suggested_action_id="open_result_history",
        )
    return MonitoringFocusHintView(
        hint_kind="overview",
        explanation=ui_text("workspace.runtime.focus.overview", app_language=app_language, fallback_text="Use this workspace to inspect runtime progress, trace, outputs, and replay posture together."),
        suggested_action_id="open_result_history",
    )



def _local_actions(
    *,
    workspace_status: str,
    app_language: str,
    action_map: dict[str, BuilderActionView],
    health: MonitoringHealthView,
    has_trace_events: bool,
    has_artifacts: bool,
) -> list[BuilderActionView]:
    artifact_reason = None if has_artifacts else ui_text("workspace.runtime.reason.artifacts_unavailable", app_language=app_language, fallback_text="Artifacts are not available yet.")
    trace_reason = None if has_trace_events else ui_text("workspace.runtime.reason.trace_unavailable", app_language=app_language, fallback_text="Trace events are not available yet.")
    replay_reason = None if health.replay_available else ui_text("workspace.runtime.reason.replay_unavailable", app_language=app_language, fallback_text="Replay is not available yet.")
    launch_reason = None if health.launch_available else ui_text("workspace.runtime.reason.launch_unavailable", app_language=app_language, fallback_text="This workflow is not ready to launch from here.")

    if workspace_status == "empty":
        return _dedupe_actions([
            _action_or_manual(action_map, "run_current", app_language=app_language, enabled=False, reason_disabled=launch_reason),
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language),
        ])
    if workspace_status == "launch_ready":
        return _dedupe_actions([
            _action_or_manual(action_map, "run_current", app_language=app_language, enabled=health.launch_available, reason_disabled=launch_reason),
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language),
            _action_or_manual(action_map, "open_trace", app_language=app_language, enabled=has_trace_events, reason_disabled=trace_reason),
        ])
    if workspace_status == "live_monitoring":
        return _dedupe_actions([
            _action_or_manual(action_map, "watch_run_progress", app_language=app_language),
            _action_or_manual(action_map, "cancel_run", app_language=app_language, enabled=health.cancel_available),
            _action_or_manual(action_map, "open_trace", app_language=app_language, enabled=has_trace_events, reason_disabled=trace_reason),
            _action_or_manual(action_map, "open_artifacts", app_language=app_language, enabled=has_artifacts, reason_disabled=artifact_reason),
            _action_or_manual(action_map, "open_result_history", app_language=app_language),
        ])
    if workspace_status == "failed_review":
        return _dedupe_actions([
            _action_or_manual(action_map, "replay_latest", app_language=app_language, enabled=health.replay_available, reason_disabled=replay_reason),
            _action_or_manual(action_map, "open_trace", app_language=app_language, enabled=has_trace_events, reason_disabled=trace_reason),
            _action_or_manual(action_map, "open_artifacts", app_language=app_language, enabled=has_artifacts, reason_disabled=artifact_reason),
            _action_or_manual(action_map, "open_visual_editor", app_language=app_language),
            _action_or_manual(action_map, "open_node_configuration", app_language=app_language),
        ])
    return _dedupe_actions([
        _action_or_manual(action_map, "open_result_history", app_language=app_language),
        _action_or_manual(action_map, "replay_latest", app_language=app_language, enabled=health.replay_available, reason_disabled=replay_reason),
        _action_or_manual(action_map, "open_artifacts", app_language=app_language, enabled=has_artifacts, reason_disabled=artifact_reason),
        _action_or_manual(action_map, "open_feedback_channel", app_language=app_language),
    ])



def _action_shortcuts(
    *,
    workspace_status: str,
    app_language: str,
    local_actions: list[BuilderActionView],
    focus: MonitoringFocusView,
) -> list[MonitoringActionShortcutView]:
    action_map = {action.action_id: action for action in local_actions}
    shortcut_specs: dict[str, list[tuple[str, str, str, str | None]]] = {
        "empty": [
            ("open_visual_editor", "primary", "selection", ui_text("workspace.runtime.shortcut.prepare_run", app_language=app_language, fallback_text="Open the editor to prepare a workflow worth running.")),
            ("open_node_configuration", "secondary", "selection", ui_text("workspace.runtime.shortcut.prepare_configuration", app_language=app_language, fallback_text="Open step settings when you need to fix configuration before running.")),
        ],
        "launch_ready": [
            ("run_current", "primary", "run", ui_text("workspace.runtime.shortcut.launch", app_language=app_language, fallback_text="Launch the current approved workflow from this monitoring surface.")),
            ("open_visual_editor", "secondary", "selection", ui_text("workspace.runtime.shortcut.return_to_editor", app_language=app_language, fallback_text="Return to the editor if you want to adjust the workflow before launching.")),
        ],
        "live_monitoring": [
            ("watch_run_progress", "primary", "runtime", ui_text("workspace.runtime.shortcut.watch_progress", app_language=app_language, fallback_text="Keep this view focused on the live run progression.")),
            ("open_trace", "secondary", "trace", ui_text("workspace.runtime.shortcut.open_trace", app_language=app_language, fallback_text="Open the trace timeline to inspect execution events in more detail.")),
            ("open_artifacts", "secondary", "artifact", ui_text("workspace.runtime.shortcut.open_artifacts", app_language=app_language, fallback_text="Inspect artifacts as they become available during the run.")),
        ],
        "failed_review": [
            ("replay_latest", "primary", "replay", ui_text("workspace.runtime.shortcut.replay", app_language=app_language, fallback_text="Replay the latest run after reviewing the failure.")),
            ("open_visual_editor", "secondary", "selection", ui_text("workspace.runtime.shortcut.return_to_editor", app_language=app_language, fallback_text="Return to the editor if the failure points to a structural issue.")),
            ("open_node_configuration", "secondary", "selection", ui_text("workspace.runtime.shortcut.inspect_configuration", app_language=app_language, fallback_text="Open step settings if the failure points to a configuration issue.")),
        ],
        "historical_review": [
            ("open_result_history", "primary", "history", ui_text("workspace.runtime.shortcut.history", app_language=app_language, fallback_text="Review recent result history from this monitoring surface.")),
            ("replay_latest", "secondary", "replay", ui_text("workspace.runtime.shortcut.replay", app_language=app_language, fallback_text="Replay the latest run if you need to validate the same path again.")),
        ],
        "terminal_review": [
            ("open_result_history", "primary", "history", ui_text("workspace.runtime.shortcut.history", app_language=app_language, fallback_text="Review recent result history from this monitoring surface.")),
            ("open_artifacts", "secondary", "artifact", ui_text("workspace.runtime.shortcut.inspect_artifact", app_language=app_language, fallback_text="Inspect the selected artifact to understand the final run outcome.")),
            ("replay_latest", "secondary", "replay", ui_text("workspace.runtime.shortcut.replay", app_language=app_language, fallback_text="Replay the latest run if you need to validate the same path again.")),
        ],
    }
    shortcuts: list[MonitoringActionShortcutView] = []
    for action_id, priority, emphasis, explanation in shortcut_specs.get(workspace_status, []):
        action = action_map.get(action_id)
        if action is None:
            continue
        target_ref = focus.run_id if action_id in {"watch_run_progress", "replay_latest", "open_result_history"} else focus.selected_artifact_id
        shortcuts.append(MonitoringActionShortcutView(action=action, target_ref=target_ref, priority=priority, emphasis=emphasis, explanation=explanation))
    return shortcuts



def _workspace_handoff(
    *,
    workspace_status: str,
    app_language: str,
    local_actions: list[BuilderActionView],
    focus: MonitoringFocusView,
) -> MonitoringWorkspaceHandoffView:
    action_map = {action.action_id: action for action in local_actions}
    if workspace_status == "empty":
        action = action_map.get("open_visual_editor")
        return MonitoringWorkspaceHandoffView(
            destination_workspace="visual_editor",
            destination_panel="graph",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            reason=ui_text("workspace.runtime.handoff.empty", app_language=app_language, fallback_text="Return to the visual editor to prepare a workflow before monitoring."),
        )
    if workspace_status == "launch_ready":
        action = action_map.get("run_current")
        return MonitoringWorkspaceHandoffView(
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            target_ref=focus.run_id,
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            reason=ui_text("workspace.runtime.handoff.launch_ready", app_language=app_language, fallback_text="Stay in runtime monitoring and launch the approved workflow from here."),
        )
    if workspace_status == "live_monitoring":
        action = action_map.get("watch_run_progress") or action_map.get("open_trace")
        return MonitoringWorkspaceHandoffView(
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            target_ref=focus.run_id,
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            reason=ui_text("workspace.runtime.handoff.live_monitoring", app_language=app_language, fallback_text="Stay in runtime monitoring while the run is still active."),
        )
    if workspace_status == "failed_review":
        action = action_map.get("open_visual_editor") or action_map.get("open_node_configuration")
        destination = "visual_editor" if action is not None and action.action_id == "open_visual_editor" else "node_configuration"
        panel = "graph" if destination == "visual_editor" else "inspector"
        return MonitoringWorkspaceHandoffView(
            destination_workspace=destination,
            destination_panel=panel,
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            reason=ui_text("workspace.runtime.handoff.failed_review", app_language=app_language, fallback_text="Use runtime evidence here, then return to editing or configuration only if the failure points there."),
        )
    action = action_map.get("open_result_history") or action_map.get("replay_latest")
    return MonitoringWorkspaceHandoffView(
        destination_workspace="runtime_monitoring",
        destination_panel="result_history",
        target_ref=focus.run_id,
        action_id=action.action_id if action is not None else None,
        action_label=action.label if action is not None else None,
        reason=ui_text("workspace.runtime.handoff.history", app_language=app_language, fallback_text="Stay in runtime monitoring to inspect history, artifacts, and replay posture together."),
    )



def _attention_targets(
    *,
    workspace_status: str,
    app_language: str,
    local_actions: list[BuilderActionView],
    execution_vm: ExecutionPanelViewModel | None,
    artifact_vm: ArtifactViewerViewModel | None,
    focus: MonitoringFocusView,
    health: MonitoringHealthView,
) -> list[MonitoringAttentionTargetView]:
    action_map = {action.action_id: action for action in local_actions}
    targets: list[MonitoringAttentionTargetView] = []
    if workspace_status == "empty":
        action = action_map.get("open_visual_editor")
        targets.append(MonitoringAttentionTargetView(
            attention_kind="prepare_run",
            urgency="high",
            title=ui_text("workspace.runtime.attention.prepare.title", app_language=app_language, fallback_text="Prepare a runnable workflow first"),
            summary=ui_text("workspace.runtime.attention.prepare.summary", app_language=app_language, fallback_text="Runtime monitoring has nothing concrete to inspect until a workflow is launched."),
            destination_workspace="visual_editor",
            destination_panel="graph",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            blocking=True,
        ))
    elif workspace_status == "launch_ready":
        action = action_map.get("run_current")
        targets.append(MonitoringAttentionTargetView(
            attention_kind="launch_run",
            urgency="high",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.attention.launch.title", app_language=app_language, fallback_text="Launch the approved workflow"),
            summary=ui_text("workspace.runtime.attention.launch.summary", app_language=app_language, fallback_text="This workflow is ready. Start it here to turn runtime monitoring into a live surface."),
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            blocking=False,
        ))
    elif workspace_status == "live_monitoring":
        action = action_map.get("watch_run_progress")
        active_label = execution_vm.active_context.active_node_label or execution_vm.active_context.active_node_id or execution_vm.run_identity.run_id if execution_vm is not None else focus.run_id
        targets.append(MonitoringAttentionTargetView(
            attention_kind="watch_live_run",
            urgency="high",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.attention.live.title", app_language=app_language, fallback_text="Watch the live run first"),
            summary=ui_text("workspace.runtime.attention.live.summary", app_language=app_language, fallback_text="The run is currently centered on {label}. Stay here until the live execution settles.").format(label=active_label or "the active run"),
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            blocking=True,
        ))
        if artifact_vm is not None and artifact_vm.selected_artifact is not None:
            artifact_action = action_map.get("open_artifacts")
            targets.append(MonitoringAttentionTargetView(
                attention_kind="inspect_artifact",
                urgency="medium",
                target_ref=artifact_vm.selected_artifact.artifact_id,
                title=ui_text("workspace.runtime.attention.artifact.title", app_language=app_language, fallback_text="Inspect the selected artifact"),
                summary=ui_text("workspace.runtime.attention.artifact.summary", app_language=app_language, fallback_text="Artifacts are already available. Use them to confirm what the live run has produced so far."),
                destination_workspace="runtime_monitoring",
                destination_panel="artifact",
                action_id=artifact_action.action_id if artifact_action is not None else None,
                action_label=artifact_action.label if artifact_action is not None else None,
                blocking=False,
            ))
    elif workspace_status == "failed_review":
        action = action_map.get("replay_latest")
        targets.append(MonitoringAttentionTargetView(
            attention_kind="failure_review",
            urgency="high",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.attention.failure.title", app_language=app_language, fallback_text="Review the failed run before replaying"),
            summary=ui_text("workspace.runtime.attention.failure.summary", app_language=app_language, fallback_text="The run still has blocking issues. Use runtime evidence to decide whether to replay or go back to editing."),
            destination_workspace="runtime_monitoring",
            destination_panel="trace_timeline",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            blocking=True,
        ))
    else:
        action = action_map.get("open_result_history")
        targets.append(MonitoringAttentionTargetView(
            attention_kind="history_review",
            urgency="medium",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.attention.history.title", app_language=app_language, fallback_text="Review the settled runtime evidence"),
            summary=ui_text("workspace.runtime.attention.history.summary", app_language=app_language, fallback_text="The live run is no longer active. Inspect the trace, artifacts, and replay posture together."),
            destination_workspace="runtime_monitoring",
            destination_panel="result_history",
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            blocking=False,
        ))
    return targets



def _progress_stages(
    *,
    workspace_status: str,
    app_language: str,
    local_actions: list[BuilderActionView],
    focus: MonitoringFocusView,
    health: MonitoringHealthView,
) -> list[MonitoringProgressStageView]:
    action_map = {action.action_id: action for action in local_actions}
    def stage_state(stage_id: str) -> str:
        if workspace_status == "empty":
            return "blocked" if stage_id in {"launch", "monitor", "inspect", "replay"} else "blocked"
        if workspace_status == "launch_ready":
            return {"launch": "current", "monitor": "ready", "inspect": "ready", "replay": "blocked"}.get(stage_id, "blocked")
        if workspace_status == "live_monitoring":
            return {"launch": "completed", "monitor": "current", "inspect": "ready", "replay": "blocked"}.get(stage_id, "blocked")
        if workspace_status == "failed_review":
            return {"launch": "completed", "monitor": "completed", "inspect": "current", "replay": "ready"}.get(stage_id, "blocked")
        return {"launch": "completed", "monitor": "completed", "inspect": "current", "replay": "ready"}.get(stage_id, "blocked")

    stage_action_ids = {
        "launch": "run_current",
        "monitor": "watch_run_progress",
        "inspect": "open_result_history",
        "replay": "replay_latest",
    }
    stage_explanations = {
        "launch": ui_text("workspace.runtime.progress.launch.explanation", app_language=app_language, fallback_text="Launch the workflow so runtime monitoring has live evidence to inspect."),
        "monitor": ui_text("workspace.runtime.progress.monitor.explanation", app_language=app_language, fallback_text="Monitor the active run until progress and outputs become stable."),
        "inspect": ui_text("workspace.runtime.progress.inspect.explanation", app_language=app_language, fallback_text="Inspect the settled run evidence, outputs, and artifacts together."),
        "replay": ui_text("workspace.runtime.progress.replay.explanation", app_language=app_language, fallback_text="Replay the latest run when you need to validate the same path again."),
    }
    stages: list[MonitoringProgressStageView] = []
    for stage_id, label_key in {
        "launch": "workspace.runtime.progress.stage.launch",
        "monitor": "workspace.runtime.progress.stage.monitor",
        "inspect": "workspace.runtime.progress.stage.inspect",
        "replay": "workspace.runtime.progress.stage.replay",
    }.items():
        action = action_map.get(stage_action_ids[stage_id])
        state = stage_state(stage_id)
        stages.append(MonitoringProgressStageView(
            stage_id=stage_id,
            label=ui_text(label_key, app_language=app_language, fallback_text=stage_id.title()),
            state=state,
            state_label=ui_text(f"workspace.runtime.progress.state.{state}", app_language=app_language, fallback_text=state.title()),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            target_ref=focus.run_id,
            explanation=stage_explanations[stage_id],
        ))
    return stages



def _closure_barriers(
    *,
    workspace_status: str,
    app_language: str,
    local_actions: list[BuilderActionView],
    focus: MonitoringFocusView,
    health: MonitoringHealthView,
) -> list[MonitoringClosureBarrierView]:
    action_map = {action.action_id: action for action in local_actions}
    barriers: list[MonitoringClosureBarrierView] = []
    if workspace_status == "empty":
        action = action_map.get("open_visual_editor")
        barriers.append(MonitoringClosureBarrierView(
            barrier_kind="no_execution_yet",
            severity="high",
            title=ui_text("workspace.runtime.barrier.no_execution.title", app_language=app_language, fallback_text="Launch a workflow before monitoring"),
            summary=ui_text("workspace.runtime.barrier.no_execution.summary", app_language=app_language, fallback_text="Runtime monitoring cannot close while there is still no execution to inspect."),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            destination_workspace="visual_editor",
            destination_panel="graph",
            blocking=True,
        ))
    elif workspace_status == "launch_ready":
        action = action_map.get("run_current")
        barriers.append(MonitoringClosureBarrierView(
            barrier_kind="run_not_started",
            severity="medium",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.barrier.run_not_started.title", app_language=app_language, fallback_text="Start the run first"),
            summary=ui_text("workspace.runtime.barrier.run_not_started.summary", app_language=app_language, fallback_text="The workflow is approved, but runtime monitoring has not yet received a live run to watch."),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            blocking=False,
        ))
    elif workspace_status == "live_monitoring":
        action = action_map.get("watch_run_progress")
        barriers.append(MonitoringClosureBarrierView(
            barrier_kind="run_in_progress",
            severity="high",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.barrier.run_in_progress.title", app_language=app_language, fallback_text="The run is still in progress"),
            summary=ui_text("workspace.runtime.barrier.run_in_progress.summary", app_language=app_language, fallback_text="Runtime monitoring should stay open while the current run is still active."),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            destination_workspace="runtime_monitoring",
            destination_panel="execution",
            blocking=True,
        ))
    elif workspace_status == "failed_review":
        action = action_map.get("replay_latest")
        barriers.append(MonitoringClosureBarrierView(
            barrier_kind="failed_run_review",
            severity="high",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.barrier.failed_run.title", app_language=app_language, fallback_text="The failed run still needs review"),
            summary=ui_text("workspace.runtime.barrier.failed_run.summary", app_language=app_language, fallback_text="Review the failed runtime evidence before deciding whether to replay or return to editing."),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            destination_workspace="runtime_monitoring",
            destination_panel="trace_timeline",
            blocking=True,
        ))
    if health.partial_surface_count:
        action = action_map.get("open_trace") or action_map.get("open_artifacts")
        barriers.append(MonitoringClosureBarrierView(
            barrier_kind="partial_surfaces",
            severity="medium",
            target_ref=focus.run_id,
            title=ui_text("workspace.runtime.barrier.partial_surfaces.title", app_language=app_language, fallback_text="Some runtime surfaces are still partial"),
            summary=ui_text("workspace.runtime.barrier.partial_surfaces.summary", app_language=app_language, fallback_text="Trace or artifact surfaces are still partial, so runtime monitoring is not fully settled yet."),
            action_id=action.action_id if action is not None else None,
            action_label=action.label if action is not None else None,
            destination_workspace="runtime_monitoring",
            destination_panel="trace_timeline" if action is not None and action.action_id == "open_trace" else "artifact",
            blocking=False,
        ))
    return barriers



def _closure_verdict(
    *,
    workspace_status: str,
    app_language: str,
    barriers: list[MonitoringClosureBarrierView],
) -> MonitoringClosureVerdictView:
    blocking_count = sum(1 for barrier in barriers if barrier.blocking)
    pending_count = len(barriers)
    dominant_kind = barriers[0].barrier_kind if barriers else None
    if workspace_status in {"empty", "launch_ready", "live_monitoring", "failed_review"}:
        closure_state = "hold_runtime_monitoring"
        summary = ui_text(
            f"workspace.runtime.closure.{workspace_status}",
            app_language=app_language,
            fallback_text="Runtime monitoring is still holding the workspace chain because live execution or unresolved review remains here.",
        )
    elif pending_count:
        closure_state = "near_closed"
        summary = ui_text(
            "workspace.runtime.closure.near_closed",
            app_language=app_language,
            fallback_text="Runtime monitoring is nearly settled, but a small amount of local review remains.",
        )
    else:
        closure_state = "workspace_chain_stable"
        summary = ui_text(
            "workspace.runtime.closure.workspace_chain_stable",
            app_language=app_language,
            fallback_text="Runtime monitoring is locally stable. The current workspace chain can be treated as provisionally closed.",
        )
    return MonitoringClosureVerdictView(
        closure_state=closure_state,
        closure_label=ui_text(f"workspace.runtime.closure.state.{closure_state}", app_language=app_language, fallback_text=closure_state.replace("_", " ")),
        should_move_on=False,
        move_on_target_workspace=None,
        pending_barrier_count=pending_count,
        blocking_barrier_count=blocking_count,
        dominant_barrier_kind=dominant_kind,
        summary=summary,
    )



def read_runtime_monitoring_workspace_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    live_events=None,
    selected_artifact_id: str | None = None,
    explanation: str | None = None,
) -> RuntimeMonitoringWorkspaceViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped, execution_record)

    execution_vm = read_execution_panel_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        execution_record=execution_record,
        live_events=live_events,
    ) if (source_unwrapped is not None or execution_record is not None) else None
    trace_vm = read_trace_timeline_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        execution_record=execution_record,
        live_events=live_events,
    ) if (source_unwrapped is not None or execution_record is not None) else None
    artifact_vm = read_artifact_viewer_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        execution_record=execution_record,
        selected_artifact_id=selected_artifact_id,
    ) if (source_unwrapped is not None or execution_record is not None) else None
    validation_vm = read_validation_panel_view_model(
        source_unwrapped if source_unwrapped is not None else execution_record,
        validation_report=validation_report,
        execution_record=execution_record,
    ) if (source_unwrapped is not None or execution_record is not None) else None
    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        execution_view=execution_vm,
        validation_view=validation_vm,
        trace_view=trace_vm,
        artifact_view=artifact_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped if source_unwrapped is not None else execution_record,
        execution_view=execution_vm,
        validation_view=validation_vm,
    )

    partial_surface_count = 0
    if trace_vm is not None and trace_vm.timeline_status == "partial":
        partial_surface_count += 1
    if artifact_vm is not None and artifact_vm.viewer_status == "partial":
        partial_surface_count += 1

    focus = MonitoringFocusView(
        run_id=execution_vm.run_identity.run_id if execution_vm is not None else None,
        active_node_id=execution_vm.active_context.active_node_id if execution_vm is not None else None,
        selected_artifact_id=(artifact_vm.selected_artifact.artifact_id if artifact_vm is not None and artifact_vm.selected_artifact is not None else selected_artifact_id),
        visible_event_count=len(trace_vm.events) if trace_vm is not None else 0,
        visible_artifact_count=len(artifact_vm.artifact_list) if artifact_vm is not None else 0,
    )
    actions = [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]
    replay_available = any(action.action_id in {"replay_latest", "open_latest_run"} and action.enabled for action in actions)
    launch_available = any(action.action_id in {"run_current", "run_from_commit"} and action.enabled for action in actions)
    health = MonitoringHealthView(
        execution_status=execution_vm.execution_status if execution_vm is not None else "unknown",
        blocking_issue_count=validation_vm.summary.blocking_count if validation_vm is not None else 0,
        warning_issue_count=validation_vm.summary.warning_count if validation_vm is not None else 0,
        replay_available=replay_available,
        launch_available=launch_available,
        cancel_available=any(action.action_id == "cancel_run" and action.enabled for action in actions),
        partial_surface_count=partial_surface_count,
    )

    workspace_status = _workspace_status(
        execution_vm=execution_vm,
        storage_role=storage_role,
        launch_available=launch_available,
        blocking_issue_count=health.blocking_issue_count,
    )

    action_map = _action_lookup(action_schema)
    local_actions = _local_actions(
        workspace_status=workspace_status,
        app_language=app_language,
        action_map=action_map,
        health=health,
        has_trace_events=bool(trace_vm and trace_vm.events),
        has_artifacts=bool(artifact_vm and artifact_vm.artifact_list),
    )
    readiness = _readiness_view(
        workspace_status=workspace_status,
        app_language=app_language,
        health=health,
        has_trace_events=bool(trace_vm and trace_vm.events),
        has_artifacts=bool(artifact_vm and artifact_vm.artifact_list),
        enabled_local_action_count=sum(1 for action in local_actions if action.enabled),
    )
    focus_hint = _focus_hint_view(
        workspace_status=workspace_status,
        app_language=app_language,
        execution_vm=execution_vm,
        artifact_vm=artifact_vm,
        trace_vm=trace_vm,
    )
    workspace_handoff = _workspace_handoff(
        workspace_status=workspace_status,
        app_language=app_language,
        local_actions=local_actions,
        focus=focus,
    )
    action_shortcuts = _action_shortcuts(
        workspace_status=workspace_status,
        app_language=app_language,
        local_actions=local_actions,
        focus=focus,
    )
    attention_targets = _attention_targets(
        workspace_status=workspace_status,
        app_language=app_language,
        local_actions=local_actions,
        execution_vm=execution_vm,
        artifact_vm=artifact_vm,
        focus=focus,
        health=health,
    )
    progress_stages = _progress_stages(
        workspace_status=workspace_status,
        app_language=app_language,
        local_actions=local_actions,
        focus=focus,
        health=health,
    )
    closure_barriers = _closure_barriers(
        workspace_status=workspace_status,
        app_language=app_language,
        local_actions=local_actions,
        focus=focus,
        health=health,
    )
    closure_verdict = _closure_verdict(
        workspace_status=workspace_status,
        app_language=app_language,
        barriers=closure_barriers,
    )

    workspace_explanation = explanation or _workspace_explanation(
        workspace_status=workspace_status,
        app_language=app_language,
    )
    suggested_actions = _workspace_suggested_actions(
        workspace_status=workspace_status,
        app_language=app_language,
    )

    return RuntimeMonitoringWorkspaceViewModel(
        workspace_status=workspace_status,
        workspace_status_label=ui_text(f"workspace.runtime.status.{workspace_status}", app_language=app_language, fallback_text=workspace_status.replace("_", " ")),
        storage_role=storage_role,
        execution=execution_vm,
        trace_timeline=trace_vm,
        artifact=artifact_vm,
        validation=validation_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        focus=focus,
        health=health,
        readiness=readiness,
        focus_hint=focus_hint,
        workspace_handoff=workspace_handoff,
        local_actions=local_actions,
        action_shortcuts=action_shortcuts,
        attention_targets=attention_targets,
        progress_stages=progress_stages,
        closure_barriers=closure_barriers,
        closure_verdict=closure_verdict,
        explanation=workspace_explanation,
        suggested_actions=suggested_actions,
    )


__all__ = [
    "MonitoringFocusView",
    "MonitoringHealthView",
    "MonitoringReadinessView",
    "MonitoringFocusHintView",
    "MonitoringWorkspaceHandoffView",
    "MonitoringActionShortcutView",
    "MonitoringAttentionTargetView",
    "MonitoringProgressStageView",
    "MonitoringClosureBarrierView",
    "MonitoringClosureVerdictView",
    "RuntimeMonitoringWorkspaceViewModel",
    "read_runtime_monitoring_workspace_view_model",
]
