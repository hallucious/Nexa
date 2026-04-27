from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel, NodeTimingCard, OutputResultCard
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.product_flow_runbook import read_product_flow_runbook_view_model


def _empty_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Runbook Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _working_save(*, metadata: dict | None = None, last_run: dict | None = None) -> WorkingSaveModel:
    merged_metadata = {"app_language": "ko-KR"}
    merged_metadata.update(dict(metadata or {}))
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Runbook Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1", "label": "Draft Generator"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run=({"run_id": "run-001"} | dict(last_run or {})), errors=[]),
        ui=UIModel(layout={}, metadata=merged_metadata),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN", category="structural", severity="medium", blocking=False, location="node:n1", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-08T00:00:00Z", started_at="2026-04-08T00:00:00Z", finished_at=(None if status == "running" else "2026-04-08T00:00:05Z"), status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type=("manual_run" if status != "running" else "manual_run")),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(started_nodes=[NodeTimingCard(node_id="n1", started_at="2026-04-08T00:00:01Z")], completed_nodes=[] if status == "running" else [NodeTimingCard(node_id="n1", finished_at="2026-04-08T00:00:04Z", outcome="success")], event_count=(1 if status == "running" else 3)),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n1", status=("partial" if status == "running" else "success"))]),
        outputs=ExecutionOutputModel(output_summary=("in progress" if status == "running" else "done"), final_outputs=[OutputResultCard(output_ref="result", source_node="n1", value_summary="done", value_ref="art-1")]),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="final answer", artifact_schema_version="1.0.0")],
            artifact_count=1,
            artifact_summary="1 artifact",
        ),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(metrics={"cost_estimate": 1.25, "actual_cost": (0.75 if status != "running" else None)}),
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


def _approval(stage: str = "awaiting_decision", outcome: str = "approved_for_commit") -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage=stage,
        final_outcome=outcome,
    )


def test_product_flow_runbook_highlights_commit_entry_after_review_is_approved() -> None:
    vm = read_product_flow_runbook_view_model(
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
    assert vm.runbook_status == "ready"
    assert vm.current_entry_id == "commit_snapshot"
    commit_entry = next(entry for entry in vm.entries if entry.entry_id == "commit_snapshot")
    assert commit_entry.entry_status == "ready"
    assert commit_entry.enabled is True
    assert commit_entry.action_id == "commit_snapshot"


def test_product_flow_runbook_keeps_beginner_result_reading_on_run_entry_after_completed_run() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run("completed"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.current_entry_id == "run_current"
    assert vm.recommended_entry_id == "run_current"
    run_entry = next(entry for entry in vm.entries if entry.entry_id == "run_current")
    trace_entry = next(entry for entry in vm.entries if entry.entry_id == "inspect_trace")
    artifact_entry = next(entry for entry in vm.entries if entry.entry_id == "inspect_artifacts")
    assert run_entry.entry_status == "complete"
    assert run_entry.enabled is True
    assert trace_entry.entry_status == "complete"
    assert trace_entry.enabled is False
    assert artifact_entry.entry_status == "complete"
    assert artifact_entry.enabled is False
    assert vm.completed_entry_count >= 4


def test_product_flow_runbook_marks_live_execution_as_live_and_offers_cancel_or_trace_monitoring() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run("running"),
    )

    assert vm.runbook_status == "live"
    run_entry = next(entry for entry in vm.entries if entry.entry_id == "run_current")
    assert run_entry.entry_status == "active"
    assert run_entry.enabled is True
    assert run_entry.action_id == "cancel_run"


def test_product_flow_runbook_prioritizes_provider_setup_before_template_and_review(monkeypatch, tmp_path) -> None:
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)

    vm = read_product_flow_runbook_view_model(_empty_working_save())

    assert vm.current_entry_id == "connect_provider"
    assert vm.recommended_entry_id == "connect_provider"
    entries = {entry.entry_id: entry for entry in vm.entries}
    assert entries["connect_provider"].action_id == "open_provider_setup"
    assert entries["choose_template"].action_id == "create_circuit_from_template"


def test_product_flow_runbook_exposes_return_use_entries_after_first_success() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(metadata={"beginner_first_success_achieved": True}),
        validation_report=_validation_report(),
        execution_record=_run("completed"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    entries = {entry.entry_id: entry for entry in vm.entries}
    assert entries["reopen_recent_results"].enabled is True
    assert entries["open_workflow_library"].enabled is True
    assert entries["open_feedback_channel"].enabled is True


def test_product_flow_runbook_keeps_recent_results_available_for_execution_record_return_use() -> None:
    vm = read_product_flow_runbook_view_model(_run("completed"), execution_record=_run("completed"))

    entry = next(entry for entry in vm.entries if entry.entry_id == "reopen_recent_results")
    assert entry.action_id == "open_result_history"
    assert entry.enabled is True


def test_product_flow_runbook_surfaces_cost_review_entry_when_estimate_is_available() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(last_run={"estimated_cost": 1.25}),
        validation_report=_validation_report(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    entries = {entry.entry_id: entry for entry in vm.entries}
    assert entries["review_run_cost"].enabled is True
    assert entries["review_run_cost"].action_id == "review_run_cost"


def test_product_flow_runbook_surfaces_watch_progress_for_running_execution() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run("running"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    assert vm.current_entry_id == "watch_run_progress"
    assert vm.recommended_entry_id == "watch_run_progress"


def test_product_flow_runbook_unlocks_deep_followthrough_after_explicit_first_success() -> None:
    vm = read_product_flow_runbook_view_model(
        _working_save(metadata={"beginner_first_success_achieved": True}),
        validation_report=_validation_report(),
        execution_record=_run("completed"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )

    entries = {entry.entry_id: entry for entry in vm.entries}
    assert entries["inspect_trace"].enabled is True
    assert entries["inspect_trace"].action_id == "open_trace"
    assert entries["inspect_trace"].preferred_panel_id == "trace_timeline"
    assert entries["inspect_artifacts"].enabled is True
    assert entries["inspect_artifacts"].action_id == "open_artifacts"
    assert entries["inspect_artifacts"].preferred_panel_id == "artifact"
