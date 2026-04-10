from __future__ import annotations

from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.ui.product_flow_gateway import read_product_flow_gateway_view_model
from src.ui.product_flow_handoff import read_product_flow_handoff_view_model
from src.ui.product_flow_journey import read_product_flow_journey_view_model


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-10T00:00:00Z", started_at="2026-04-10T00:00:00Z", finished_at=(None if status == "running" else "2026-04-10T00:00:05Z"), status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=(1 if status == "running" else 3)),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary=("running" if status == "running" else "done"), final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="done", value_ref="artifact://art-1")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="final", artifact_schema_version="1.0.0")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_product_flow_journey_prefers_run_for_commit_snapshot_source() -> None:
    vm = read_product_flow_journey_view_model(_commit())
    assert vm.source_role == "commit_snapshot"
    assert vm.current_step_id == "run_current"
    run_step = next(step for step in vm.steps if step.step_id == "run_current")
    assert run_step.actionable is True


def test_product_flow_handoff_prefers_run_for_commit_snapshot_source() -> None:
    vm = read_product_flow_handoff_view_model(_commit())
    assert vm.source_role == "commit_snapshot"
    assert vm.primary_entry_id == "run_current"
    assert vm.primary_action_id == "run_from_commit"


def test_product_flow_gateway_prefers_run_gateway_for_commit_snapshot_source() -> None:
    vm = read_product_flow_gateway_view_model(_commit())
    assert vm.source_role == "commit_snapshot"
    assert vm.current_gateway_id == "run"
    assert vm.recommended_gateway_id == "run"
    run_stage = next(stage for stage in vm.stages if stage.gateway_id == "run")
    assert run_stage.required_action_id == "run_from_commit"


def test_product_flow_gateway_accepts_execution_record_source_without_proposal_cycle() -> None:
    vm = read_product_flow_gateway_view_model(_run("completed"))
    assert vm.source_role == "execution_record"
    assert vm.current_gateway_id in {"followthrough", "run"}


def test_product_flow_handoff_prefers_followthrough_for_execution_record_source() -> None:
    vm = read_product_flow_handoff_view_model(_run("completed"))
    assert vm.source_role == "execution_record"
    assert vm.primary_entry_id in {"inspect_trace", "inspect_artifacts", "compare_results", "run_current"}
    assert vm.primary_entry_id != "review_proposal"
