from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.graph_workspace import GraphPreviewOverlay


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={"viewport_center": {"x": 10, "y": 20}}, metadata={
            "selected_node_ids": ["n1"],
            "active_theme_id": "nexa-dark",
            "active_layout_id": "builder-default",
            "density_mode": "comfortable",
            "user_mode": "advanced",
            "active_panel": "validation",
            "app_language": "ko-KR",
        }),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001"),
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
        timeline=ExecutionTimelineModel(event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="art-1", artifact_type="final_output", producer_node="n1", hash="abc123", ref="artifact://art-1", summary="summary")], artifact_count=1, artifact_summary="1 artifact"),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report() -> ValidationReport:
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


def _approval() -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(approval_id="approval-001", intent_ref="intent-001", patch_ref="patch-001", precheck_ref="pre-001", preview_ref="preview-001", current_stage="awaiting_decision", final_outcome="approved_for_commit")


def test_builder_shell_composes_connected_builder_surfaces() -> None:
    vm = read_builder_shell_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-ov-1", summary="preview"),
        selected_ref="node:n1",
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )
    assert vm.shell_status == "ready"
    assert vm.shell_mode == "designer_review"
    assert vm.coordination.active_panel == "validation"
    assert vm.action_schema.source_role == "working_save"
    assert vm.top_bar is not None
    assert vm.command_palette is not None
    assert vm.active_workspace_id == "node_configuration"
    assert vm.visual_editor is not None
    assert vm.runtime_monitoring is not None
    assert vm.node_configuration is not None
    assert vm.graph is not None
    assert vm.inspector is not None
    assert vm.validation is not None
    assert vm.storage is not None
    assert vm.execution is not None
    assert vm.trace_timeline is not None
    assert vm.artifact is not None
    assert vm.designer is not None
    assert vm.layout.active_theme_id == "nexa-dark"
    assert vm.top_bar.storage_badge.label == "워킹 세이브"
    assert vm.command_palette.placeholder == "노드, 문제, 실행, 액션 검색"
    assert vm.shell_mode_label == "Designer 검토"
    assert vm.active_workspace_label == "노드 구성"
    assert vm.shell_status_label == "셸 준비 완료"



def test_builder_shell_uses_graph_selection_as_inspector_selection_when_selected_ref_is_omitted() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-002", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n1"], "app_language": "ko-KR"}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.inspector is not None
    assert vm.inspector.object_id == "n1"
    assert vm.coordination.active_panel == "inspector"


def test_builder_shell_marks_blocked_shell_status_when_validation_is_blocked() -> None:
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_builder_shell_view_model(_working_save(), validation_report=report)

    assert vm.validation is not None
    assert vm.validation.overall_status == "blocked"
    assert vm.shell_status == "blocked"
    assert vm.shell_status_label == "셸 차단 상태"


def test_builder_shell_uses_runtime_monitoring_workspace_for_execution_record_sources() -> None:
    vm = read_builder_shell_view_model(_run())

    assert vm.storage_role == "execution_record"
    assert vm.shell_mode == "run_review"
    assert vm.active_workspace_id == "runtime_monitoring"
    assert vm.runtime_monitoring is not None
    assert vm.visual_editor is None


def test_builder_shell_prefers_runtime_monitoring_workspace_when_artifact_panel_is_active() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-003", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_artifact_ids": ["art-1"], "app_language": "ko-KR"}),
    )

    vm = read_builder_shell_view_model(source, execution_record=_run())

    assert vm.coordination.active_panel == "artifact"
    assert vm.active_workspace_id == "runtime_monitoring"


def test_builder_shell_prefers_runtime_monitoring_workspace_when_trace_panel_is_active() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-004", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_trace_event_ids": ["event-1"], "app_language": "ko-KR"}),
    )

    vm = read_builder_shell_view_model(source, execution_record=_run())

    assert vm.coordination.active_panel == "trace_timeline"
    assert vm.active_workspace_id == "runtime_monitoring"


def test_builder_shell_uses_execution_record_focus_node_for_commit_snapshot_run_review() -> None:
    snapshot = _commit()
    record = _run()

    vm = read_builder_shell_view_model(snapshot, execution_record=record)

    assert vm.graph is not None
    assert vm.graph.selected_node_ids == ["n1"]
    assert vm.inspector is not None
    assert vm.inspector.object_id == "n1"
    assert vm.inspector.status_summary.execution_state in {"failed", "completed", "running", "partial"}


