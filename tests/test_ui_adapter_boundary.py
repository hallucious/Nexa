from __future__ import annotations


from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import CircuitDraftPreview, ConfirmationPreview, GraphViewModel, SummaryCard, StructuralPreview
from src.designer.models.circuit_patch_plan import ChangeScope, CircuitPatchPlan, PatchOperation
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.designer.models.designer_intent import ConstraintSet, DesignerIntent, ObjectiveSpec, TargetScope
from src.designer.models.designer_session_state_card import AvailableResources, ConversationContext, CurrentSelectionState, DesignerSessionStateCard, SessionTargetScope, WorkingSaveReality
from src.designer.models.validation_precheck import AmbiguityAssessmentReport, CostAssessmentReport, EvaluatedScope, ResolutionReport, ValidationPrecheck, ValidityReport
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.adapter import NexaUIViewAdapter
from src.ui.action_schema import read_builder_action_schema
from src.ui.panel_coordination import read_panel_coordination_state
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.graph_workspace import GraphPreviewOverlay
from src.engine.execution_event import ExecutionEvent


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
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


def test_ui_adapter_routes_read_models_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    preview = GraphPreviewOverlay(overlay_id="preview-001", summary="test preview")

    graph_vm = adapter.read_graph_view_model(_working_save(), preview_overlay=preview)
    storage_vm = adapter.read_storage_view_model(_working_save())
    diff_vm = adapter.read_diff_view_model(diff_mode="draft_vs_commit", source=_working_save(), target=_commit())

    assert graph_vm.storage_role == "execution_record"
    assert storage_vm.active_storage_role == "working_save"
    assert diff_vm.viewer_status == "ready"



def test_ui_adapter_routes_execution_trace_and_artifact_read_models_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    live_events = [
        ExecutionEvent("execution_started", "run-001", None, 0, {}),
        ExecutionEvent("node_started", "run-001", "n1", 5, {"stage": "provider"}),
    ]

    execution_vm = adapter.read_execution_panel_view_model(_working_save(), live_events=live_events)
    trace_vm = adapter.read_trace_timeline_view_model(_run(), live_events=live_events)
    artifact_vm = adapter.read_artifact_viewer_view_model(_run())

    assert execution_vm.source_mode == "live_execution"
    assert trace_vm.source_mode == "live_event_stream"
    assert artifact_vm.viewer_status in {"ready", "partial"}



def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="MISSING_INPUT", category="structural", severity="high", blocking=True, location="node:n1", message="missing input")],
        blocking_count=1,
        warning_count=0,
        result="failed",
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
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage="awaiting_decision",
        final_outcome="pending",
        precheck_status="pass",
    )


def test_ui_adapter_routes_inspector_validation_and_designer_read_models_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    inspector_vm = adapter.read_inspector_panel_view_model(_working_save(), selected_ref="node:n1", validation_report=_validation_report())
    validation_vm = adapter.read_validation_panel_view_model(_working_save(), validation_report=_validation_report())
    designer_vm = adapter.read_designer_panel_view_model(
        _working_save(),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=_approval(),
    )
    assert inspector_vm.object_type == "node"
    assert validation_vm.overall_status == "blocked"
    assert designer_vm.intent_state.intent_id == "intent-001"


def test_ui_adapter_routes_builder_shell_coordination_and_action_schema_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    graph_vm = adapter.read_graph_view_model(_working_save())
    storage_vm = adapter.read_storage_view_model(_working_save())
    validation_vm = adapter.read_validation_panel_view_model(_working_save(), validation_report=_validation_report())
    execution_vm = adapter.read_execution_panel_view_model(_working_save(), execution_record=_run())
    designer_vm = adapter.read_designer_panel_view_model(_working_save(), approval_flow=_approval())

    action_vm = adapter.read_builder_action_schema_view(
        _working_save(),
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
        designer_view=designer_vm,
    )
    coordination_vm = adapter.read_panel_coordination_state_view(
        _working_save(),
        graph_view=graph_vm,
        storage_view=storage_vm,
        execution_view=execution_vm,
        validation_view=validation_vm,
        designer_view=designer_vm,
    )
    shell_vm = adapter.read_builder_shell_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
    )

    assert action_vm.source_role == "working_save"
    assert coordination_vm.storage_role == "working_save"
    assert shell_vm.storage_role == "working_save"


