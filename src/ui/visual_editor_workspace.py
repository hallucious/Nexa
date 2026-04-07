from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.i18n import ui_language_from_sources, ui_text
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model


@dataclass(frozen=True)
class EditorCanvasSummaryView:
    node_count: int = 0
    edge_count: int = 0
    selected_node_count: int = 0
    selected_edge_count: int = 0
    preview_change_count: int = 0
    blocked_finding_count: int = 0


@dataclass(frozen=True)
class EditorComparisonStateView:
    diff_mode: str | None = None
    viewer_status: str = "hidden"
    change_count: int = 0
    selected_change_id: str | None = None
    can_open_diff: bool = False


@dataclass(frozen=True)
class VisualEditorWorkspaceViewModel:
    workspace_status: str = "ready"
    workspace_status_label: str | None = None
    storage_role: str = "none"
    graph: GraphWorkspaceViewModel | None = None
    diff: DiffViewerViewModel | None = None
    coordination: BuilderPanelCoordinationStateView = field(default_factory=BuilderPanelCoordinationStateView)
    action_schema: BuilderActionSchemaView = field(default_factory=BuilderActionSchemaView)
    storage: StoragePanelViewModel | None = None
    validation: ValidationPanelViewModel | None = None
    canvas_summary: EditorCanvasSummaryView = field(default_factory=EditorCanvasSummaryView)
    comparison_state: EditorComparisonStateView = field(default_factory=EditorComparisonStateView)
    can_edit_graph: bool = False
    can_preview_changes: bool = False
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



def read_visual_editor_workspace_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    validation_report: ValidationReport | None = None,
    preview_overlay: GraphPreviewOverlay | None = None,
    diff_mode: str | None = None,
    diff_source=None,
    diff_target=None,
    explanation: str | None = None,
) -> VisualEditorWorkspaceViewModel:
    source_unwrapped = _unwrap(source)
    storage_role = _storage_role(source_unwrapped)
    app_language = ui_language_from_sources(source_unwrapped)

    graph_vm = read_graph_view_model(
        source,
        validation_report=validation_report,
        preview_overlay=preview_overlay,
    ) if source is not None else None
    storage_vm = read_storage_view_model(source_unwrapped) if source_unwrapped is not None else None
    validation_vm = read_validation_panel_view_model(source_unwrapped, validation_report=validation_report) if source_unwrapped is not None else None

    diff_vm = None
    if diff_mode and diff_source is not None and diff_target is not None:
        diff_vm = read_diff_view_model(diff_mode=diff_mode, source=diff_source, target=diff_target)
    elif preview_overlay is not None and source_unwrapped is not None:
        diff_vm = read_diff_view_model(diff_mode="preview_vs_current", source=preview_overlay, target=source_unwrapped)

    coordination_vm = read_panel_coordination_state(
        source_unwrapped,
        graph_view=graph_vm,
        storage_view=storage_vm,
        diff_view=diff_vm,
        validation_view=validation_vm,
    )
    action_schema = read_builder_action_schema(
        source_unwrapped,
        storage_view=storage_vm,
        validation_view=validation_vm,
    )

    preview_change_count = 0
    if graph_vm is not None and graph_vm.preview_overlay is not None:
        overlay = graph_vm.preview_overlay
        preview_change_count = len(overlay.added_node_ids) + len(overlay.updated_node_ids) + len(overlay.removed_edge_ids)

    canvas_summary = EditorCanvasSummaryView(
        node_count=graph_vm.graph_metrics.node_count if graph_vm is not None else 0,
        edge_count=graph_vm.graph_metrics.edge_count if graph_vm is not None else 0,
        selected_node_count=len(graph_vm.selected_node_ids) if graph_vm is not None else 0,
        selected_edge_count=len(graph_vm.selected_edge_ids) if graph_vm is not None else 0,
        preview_change_count=preview_change_count,
        blocked_finding_count=validation_vm.summary.blocking_count if validation_vm is not None else 0,
    )
    comparison_state = EditorComparisonStateView(
        diff_mode=diff_vm.diff_mode if diff_vm is not None else None,
        viewer_status=diff_vm.viewer_status if diff_vm is not None else "hidden",
        change_count=sum(group.count for group in diff_vm.grouped_changes) if diff_vm is not None else 0,
        selected_change_id=diff_vm.selected_change.change_id if diff_vm is not None and diff_vm.selected_change is not None else None,
        can_open_diff=any(action.action_id == "open_diff" and action.enabled for action in [*action_schema.primary_actions, *action_schema.secondary_actions, *action_schema.contextual_actions]) or diff_vm is not None,
    )

    if graph_vm is None:
        workspace_status = "empty"
    elif validation_vm is not None and validation_vm.overall_status == "blocked":
        workspace_status = "blocked"
    elif graph_vm.preview_overlay is not None:
        workspace_status = "previewing"
    else:
        workspace_status = "editing" if storage_role == "working_save" else "viewing"

    return VisualEditorWorkspaceViewModel(
        workspace_status=workspace_status,
        workspace_status_label=ui_text(f"workspace.visual_editor.status.{workspace_status}", app_language=app_language, fallback_text=workspace_status.replace("_", " ")),
        storage_role=storage_role,
        graph=graph_vm,
        diff=diff_vm,
        coordination=coordination_vm,
        action_schema=action_schema,
        storage=storage_vm,
        validation=validation_vm,
        canvas_summary=canvas_summary,
        comparison_state=comparison_state,
        can_edit_graph=storage_role == "working_save",
        can_preview_changes=graph_vm is not None and graph_vm.preview_overlay is not None,
        explanation=explanation,
    )


__all__ = [
    "EditorCanvasSummaryView",
    "EditorComparisonStateView",
    "VisualEditorWorkspaceViewModel",
    "read_visual_editor_workspace_view_model",
]