def test_builder_shell_recovers_inspector_selection_from_blocking_validation_location_when_ui_selection_is_missing() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-003", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}, {"id": "n2"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n2", message="blocked")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_builder_shell_view_model(source, validation_report=report)

    assert vm.graph is not None and vm.graph.selected_node_ids == ["n2"]
    assert vm.inspector is not None and vm.inspector.object_id == "n2"
    assert vm.coordination.active_panel == "validation"


def test_builder_shell_marks_execution_record_context_as_terminal_when_not_live() -> None:
    vm = read_builder_shell_view_model(_run())

    assert vm.storage_role == "execution_record"
    assert vm.shell_status == "terminal"
    assert vm.shell_status_label == "Shell in history mode"



def test_builder_shell_projects_beginner_empty_workspace_state() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty Draft"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.coordination.active_panel == "designer"
    assert vm.diagnostics.beginner_mode is True
    assert vm.diagnostics.empty_workspace_mode is True
    assert vm.diagnostics.advanced_surfaces_unlocked is False
    assert vm.coordination.visible_panels == ["designer"]
    assert vm.designer is not None
    assert vm.designer.request_state.input_placeholder == "What would you like to build? Describe your goal."


def test_builder_shell_uses_beginner_workspace_labels_before_first_success() -> None:
    beginner = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-beginner", name="Starter"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )
    vm = read_builder_shell_view_model(beginner)

    assert vm.top_bar.storage_badge.label == "저장되지 않음"
    assert vm.command_palette.placeholder == "단계, 문제, 실행, 액션 검색"
    assert vm.active_workspace_id == "node_configuration"
    assert vm.active_workspace_label == "단계 설정"


def test_builder_shell_projects_beginner_onboarding_hint_for_empty_workspace() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty-hint", name="Empty Draft"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.beginner_onboarding.visible is True
    assert vm.beginner_onboarding.title == "Start with your goal"
    assert vm.beginner_onboarding.primary_action_label == "Open Designer"
    assert vm.beginner_onboarding.primary_action_target == "designer"


def test_builder_shell_projects_beginner_onboarding_hint_for_blocked_validation() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-blocked", name="Blocked Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="Choose an AI model for step 1")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_builder_shell_view_model(source, validation_report=report)

    assert vm.beginner_onboarding.visible is True
    assert vm.beginner_onboarding.title == "Fix this before running"
    assert vm.beginner_onboarding.summary == "Choose an AI model for step 1"
    assert vm.beginner_onboarding.primary_action_label == "Fix this step"
    assert vm.beginner_onboarding.primary_action_target == "validation"


def test_builder_shell_projects_template_gallery_through_designer_for_empty_workspace() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.designer is not None
    assert vm.designer.template_gallery.visible is True
    assert len(vm.designer.template_gallery.templates) == 10
    assert vm.designer.template_gallery.category_count >= 5
    assert vm.designer.provider_setup_guidance.visible is True
    assert vm.designer.provider_setup_guidance.primary_action_target == "provider_setup"



def test_builder_shell_projects_library_workspace_surface_from_active_panel() -> None:
    source = _working_save()
    source.ui.metadata["active_panel"] = "circuit_library"
    vm = read_builder_shell_view_model(source, execution_record=_run())

    assert vm.active_workspace_id == "library"
    assert vm.circuit_library is not None
    assert vm.circuit_library.visible is True
    assert vm.coordination.active_panel == "circuit_library"



def test_builder_shell_projects_result_history_surface_for_recent_runs() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={"run_id": "run-local", "status": "completed", "summary": "Recent result details are available.", "output_preview": "hello"}, errors=[]),
        ui=UIModel(layout={}, metadata={"active_panel": "result_history", "app_language": "ko-KR"}),
    )
    vm = read_builder_shell_view_model(source)

    assert vm.active_workspace_id == "runtime_monitoring"
    assert vm.result_history is not None
    assert vm.result_history.visible is True
    assert vm.coordination.active_panel == "result_history"



def test_builder_shell_honors_explicit_open_visual_editor_action() -> None:
    source = _working_save()
    vm = read_builder_shell_view_model(source, selected_action_id="open_visual_editor")

    assert vm.active_workspace_id == "visual_editor"
    assert vm.coordination.active_panel == "graph"
    assert vm.coordination.panel_order[0] == "graph"


