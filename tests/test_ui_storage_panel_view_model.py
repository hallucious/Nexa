from __future__ import annotations

from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
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
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import DesignerDraftModel, RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.storage_panel import read_storage_view_model


def _working_save(*, source_commit_id: str | None = None) -> WorkingSaveModel:
    validation_summary = {"blocking_count": 0}
    if source_commit_id is not None:
        validation_summary["source_commit_id"] = source_commit_id
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Draft",
            updated_at="2026-04-06T00:00:00Z",
        ),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(
            status="validated",
            validation_summary=validation_summary,
            last_run={
                "run_id": "run-001",
                "status": "completed",
                "commit_id": "commit-001",
                "artifact_ids": ["artifact::output::out"],
            },
            errors=[],
        ),
        ui=UIModel(layout={}, metadata={}),
        designer=DesignerDraftModel(data={"pending": True}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version="1.0.0",
            storage_role="commit_snapshot",
            commit_id="commit-001",
            source_working_save_id="ws-001",
            name="Approved Draft",
            updated_at="2026-04-06T01:00:00Z",
        ),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={"warning_count": 0}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={"approved_at": "2026-04-06T01:00:00Z"}),
        lineage=CommitLineageModel(parent_commit_id="commit-000", source_working_save_id="ws-001", metadata={}),
    )


def _execution() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-06T02:00:00Z",
            started_at="2026-04-06T02:00:00Z",
            finished_at="2026-04-06T02:00:05Z",
            status="completed",
            title="Run 1",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(trace_ref="trace://run-001", event_stream_ref="events://run-001"),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="out", value_summary="done")], output_summary="1 output"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="artifact::output::out", artifact_type="final_output")], artifact_count=1),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_storage_view_model_projects_complete_lifecycle_for_working_save() -> None:
    vm = read_storage_view_model(
        _working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.active_storage_role == "working_save"
    assert vm.panel_mode == "draft_focus"
    assert vm.lifecycle_summary.current_stage == "review_ready"
    assert vm.lifecycle_summary.latest_commit_id == "commit-001"
    assert vm.lifecycle_summary.latest_run_id == "run-001"
    assert vm.working_save_card is not None
    assert vm.working_save_card.can_submit_for_review is True
    assert vm.commit_snapshot_card is not None
    assert vm.execution_record_card is not None
    assert vm.relationship_graph.draft_vs_commit_status == "in_sync"
    assert any(action.action_type == "save_working_save" and action.enabled for action in vm.available_actions)
    assert any(action.action_type == "run_from_commit" and action.enabled for action in vm.available_actions)



def test_read_storage_view_model_projects_execution_focus_without_blurring_truth_domains() -> None:
    vm = read_storage_view_model(
        _execution(),
        latest_working_save=_working_save(source_commit_id="commit-001"),
        latest_commit_snapshot=_commit(),
    )

    assert vm.active_storage_role == "execution_record"
    assert vm.panel_mode == "execution_focus"
    assert vm.lifecycle_summary.current_stage == "executed"
    assert vm.execution_record_card is not None
    assert vm.execution_record_card.trace_available is True
    assert vm.execution_record_card.can_open_artifacts is True
    assert vm.commit_snapshot_card is not None
    assert vm.working_save_card is not None



def test_read_storage_view_model_surfaces_stale_commit_reference_diagnostics() -> None:
    vm = read_storage_view_model(
        _working_save(source_commit_id="commit-old"),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_execution(),
    )

    assert vm.diagnostics.stale_reference_count >= 1
    assert vm.diagnostics.lifecycle_warning_count >= 1
    assert vm.diagnostics.last_error_label is not None
