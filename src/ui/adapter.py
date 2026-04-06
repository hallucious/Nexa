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

    def read_diff_view_model(
        self,
        *,
        diff_mode: str,
        source,
        target,
        explanation: str | None = None,
    ) -> DiffViewerViewModel:
        return read_diff_view_model(diff_mode=diff_mode, source=source, target=target, explanation=explanation)


__all__ = ["NexaUIViewAdapter"]
