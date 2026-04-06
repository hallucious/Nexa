from __future__ import annotations

from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultsModel,
    OutputResultCard,
)
from src.ui.artifact_viewer import read_artifact_viewer_view_model


def _record(*, trigger_type: str = "manual_run") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-07T00:00:00Z", started_at="2026-04-07T00:00:00Z", finished_at="2026-04-07T00:00:02Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type=trigger_type),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="final", source_node="draft", value_summary="done", value_type="text", value_ref="artifact::final")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[
            ArtifactRecordCard(artifact_id="artifact::final", artifact_type="final_output", producer_node="draft", hash="abc", summary="done"),
            ArtifactRecordCard(artifact_id="artifact::debug", artifact_type="debug_log", producer_node="draft", summary="trace chunk"),
        ], artifact_count=2),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_artifact_viewer_view_model_projects_execution_record_artifacts() -> None:
    vm = read_artifact_viewer_view_model(_record())

    assert vm.source_mode == "execution_record_artifacts"
    assert vm.storage_role == "execution_record"
    assert vm.viewer_status == "ready"
    assert vm.artifact_summary.total_artifact_count == 2
    assert vm.artifact_summary.final_artifact_count == 1
    assert vm.selected_artifact is not None
    assert vm.selected_artifact.artifact_id == "artifact::final"



def test_read_artifact_viewer_view_model_marks_replay_artifacts_explicitly() -> None:
    vm = read_artifact_viewer_view_model(_record(trigger_type="replay_run"))

    assert vm.source_mode == "replay_artifacts"
    assert vm.related_links.related_run_ids == ["run-001"]



def test_read_artifact_viewer_view_model_reports_idle_when_no_execution_record_is_loaded() -> None:
    vm = read_artifact_viewer_view_model(None)

    assert vm.viewer_status == "idle"
    assert vm.diagnostics.last_error_label is not None
