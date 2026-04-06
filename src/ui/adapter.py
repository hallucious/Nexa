from __future__ import annotations

from dataclasses import dataclass

from src.contracts.nex_contract import ValidationReport
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.execution_record_model import ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.working_save_model import WorkingSaveModel
from src.ui.diff_viewer import DiffViewerViewModel, read_diff_view_model
from src.ui.graph_workspace import GraphPreviewOverlay, GraphWorkspaceViewModel, read_graph_view_model
from src.ui.storage_panel import StoragePanelViewModel, read_storage_view_model
from src.ui.execution_panel import ExecutionPanelViewModel, read_execution_panel_view_model
from src.ui.trace_timeline_viewer import TraceTimelineViewerViewModel, read_trace_timeline_view_model
from src.ui.artifact_viewer import ArtifactViewerViewModel, read_artifact_viewer_view_model
from src.ui.inspector_panel import SelectedObjectViewModel, read_selected_object_view_model
from src.ui.validation_panel import ValidationPanelViewModel, read_validation_panel_view_model
from src.ui.designer_panel import DesignerPanelViewModel, read_designer_panel_view_model
from src.ui.builder_shell import BuilderShellViewModel, read_builder_shell_view_model
from src.ui.action_schema import BuilderActionSchemaView, read_builder_action_schema
from src.ui.panel_coordination import BuilderPanelCoordinationStateView, read_panel_coordination_state


@dataclass(frozen=True)
class NexaUIViewAdapter:
    latest_working_save: WorkingSaveModel | None = None
    latest_commit_snapshot: CommitSnapshotModel | None = None
    latest_execution_record: ExecutionRecordModel | None = None

    def read_graph_view_model(
        self,
        source: WorkingSaveModel | CommitSnapshotModel | LoadedNexArtifact,
        *,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
    ) -> GraphWorkspaceViewModel:
        return read_graph_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
        )

    def read_storage_view_model(
        self,
        active_source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
        *,
        explanation: str | None = None,
    ) -> StoragePanelViewModel:
        return read_storage_view_model(
            active_source,
            latest_working_save=self.latest_working_save,
            latest_commit_snapshot=self.latest_commit_snapshot,
            latest_execution_record=self.latest_execution_record,
            explanation=explanation,
        )


    def read_execution_panel_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        explanation: str | None = None,
    ) -> ExecutionPanelViewModel:
        return read_execution_panel_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            explanation=explanation,
        )

    def read_trace_timeline_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        live_events=None,
        explanation: str | None = None,
    ) -> TraceTimelineViewerViewModel:
        return read_trace_timeline_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            live_events=live_events,
            explanation=explanation,
        )


    def read_inspector_panel_view_model(
        self,
        source,
        *,
        selected_ref: str | None = None,
        validation_report: ValidationReport | None = None,
        execution_record: ExecutionRecordModel | None = None,
        preview_overlay: GraphPreviewOverlay | None = None,
        explanation: str | None = None,
    ) -> SelectedObjectViewModel:
        return read_selected_object_view_model(
            source,
            selected_ref=selected_ref,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            explanation=explanation,
        )

    def read_validation_panel_view_model(
        self,
        source,
        *,
        validation_report: ValidationReport | None = None,
        precheck=None,
        execution_record: ExecutionRecordModel | None = None,
        explanation: str | None = None,
    ) -> ValidationPanelViewModel:
        return read_validation_panel_view_model(
            source,
            validation_report=validation_report,
            precheck=precheck,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            explanation=explanation,
        )

    def read_designer_panel_view_model(
        self,
        source,
        *,
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> DesignerPanelViewModel:
        return read_designer_panel_view_model(
            source,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )

    def read_artifact_viewer_view_model(
        self,
        source,
        *,
        execution_record: ExecutionRecordModel | None = None,
        selected_artifact_id: str | None = None,
        explanation: str | None = None,
    ) -> ArtifactViewerViewModel:
        return read_artifact_viewer_view_model(
            source,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            selected_artifact_id=selected_artifact_id,
            explanation=explanation,
        )

    def read_diff_view_model(
        self,
        *,
        diff_mode: str,
        source,
        target,
        explanation: str | None = None,
    ) -> DiffViewerViewModel:
        return read_diff_view_model(diff_mode=diff_mode, source=source, target=target, explanation=explanation)

    def read_builder_action_schema_view(
        self,
        source,
        *,
        storage_view: StoragePanelViewModel | None = None,
        validation_view: ValidationPanelViewModel | None = None,
        execution_view: ExecutionPanelViewModel | None = None,
        designer_view: DesignerPanelViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderActionSchemaView:
        return read_builder_action_schema(
            source,
            storage_view=storage_view,
            validation_view=validation_view,
            execution_view=execution_view,
            designer_view=designer_view,
            explanation=explanation,
        )

    def read_panel_coordination_state_view(
        self,
        source,
        *,
        graph_view: GraphWorkspaceViewModel | None = None,
        storage_view: StoragePanelViewModel | None = None,
        diff_view: DiffViewerViewModel | None = None,
        execution_view: ExecutionPanelViewModel | None = None,
        validation_view: ValidationPanelViewModel | None = None,
        designer_view: DesignerPanelViewModel | None = None,
        explanation: str | None = None,
    ) -> BuilderPanelCoordinationStateView:
        return read_panel_coordination_state(
            source,
            graph_view=graph_view,
            storage_view=storage_view,
            diff_view=diff_view,
            execution_view=execution_view,
            validation_view=validation_view,
            designer_view=designer_view,
            explanation=explanation,
        )

    def read_builder_shell_view_model(
        self,
        source,
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
        session_state_card=None,
        intent=None,
        patch_plan=None,
        precheck=None,
        preview=None,
        approval_flow=None,
        explanation: str | None = None,
    ) -> BuilderShellViewModel:
        return read_builder_shell_view_model(
            source,
            validation_report=validation_report,
            execution_record=execution_record if execution_record is not None else self.latest_execution_record,
            preview_overlay=preview_overlay,
            selected_ref=selected_ref,
            live_events=live_events,
            diff_mode=diff_mode,
            diff_source=diff_source,
            diff_target=diff_target,
            selected_artifact_id=selected_artifact_id,
            session_state_card=session_state_card,
            intent=intent,
            patch_plan=patch_plan,
            precheck=precheck,
            preview=preview,
            approval_flow=approval_flow,
            explanation=explanation,
        )


__all__ = ["NexaUIViewAdapter"]
