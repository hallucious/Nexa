from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview
from src.designer.models.circuit_patch_plan import CircuitPatchPlan
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import DesignerIntent
from src.designer.models.designer_session_state_card import DesignerSessionStateCard
from src.designer.models.validation_precheck import ValidationPrecheck
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class BuilderShellLayoutView:
    active_theme_id: str | None = None
    active_layout_id: str | None = None
    density_mode: str | None = None
    user_mode: str | None = None
    zoom_level: float | None = None
    viewport_center: dict[str, Any] = field(default_factory=dict)
    dock_mode: str | None = None


@dataclass(frozen=True)
class BuilderShellDiagnosticsView:
    warning_count: int = 0
    stale_selection_count: int = 0
    panel_coordination_warning: bool = False
    partial_panel_count: int = 0
    explanation: str | None = None


@dataclass(frozen=True)
class BuilderShellViewModel:
    shell_status: str = "ready"
    storage_role: str = "none"
    shell_mode: str = "builder"
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    graph: GraphWorkspaceViewModel | None = None
    inspector: SelectedObjectViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    storage: StoragePanelViewModel | None = None
    execution: ExecutionPanelViewModel | None = None
    trace_timeline: TraceTimelineViewerViewModel | None = None
    artifact: ArtifactViewerViewModel | None = None
    diff: DiffViewerViewModel | None = None
    designer: DesignerPanelViewModel | None = None
    layout: BuilderShellLayoutView = field(default_factory=BuilderShellLayoutView)
    diagnostics: BuilderShellDiagnosticsView = field(default_factory=BuilderShellDiagnosticsView)
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


def _ui_metadata(source) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.metadata or {})
    return {}


def _ui_layout(source) -> dict[str, Any]:
    if isinstance(source, WorkingSaveModel):
        return dict(source.ui.layout or {})
    return {}