def test_ui_adapter_routes_phase5_workspace_integrations_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    preview = GraphPreviewOverlay(overlay_id="preview-001", summary="test preview")

    visual_vm = adapter.read_visual_editor_workspace_view_model(
        _working_save(),
        validation_report=_validation_report(),
        preview_overlay=preview,
    )
    config_vm = adapter.read_node_configuration_workspace_view_model(
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
    monitoring_vm = adapter.read_runtime_monitoring_workspace_view_model(
        _commit(),
        execution_record=_run(),
    )

    assert visual_vm.storage_role == "working_save"
    assert config_vm.storage_role == "working_save"
    assert monitoring_vm.execution is not None


def test_ui_adapter_routes_builder_workflow_layers_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )

    proposal_vm = adapter.read_proposal_commit_workflow_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation_report(),
        execution_record=_run(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-001", summary="test preview"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=DesignerApprovalFlowState(
            approval_id="approval-002",
            intent_ref="intent-001",
            patch_ref="patch-001",
            precheck_ref="pre-001",
            preview_ref="preview-001",
            current_stage="awaiting_decision",
            final_outcome="approved_for_commit",
            precheck_status="pass",
        ),
    )
    launch_vm = adapter.read_execution_launch_workflow_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
    )
    hub_vm = adapter.read_builder_workflow_hub_view_model(
        _working_save(),
        selected_ref="node:n1",
        validation_report=_validation_report(),
        execution_record=_run(),
        preview_overlay=GraphPreviewOverlay(overlay_id="preview-001", summary="test preview"),
        session_state_card=_session_card(),
        intent=_intent(),
        patch_plan=_patch(),
        precheck=_precheck(),
        preview=_preview(),
        approval_flow=DesignerApprovalFlowState(
            approval_id="approval-002",
            intent_ref="intent-001",
            patch_ref="patch-001",
            precheck_ref="pre-001",
            preview_ref="preview-001",
            current_stage="awaiting_decision",
            final_outcome="approved_for_commit",
            precheck_status="pass",
        ),
    )

    assert proposal_vm.storage_role == "working_save"
    assert launch_vm.storage_role == "working_save"
    assert hub_vm.proposal_commit is not None
    assert hub_vm.execution_launch is not None



def test_ui_adapter_routes_builder_command_and_interaction_layers_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    workflow_hub = adapter.read_builder_workflow_hub_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
    )
    command_routing = adapter.read_builder_command_routing_view_model(
        _working_save(),
        action_schema=workflow_hub.shell.action_schema,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
    )
    interaction_transition = adapter.read_builder_interaction_transition_view_model(
        _working_save(),
        command_routing=command_routing,
        workflow_hub=workflow_hub,
        coordination_state=workflow_hub.shell.coordination,
        selected_action_id="run_current",
    )
    interaction_hub = adapter.read_builder_interaction_hub_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
        selected_action_id="run_current",
    )

    assert command_routing.source_role == "working_save"
    assert interaction_transition.target_workspace_id == "runtime_monitoring"
    assert interaction_hub.command_routing is not None


def test_ui_adapter_routes_builder_dispatch_and_lifecycle_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    interaction_hub_vm = adapter.read_builder_interaction_hub_view_model(
        _working_save(),
        validation_report=_validation_report(),
        execution_record=_run(),
    )
    intent_emission_vm = adapter.read_intent_emission_view_model(_working_save(), interaction_hub=interaction_hub_vm)
    dispatch_contract_vm = adapter.read_command_dispatch_contract_view_model(
        _working_save(),
        interaction_hub=interaction_hub_vm,
        intent_emission=intent_emission_vm,
    )
    lifecycle_vm = adapter.read_interaction_lifecycle_view_model(
        _working_save(),
        interaction_hub=interaction_hub_vm,
        dispatch_contract=dispatch_contract_vm,
    )
    dispatch_hub_vm = adapter.read_builder_dispatch_hub_view_model(_working_save(), interaction_hub=interaction_hub_vm)

    assert intent_emission_vm.source_role == "working_save"
    assert dispatch_contract_vm.source_role == "working_save"
    assert lifecycle_vm.source_role == "working_save"
    assert dispatch_hub_vm.source_role == "working_save"



def test_ui_adapter_routes_execution_adapter_and_state_change_layers_through_stable_boundary() -> None:
    adapter = NexaUIViewAdapter(
        latest_working_save=_working_save(),
        latest_commit_snapshot=_commit(),
        latest_execution_record=_run(),
    )
    dispatch_hub_vm = adapter.read_builder_dispatch_hub_view_model(_working_save())
    execution_adapter_vm = adapter.read_command_execution_adapter_view_model(_working_save(), dispatch_hub=dispatch_hub_vm)
    state_change_vm = adapter.read_interaction_state_change_view_model(
        _working_save(),
        dispatch_hub=dispatch_hub_vm,
        execution_adapters=execution_adapter_vm,
    )
    execution_hub_vm = adapter.read_builder_execution_adapter_hub_view_model(_working_save(), dispatch_hub=dispatch_hub_vm)

    assert execution_adapter_vm.source_role == "working_save"
    assert state_change_vm.source_role == "working_save"
    assert execution_hub_vm.source_role == "working_save"
