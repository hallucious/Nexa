from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
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
    cancel_available: bool = False
    partial_surface_count: int = 0


@dataclass(frozen=True)
class RuntimeMonitoringWorkspaceViewModel:
    workspace_status: str = "ready"
    storage_role: str = "none"
    execution: ExecutionPanelViewModel | None = None
    trace_timeline: TraceTimelineViewerViewModel | None = None
    artifact: ArtifactViewerViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    focus: MonitoringFocusView = field(default_factory=MonitoringFocusView)
    health: MonitoringHealthView = field(default_factory=MonitoringHealthView)
    explanation: str | None = None



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
    health = MonitoringHealthView(
        execution_status=execution_vm.execution_status if execution_vm is not None else "unknown",
        blocking_issue_count=validation_vm.summary.blocking_count if validation_vm is not None else 0,
        warning_issue_count=validation_vm.summary.warning_count if validation_vm is not None else 0,
        replay_available=any(action.action_id == "replay_latest" and action.enabled for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]),
        cancel_available=any(action.action_id == "cancel_run" and action.enabled for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]),
        partial_surface_count=partial_surface_count,
    )

    if execution_vm is None:
        workspace_status = "empty"
    elif execution_vm.execution_status in {"running", "queued"}:
        workspace_status = "live_monitoring"
    elif health.blocking_issue_count:
        workspace_status = "failed_review"
    else:
        workspace_status = "historical_review"

    return RuntimeMonitoringWorkspaceViewModel(
        workspace_status=workspace_status,
        storage_role=storage_role,
        execution=execution_vm,
        trace_timeline=trace_vm,
        artifact=artifact_vm,
        validation=validation_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        focus=focus,
        health=health,
        explanation=explanation,
    )


__all__ = [
    "MonitoringFocusView",
    "MonitoringHealthView",
    "RuntimeMonitoringWorkspaceViewModel",
    "read_runtime_monitoring_workspace_view_model",
]
