from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.circuit_draft_preview import GraphViewModel
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ArtifactRecordCard, ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionIssue, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultCard, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.graph_workspace import GraphPreviewOverlay
from src.ui.visual_editor_workspace import read_visual_editor_workspace_view_model
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}, {"id": "n2"}], edges=[{"from": "n1", "to": "n2"}], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"selected_node_ids": ["n2"], "app_language": "ko-KR"}),
    )




def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001", name="Approved"),
        circuit=CircuitModel(nodes=[{"id": "n1"}, {"id": "n2"}], edges=[{"from": "n1", "to": "n2"}], entry="n1", outputs=[]),
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
        timeline=ExecutionTimelineModel(event_count=3),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )



def _run_with_focus() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-002", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=3),
        node_results=NodeResultsModel(results=[NodeResultCard(node_id="n2", status="failed")]),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(artifact_refs=[ArtifactRecordCard(artifact_id="a1", artifact_type="text", producer_node="n2")]),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _run_with_validation_issue() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-003", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(event_count=1),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[ExecutionIssue(issue_code="WARN_EXEC", category="validation", severity="medium", location="node:n2", message="warning")], errors=[]),
        observability=ExecutionObservabilityModel(),
    )

def _validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="WARN_LINK", category="structural", severity="medium", blocking=False, location="edge:n1->n2", message="warn")],
        blocking_count=0,
        warning_count=1,
        result="passed_with_findings",
    )


def test_visual_editor_workspace_projects_phase5_editor_surface() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-1",
        summary="add review node",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=["edge_0:n1->n2"],
    )

    vm = read_visual_editor_workspace_view_model(
        _working_save(),
        validation_report=_validation(),
        preview_overlay=overlay,
    )

    assert vm.workspace_status == "previewing"
    assert vm.storage_role == "working_save"
    assert vm.graph is not None
    assert vm.canvas_summary.node_count == 2
    assert vm.canvas_summary.selected_node_count == 1
    assert vm.canvas_summary.preview_change_count == 3
    assert vm.can_edit_graph is True
    assert vm.can_preview_changes is True
    assert vm.comparison_state.viewer_status == "ready"
    assert vm.action_schema.source_role == "working_save"
    assert vm.workspace_status_label == "변경 미리보기 중"


def test_visual_editor_workspace_enters_reviewing_when_commit_snapshot_has_execution_context() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run())
    assert vm.storage is not None
    assert vm.storage.execution_record_card is not None
    assert vm.storage.execution_record_card.run_id == "run-001"
    assert vm.workspace_status == "reviewing"


def test_visual_editor_workspace_treats_compare_runs_as_comparison_availability() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run())
    assert vm.comparison_state.can_open_diff is True
    assert vm.workspace_status_label == "Reviewing graph"


def test_visual_editor_workspace_propagates_execution_record_into_graph_focus() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())
    assert vm.graph is not None
    assert vm.graph.layout_hints is not None
    assert vm.graph.layout_hints.suggested_focus_node_id == "n2"


def test_visual_editor_workspace_propagates_execution_record_into_validation() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_validation_issue())
    assert vm.validation is not None
    assert vm.validation.source_mode == "execution_guard"
    assert vm.validation.summary.warning_count == 1
    assert vm.workspace_status == "reviewing"


def test_visual_editor_workspace_exposes_empty_state_explanation() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )

    vm = read_visual_editor_workspace_view_model(working)

    assert vm.workspace_status == "empty"
    assert vm.explanation == "Start by describing what you want to build, or open a starter workflow."


def test_visual_editor_workspace_exposes_suggested_actions_for_empty_state() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "ko-KR"}),
    )
    vm = read_visual_editor_workspace_view_model(working)

    assert vm.workspace_status == "empty"
    assert [action.action_id for action in vm.suggested_actions] == [
        "create_circuit_from_template",
        "open_provider_setup",
        "open_file_input",
    ]



def _blocking_validation() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="ERR_NODE", category="structural", severity="high", blocking=True, location="node:n2", message="missing provider")],
        blocking_count=1,
        warning_count=0,
        result="blocked",
    )


def test_visual_editor_workspace_exposes_local_actions_for_empty_state() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )

    vm = read_visual_editor_workspace_view_model(working)

    assert vm.readiness.posture == "creation"
    assert [action.action_id for action in vm.local_actions[:3]] == [
        "create_circuit_from_template",
        "open_provider_setup",
        "open_file_input",
    ]
    assert vm.focus_hint.hint_kind == "empty_canvas"
    assert vm.focus_hint.suggested_action_id == "create_circuit_from_template"


