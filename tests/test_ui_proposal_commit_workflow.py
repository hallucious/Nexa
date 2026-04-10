from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.proposal_commit_workflow import read_proposal_commit_workflow_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n1"]}),
    )




def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )

def _run() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report(result: str = "passed") -> ValidationReport:
    if result == "failed":
        return ValidationReport(
            role="working_save",
            findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")],
            blocking_count=1,
            warning_count=0,
            result="failed",
        )
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def _session_card() -> DesignerSessionStateCard:
    return DesignerSessionStateCard(
        card_version="0.1",
        session_id="sess-001",
        storage_role="working_save",
        current_working_save=WorkingSaveReality(mode="existing_draft", savefile_ref="working_save:ws-001", circuit_summary="single node"),
        current_selection=CurrentSelectionState(selection_mode="node", selected_refs=("node:n1",)),
        target_scope=SessionTargetScope(mode="existing_circuit"),
        available_resources=AvailableResources(),
        objective=ObjectiveSpec(primary_goal="Improve it"),
        constraints=ConstraintSet(),
        conversation_context=ConversationContext(user_request_text="Improve node"),
    )


def _intent() -> DesignerIntent:
    return DesignerIntent(
        intent_id="intent-001",
        category="MODIFY_CIRCUIT",
        user_request_text="Improve node",
        target_scope=TargetScope(mode="existing_circuit", savefile_ref="working_save:ws-001"),
        objective=ObjectiveSpec(primary_goal="Improve it"),
        constraints=ConstraintSet(),
        proposed_actions=(),
        assumptions=(),
        ambiguity_flags=(),
        risk_flags=(),
        requires_user_confirmation=False,
        confidence=0.8,
        explanation="improve node",
    )


def _patch() -> CircuitPatchPlan:
    return CircuitPatchPlan(
        patch_id="patch-001",
        patch_mode="modify_existing",
        summary="modify node",
        intent_ref="intent-001",
        change_scope=ChangeScope(scope_level="bounded", touch_mode="structural_edit", touched_nodes=("n1",)),
        operations=(PatchOperation(op_id="op-1", op_type="update_node_metadata", target_ref="node:n1"),),
        target_savefile_ref="working_save:ws-001",
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


def _preview() -> CircuitDraftPreview:
    return CircuitDraftPreview(
        preview_id="preview-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_mode="patch_modify",
        summary_card=SummaryCard(title="modify", one_sentence_summary="modify node", proposal_type="modify", change_scope="bounded", touched_node_count=1, touched_edge_count=0, touched_output_count=0),
        structural_preview=StructuralPreview(before_exists=True, before_node_count=1, after_node_count=1, before_edge_count=0, after_edge_count=0, modified_nodes=("n1",)),
        confirmation_preview=ConfirmationPreview(required_confirmations=(), auto_commit_allowed=False),
        graph_view_model=GraphViewModel(node_count=1, edge_count=0),
    )


def _approval(final_outcome: str = "approved_for_commit") -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(approval_id="approval-001", intent_ref="intent-001", patch_ref="patch-001", precheck_ref="pre-001", preview_ref="preview-001", current_stage="awaiting_decision", final_outcome=final_outcome)


def test_proposal_commit_workflow_becomes_commit_ready_for_approved_designer_state() -> None:
    vm = read_proposal_commit_workflow_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation_report(),
        execution_record=_run(),
        preview_overlay=GraphPreviewOverlay(overlay_id="ov-1", summary="preview"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )
    assert vm.workflow_status == "commit_ready"
    assert vm.can_commit is True
    assert vm.summary.commit_eligible is True
    assert vm.summary.next_step_label == "Commit snapshot"


def test_proposal_commit_workflow_is_blocked_when_validation_is_blocked() -> None:
    vm = read_proposal_commit_workflow_view_model(_working_save(), selected_ref="node:n1", validation_report=_validation_report("failed"))
    assert vm.workflow_status == "blocked"
    assert vm.can_commit is False
    assert vm.summary.blocking_count == 1


def test_proposal_commit_workflow_localizes_next_step_for_korean_app_language() -> None:
    working = _working_save()
    working.ui.metadata["app_language"] = "ko-KR"

    vm = read_proposal_commit_workflow_view_model(working, selected_ref="node:n1", validation_report=_validation_report())

    assert vm.summary.next_step_label == "Designer 제안을 시작하거나 현재 드래프트 검토"


def test_proposal_commit_workflow_propagates_latest_run_into_commit_snapshot_storage_context() -> None:
    vm = read_proposal_commit_workflow_view_model(_commit(), execution_record=_run())
    assert vm.storage is not None
    assert vm.storage.execution_record_card is not None
    assert vm.storage.execution_record_card.run_id == "run-001"
    assert vm.summary.next_step_label == "Run from commit"


def test_proposal_commit_workflow_prefers_followthrough_action_for_execution_record_context() -> None:
    vm = read_proposal_commit_workflow_view_model(_run())
    assert vm.storage is not None
    assert vm.storage.execution_record_card is not None
    assert vm.action_state.compare_action is not None
    assert vm.action_state.compare_action.action_id in {"open_trace", "open_artifacts", "compare_runs", "open_latest_run", "open_diff"}
    assert vm.summary.next_step_label in {"Open trace", "Open artifacts", "Compare runs", "Open latest run", "Open Diff"}



def test_proposal_commit_workflow_exposes_beginner_confirmation_summary_before_first_success() -> None:
    vm = read_proposal_commit_workflow_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation_report(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.beginner_mode is True
    assert vm.hide_internal_governance_by_default is True
    assert vm.beginner_confirmation.visible is True
    assert vm.beginner_confirmation.title == "Here is what I will build"
    assert vm.beginner_confirmation.summary == "modify node"
    assert vm.beginner_confirmation.prompt == "Does this look right?"
    assert vm.beginner_confirmation.primary_action_label == "Approve"
    assert vm.beginner_confirmation.secondary_action_label == "Revise"


def test_proposal_commit_workflow_disables_beginner_confirmation_after_first_success() -> None:
    vm = read_proposal_commit_workflow_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation_report(),
        execution_record=_run(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.beginner_mode is False
    assert vm.hide_internal_governance_by_default is False
    assert vm.beginner_confirmation.visible is False