def read_builder_shell_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    validation_report: ValidationReport | None = None,
    execution_record: ExecutionRecordModel | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    selected_ref: str | None = None,
    live_events=None,
    diff_mode: str | None = None,
    diff_source=None,
    diff_target=None,
    selected_artifact_id: str | None = None,
    session_state_card: DesignerSessionStateCard | None = None,
    intent: DesignerIntent | None = None,
    patch_plan: CircuitPatchPlan | None = None,
    precheck: ValidationPrecheck | None = None,
    preview: CircuitDraftPreview | None = None,
    approval_flow: DesignerApprovalFlowState | None = None,
    explanation: str | None = None,
) -> BuilderShellViewModel:
    source_unwrapped = _unwrap(source)
    role = _storage_role(source_unwrapped)

    graph_vm = read_graph_view_model(
        source,
        validation_report=validation_report,
        execution_record=execution_record,
        preview_overlay=preview_overlay,
    ) if source is not None else None

    storage_vm = read_storage_view_model(source_unwrapped) if source_unwrapped is not None else None
    execution_vm = read_execution_panel_view_model(source_unwrapped, execution_record=execution_record, live_events=live_events) if source_unwrapped is not None else None
    trace_vm = read_trace_timeline_view_model(source_unwrapped if isinstance(source_unwrapped, ExecutionRecordModel) else source_unwrapped, execution_record=execution_record, live_events=live_events) if (source_unwrapped is not None or execution_record is not None) else None
    artifact_vm = read_artifact_viewer_view_model(source_unwrapped if source_unwrapped is not None else execution_record, execution_record=execution_record, selected_artifact_id=selected_artifact_id) if (source_unwrapped is not None or execution_record is not None) else None
    inspector_vm = read_selected_object_view_model(source_unwrapped, selected_ref=selected_ref, validation_report=validation_report, execution_record=execution_record, preview_overlay=preview_overlay) if source_unwrapped is not None else None
    validation_vm = read_validation_panel_view_model(source_unwrapped, validation_report=validation_report, precheck=precheck, execution_record=execution_record) if source_unwrapped is not None else None
    designer_vm = read_designer_panel_view_model(source_unwrapped, session_state_card=session_state_card, intent=intent, patch_plan=patch_plan, precheck=precheck, preview=preview, approval_flow=approval_flow) if source_unwrapped is not None else None

    diff_vm = None
    if diff_mode and diff_source is not None and diff_target is not None:
        diff_vm = read_diff_view_model(diff_mode=diff_mode, source=diff_source, target=diff_target)
    elif preview_overlay is not None and source_unwrapped is not None:
        diff_vm = read_diff_view_model(diff_mode="preview_vs_current", source=preview_overlay, target=source_unwrapped)
    elif isinstance(source_unwrapped, WorkingSaveModel) and storage_vm is not None and storage_vm.commit_snapshot_card is not None and storage_vm.commit_snapshot_card.commit_id is not None:
        # default shell comparison is only available when explicit commit target is supplied later.
        diff_vm = None

    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        graph_view=graph_vm,
        storage_view=storage_vm,
        diff_view=diff_vm,
        execution_view=execution_vm,
        validation_view=validation_vm,
        designer_view=designer_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        designer_view=designer_vm,
    )

    metadata = _ui_metadata(source_unwrapped)
    layout = _ui_layout(source_unwrapped)
    layout_vm = BuilderShellLayoutView(
        active_theme_id=str(metadata.get("active_theme_id")) if metadata.get("active_theme_id") is not None else None,
        active_layout_id=str(metadata.get("active_layout_id")) if metadata.get("active_layout_id") is not None else None,
        density_mode=str(metadata.get("density_mode")) if metadata.get("density_mode") is not None else None,
        user_mode=str(metadata.get("user_mode")) if metadata.get("user_mode") is not None else None,
        zoom_level=float(metadata.get("zoom_level")) if isinstance(metadata.get("zoom_level"), (int, float)) else None,
        viewport_center=dict(layout.get("viewport_center") or {}),
        dock_mode=str(metadata.get("dock_mode")) if metadata.get("dock_mode") is not None else None,
    )

    warning_count = 0
    partial_panel_count = 0
    for vm in [diff_vm, artifact_vm, trace_vm]:
        if vm is not None and getattr(vm, "viewer_status", None) == "partial":
            partial_panel_count += 1
    if validation_vm is not None:
        warning_count += validation_vm.summary.warning_count + validation_vm.summary.confirmation_count
    if storage_vm is not None:
        warning_count += storage_vm.diagnostics.lifecycle_warning_count

    shell_mode = "builder"
    if execution_vm is not None and execution_vm.execution_status in {"running", "queued"}:
        shell_mode = "runtime_monitoring"
    elif designer_vm is not None and designer_vm.request_state.request_status in {"submitted", "editing"}:
        shell_mode = "designer_review"
    elif role == "working_save":
        shell_mode = "draft_edit"
    elif role == "commit_snapshot":
        shell_mode = "snapshot_review"
    elif role == "execution_record":
        shell_mode = "run_review"

    diagnostics = BuilderShellDiagnosticsView(
        warning_count=warning_count,
        stale_selection_count=coordination_vm.stale_reference_count,
        panel_coordination_warning=coordination_vm.active_panel not in coordination_vm.visible_panels,
        partial_panel_count=partial_panel_count,
    )
    shell_status = "ready"
    if diagnostics.panel_coordination_warning:
        shell_status = "partial"
    if source_unwrapped is None:
        shell_status = "failed"

    return BuilderShellViewModel(
        shell_status=shell_status,
        storage_role=role,
        shell_mode=shell_mode,
        coordination=coordination_vm,
        action_schema=action_schema,
        graph=graph_vm,
        inspector=inspector_vm,
        validation=validation_vm,
        storage=storage_vm,
        execution=execution_vm,
        trace_timeline=trace_vm,
        artifact=artifact_vm,
        diff=diff_vm,
        designer=designer_vm,
        layout=layout_vm,
        diagnostics=diagnostics,
        explanation=explanation,
    )


__all__ = [
    "BuilderShellLayoutView",
    "BuilderShellDiagnosticsView",
    "BuilderShellViewModel",
    "read_builder_shell_view_model",
]