def test_visual_editor_workspace_surfaces_selection_focused_editing_guidance() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation())

    assert vm.workspace_status == "editing"
    assert vm.readiness.posture == "active_editing"
    assert vm.readiness.selected_object_count == 1
    assert vm.focus_hint.hint_kind == "node_selection"
    assert vm.focus_hint.target_ref == "node:n2"
    assert vm.focus_hint.suggested_action_id == "open_node_configuration"
    assert [action.action_id for action in vm.suggested_actions] == [
        "open_node_configuration",
        "run_current",
        "review_draft",
    ]


def test_visual_editor_workspace_prioritizes_repair_actions_when_blocked() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_blocking_validation())

    assert vm.workspace_status == "blocked"
    assert vm.readiness.posture == "repair"
    assert [action.action_id for action in vm.suggested_actions] == [
        "open_node_configuration",
        "request_revision",
        "open_provider_setup",
    ]
    assert vm.suggested_actions[1].enabled is False


def test_visual_editor_workspace_exposes_run_linked_review_posture_and_runtime_action() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())

    assert vm.workspace_status == "reviewing"
    assert vm.readiness.posture == "run_linked_review"
    assert vm.focus_hint.hint_kind == "run_focus"
    assert vm.focus_hint.target_ref == "node:n2"
    assert vm.focus_hint.suggested_action_id == "open_runtime_monitoring"
    assert any(action.action_id == "open_runtime_monitoring" and action.enabled for action in vm.local_actions)


def test_visual_editor_workspace_exposes_selection_summary_and_shortcuts_for_editing() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation())

    assert vm.selection_summary.selection_mode == "node"
    assert vm.selection_summary.target_ref == "node:n2"
    assert vm.selection_summary.label == "n2"
    assert vm.selection_summary.secondary_label == "unknown"
    assert vm.selection_summary.next_action_id == "open_node_configuration"
    assert vm.action_shortcuts[0].action.action_id == "open_node_configuration"
    assert vm.action_shortcuts[0].priority == "primary"
    assert vm.action_shortcuts[0].emphasis == "selection"


def test_visual_editor_workspace_selection_summary_counts_blocking_findings() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_blocking_validation())

    assert vm.selection_summary.selection_mode == "node"
    assert vm.selection_summary.related_blocking_count == 1
    assert vm.selection_summary.related_warning_count == 0
    assert vm.selection_summary.explanation == "선택한 스텝에 차단 문제가 있습니다. 먼저 구성을 열어 수정하세요."
    assert vm.action_shortcuts[0].emphasis == "repair"


def test_visual_editor_workspace_preview_shortcuts_prioritize_review_and_commit() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-2",
        summary="update review node",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=[],
    )

    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation(), preview_overlay=overlay)

    assert [shortcut.action.action_id for shortcut in vm.action_shortcuts] == [
        "review_draft",
        "commit_snapshot",
        "open_diff",
    ]
    assert vm.action_shortcuts[1].emphasis == "approval"


def test_visual_editor_workspace_exposes_run_focus_summary_and_shortcuts() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())

    assert vm.selection_summary.selection_mode == "run_focus"
    assert vm.selection_summary.target_ref == "node:n2"
    assert vm.selection_summary.label == "n2"
    assert vm.selection_summary.has_execution_history is True
    assert vm.selection_summary.next_action_id == "open_runtime_monitoring"
    assert [shortcut.action.action_id for shortcut in vm.action_shortcuts] == [
        "open_runtime_monitoring",
        "open_diff",
        "replay_latest",
    ]
    assert vm.action_shortcuts[0].emphasis == "runtime"



def test_visual_editor_workspace_handoff_prefers_designer_entry_for_empty_state() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )

    vm = read_visual_editor_workspace_view_model(working)

    assert vm.workspace_handoff.destination_workspace == "visual_editor"
    assert vm.workspace_handoff.destination_panel == "designer"
    assert vm.workspace_handoff.action_id == "create_circuit_from_template"
    assert vm.workspace_handoff.reason == "Stay in the visual editor and start from the designer entry surface."


def test_visual_editor_workspace_handoff_routes_blocked_selection_to_node_configuration() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_blocking_validation())

    assert vm.workspace_handoff.destination_workspace == "node_configuration"
    assert vm.workspace_handoff.destination_panel == "inspector"
    assert vm.workspace_handoff.target_ref == "node:n2"
    assert vm.workspace_handoff.action_id == "open_node_configuration"


def test_visual_editor_workspace_handoff_routes_previewing_to_diff_inside_editor() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-3",
        summary="preview changes",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=[],
    )

    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation(), preview_overlay=overlay)

    assert vm.workspace_handoff.destination_workspace == "visual_editor"
    assert vm.workspace_handoff.destination_panel == "diff"
    assert vm.workspace_handoff.action_id == "open_diff"


