from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, PrecheckFinding, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel, NodeTimingCard, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.product_flow_e2e_path import read_product_flow_e2e_path_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="E2E Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1", "label": "Draft Generator"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={"run_id": "run-001"}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )


def _validation_report(blocking: int = 0, warning: int = 1) -> ValidationReport:
    findings = []
    if warning:
        findings.append(ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn"))
    if blocking:
        findings.append(ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked"))
    return ValidationReport(
        role="working_save",
        findings=findings,
        blocking_count=blocking,
        warning_count=warning,
        result=("failed" if blocking else "passed_with_findings"),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", finished_at=(None if status == "running" else "2026-04-08T00:00:05Z"), status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(started_nodes=[NodeTimingCard(node_id="n1", started_at="2026-04-08T00:00:01Z")], completed_nodes=[] if status == "running" else [NodeTimingCard(node_id="n1", finished_at="2026-04-08T00:00:04Z", outcome="success")], event_count=(1 if status == "running" else 3)),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n1", status=("partial" if status == "running" else "success"))]),
        outputs=ExecutionOutputModel(output_summary=("in progress" if status == "running" else "done"), final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="done", value_ref="art-1")]),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="final answer", artifact_schema_version="1.0.0")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
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


def _precheck(status: str = "pass") -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("n1",)),
        overall_status=status,
        structural_validity=ValidityReport(status=("blocked" if status == "blocked" else "valid")),
        dependency_validity=ValidityReport(status=("blocked" if status == "blocked" else "valid")),
        input_output_validity=ValidityReport(status=("blocked" if status == "blocked" else "valid")),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status=("blocked" if status == "blocked" else "valid")),
        cost_assessment=CostAssessmentReport(status="acceptable"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="clear"),
        blocking_findings=(PrecheckFinding(issue_code="PRECHECK_BLOCKED", message="blocked"),) if status == "blocked" else (),
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


def _approval(stage: str = "awaiting_decision", outcome: str = "approved_for_commit") -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage=stage,
        final_outcome=outcome,
        precheck_status=("blocked" if outcome == "pending" and stage == "awaiting_precheck" else "pass"),
    )


def test_product_flow_e2e_path_prioritizes_commit_then_run_for_reviewed_working_save() -> None:
    vm = read_product_flow_e2e_path_view_model(
        _working_save(),
        validation_report=_validation_report(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.source_role == "working_save"
    assert vm.path_status == "actionable"
    assert vm.current_checkpoint_id == "commit"
    assert vm.recommended_checkpoint_id == "commit"
    assert vm.next_action_id == "commit_snapshot"
    assert vm.next_workspace_id == "node_configuration"


def test_product_flow_e2e_path_prefers_followthrough_targets_when_completed_run_history_exists() -> None:
    vm = read_product_flow_e2e_path_view_model(_working_save(), execution_record=_run("completed"))

    assert vm.source_role == "working_save"
    assert vm.path_status == "actionable"
    assert vm.current_checkpoint_id == "run" or vm.current_checkpoint_id == "commit"
    assert any(checkpoint.checkpoint_id in {"trace", "artifact", "diff"} and checkpoint.actionable for checkpoint in vm.checkpoints)
    assert vm.actionable_checkpoint_count >= 1


def test_product_flow_e2e_path_marks_commit_path_blocked_when_precheck_blocks_commit_boundary() -> None:
    vm = read_product_flow_e2e_path_view_model(
        _working_save(),
        validation_report=_validation_report(blocking=1, warning=0),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(status="blocked"),
        preview=_preview(),
        approval_flow=_approval(stage="awaiting_precheck", outcome="pending"),
    )

    commit = next(checkpoint for checkpoint in vm.checkpoints if checkpoint.checkpoint_id == "commit")
    assert commit.checkpoint_status == "blocked"
    assert vm.path_status == "actionable"
    assert vm.next_action_id == "request_revision"
    assert vm.blocked_checkpoint_count >= 1
