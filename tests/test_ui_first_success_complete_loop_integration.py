from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.designer.models.circuit_draft_preview import (
    CircuitDraftPreview,
    ConfirmationPreview,
    GraphViewModel,
    SummaryCard,
    StructuralPreview,
)
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
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
    OutputResultCard,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.beginner_milestones import apply_beginner_first_success_completion
from src.ui.builder_shell import read_builder_shell_view_model


def _working_save(*, empty: bool = False, metadata: dict | None = None) -> WorkingSaveModel:
    nodes = [] if empty else [{"id": "draft", "kind": "provider", "label": "Draft"}]
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="First Success Loop",
        ),
        circuit=CircuitModel(
            nodes=nodes,
            edges=[],
            entry=None if empty else "draft",
            outputs=[] if empty else [{"name": "result", "source": "node.draft.output.result"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata or {"app_language": "en-US"}),
    )


def _clean_validation() -> ValidationReport:
    return ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed")


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("draft",)),
        overall_status="pass",
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="valid"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="valid"),
        cost_assessment=CostAssessmentReport(status="acceptable"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
    )


def _preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Preview",
            one_sentence_summary="Review this workflow before it can run.",
            proposal_type="modify",
            change_scope="bounded",
            touched_node_count=1,
            touched_edge_count=0,
            touched_output_count=0,
        ),
        structural_preview=StructuralPreview(
            before_exists=True,
            before_node_count=1,
            after_node_count=1,
            before_edge_count=0,
            after_edge_count=0,
            modified_nodes=("draft",),
        ),
        confirmation_preview=ConfirmationPreview(required_confirmations=(), auto_commit_allowed=False),
        graph_view_model=GraphViewModel(node_count=1, edge_count=0),
    )


def _approval(*, current_stage: str = "awaiting_decision", final_outcome: str = "pending") -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage=current_stage,
        final_outcome=final_outcome,
    )


def _completed_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:05Z",
            status="completed",
            title="Demo Run",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1, node_order=["draft"]),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="draft", status="success", output_summary="draft ready")]),
        outputs=ExecutionOutputModel(
            final_outputs=[
                OutputResultCard(
                    output_ref="final",
                    source_node="draft",
                    value_summary="Readable result",
                    value_type="text",
                    value_payload="Readable result body",
                )
            ],
            output_summary="Readable result",
        ),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[
                ArtifactRecordCard(
                    artifact_id="artifact-001",
                    artifact_type="final_output",
                    producer_node="draft",
                    ref="artifact://final",
                )
            ]
        ),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_complete_first_success_loop_progresses_without_crossing_engine_truth_boundaries() -> None:
    empty_vm = read_builder_shell_view_model(_working_save(empty=True))
    assert empty_vm.first_success_flow.current_step_id == "describe_goal"
    assert empty_vm.first_success_flow.preferred_panel_id == "designer"

    review_vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_clean_validation(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )
    assert review_vm.first_success_flow.current_step_id == "review_workflow"
    assert review_vm.first_success_flow.next_action_id == "approve_for_commit"
    assert review_vm.first_success_flow.designer_proposal.proposal_state == "awaiting_approval"

    approved_vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_clean_validation(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(current_stage="ready_to_commit", final_outcome="approved_for_commit"),
    )
    assert approved_vm.first_success_flow.designer_proposal.review_complete is True

    result_vm = read_builder_shell_view_model(
        _working_save(),
        execution_record=_completed_record(),
    )
    assert result_vm.first_success_flow.current_step_id == "read_result"
    assert result_vm.first_success_flow.result_reading.completion_action_id == "mark_first_result_read"
    assert result_vm.first_success_flow.advanced_surfaces_unlocked is False

    completion_patch = result_vm.first_success_flow.result_reading.completion_metadata_patch
    completed_source = apply_beginner_first_success_completion(
        _working_save(),
        run_id=completion_patch.get("beginner_first_success_run_id"),
        output_ref=completion_patch.get("beginner_first_success_output_ref"),
        artifact_ref=completion_patch.get("beginner_first_success_artifact_ref"),
        completed_at=completion_patch.get("beginner_first_success_completed_at"),
    )
    complete_vm = read_builder_shell_view_model(
        completed_source,
        execution_record=_completed_record(),
    )
    assert complete_vm.first_success_flow.flow_state == "complete"
    assert complete_vm.first_success_flow.advanced_surfaces_unlocked is True
    assert complete_vm.first_success_flow.result_reading.read_complete is True
    assert complete_vm.first_success_flow.next_action_id == "open_result_history"