def test_visual_editor_workspace_handoff_routes_run_focus_to_runtime_monitoring() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())

    assert vm.workspace_handoff.destination_workspace == "runtime_monitoring"
    assert vm.workspace_handoff.destination_panel == "execution"
    assert vm.workspace_handoff.target_ref == "node:n2"
    assert vm.workspace_handoff.action_id == "open_runtime_monitoring"



def test_visual_editor_workspace_attention_targets_prioritize_repair_when_blocked() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_blocking_validation())

    assert vm.attention_targets[0].attention_kind == "repair_selection"
    assert vm.attention_targets[0].urgency == "high"
    assert vm.attention_targets[0].destination_workspace == "node_configuration"
    assert vm.attention_targets[0].destination_panel == "inspector"
    assert vm.attention_targets[0].action_id == "open_node_configuration"
    assert vm.attention_targets[0].blocking is True


def test_visual_editor_workspace_attention_targets_review_preview_changes() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-4",
        summary="preview more changes",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=[],
    )

    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation(), preview_overlay=overlay)

    assert vm.attention_targets[0].attention_kind == "preview_review"
    assert vm.attention_targets[0].urgency == "medium"
    assert vm.attention_targets[0].destination_workspace == "visual_editor"
    assert vm.attention_targets[0].destination_panel == "diff"
    assert vm.attention_targets[0].summary == "커밋하기 전에 diff를 열어 대기 중인 그래프 변경 2개를 확인하세요."


def test_visual_editor_workspace_attention_targets_raise_runtime_investigation_for_run_focus() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())

    assert vm.attention_targets[0].attention_kind == "runtime_investigation"
    assert vm.attention_targets[0].urgency == "high"
    assert vm.attention_targets[0].destination_workspace == "runtime_monitoring"
    assert vm.attention_targets[0].action_id == "open_runtime_monitoring"


def test_visual_editor_workspace_attention_targets_keep_empty_state_in_designer_entry() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )

    vm = read_visual_editor_workspace_view_model(working)

    assert vm.attention_targets[0].attention_kind == "start"
    assert vm.attention_targets[0].destination_workspace == "visual_editor"
    assert vm.attention_targets[0].destination_panel == "designer"
    assert vm.attention_targets[0].action_id == "create_circuit_from_template"



def test_visual_editor_workspace_progress_stages_start_in_creation_state_when_empty() -> None:
    working = WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": "en-US"}),
    )

    vm = read_visual_editor_workspace_view_model(working)

    assert [stage.stage_id for stage in vm.progress_stages] == ["configure", "review", "run"]
    assert [stage.state for stage in vm.progress_stages] == ["current", "blocked", "blocked"]
    assert vm.progress_stages[0].action_id == "create_circuit_from_template"
    assert vm.closure_barriers[0].barrier_kind == "start"
    assert vm.closure_barriers[0].action_id == "create_circuit_from_template"



def test_visual_editor_workspace_progress_stages_and_barrier_prioritize_preview_review() -> None:
    overlay = GraphPreviewOverlay(
        overlay_id="preview-5",
        summary="preview changes",
        added_node_ids=["n3"],
        updated_node_ids=["n2"],
        removed_edge_ids=[],
    )

    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation(), preview_overlay=overlay)

    assert [stage.state for stage in vm.progress_stages] == ["ready", "current", "blocked"]
    assert vm.progress_stages[1].action_id == "open_diff"
    assert vm.closure_barriers[0].barrier_kind == "pending_review"
    assert vm.closure_barriers[0].action_id == "open_diff"



def test_visual_editor_workspace_progress_stages_show_run_current_for_run_focus_review() -> None:
    vm = read_visual_editor_workspace_view_model(_commit(), execution_record=_run_with_focus())

    assert [stage.state for stage in vm.progress_stages] == ["ready", "ready", "current"]
    assert vm.progress_stages[2].action_id == "open_runtime_monitoring"
    assert vm.closure_barriers[0].barrier_kind == "runtime_focus"
    assert vm.closure_barriers[0].action_id == "open_runtime_monitoring"



def test_visual_editor_workspace_editing_progress_and_barrier_follow_attention() -> None:
    vm = read_visual_editor_workspace_view_model(_working_save(), validation_report=_validation())

    assert [stage.state for stage in vm.progress_stages] == ["current", "ready", "ready"]
    assert vm.progress_stages[0].action_id == "open_node_configuration"
    assert vm.progress_stages[1].action_id == "review_draft"
    assert vm.progress_stages[2].action_id == "run_current"
    assert vm.closure_barriers[0].barrier_kind == "follow_attention"
    assert vm.closure_barriers[0].action_id == "open_node_configuration"