def test_builder_shell_honors_explicit_open_node_configuration_action() -> None:
    source = _working_save()
    vm = read_builder_shell_view_model(source, selected_action_id="open_node_configuration")

    assert vm.active_workspace_id == "node_configuration"
    assert vm.coordination.active_panel in {"inspector", "designer", "validation"}
    assert vm.coordination.panel_order[0] == vm.coordination.active_panel


def test_builder_shell_honors_explicit_open_runtime_monitoring_action() -> None:
    source = _working_save()
    vm = read_builder_shell_view_model(source, execution_record=_run(), selected_action_id="open_runtime_monitoring")

    assert vm.active_workspace_id == "runtime_monitoring"
    assert vm.coordination.active_panel == "execution"
    assert vm.coordination.panel_order[0] == "execution"


def test_builder_shell_projects_workspace_chain_review_when_visual_editor_still_holds() -> None:
    source = _working_save()
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_builder_shell_view_model(source, validation_report=report, execution_record=_run())

    assert vm.workspace_chain.chain_state == "hold_visual_editor"
    assert vm.workspace_chain.next_bottleneck_workspace == "visual_editor"
    assert vm.workspace_chain.recommended_action_id == "open_visual_editor"
    assert vm.workspace_chain.stages[0].workspace_id == "visual_editor"
    assert vm.workspace_chain.stages[1].workspace_id == "node_configuration"
    assert vm.workspace_chain.stages[2].workspace_id == "runtime_monitoring"


def test_builder_shell_projects_workspace_chain_review_when_runtime_monitoring_still_holds() -> None:
    source = _working_save()
    record = ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-live", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", status="running"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=2),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="running"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )

    vm = read_builder_shell_view_model(source, execution_record=record)

    assert vm.workspace_chain.chain_state == "hold_runtime_monitoring"
    assert vm.workspace_chain.next_bottleneck_workspace == "runtime_monitoring"
    assert vm.workspace_chain.recommended_action_id == "open_runtime_monitoring"


def test_builder_shell_projects_workspace_chain_stable_when_current_chain_is_locally_settled() -> None:
    vm = read_builder_shell_view_model(_run())

    assert vm.workspace_chain.chain_state == "workspace_chain_stable"
    assert vm.workspace_chain.next_bottleneck_workspace is None
    assert vm.workspace_chain.recommended_action_id is None


def test_builder_shell_projects_product_readiness_hold_for_first_success_setup(monkeypatch) -> None:
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "PERPLEXITY_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty-ready", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.product_readiness.review_state == "hold_first_success_setup"
    assert vm.product_readiness.next_bottleneck_stage == "first_success_setup"
    assert vm.product_readiness.stages[0].stage_id == "first_success_setup"
    assert vm.product_readiness.stages[0].stage_state in {"provider_setup_needed", "goal_entry_needed"}


def test_builder_shell_projects_product_readiness_hold_for_first_success_run(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    source = _working_save()
    report = ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="BLOCK", category="structural", severity="high", blocking=True, location="node:n1", message="Choose an AI model for step 1")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )

    vm = read_builder_shell_view_model(source, validation_report=report)

    assert vm.product_readiness.review_state == "hold_first_success_run"
    assert vm.product_readiness.next_bottleneck_stage == "first_success_run"
    assert vm.product_readiness.recommended_action_id == "open_node_configuration"
    assert vm.product_readiness.stages[1].stage_state == "fix_before_run"


def test_builder_shell_projects_product_readiness_hold_for_return_use() -> None:
    source = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-return-use", name="Reusable"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"beginner_first_success_achieved": True}),
    )

    vm = read_builder_shell_view_model(source)

    assert vm.product_readiness.review_state == "hold_return_use"
    assert vm.product_readiness.next_bottleneck_stage == "return_use"
    assert vm.product_readiness.recommended_action_id == "open_result_history"
    assert vm.product_readiness.stages[2].stage_state == "history_needed"


def test_builder_shell_projects_product_readiness_stable_for_historical_result_surface() -> None:
    vm = read_builder_shell_view_model(_run())

    assert vm.product_readiness.review_state == "product_surface_stable"
    assert vm.product_readiness.next_bottleneck_stage is None
    assert vm.product_readiness.recommended_action_id is None
    assert vm.product_readiness.stages[2].stage_state == "complete"
