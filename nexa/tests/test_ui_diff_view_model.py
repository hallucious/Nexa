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
    NodeResultCard,
    NodeResultsModel,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.diff_viewer import read_diff_view_model
from src.ui.graph_workspace import GraphPreviewOverlay


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(
            nodes=[{"id": "node_a", "label": "Node A"}, {"id": "node_b", "label": "Node B"}],
            edges=[{"from": "node_a", "to": "node_b"}],
            entry="node_a",
            outputs=[{"name": "out", "source": "node_b"}],
        ),
        resources=ResourcesModel(prompts={}, providers={"openai:gpt": {"type": "gpt"}}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _commit_snapshot() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(
            nodes=[{"id": "node_a", "label": "Node A updated"}, {"id": "node_c", "label": "Node C"}],
            edges=[{"from": "node_a", "to": "node_c"}],
            entry="node_a",
            outputs=[{"name": "out", "source": "node_c"}],
        ),
        resources=ResourcesModel(prompts={}, providers={"openai:gpt": {"type": "gpt"}, "anthropic:claude": {"type": "claude"}}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed_with_warnings", summary={"warning_count": 1}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(parent_commit_id=None, source_working_save_id="ws-001", metadata={}),
    )


def _run(run_id: str, *, status: str, artifact_ids: list[str]) -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id=run_id, record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="node_a", status="success" if status == "completed" else (status if status in {"failed", "partial", "cancelled", "skipped"} else "success"), output_summary=status)]),
        outputs=ExecutionOutputModel(output_summary=f"run {run_id}"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id=artifact_id, artifact_type="final_output") for artifact_id in artifact_ids], artifact_count=len(artifact_ids)),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_diff_view_model_supports_draft_vs_commit_structural_comparison() -> None:
    vm = read_diff_view_model(diff_mode="draft_vs_commit", source=_working_save(), target=_commit_snapshot())

    assert vm.viewer_status == "ready"
    assert vm.source_ref.endpoint_type == "working_save"
    assert vm.target_ref.endpoint_type == "commit_snapshot"
    assert vm.summary.total_change_count >= 4
    assert any(group.group_label == "Node" for group in vm.grouped_changes)
    assert vm.selected_change is not None



def test_read_diff_view_model_supports_run_vs_run_execution_comparison() -> None:
    vm = read_diff_view_model(diff_mode="run_vs_run", source=_run("run-001", status="completed", artifact_ids=["artifact::1"]), target=_run("run-002", status="failed", artifact_ids=["artifact::2"]))

    assert vm.viewer_status == "ready"
    assert vm.summary.execution_change_count >= 1
    assert vm.summary.artifact_change_count >= 1
    assert "run-001" in vm.related_links.related_run_ids
    assert "artifact::1" in vm.related_links.related_artifact_ids or "artifact::2" in vm.related_links.related_artifact_ids



def test_read_diff_view_model_supports_preview_vs_current_without_implying_commit() -> None:
    preview = GraphPreviewOverlay(
        overlay_id="preview-001",
        summary="Add reviewer",
        added_node_ids=["reviewer"],
        updated_node_ids=["node_b"],
        removed_edge_ids=["edge_0:node_a->node_b"],
        destructive_change_present=True,
        requires_confirmation=True,
    )

    vm = read_diff_view_model(diff_mode="preview_vs_current", source=preview, target=_working_save())

    assert vm.viewer_status == "ready"
    assert vm.source_ref.endpoint_type == "preview"
    assert vm.summary.destructive_change_count >= 1
    assert any(group.group_label == "Edge" for group in vm.grouped_changes)


def test_read_diff_view_model_localizes_summary_and_groups_for_korean_app_language() -> None:
    working = _working_save()
    working.ui.metadata["app_language"] = "ko-KR"

    vm = read_diff_view_model(diff_mode="draft_vs_commit", source=working, target=_commit_snapshot())

    assert "변경" in (vm.summary.top_summary_label or "")
    assert any(group.group_label == "노드" for group in vm.grouped_changes)
