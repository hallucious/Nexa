from __future__ import annotations

from src.storage.models.commit_snapshot_model import (
    CommitApprovalModel,
    CommitLineageModel,
    CommitSnapshotMeta,
    CommitSnapshotModel,
    CommitValidationModel,
)
from src.storage.models.execution_record_model import (
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
from src.storage.validators.shared_validator import validate_working_save
from src.ui.graph_workspace import GraphPreviewOverlay, read_graph_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="0.1.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="demo graph",
        ),
        circuit=CircuitModel(
            nodes=[
                {
                    "id": "draft_generator",
                    "type": "provider",
                    "label": "Draft Generator",
                    "resource_ref": {"provider": "openai:gpt"},
                    "inputs": {"question": "state.input.question"},
                    "outputs": {"draft": "state.working.draft"},
                    "metadata": {"position": {"x": 10, "y": 20}},
                },
                {
                    "id": "review_bundle",
                    "kind": "subcircuit",
                    "label": "Review Bundle",
                    "execution": {
                        "subcircuit": {
                            "child_circuit_ref": "internal:review_bundle",
                        }
                    },
                    "inputs": {"draft": "state.working.draft"},
                    "outputs": {"result": "state.working.reviewed"},
                },
            ],
            edges=[
                {"from": "draft_generator", "to": "review_bundle"},
            ],
            entry="draft_generator",
            outputs=[{"name": "result", "source": "state.working.reviewed"}],
            subcircuits={"review_bundle": {"nodes": [], "edges": [], "outputs": []}},
        ),
        resources=ResourcesModel(
            prompts={},
            providers={"openai:gpt": {"type": "gpt"}},
            plugins={},
        ),
        state=StateModel(input={"question": "What next?"}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(
            layout={"layout_mode": "manual", "minimap_enabled": True},
            metadata={"selected_node_ids": ["review_bundle"]},
        ),
    )


def _commit_snapshot() -> CommitSnapshotModel:
    base = _working_save()
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(
            format_version=base.meta.format_version,
            storage_role="commit_snapshot",
            commit_id="commit-001",
            name="approved demo graph",
        ),
        circuit=base.circuit,
        resources=base.resources,
        state=base.state,
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(parent_commit_id=None, source_working_save_id=base.meta.working_save_id, metadata={}),
    )


def _execution_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="0.1.0",
            created_at="2026-01-01T00:00:00Z",
            started_at="2026-01-01T00:00:00Z",
            finished_at="2026-01-01T00:00:02Z",
            status="completed",
            title="Run 1",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=2000, node_order=["draft_generator", "review_bundle"]),
        node_results=NodeResultsModel(
            results=[
                NodeResultCard(node_id="draft_generator", status="success", output_summary="draft ready"),
                NodeResultCard(node_id="review_bundle", status="failed", output_summary="review failed", error_count=1),
            ]
        ),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(errors=[], warnings=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_graph_view_model_projects_working_save_with_validation_findings() -> None:
    working = _working_save()
    # Remove entry to generate a blocking finding while remaining loadable in Working Save terms.
    invalid = WorkingSaveModel(
        meta=working.meta,
        circuit=CircuitModel(
            nodes=working.circuit.nodes,
            edges=working.circuit.edges,
            entry=None,
            outputs=working.circuit.outputs,
            subcircuits=working.circuit.subcircuits,
        ),
        resources=working.resources,
        state=working.state,
        runtime=working.runtime,
        ui=working.ui,
    )
    report = validate_working_save(invalid)

    vm = read_graph_view_model(invalid, validation_report=report)

    assert vm.storage_role == "working_save"
    assert vm.graph_status == "invalid"
    assert vm.graph_metrics.node_count == 2
    assert vm.graph_findings_summary.validation_blocking_count >= 1
    assert vm.selected_node_ids == ["review_bundle"]
    assert vm.layout_hints is not None
    assert vm.layout_hints.layout_mode == "manual"


def test_read_graph_view_model_projects_commit_snapshot_as_approved() -> None:
    snapshot = _commit_snapshot()

    vm = read_graph_view_model(snapshot)

    assert vm.storage_role == "commit_snapshot"
    assert vm.graph_status == "approved"
    assert vm.graph_id == "commit_snapshot:commit-001"
    assert vm.nodes[1].kind == "subcircuit"
    assert vm.nodes[1].child_refs == ["internal:review_bundle"]


def test_read_graph_view_model_projects_execution_overlay_and_node_statuses() -> None:
    snapshot = _commit_snapshot()
    record = _execution_record()

    vm = read_graph_view_model(snapshot, execution_record=record)

    assert vm.storage_role == "execution_record"
    assert vm.graph_status == "completed"
    assert vm.graph_id == "execution_record:run-001"
    node_statuses = {node.node_id: node.status for node in vm.nodes}
    assert node_statuses["draft_generator"] == "completed"
    assert node_statuses["review_bundle"] == "failed"
    assert vm.graph_metrics.completed_node_count == 1
    assert vm.graph_metrics.failed_node_count == 1


def test_read_graph_view_model_projects_preview_overlay_without_committing_truth() -> None:
    working = _working_save()
    overlay = GraphPreviewOverlay(
        overlay_id="preview-001",
        summary="Add reviewer and remove old edge",
        added_node_ids=["new_reviewer"],
        updated_node_ids=["review_bundle"],
        removed_edge_ids=["edge_0:draft_generator->review_bundle"],
        destructive_change_present=True,
        requires_confirmation=True,
    )

    vm = read_graph_view_model(working, preview_overlay=overlay)

    node = next(node for node in vm.nodes if node.node_id == "review_bundle")
    edge = vm.edges[0]
    assert node.preview_change_state == "updated"
    assert node.status == "preview_updated"
    assert vm.preview_overlay is overlay
    assert vm.graph_metrics.preview_updated_count == 1
    assert edge.preview_change_state == "removed"
    assert edge.status == "preview_removed"


def test_read_graph_view_model_localizes_badges_for_korean_working_save() -> None:
    working = _working_save()
    localized = WorkingSaveModel(
        meta=working.meta,
        circuit=working.circuit,
        resources=working.resources,
        state=working.state,
        runtime=working.runtime,
        ui=UIModel(layout=working.ui.layout, metadata={**working.ui.metadata, "app_language": "ko-KR"}),
    )

    vm = read_graph_view_model(localized)

    review_node = next(node for node in vm.nodes if node.node_id == "review_bundle")
    assert review_node.input_summary == "1개 바인딩"
    assert any(badge.label == "서브회로" for badge in review_node.badges)


def test_read_graph_view_model_defaults_selection_to_failed_node_from_execution_record() -> None:
    snapshot = _commit_snapshot()
    record = _execution_record()

    vm = read_graph_view_model(snapshot, execution_record=record)

    assert vm.selected_node_ids == ["review_bundle"]
    assert vm.layout_hints is not None
    assert vm.layout_hints.suggested_focus_node_id == "review_bundle"
