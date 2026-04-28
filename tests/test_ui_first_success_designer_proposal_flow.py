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
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(
            format_version="1.0.0",
            storage_role="working_save",
            working_save_id="ws-001",
            name="Designer Review Draft",
        ),
        circuit=CircuitModel(
            nodes=[{"id": "n1", "kind": "provider", "label": "Summarize"}],
            edges=[],
            entry="n1",
            outputs=[{"name": "result", "source": "node.n1.output.result"}],
        ),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )


def _clean_validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[],
        blocking_count=0,
        warning_count=0,
        result="passed",
    )


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("n1",)),
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


def _preview(summary: str = "Add a summarization workflow.") -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(
            title="Preview",
            one_sentence_summary=summary,
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
            modified_nodes=("n1",),
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


def test_first_success_flow_routes_preview_ready_designer_proposal_to_approval() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_clean_validation(),
        precheck=_precheck(),
        preview=_preview("Review this workflow before it can run."),
        approval_flow=_approval(),
    )

    assert vm.first_success_flow.visible is True
    assert vm.first_success_flow.flow_state == "blocked"
    assert vm.first_success_flow.current_step_id == "review_workflow"
    assert vm.first_success_flow.next_action_id == "approve_for_commit"
    assert vm.first_success_flow.preferred_panel_id == "designer"
    assert vm.first_success_flow.designer_proposal.visible is True
    assert vm.first_success_flow.designer_proposal.proposal_state == "awaiting_approval"
    assert vm.first_success_flow.designer_proposal.summary == "Review this workflow before it can run."

    review_step = next(step for step in vm.first_success_flow.steps if step.step_id == "review_workflow")
    assert review_step.state == "blocked"
    assert review_step.recommended_action_id == "approve_for_commit"
    assert review_step.preferred_panel_id == "designer"


def test_first_success_flow_marks_approved_designer_proposal_review_complete() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_clean_validation(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(current_stage="ready_to_commit", final_outcome="approved_for_commit"),
    )

    assert vm.first_success_flow.designer_proposal.visible is True
    assert vm.first_success_flow.designer_proposal.proposal_state == "approved"
    assert vm.first_success_flow.designer_proposal.review_complete is True
    assert vm.first_success_flow.designer_proposal.commit_eligible is True

    review_step = next(step for step in vm.first_success_flow.steps if step.step_id == "review_workflow")
    assert review_step.state == "complete"
